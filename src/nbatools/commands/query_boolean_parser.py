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


def consume_condition_at(text: str, start_index: int) -> tuple[ConditionNode, int] | None:
    remaining = text[start_index:]

    patterns = [
        (rf"^{STAT_EQUALITY_OPERATOR}\s*(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b", "eq", 0.0),
        (rf"^{STAT_PATTERN}\s*{STAT_EQUALITY_OPERATOR}\s*(\d+(?:\.\d+)?)\b", "reverse_eq", 0.0),
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


def condition_tree_leaves(node: Node) -> tuple[ConditionNode, ...]:
    """Return the predicates of the existing tree without flattening its logic."""
    if isinstance(node, ConditionNode):
        return (node,)
    return condition_tree_leaves(node.left) + condition_tree_leaves(node.right)


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


def boolean_filter_mode(text: str) -> str | None:
    """Describe how parsed threshold filters are combined for consumers."""
    operator_kinds = {
        token.kind for token in tokenize_condition_expression(text) if token.kind in {"AND", "OR"}
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
