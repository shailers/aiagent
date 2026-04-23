# Telegram AI Agent

A personal AI agent that lives in Telegram, powered by Claude.

## Setup

### 1. Create a Telegram bot
- Open Telegram, message `@BotFather`
- Send `/newbot`, follow the prompts
- Copy the bot token

### 2. Install dependencies
```bash
cd telegram-agent
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your actual tokens
```

### 4. Run
```bash
python bot.py
```

## Commands
- `/start` — Initialize the bot
- `/reset` — Clear conversation history

## Structure
```
telegram-agent/
├── bot.py           # Telegram bot (polling mode)
├── agent.py         # LLM agent with conversation memory
├── conversations/   # Per-user conversation history (JSON)
├── requirements.txt
├── .env.example
└── README.md
```

## Notes
- Conversation history is stored as JSON files per user ID
- History is capped at 50 messages (configurable in agent.py)
- Uses Claude Sonnet by default (configurable via ANTHROPIC_MODEL)
