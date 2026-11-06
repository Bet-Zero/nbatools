from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from nbatools.commands._constants import (
    STAT_ALIASES,
    STAT_EQUALITY_OPERATOR,
    STAT_PATTERN,
    contains_boolean_or,
)


@dataclass(frozen=True)
class ConditionNode:
    stat: str
    min_value: float | None = None
    max_value: float | None = None
    source_text: str = ""
    governs_following_stats: bool = False


@dataclass(frozen=True)
class AndNode:
    left: Node
    right: Node


@dataclass(frozen=True)
class OrNode:
    left: Node
    right: Node


Node = ConditionNode | AndNode | OrNode


@dataclass(frozen=True)
class Token:
    kind: str
    value: object | None = None
    source_text: str = ""


class BooleanQueryParseError(ValueError):
    pass


def normalize_condition_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def detect_stat(text: str) -> str | None:
    normalized = normalize_condition_text(text)
    for key in sorted(STAT_ALIASES.keys(), key=len, reverse=True):
        if normalized == key:
            return STAT_ALIASES[key]
    return None


def _parse_threshold_match(
    value_text: str, stat_text: str, mode: str, epsilon: float
) -> ConditionNode:
    value = 0.0 if value_text in {"zero", "no"} else float(value_text)
    stat = detect_stat(stat_text)
    if stat is None:
        raise BooleanQueryParseError(f"Unsupported stat phrase: {stat_text}")

    if mode == "eq":
        return ConditionNode(stat=stat, min_value=value, max_value=value)

    if mode == "min":
        return ConditionNode(
            stat=stat,
            min_value=value + epsilon,
            max_value=None,
            source_text=f"{mode}:{value_text}:{stat_text}",
        )

    return ConditionNode(
        stat=stat,
        min_value=None,
        max_value=value - epsilon,
        source_text=f"{mode}:{value_text}:{stat_text}",
    )


def _consume_owned_condition(text: str, *, team=None, opponent=None):
    """Reuse the context readers, retaining their owner and complete text span."""
    from nbatools.commands._parse_helpers import extract_opponent_points_allowed_conditions
    from nbatools.commands._player_game_context import (
        _OPP_STAT_BOUND,
        _opponent_bounds,
        team_noun_stat_conditions,
        team_subject_stat_conditions,
    )

    # Noun owners use exactly the same bound grammar as player statistics.
    # Remove only the owner token while reading this one leaf, then restore
    # its span and prefixed column; no query-wide phrase rewriting occurs.
    candidates = []
    noun = re.search(
        rf"\b(?P<owner>(?:(?:the|his|her|their|our)\s+)?team(?:'s)?|opponents?(?:'s?|s')?)\s+(?P<stat>{STAT_PATTERN})\b",
        text,
    )
    if noun:
        a = noun.start("owner")
        clean = text[:a] + text[noun.start("stat") :]
        consumed = consume_condition_at(clean, 0, team=team, opponent=opponent)
        removed = noun.start("stat") - a
        if consumed and consumed[1] + removed >= noun.end("stat"):
            leaf, end = consumed
            end += removed
            side = "opponent" if noun.group("owner").startswith("opponent") else "team"
            candidates.append(
                (
                    end,
                    f"{side}_{leaf.stat}",
                    dict(min_value=leaf.min_value, max_value=leaf.max_value),
                    False,
                )
            )
    noun_spans = {(c["start"], c["end"]) for c in team_noun_stat_conditions(text)}
    opponent_noun_spans = {m.span() for m in _OPP_STAT_BOUND.finditer(text)}
    for item in team_subject_stat_conditions(
        text,
        tuple(x for x in (team, *(opponent if isinstance(opponent, list) else [opponent])) if x),
    ):
        if item["start"] != 0:
            continue
        owner = item["team"]
        if owner == "TEAM" or owner == team:
            stat = "team_" + item["stat"]
        elif isinstance(opponent, str) and owner == opponent:
            stat = "opponent_" + item["stat"]
        else:
            raise BooleanQueryParseError(
                "Named statistical owner needs an explicit common team/opponent scope"
            )
        candidates.append((item["end"], stat, item, (item["start"], item["end"]) not in noun_spans))
    for span, item in _opponent_bounds(text):
        if span.span()[0] == 0:
            candidates.append(
                (span.span()[1], item["stat"], item, span.span() not in opponent_noun_spans)
            )
    for item in extract_opponent_points_allowed_conditions(text):
        if item["start"] == 0:
            candidates.append(
                (
                    item["end"],
                    item["stat"],
                    item,
                    (item["start"], item["end"]) not in opponent_noun_spans,
                )
            )
    # The existing team verbal grammar also describes the explicitly opposing
    # side. Reuse its bounds rather than strip that subject and read a player stat.
    lead = re.match(r"(?:the\s+)?(?:opponents?|other\s+team|opposing\s+team)\s+", text)
    if lead:
        replacement = "team " + text[lead.end() :]
        for item in team_subject_stat_conditions(replacement):
            if item["start"] == 0:
                candidates.append(
                    (item["end"] + lead.end() - 5, "opponent_" + item["stat"], item, True)
                )
    if not candidates:
        return None
    end, stat, item, governs = max(candidates, key=lambda c: c[0])
    return ConditionNode(stat, item["min_value"], item["max_value"], text[:end], governs), end


