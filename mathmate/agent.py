"""
MathMate's root agent definition.

This is the ADK entrypoint: `adk web`, `adk run mathmate`, and the
custom Runner in main.py all look for a module-level `root_agent`.
"""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext

from .prompts import TUTOR_INSTRUCTION
from .state_schema import STATE_CURRENT_STEP, default_state
from .tools import check_algebra_step, generate_practice_problem, update_mastery

load_dotenv()

# Native Gemini via ADK -- no LiteLLM, so no Groq reasoning_content bug.
# Needs GOOGLE_API_KEY in .env (free key: https://aistudio.google.com/apikey).
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")


def _ensure_default_state(callback_context: CallbackContext) -> None:
    """before_agent_callback: seed session.state on a student's very
    first turn so the agent + tools never have to special-case missing
    keys. Cheap and idempotent — only runs the seed once per session.
    """
    if STATE_CURRENT_STEP not in callback_context.state:
        for key, value in default_state().items():
            callback_context.state[key] = value


root_agent = Agent(
    name="mathmate_tutor",
    model=MODEL,
    description=(
        "An autonomous algebra tutor that guides students through "
        "algebra problems step-by-step using Socratic questioning, exact "
        "symbolic verification, and session-state-driven personalization."
    ),
    instruction=TUTOR_INSTRUCTION,
    tools=[generate_practice_problem, check_algebra_step, update_mastery],
    before_agent_callback=_ensure_default_state,
)