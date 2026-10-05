"""MathMate web app (Streamlit). Run: streamlit run app.py"""

import asyncio
import threading
import time
import uuid

import streamlit as st
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from mathmate.agent import root_agent
from mathmate.state_schema import (
    DEFAULT_TOPICS, STATE_ATTEMPTS, STATE_CURRENT_PROBLEM, STATE_CURRENT_TOPIC,
    STATE_HINTS_USED, STATE_MASTERY, STATE_PROBLEMS_SOLVED,
)

load_dotenv()
APP_NAME, USER_ID = "mathmate", "web_student"

st.set_page_config(page_title="MathMate AI", page_icon="🧮", layout="wide")


@st.cache_resource
def get_backend():
    """One background event loop + runner shared across reruns."""
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    svc = InMemorySessionService()
    return loop, svc, Runner(agent=root_agent, app_name=APP_NAME, session_service=svc)


loop, svc, runner = get_backend()


def run(coro):
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


if "sid" not in st.session_state:
    st.session_state.sid = str(uuid.uuid4())
    st.session_state.msgs = []
    run(svc.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=st.session_state.sid))


async def ask(text: str, sid: str) -> str:
    content = types.Content(role="user", parts=[types.Part(text=text)])
    out = []
    async for ev in runner.run_async(user_id=USER_ID, session_id=sid, new_message=content):
        if ev.is_final_response() and ev.content and ev.content.parts:
            out += [p.text for p in ev.content.parts if p.text]
    return "\n".join(out) or "(no reply)"


def get_state() -> dict:
    s = run(svc.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=st.session_state.sid))
    return dict(s.state) if s else {}


def send(text: str):
    st.session_state.msgs.append(("user", text))
    reply = None
    for attempt, wait in enumerate((3, 8, 15, 0)):
        try:
            reply = run(ask(text, st.session_state.sid))
            break
        except Exception as e:
            msg = str(e)
            busy = any(k in msg for k in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"))
            if busy and wait:
                time.sleep(wait)  # Gemini overloaded / rate limited: back off and retry
                continue
            reply = (
                "⚠️ Gemini is busy or rate-limited right now. Wait a minute and try again."
                if busy else f"⚠️ {type(e).__name__}: {e}"
            )
            break
    st.session_state.msgs.append(("assistant", reply))


# ---------- Sidebar: live progress ----------
state = get_state()
with st.sidebar:
    st.title("🧮 MathMate")
    st.caption("Socratic algebra tutor · Google ADK + Gemini")
    st.subheader("Your progress")
    st.metric("Problems solved", state.get(STATE_PROBLEMS_SOLVED, 0))
    mastery = state.get(STATE_MASTERY) or {t: 0.0 for t in DEFAULT_TOPICS}
    for topic, val in mastery.items():
        st.caption(topic.replace("_", " ").title())
        st.progress(min(max(float(val), 0.0), 1.0))
    if state.get(STATE_CURRENT_PROBLEM):
        st.subheader("Current problem")
        st.info(str(state[STATE_CURRENT_PROBLEM]))
        c1, c2 = st.columns(2)
        c1.metric("Attempts", state.get(STATE_ATTEMPTS, 0))
        c2.metric("Hints", state.get(STATE_HINTS_USED, 0))
    if st.button("🔄 New session", use_container_width=True):
        for k in ("sid", "msgs"):
            st.session_state.pop(k, None)
        st.rerun()

# ---------- Main chat ----------
st.header("Learn algebra step by step")
st.caption("Pick a topic, solve one step at a time, and MathMate verifies each step symbolically.")

if not st.session_state.msgs:
    st.markdown("**Quick start:**")
    cols = st.columns(len(DEFAULT_TOPICS))
    for col, topic in zip(cols, DEFAULT_TOPICS):
        label = topic.replace("_", " ").title()
        if col.button(label, use_container_width=True):
            send(f"Hi! I want to practice {label}.")
            st.rerun()

for role, text in st.session_state.msgs:
    with st.chat_message(role):
        st.markdown(text)

if prompt := st.chat_input("Type your answer or ask for a hint..."):
    with st.spinner("MathMate is thinking..."):
        send(prompt)
    st.rerun()