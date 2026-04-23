import os
import json
import logging
from pathlib import Path
from anthropic import AsyncAnthropic

from tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

HISTORY_DIR = Path("conversations")
HISTORY_DIR.mkdir(exist_ok=True)

MAX_HISTORY_MESSAGES = 50
MAX_TOOL_ROUNDS = 5  # Safety limit on tool call loops

SYSTEM_PROMPT = """You are a personal AI agent communicating through Telegram.
Be concise — this is a chat messenger, not an essay platform.
Be direct, genuine, and useful. No filler, no fluff.
You have memory of the conversation so far, so reference previous context naturally.

You have access to tools. Use them when the user's question requires current or external information.
Don't announce that you're using a tool — just use it and give the answer."""


class Agent:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    def _history_path(self, user_id: str) -> Path:
        return HISTORY_DIR / f"{user_id}.json"

    def _load_history(self, user_id: str) -> list[dict]:
        path = self._history_path(user_id)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    def _save_history(self, user_id: str, messages: list[dict]):
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
            # Tool use loop: Claude may call tools, we execute them,
            # feed results back, and let Claude continue until it
            # produces a final text response.
            for _ in range(MAX_TOOL_ROUNDS):
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                )

                # If Claude wants to use tools, execute them
                if response.stop_reason == "tool_use":
                    # Build the assistant message content (text + tool_use blocks)
                    assistant_content = []
                    for block in response.content:
                        if block.type == "text":
                            assistant_content.append({
                                "type": "text",
                                "text": block.text,
                            })
                        elif block.type == "tool_use":
                            assistant_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            })

                    messages.append({"role": "assistant", "content": assistant_content})

                    # Execute each tool and collect results
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            result = await execute_tool(block.name, block.input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })

                    messages.append({"role": "user", "content": tool_results})

                else:
                    # Claude is done — extract final text
                    break

            # Get the final text response
            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

            if not final_text:
                final_text = "I processed that but have nothing to say. That's a first."

            # Save clean history (store only the final text for assistant)
            messages.append({"role": "assistant", "content": final_text})
            self._save_history(user_id, messages)

            return final_text

        except Exception as e:
            logger.error(f"LLM error for user {user_id}: {e}")
            return f"Something went wrong: {e}"
