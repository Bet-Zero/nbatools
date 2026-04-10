import pandas as pd
import pytest

from nbatools.commands.query_boolean_parser import (
    AndNode,
    BooleanQueryParseError,
    ConditionNode,
    OrNode,
    condition_node_to_mask,
    evaluate_condition_tree,
    expression_contains_boolean_ops,
    parse_condition_text,
    tokenize_condition_expression,
    tree_to_dict,
)


def test_expression_contains_boolean_ops_detects_and_or_parens():
    assert expression_contains_boolean_ops("over 25 points and over 10 rebounds") is True
    assert expression_contains_boolean_ops("over 25 points or over 10 rebounds") is True
    assert expression_contains_boolean_ops("(over 25 points)") is True
    assert expression_contains_boolean_ops("over 25 points") is False


def test_tokenize_single_condition():
    tokens = tokenize_condition_expression("over 25 points")
    assert len(tokens) == 1
    assert tokens[0].kind == "CONDITION"
    node = tokens[0].value
    assert isinstance(node, ConditionNode)
    assert node.stat == "pts"
    assert node.min_value is not None
    assert node.max_value is None


def test_tokenize_between_condition_as_single_token():
    tokens = tokenize_condition_expression("between 20 and 30 points")
    assert len(tokens) == 1
    assert tokens[0].kind == "CONDITION"
    node = tokens[0].value
    assert isinstance(node, ConditionNode)
    assert node.stat == "pts"
    assert node.min_value == 20
    assert node.max_value == 30


def test_tokenize_parens_and_boolean_ops():
    tokens = tokenize_condition_expression(
        "(over 25 points and over 10 rebounds) or over 15 assists"
    )
    kinds = [t.kind for t in tokens]
    assert kinds == ["LPAREN", "CONDITION", "AND", "CONDITION", "RPAREN", "OR", "CONDITION"]


def test_parse_and_expression():
    tree = parse_condition_text("over 25 points and over 10 rebounds")
    assert isinstance(tree, AndNode)
    assert isinstance(tree.left, ConditionNode)
    assert isinstance(tree.right, ConditionNode)
    assert tree.left.stat == "pts"
    assert tree.right.stat == "reb"


def test_parse_or_expression():
    tree = parse_condition_text("over 25 points or over 10 rebounds")
    assert isinstance(tree, OrNode)
    assert isinstance(tree.left, ConditionNode)
    assert isinstance(tree.right, ConditionNode)


def test_parse_grouped_expression():
    tree = parse_condition_text("(over 25 points and over 10 rebounds) or over 15 assists")
    assert isinstance(tree, OrNode)
    assert isinstance(tree.left, AndNode)
    assert isinstance(tree.right, ConditionNode)


def test_parse_nested_precedence_expression():
    tree = parse_condition_text("over 25 points and (over 10 rebounds or over 15 assists)")
    assert isinstance(tree, AndNode)
    assert isinstance(tree.left, ConditionNode)
    assert isinstance(tree.right, OrNode)


def test_parse_raises_on_unmatched_left_paren():
    with pytest.raises(BooleanQueryParseError):
        parse_condition_text("(over 25 points and over 10 rebounds")


def test_parse_raises_on_unmatched_right_paren():
    with pytest.raises(BooleanQueryParseError):
        parse_condition_text("over 25 points)")


def test_parse_raises_on_malformed_expression():
    with pytest.raises(BooleanQueryParseError):
        parse_condition_text("over 25 points and or over 10 rebounds")


def test_condition_node_to_mask():
    df = pd.DataFrame(
        {
            "pts": [20, 26, 31],
            "reb": [9, 11, 8],
        }
    )
    node = ConditionNode(stat="pts", min_value=25.0001, max_value=None)
    mask = condition_node_to_mask(node, df)
    assert list(mask.astype(bool)) == [False, True, True]


def test_evaluate_and_tree():
    df = pd.DataFrame(
        {
            "pts": [20, 26, 31],
            "reb": [9, 11, 8],
        }
    )
    tree = parse_condition_text("over 25 points and over 10 rebounds")
    out = evaluate_condition_tree(tree, df)
    assert len(out) == 1
    assert int(out.iloc[0]["pts"]) == 26
    assert int(out.iloc[0]["reb"]) == 11


def test_evaluate_or_tree():
    df = pd.DataFrame(
        {
            "pts": [20, 26, 31],
            "reb": [9, 11, 8],
        }
    )
    tree = parse_condition_text("over 25 points or over 10 rebounds")
    out = evaluate_condition_tree(tree, df)
    assert len(out) == 2
    assert list(out["pts"]) == [26, 31]


def test_evaluate_grouped_tree():
    df = pd.DataFrame(
        {
            "pts": [20, 26, 31, 18],
            "reb": [9, 11, 8, 7],
            "ast": [16, 5, 6, 17],
        }
    )
    tree = parse_condition_text("(over 25 points and over 10 rebounds) or over 15 assists")
    out = evaluate_condition_tree(tree, df)
    assert len(out) == 3
    assert list(out["pts"]) == [20, 26, 18]


def test_tree_to_dict_smoke():
    tree = parse_condition_text("(over 25 points and over 10 rebounds) or over 15 assists")
    payload = tree_to_dict(tree)
    assert payload["type"] == "or"
    assert payload["left"]["type"] == "and"
    assert payload["right"]["type"] == "condition"
