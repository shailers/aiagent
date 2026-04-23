import os
import json
import logging
from pathlib import Path
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

HISTORY_DIR = Path("conversations")
HISTORY_DIR.mkdir(exist_ok=True)

MAX_HISTORY_MESSAGES = 50  # Keep last N messages per user

SYSTEM_PROMPT = """You are a personal AI agent communicating through Telegram.
Be concise — this is a chat messenger, not an essay platform.
Be direct, genuine, and useful. No filler, no fluff.
You have memory of the conversation so far, so reference previous context naturally."""


class Agent:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    def _history_path(self, user_id: str) -> Path:
        return HISTORY_DIR / f"{user_id}.json"

    def _load_history(self, user_id: str) -> list[dict]:
        path = self._history_path(user_id)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    def _save_history(self, user_id: str, messages: list[dict]):
        # Trim to last N messages
        trimmed = messages[-MAX_HISTORY_MESSAGES:]
        path = self._history_path(user_id)
        with open(path, "w") as f:
            json.dump(trimmed, f, indent=2)

    def reset_conversation(self, user_id: str):
        path = self._history_path(user_id)
        if path.exists():
            path.unlink()
        logger.info(f"Conversation reset for user {user_id}")

    async def respond(self, user_id: str, user_message: str) -> str:
        messages = self._load_history(user_id)
        messages.append({"role": "user", "content": user_message})

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            )

            assistant_message = response.content[0].text

            messages.append({"role": "assistant", "content": assistant_message})
            self._save_history(user_id, messages)

            return assistant_message

        except Exception as e:
            logger.error(f"LLM error for user {user_id}: {e}")
            return f"Something went wrong: {e}"