def consume_condition_at(
    text: str, start_index: int, *, team=None, opponent=None
) -> tuple[ConditionNode, int] | None:
    remaining = text[start_index:]
    owned = _consume_owned_condition(remaining, team=team, opponent=opponent)
    if owned:
        return owned[0], start_index + owned[1]

    patterns = [
        (rf"^{STAT_EQUALITY_OPERATOR}\s*(\d+(?:\.\d+)?|zero|no)\s+{STAT_PATTERN}\b", "eq", 0.0),
        (
            rf"^{STAT_PATTERN}\s*{STAT_EQUALITY_OPERATOR}\s*(\d+(?:\.\d+)?|zero|no)\b",
            "reverse_eq",
            0.0,
        ),
        (
            rf"^between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "between",
            0.0,
        ),
        (
            rf"^(?:over|above|exceed(?:s|ed)?)\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "min",
            0.0001,
        ),
        (
            rf"^at least\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "min",
            0.0,
        ),
        (
            rf"^under\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
        ),
        (
            rf"^less than\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
        ),
    ]

    for pattern, mode, epsilon in patterns:
        m = re.match(pattern, remaining)
        if not m:
            continue

        matched_text = m.group(0)
        if mode == "between":
            low = float(m.group(1))
            high = float(m.group(2))
            if low > high:
                low, high = high, low

            stat = detect_stat(m.group(3))
            if stat is None:
                raise BooleanQueryParseError(f"Unsupported stat phrase: {m.group(3)}")

            node = ConditionNode(
                stat=stat,
                min_value=low,
                max_value=high,
                source_text=matched_text,
            )
            return node, start_index + len(matched_text)

        node = (
            _parse_threshold_match(m.group(2), m.group(1), "eq", epsilon)
            if mode == "reverse_eq"
            else _parse_threshold_match(m.group(1), m.group(2), mode, epsilon)
        )
        node = ConditionNode(
            stat=node.stat,
            min_value=node.min_value,
            max_value=node.max_value,
            source_text=matched_text,
        )
        return node, start_index + len(matched_text)

    # Share the established bound vocabulary (reverse bounds, ceilings,
    # inclusive shorthand) instead of maintaining a second operator list.
    from nbatools.commands._parse_helpers import extract_threshold_conditions

    shared = [c for c in extract_threshold_conditions(remaining) if c["start"] == 0]
    if shared:
        bound = max(shared, key=lambda c: c["end"])
        return ConditionNode(
            stat=bound["stat"],
            min_value=bound["min_value"],
            max_value=bound["max_value"],
            source_text=bound["text"],
        ), start_index + bound["end"]
    bare = re.match(rf"^(\d+(?:\.\d+)?|zero|no)(\+)?\s+{STAT_PATTERN}\b", remaining)
    if bare:
        value = 0.0 if bare.group(1) in ("zero", "no") else float(bare.group(1))
        return ConditionNode(
            stat=detect_stat(bare.group(3)),
            min_value=value,
            max_value=0.0 if value == 0 and not bare.group(2) else None,
            source_text=bare.group(0),
        ), start_index + bare.end()

    return None


