"""
Tool definitions and execution for the agent.

To add a new tool:
1. Define it in TOOL_DEFINITIONS (Anthropic tool format)
2. Add an async handler function
3. Register it in TOOL_HANDLERS

That's it. The agent loop in agent.py handles the rest.
"""

import os
import logging
import httpx

logger = logging.getLogger(__name__)


# --- Tool Definitions (sent to Claude) ---

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current information. Use this when the user asks about "
            "recent events, news, weather, prices, or anything that requires up-to-date data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_weather",
        "description": (
            "Get current weather for a location. "
            "Use this when the user asks about weather conditions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name, e.g. 'Tel Aviv' or 'London'",
                }
            },
            "required": ["location"],
        },
    },
]


# --- Tool Handlers ---

async def handle_web_search(query: str) -> str:
    """Search the web using Tavily API."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Web search is not configured. Set TAVILY_API_KEY in .env"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": 5,
                    "include_answer": True,
                },
                timeout=15.0,
            )
            data = response.json()

            # Build a concise result string
            parts = []
            if data.get("answer"):
                parts.append(f"Summary: {data['answer']}")

            for result in data.get("results", [])[:3]:
                title = result.get("title", "")
                content = result.get("content", "")[:200]
                url = result.get("url", "")
                parts.append(f"- {title}: {content}... ({url})")

            return "\n".join(parts) if parts else "No results found."

    except Exception as e:
        logger.error(f"Web search error: {e}")
        return f"Search failed: {e}"


async def handle_get_weather(location: str) -> str:
    """Get weather using OpenWeatherMap API."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Weather is not configured. Set OPENWEATHER_API_KEY in .env"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": location,
                    "appid": api_key,
                    "units": "metric",
                },
                timeout=10.0,
            )
            data = response.json()

            if data.get("cod") != 200:
                return f"Couldn't find weather for '{location}'"

            weather = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]

            return (
                f"Weather in {data['name']}: {weather}, "
                f"{temp}°C (feels like {feels_like}°C), "
                f"humidity {humidity}%"
            )

    except Exception as e:
        logger.error(f"Weather error: {e}")
        return f"Weather lookup failed: {e}"


# --- Handler Registry ---

TOOL_HANDLERS = {
    "web_search": lambda args: handle_web_search(args["query"]),
    "get_weather": lambda args: handle_get_weather(args["location"]),
}


async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name and return the result as a string."""
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return f"Unknown tool: {name}"

    logger.info(f"Executing tool: {name} with args: {args}")
    result = await handler(args)
    logger.info(f"Tool result ({name}): {result[:200]}")
    return result
