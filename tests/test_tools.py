"""
Unit tests for MathMate's deterministic tools.

These never touch Gemini — they test the sympy-backed math verification
and problem-bank logic in isolation, so CI can run them with zero API
credentials.
"""

from unittest.mock import MagicMock

from mathmate.tools import check_algebra_step, generate_practice_problem, update_mastery


def _fake_tool_context():
    ctx = MagicMock()
    ctx.state = {}
    return ctx


def test_valid_linear_step():
    ctx = _fake_tool_context()
    result = check_algebra_step("2*x + 3 = 11", "2*x = 8", ctx)
    assert result["valid"] is True
    assert ctx.state["current_step"] == 1


def test_invalid_linear_step():
    ctx = _fake_tool_context()
    result = check_algebra_step("2*x + 3 = 11", "2*x = 14", ctx)
    assert result["valid"] is False


def test_valid_expression_expansion():
    ctx = _fake_tool_context()
    result = check_algebra_step("(x + 2)*(x + 3)", "x**2 + 5*x + 6", ctx)
    assert result["valid"] is True


def test_invalid_expression_expansion():
    ctx = _fake_tool_context()
    result = check_algebra_step("(x + 2)*(x + 3)", "x**2 + 6*x + 6", ctx)
    assert result["valid"] is False


def test_scalar_multiple_equation_is_valid():
    # Multiplying both sides by 2 should still count as equivalent.
    ctx = _fake_tool_context()
    result = check_algebra_step("x + 3 = 5", "2*x + 6 = 10", ctx)
    assert result["valid"] is True


def test_generate_practice_problem_sets_state():
    ctx = _fake_tool_context()
    result = generate_practice_problem("linear_equations", "easy", ctx)
    assert "problem" in result
    assert ctx.state["current_topic"] == "linear_equations"
    assert ctx.state["current_step"] == 0


def test_generate_practice_problem_unknown_topic():
    ctx = _fake_tool_context()
    result = generate_practice_problem("calculus", "easy", ctx)
    assert "error" in result


def test_generate_practice_problem_unknown_difficulty():
    ctx = _fake_tool_context()
    result = generate_practice_problem("linear_equations", "impossible", ctx)
    assert "error" in result


def test_update_mastery_increases_score_no_hints():
    ctx = _fake_tool_context()
    ctx.state["mastery"] = {"linear_equations": 0.0}
    result = update_mastery("linear_equations", True, ctx)
    assert result["mastery"] == 0.15
    assert ctx.state["problems_solved"] == 1
    assert len(ctx.state["session_history"]) == 1


def test_update_mastery_smaller_bump_with_hints():
    ctx = _fake_tool_context()
    ctx.state["mastery"] = {"linear_equations": 0.0}
    result = update_mastery("linear_equations", False, ctx)
    assert result["mastery"] == 0.05


def test_update_mastery_caps_at_one():
    ctx = _fake_tool_context()
    ctx.state["mastery"] = {"linear_equations": 0.95}
    result = update_mastery("linear_equations", True, ctx)
    assert result["mastery"] == 1.0