def tokenize_condition_expression(text: str, *, team=None, opponent=None) -> list[Token]:
    normalized = normalize_condition_text(text)
    tokens: list[Token] = []
    i = 0

    while i < len(normalized):
        ch = normalized[i]

        if ch.isspace():
            i += 1
            continue

        if ch == "(":
            tokens.append(Token(kind="LPAREN", source_text="("))
            i += 1
            continue

        if ch == ")":
            tokens.append(Token(kind="RPAREN", source_text=")"))
            i += 1
            continue

        if normalized.startswith("and", i):
            before_ok = i == 0 or normalized[i - 1].isspace() or normalized[i - 1] == "("
            after_idx = i + 3
            after_ok = (
                after_idx == len(normalized)
                or normalized[after_idx].isspace()
                or normalized[after_idx] == ")"
            )
            if before_ok and after_ok:
                tokens.append(Token(kind="AND", source_text="and"))
                i = after_idx
                continue

        if normalized.startswith("or", i):
            before_ok = i == 0 or normalized[i - 1].isspace() or normalized[i - 1] == "("
            after_idx = i + 2
            after_ok = (
                after_idx == len(normalized)
                or normalized[after_idx].isspace()
                or normalized[after_idx] == ")"
            )
            if before_ok and after_ok:
                tokens.append(Token(kind="OR", source_text="or"))
                i = after_idx
                continue

        join = re.match(r"(?:with|when|while|where)\b\s*", normalized[i:])
        if join:
            if tokens and tokens[-1].kind in {"CONDITION", "RPAREN"}:
                tokens.append(Token(kind="AND", source_text=join.group()))
            i += join.end()
            continue
        consumed = consume_condition_at(normalized, i, team=team, opponent=opponent)
        if consumed is not None:
            node, new_i = consumed
            tokens.append(Token(kind="CONDITION", value=node, source_text=node.source_text))
            i = new_i
            continue

        snippet = normalized[i : i + 40]
        raise BooleanQueryParseError(f"Could not parse condition expression near: '{snippet}'")

    # A governing verbal subject can own a list ("team had 120 points and
    # 30 assists"). Until complete elided lists are bound, never reinterpret
    # that second statistic as the player's. Explicit noun owners remain
    # per-leaf and do not make a separate player-stat sibling inherit them.
    governed = [False]
    for token in tokens:
        if token.kind == "LPAREN":
            governed.append(governed[-1])
        elif token.kind == "RPAREN" and len(governed) > 1:
            governed.pop()
        elif token.kind == "CONDITION":
            leaf = token.value
            owned = leaf.stat.startswith(("team_", "opponent_"))
            if not owned and governed[-1]:
                raise BooleanQueryParseError(
                    "Elided team/opponent stat lists are not yet supported"
                )
            governed[-1] = leaf.governs_following_stats
    return tokens


class _TokenStream:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def peek(self) -> Token | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def consume(self) -> Token:
        token = self.peek()
        if token is None:
            raise BooleanQueryParseError("Unexpected end of expression")
        self.index += 1
        return token

    def expect(self, kind: str) -> Token:
        token = self.peek()
        if token is None:
            raise BooleanQueryParseError(f"Expected {kind} but reached end of expression")
        if token.kind != kind:
            raise BooleanQueryParseError(f"Expected {kind} but found {token.kind}")
        return self.consume()


def parse_condition_expression(tokens: list[Token]) -> Node:
    if not tokens:
        raise BooleanQueryParseError("Empty condition expression")

    stream = _TokenStream(tokens)

    def parse_expression() -> Node:
        return parse_or()

    def parse_or() -> Node:
        node = parse_and()
        while True:
            token = stream.peek()
            if token is None or token.kind != "OR":
                break
            stream.consume()
            right = parse_and()
            node = OrNode(left=node, right=right)
        return node

    def parse_and() -> Node:
        node = parse_primary()
        while True:
            token = stream.peek()
            if token is None or token.kind != "AND":
                break
            stream.consume()
            right = parse_primary()
            node = AndNode(left=node, right=right)
        return node

    def parse_primary() -> Node:
        token = stream.peek()
        if token is None:
            raise BooleanQueryParseError("Expected condition or '(' but reached end of expression")

        if token.kind == "LPAREN":
            stream.consume()
            node = parse_expression()
            stream.expect("RPAREN")
            return node

        if token.kind == "CONDITION":
            return stream.consume().value  # type: ignore[return-value]

        raise BooleanQueryParseError(f"Expected condition or '(' but found {token.kind}")

    root = parse_expression()

    if stream.peek() is not None:
        raise BooleanQueryParseError(f"Unexpected token after expression: {stream.peek().kind}")

    return root


def parse_condition_text(text: str, *, team=None, opponent=None) -> Node:
    tokens = tokenize_condition_expression(text, team=team, opponent=opponent)
    return parse_condition_expression(tokens)


def condition_tree_leaves(node: Node) -> tuple[ConditionNode, ...]:
    """Return the predicates of the existing tree without flattening its logic."""
    if isinstance(node, ConditionNode):
        return (node,)
    return condition_tree_leaves(node.left) + condition_tree_leaves(node.right)


