"""
Tools available to the MathMate tutoring agent.

Each tool is a plain Python function with type hints and a docstring —
ADK turns these into function-calling schemas automatically and passes a
`ToolContext` for reading/writing session state. Tools own the things an
LLM is unreliable at:

  * `check_algebra_step`      -> exact symbolic verification (sympy),
                                  not an LLM guessing whether math is right
  * `generate_practice_problem` -> deterministic problem selection +
                                  resets the per-problem state
  * `update_mastery`          -> persistent, monotonic bookkeeping

The agent's job (in prompts.py / agent.py) is pedagogy: deciding *when*
to call these, and how to talk to the student about the results.
"""

import random
from typing import Any, Dict, Tuple

import sympy
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

try:
    from google.adk.tools import ToolContext
except ImportError:  # allows tools.py to be imported/tested without ADK installed
    ToolContext = Any  # type: ignore

from .state_schema import (
    STATE_ATTEMPTS,
    STATE_CURRENT_PROBLEM,
    STATE_CURRENT_STEP,
    STATE_CURRENT_TOPIC,
    STATE_HINTS_USED,
    STATE_HISTORY,
    STATE_MASTERY,
    STATE_PROBLEMS_SOLVED,
)

_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)

_PROBLEM_BANK = {
    "linear_equations": {
        "easy": ["2*x + 3 = 11", "5*x - 4 = 16", "3*(x - 2) = 9"],
        "medium": ["2*x + 5 = 3*x - 7", "4*(x + 1) - 2 = 3*x + 5", "(x/2) + 3 = 10"],
        "hard": ["3*(2*x - 1) + 4 = 5*(x + 2) - 3", "(2*x + 1)/3 - (x - 1)/2 = 1"],
    },
    "quadratic_equations": {
        "easy": ["x**2 - 5*x + 6 = 0", "x**2 - 9 = 0", "x**2 + 4*x = 0"],
        "medium": ["2*x**2 - 3*x - 2 = 0", "x**2 - 2*x - 15 = 0"],
        "hard": ["3*x**2 - 5*x - 2 = 0", "x**2 - 4*x + 1 = 0"],
    },
    "systems_of_equations": {
        "easy": ["x + y = 10, x - y = 2"],
        "medium": ["2*x + y = 7, x - y = 2"],
        "hard": ["3*x + 2*y = 16, 5*x - y = 7"],
    },
    "polynomials": {
        "easy": ["(x + 2)*(x + 3)", "x**2*(x + 1)"],
        "medium": ["(x + 1)*(x**2 - x + 1)", "(2*x - 1)*(x + 4)"],
        "hard": ["(x - 1)*(x + 2)*(x - 3)"],
    },
    "inequalities": {
        "easy": ["2*x + 3 > 9"],
        "medium": ["-3*x + 5 <= 2*x - 10"],
        "hard": ["2*(x - 1) > 3*(x + 2) - 5"],
    },
}


def generate_practice_problem(topic: str, difficulty: str, tool_context: "ToolContext") -> Dict[str, Any]:
    """Pick a fresh practice problem for the student and store it as the
    active problem in session state, resetting per-problem counters.

    Args:
        topic: One of "linear_equations", "quadratic_equations",
            "systems_of_equations", "polynomials", "inequalities".
        difficulty: One of "easy", "medium", "hard".

    Returns:
        Dict with the chosen problem, topic, and difficulty, or an
        "error" key if the topic/difficulty isn't recognized.
    """
    topic = topic.lower().strip()
    difficulty = difficulty.lower().strip()

    if topic not in _PROBLEM_BANK:
        return {"error": f"Unknown topic '{topic}'. Known topics: {list(_PROBLEM_BANK)}"}
    if difficulty not in _PROBLEM_BANK[topic]:
        return {"error": f"Unknown difficulty '{difficulty}'. Use easy, medium, or hard."}

    problem = random.choice(_PROBLEM_BANK[topic][difficulty])

    tool_context.state[STATE_CURRENT_TOPIC] = topic
    tool_context.state[STATE_CURRENT_PROBLEM] = problem
    tool_context.state[STATE_CURRENT_STEP] = 0
    tool_context.state[STATE_HINTS_USED] = 0
    tool_context.state[STATE_ATTEMPTS] = 0

    return {"topic": topic, "difficulty": difficulty, "problem": problem}


