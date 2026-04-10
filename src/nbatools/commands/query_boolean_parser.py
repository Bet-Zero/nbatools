from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

STAT_ALIASES = {
    "points": "pts",
    "point": "pts",
    "pts": "pts",
    "rebounds": "reb",
    "rebound": "reb",
    "reb": "reb",
    "assists": "ast",
    "assist": "ast",
    "ast": "ast",
    "steals": "stl",
    "steal": "stl",
    "stl": "stl",
    "blocks": "blk",
    "block": "blk",
    "blk": "blk",
    "threes made": "fg3m",
    "three pointers made": "fg3m",
    "three-point makes": "fg3m",
    "threes": "fg3m",
    "3pm": "fg3m",
    "3s": "fg3m",
    "fg3m": "fg3m",
    "turnovers": "tov",
    "turnover": "tov",
    "tov": "tov",
}


STAT_PATTERN = (
    r"(points|point|pts|rebounds|rebound|reb|assists|assist|ast|"
    r"steals|steal|stl|blocks|block|blk|"
    r"threes made|three pointers made|three-point makes|threes|3pm|3s|fg3m|"
    r"turnovers|turnover|tov)"
)


@dataclass(frozen=True)
class ConditionNode:
    stat: str
    min_value: float | None = None
    max_value: float | None = None
    source_text: str = ""


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
    value = float(value_text)
    stat = detect_stat(stat_text)
    if stat is None:
        raise BooleanQueryParseError(f"Unsupported stat phrase: {stat_text}")

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


def consume_condition_at(text: str, start_index: int) -> tuple[ConditionNode, int] | None:
    remaining = text[start_index:]

    patterns = [
        (
            rf"^between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "between",
            0.0,
        ),
        (
            rf"^over\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
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

        node = _parse_threshold_match(m.group(1), m.group(2), mode, epsilon)
        node = ConditionNode(
            stat=node.stat,
            min_value=node.min_value,
            max_value=node.max_value,
            source_text=matched_text,
        )
        return node, start_index + len(matched_text)

    return None


def tokenize_condition_expression(text: str) -> list[Token]:
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

        consumed = consume_condition_at(normalized, i)
        if consumed is not None:
            node, new_i = consumed
            tokens.append(Token(kind="CONDITION", value=node, source_text=node.source_text))
            i = new_i
            continue

        snippet = normalized[i : i + 40]
        raise BooleanQueryParseError(f"Could not parse condition expression near: '{snippet}'")

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


def parse_condition_text(text: str) -> Node:
    tokens = tokenize_condition_expression(text)
    return parse_condition_expression(tokens)


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
        or (" or " in normalized)
        or ("(" in normalized)
        or (")" in normalized)
    )


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