def prepare_player_condition_frame(node: Node, df: pd.DataFrame) -> pd.DataFrame:
    """Attach same-game context before either branch; unknown is not a zero."""
    from nbatools.commands.data_utils import attach_player_game_context_stats
    from nbatools.commands.player_game_finder import ALLOWED_STATS

    wanted = {leaf.stat for leaf in condition_tree_leaves(node)}
    if wanted - ALLOWED_STATS.keys():
        raise BooleanQueryParseError(
            f"Unsupported player-game statistics: {sorted(wanted - ALLOWED_STATS.keys())}"
        )
    frame = attach_player_game_context_stats(df, wanted, strict=True)
    required = {"player_id", *wanted}
    if any(
        c not in frame or pd.to_numeric(frame[c], errors="coerce").isna().any() for c in required
    ):
        raise FileNotFoundError(
            "Requested Boolean predicate or player identity has unknown coverage"
        )
    return frame


def require_player_boolean_scope(df: pd.DataFrame, scope: dict) -> None:
    """Do not let a missing requested scope value drop rows before the tree."""
    for column, keys in {
        "team_abbr": ("team",),
        "opponent_team_abbr": ("opponent",),
        "game_date": ("start_date", "end_date"),
        "is_home": ("home_only",),
        "is_away": ("away_only",),
        "wl": ("wins_only", "losses_only"),
    }.items():
        if any(scope.get(key) for key in keys):
            if column not in df or df[column].isna().any():
                raise FileNotFoundError(f"Requested Boolean scope has unknown {column} coverage")


def condition_node_to_mask(node: ConditionNode, df: pd.DataFrame) -> pd.Series:
    if node.stat not in df.columns:
        raise BooleanQueryParseError(f"Condition stat '{node.stat}' not found in result columns")

    values = pd.to_numeric(df[node.stat], errors="coerce")
    mask = pd.Series(True, index=df.index)

    if node.min_value is not None:
        mask &= values >= node.min_value

    if node.max_value is not None:
        mask &= values <= node.max_value

    mask = mask.fillna(False)
    return mask


def evaluate_condition_tree_to_mask(node: Node, df: pd.DataFrame) -> pd.Series:
    if isinstance(node, ConditionNode):
        return condition_node_to_mask(node, df)

    if isinstance(node, AndNode):
        return evaluate_condition_tree_to_mask(node.left, df) & evaluate_condition_tree_to_mask(
            node.right, df
        )

    if isinstance(node, OrNode):
        return evaluate_condition_tree_to_mask(node.left, df) | evaluate_condition_tree_to_mask(
            node.right, df
        )

    raise BooleanQueryParseError(f"Unsupported node type: {type(node).__name__}")


def evaluate_condition_tree(node: Node, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    mask = evaluate_condition_tree_to_mask(node, df)
    return df[mask].copy()


def expression_contains_boolean_ops(text: str) -> bool:
    normalized = normalize_condition_text(text)
    return (
        (" and " in normalized)
        or contains_boolean_or(normalized)
        or ("(" in normalized)
        or (")" in normalized)
    )


def has_owned_conjunction(text: str) -> bool:
    """Identify the existing owned-stat grammar beside an AND condition."""
    if not re.search(r"\band\b", text):
        return False
    from nbatools.commands._parse_helpers import extract_opponent_points_allowed_conditions
    from nbatools.commands._player_game_context import (
        _opponent_bounds,
        team_subject_stat_conditions,
    )

    return bool(
        team_subject_stat_conditions(text)
        or _opponent_bounds(text)
        or extract_opponent_points_allowed_conditions(text)
        or re.search(rf"\b(?:team|opponents?)(?:'s)?\s+{STAT_PATTERN}\b", text)
    )


def boolean_filter_mode(text: str, *, team=None, opponent=None) -> str | None:
    """Describe how parsed threshold filters are combined for consumers."""
    operator_kinds = {
        token.kind
        for token in tokenize_condition_expression(text, team=team, opponent=opponent)
        if token.kind in {"AND", "OR"}
    }
    if operator_kinds == {"OR"}:
        return "any"
    if operator_kinds == {"AND"}:
        return "all"
    if operator_kinds == {"AND", "OR"}:
        return "grouped"
    return None


def tree_to_dict(node: Node) -> dict:
    if isinstance(node, ConditionNode):
        return {
            "type": "condition",
            "stat": node.stat,
            "min_value": node.min_value,
            "max_value": node.max_value,
            "source_text": node.source_text,
        }

    if isinstance(node, AndNode):
        return {
            "type": "and",
            "left": tree_to_dict(node.left),
            "right": tree_to_dict(node.right),
        }

    if isinstance(node, OrNode):
        return {
            "type": "or",
            "left": tree_to_dict(node.left),
            "right": tree_to_dict(node.right),
        }

    raise BooleanQueryParseError(f"Unsupported node type: {type(node).__name__}")
