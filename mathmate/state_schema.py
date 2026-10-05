"""
Session-state schema for MathMate.

ADK sessions store state as a flat dict per (app, user, session). We
centralize key names + a default factory here so the agent instructions,
tools, and app entrypoint never disagree about shape. This is the backbone
of "context-aware, multi-turn tutoring": every tool reads/writes through
these keys, and the agent's instructions reference them by name.
"""

from typing import Any, Dict

STATE_STUDENT_NAME = "student_name"
STATE_CURRENT_TOPIC = "current_topic"
STATE_CURRENT_PROBLEM = "current_problem"
STATE_CURRENT_STEP = "current_step"
STATE_HINTS_USED = "hints_used_this_problem"
STATE_ATTEMPTS = "attempts_this_problem"
STATE_MASTERY = "mastery"                 # dict[topic -> float 0..1]
STATE_PROBLEMS_SOLVED = "problems_solved"
STATE_HISTORY = "session_history"         # list[str], most recent last

DEFAULT_TOPICS = (
    "linear_equations",
    "quadratic_equations",
    "systems_of_equations",
    "polynomials",
    "inequalities",
)


def default_state() -> Dict[str, Any]:
    """Fresh state for a brand-new student session."""
    return {
        STATE_STUDENT_NAME: None,
        STATE_CURRENT_TOPIC: None,
        STATE_CURRENT_PROBLEM: None,
        STATE_CURRENT_STEP: 0,
        STATE_HINTS_USED: 0,
        STATE_ATTEMPTS: 0,
        STATE_MASTERY: {topic: 0.0 for topic in DEFAULT_TOPICS},
        STATE_PROBLEMS_SOLVED: 0,
        STATE_HISTORY: [],
    }