def check_algebra_step(
    original_expression: str,
    student_rewrite: str,
    tool_context: "ToolContext",
) -> Dict[str, Any]:
    """Verify whether the student's rewritten line is mathematically
    equivalent to the original — i.e. whether their algebra STEP was
    valid, regardless of whether it's closer to the final answer.

    Uses exact symbolic math (sympy) so the check is always correct; the
    agent should call this instead of judging algebra itself.

    Args:
        original_expression: The line before the student's step, e.g.
            "2*x + 3 = 11".
        student_rewrite: The student's proposed next line, e.g. "2*x = 8".

    Returns:
        Dict with "valid" (bool) and "reason" (short internal
        explanation — the agent decides how to phrase feedback, this is
        not user-facing text).
    """
    tool_context.state[STATE_ATTEMPTS] = tool_context.state.get(STATE_ATTEMPTS, 0) + 1

    try:
        valid, reason = _check_equivalence(original_expression, student_rewrite)
    except Exception as exc:  # noqa: BLE001 - surface parse errors to the agent, don't crash
        return {"valid": False, "reason": f"Could not parse the math: {exc}"}

    if valid:
        tool_context.state[STATE_CURRENT_STEP] = tool_context.state.get(STATE_CURRENT_STEP, 0) + 1

    return {"valid": valid, "reason": reason}


def _check_equivalence(before: str, after: str) -> Tuple[bool, str]:
    """Core symbolic comparison. Handles bare expressions and single
    'lhs = rhs' equations. (Systems of equations are checked per-line by
    the agent calling this once per equation.)"""
    if "=" in before and "=" in after:
        b_lhs, b_rhs = before.split("=", 1)
        a_lhs, a_rhs = after.split("=", 1)
        b = parse_expr(b_lhs, transformations=_TRANSFORMS) - parse_expr(b_rhs, transformations=_TRANSFORMS)
        a = parse_expr(a_lhs, transformations=_TRANSFORMS) - parse_expr(a_rhs, transformations=_TRANSFORMS)

        if b == 0 and a == 0:
            return True, "Both sides reduce to 0 = 0; equivalent."
        if a == 0:
            return False, "The rewritten equation lost the variable entirely."

        ratio = sympy.simplify(b / a)
        if ratio.is_number and ratio != 0:
            return True, "Equation is a valid scalar multiple of the original — equivalent."
        return False, "The equation's solution set changed."

    b = parse_expr(before, transformations=_TRANSFORMS)
    a = parse_expr(after, transformations=_TRANSFORMS)
    if sympy.simplify(b - a) == 0:
        return True, "Expressions are algebraically identical."
    return False, "Expressions are not equivalent."


def update_mastery(topic: str, solved_without_hints: bool, tool_context: "ToolContext") -> Dict[str, Any]:
    """Record that the student finished a problem, nudging their mastery
    score for that topic and logging the event to session history.

    Args:
        topic: The topic just practiced.
        solved_without_hints: True if the student solved it independently.

    Returns:
        Dict with the updated mastery score for that topic.
    """
    mastery = tool_context.state.get(STATE_MASTERY, {})
    current = mastery.get(topic, 0.0)
    delta = 0.15 if solved_without_hints else 0.05
    mastery[topic] = round(min(1.0, current + delta), 2)
    tool_context.state[STATE_MASTERY] = mastery

    tool_context.state[STATE_PROBLEMS_SOLVED] = tool_context.state.get(STATE_PROBLEMS_SOLVED, 0) + 1

    history = tool_context.state.get(STATE_HISTORY, [])
    history.append(
        f"Solved a {topic} problem "
        f"({'no hints' if solved_without_hints else 'with hints'}); "
        f"mastery now {mastery[topic]}"
    )
    tool_context.state[STATE_HISTORY] = history[-20:]  # keep it bounded

    return {"topic": topic, "mastery": mastery[topic]}
