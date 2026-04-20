import httpx
import json
import re
import logging
from typing import Optional

logger = logging.getLogger("deepsearch.llm")

LLM_PROVIDERS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "google": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    "minimax": "https://api.minimax.chat/v1/text/chatcompletion_v2",
    "z.ai": "https://api.z.ai/api/coding/paas/v4/chat/completions",
}


async def _call_openai_compatible(url: str, model: str, messages: list[dict], api_key: str, temperature: float) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if "z.ai" not in url:
        payload["max_tokens"] = 4096
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=90.0)) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        if "choices" not in data:
            raise RuntimeError(f"Unexpected API response (no choices): {str(data)[:200]}")
        content = data["choices"][0].get("message", {}).get("content", "")
        if not content:
            raise RuntimeError(f"Empty response for model {model}")
        return content


async def _call_anthropic(model: str, messages: list[dict], api_key: str, temperature: float) -> str:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    system_text = ""
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
        else:
            user_messages.append({"role": m["role"], "content": m["content"]})
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": user_messages,
        "temperature": temperature,
    }
    if system_text:
        payload["system"] = system_text
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=90.0)) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        if "content" not in data or not data["content"]:
            raise RuntimeError(f"Unexpected Anthropic response: {str(data)[:200]}")
        return data["content"][0].get("text", "")


async def _call_google(model: str, messages: list[dict], api_key: str, temperature: float) -> str:
    contents = []
    for m in messages:
        if m["role"] == "system":
            contents.append({"role": "user", "parts": [{"text": m["content"]}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        elif m["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": m["content"]}]})
        else:
            contents.append({"role": "user", "parts": [{"text": m["content"]}]})
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": temperature},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=90.0)) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected Google AI response: {str(data)[:200]}")


async def _call_minimax(model: str, messages: list[dict], api_key: str, temperature: float) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=90.0)) as client:
        response = await client.post(
            "https://api.minimax.chat/v1/text/chatcompletion_v2",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        if "choices" not in data:
            raise RuntimeError(f"Unexpected MiniMax response: {str(data)[:200]}")
        content = data["choices"][0].get("message", {}).get("content", "")
        if not content:
            raise RuntimeError(f"Empty MiniMax response for model {model}")
        return content


async def call_llm(
    model: str,
    messages: list[dict],
    api_key: str,
    provider: str = "openrouter",
    temperature: float = 0.2,
) -> str:
    if provider not in LLM_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")

    if provider == "openrouter" and model.startswith("openrouter/"):
        model = model[len("openrouter/"):]

    url = LLM_PROVIDERS[provider]
    logger.info(f"LLM call: provider={provider} model={model} url={url}")

    try:
        if provider in ("openrouter", "openai", "z.ai"):
            result = await _call_openai_compatible(url, model, messages, api_key, temperature)
        elif provider == "anthropic":
            result = await _call_anthropic(model, messages, api_key, temperature)
        elif provider == "google":
            result = await _call_google(model, messages, api_key, temperature)
        elif provider == "minimax":
            result = await _call_minimax(model, messages, api_key, temperature)
        else:
            raise ValueError(f"Unhandled provider: {provider}")
        logger.info(f"LLM call success: provider={provider} model={model} len={len(result)}")
        return result
    except httpx.TimeoutException:
        logger.error(f"LLM timeout: provider={provider} model={model}")
        raise RuntimeError(f"Timeout calling {provider} model '{model}'. Try a faster/smaller model.")
    except httpx.HTTPStatusError as e:
        logger.error(f"LLM HTTP error: provider={provider} model={model} status={e.response.status_code} body={e.response.text[:300]}")
        raise RuntimeError(f"HTTP {e.response.status_code} from {provider}: {e.response.text[:300]}")
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"LLM call failed: provider={provider} model={model} error={e}")
        raise RuntimeError(f"LLM call failed ({provider}/{model}): {str(e)[:200]}")


def _extract_json_from_text(text: str) -> Optional[dict]:
    # Try to find a JSON object in the text
    # First, try the whole text
    stripped = text.strip()
    if stripped.startswith("{"):
        depth = 0
        for i, ch in enumerate(stripped):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = stripped[:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    # Try to find { at any position
    start = stripped.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(stripped)):
            ch = stripped[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = stripped[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        continue

    return None


def _try_repair_truncated_json(text: str) -> Optional[dict]:
    # Try progressively closing open brackets
    stripped = text.strip()

    # Find start of JSON
    start = stripped.find("{")
    if start < 0:
        return None
    partial = stripped[start:]

    # Count open brackets
    open_braces = 0
    open_brackets = 0
    in_string = False
    escape = False
    for ch in partial:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            open_braces += 1
        elif ch == "}":
            open_braces -= 1
        elif ch == "[":
            open_brackets += 1
        elif ch == "]":
            open_brackets -= 1

    # Close any open string
    if in_string:
        partial += '"'

    # Remove trailing comma or incomplete key-value
    partial = partial.rstrip()
    if partial.endswith(","):
        partial = partial[:-1]

    # Try just closing everything
    candidate = partial + "]" * max(0, open_brackets) + "}" * max(0, open_braces)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # More aggressive: strip back to last complete value
    for suffix in ["}", "]}", '"}]}}', '"]}}', '"}]}', '"}]}]}', "}}"]:
        try:
            return json.loads(partial + suffix)
        except json.JSONDecodeError:
            continue

    return None


def _text_to_fallback_response(text: str) -> dict:
    # Strip markdown code fences
    stripped = text.strip()
    m = re.search(r"```(?:json)?(.*?)```", stripped, re.DOTALL)
    if m:
        stripped = m.group(1).strip()

    # Try to parse as JSON first
    parsed = _extract_json_from_text(stripped)
    if parsed:
        if isinstance(parsed, dict) and "answer" in parsed:
            return parsed
        # JSON parsed but wrong shape - convert to string answer
        return {
            "answer": json.dumps(parsed, indent=2) if len(str(parsed)) < 5000 else str(parsed)[:5000],
            "sources": [],
            "follow_up_questions": [],
        }

    # Not valid JSON at all - use raw text as answer
    return {
        "answer": stripped,
        "sources": [],
        "follow_up_questions": [],
    }


async def structured_call(
    model: str,
    messages: list[dict],
    api_key: str,
    provider: str = "openrouter",
    temperature: float = 0.2,
) -> dict:
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

    # 1. Try direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # 2. Try to extract JSON from surrounding text
    extracted = _extract_json_from_text(text)
    if extracted:
        return extracted

    # 3. Try to repair truncated JSON
    repaired = _try_repair_truncated_json(text)
    if repaired:
        logger.warning(f"Repaired truncated JSON from {provider}/{model}")
        return repaired

    # 4. Fallback: wrap raw text as answer
    logger.warning(f"LLM returned non-JSON response from {provider}/{model}, using text fallback")
    return _text_to_fallback_response(text)
