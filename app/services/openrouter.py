import httpx
import json
from typing import Optional


LLM_PROVIDERS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "z.ai": "https://z.ai/v1/api/chat/completions",
    "minimax": "https://api.minimax.chat/v1/text/chatcompletion_v2",
}


def call_llm(
    model: str,
    messages: list[dict],
    api_key: str,
    provider: str = "openrouter",
    temperature: float = 0.2,
) -> str:
    """
    Call an LLM via OpenRouter-compatible or Z.ai/MiniMax API.
    Returns the assistant's response text.
    """
    if provider not in LLM_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")

    url = LLM_PROVIDERS[provider]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    # MiniMax uses a different param name
    if provider == "minimax":
        payload["model"] = model
        headers.pop("Content-Type", None)
        # MiniMax also wraps in a slightly different structure
        payload["messages"] = messages

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def structured_call(
    model: str,
    messages: list[dict],
    api_key: str,
    provider: str = "openrouter",
    temperature: float = 0.2,
) -> dict:
    """Call LLM and parse JSON response."""
    text = call_llm(model, messages, api_key, provider, temperature)
    # Try to extract JSON from markdown code blocks if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
