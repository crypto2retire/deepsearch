import httpx
import json
import logging
from typing import Optional

logger = logging.getLogger("deepsearch.llm")

LLM_PROVIDERS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "z.ai": "https://z.ai/v1/api/chat/completions",
    "minimax": "https://api.minimax.chat/v1/text/chatcompletion_v2",
}


async def call_llm(
    model: str,
    messages: list[dict],
    api_key: str,
    provider: str = "openrouter",
    temperature: float = 0.2,
) -> str:
    """
    Call an LLM via OpenRouter-compatible or Z.ai/MiniMax API.
    Returns the assistant's response text.
    Raises RuntimeError with details on timeout or API error.
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

    if provider == "minimax":
        payload["model"] = model
        headers.pop("Content-Type", None)
        payload["messages"] = messages

    logger.info(f"LLM call: provider={provider} model={model} url={url}")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=90.0)) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            if "choices" not in data:
                raise RuntimeError(f"Unexpected API response (no choices): {str(data)[:200]}")
            content = data["choices"][0].get("message", {}).get("content", "")
            if not content:
                raise RuntimeError(f"Empty response from {provider} for model {model}")
            logger.info(f"LLM call success: provider={provider} model={model} len={len(content)}")
            return content
    except httpx.TimeoutException:
        logger.error(f"LLM timeout: provider={provider} model={model}")
        raise RuntimeError(f"Timeout calling {provider} model '{model}'. Try a faster/smaller model.")
    except httpx.HTTPStatusError as e:
        logger.error(f"LLM HTTP error: provider={provider} model={model} status={e.response.status_code} body={e.response.text[:300]}")
        raise RuntimeError(f"HTTP {e.response.status_code} from {provider}: {e.response.text[:300]}")
    except Exception as e:
        logger.error(f"LLM call failed: provider={provider} model={model} error={e}")
        raise RuntimeError(f"LLM call failed ({provider}/{model}): {str(e)[:200]}")


async def structured_call(
    model: str,
    messages: list[dict],
    api_key: str,
    provider: str = "openrouter",
    temperature: float = 0.2,
) -> dict:
    """Call LLM and parse JSON response. Raises RuntimeError on failure."""
    text = await call_llm(model, messages, api_key, provider, temperature)
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        parts = text.split("```", 2)
        if len(parts) >= 3:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Planner returned non-JSON response: {str(e)[:100]} — raw: {text[:200]}")