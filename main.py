"""
Interactive CLI for MathMate.

Usage:
    python main.py

Requires GOOGLE_API_KEY (or Vertex AI project/location) set in your
environment or a .env file — see .env.example.
"""

import asyncio
import uuid

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from mathmate.agent import root_agent

load_dotenv()

APP_NAME = "mathmate"
USER_ID = "local_student"


async def main() -> None:
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)

    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

    print("MathMate is ready. Type 'quit' to exit.\n")

    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_text.lower() in {"quit", "exit"}:
            break
        if not user_text:
            continue

        content = types.Content(role="user", parts=[types.Part(text=user_text)])

        async for event in runner.run_async(user_id=USER_ID, session_id=session_id, new_message=content):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"MathMate: {part.text}\n")


if __name__ == "__main__":
    asyncio.run(main())
