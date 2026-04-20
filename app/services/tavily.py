import httpx
from app.services.prefs import get_tavily_api_key

def search_tavily(query: str, top_k: int = 10) -> list[dict]:
    api_key = get_tavily_api_key()
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set in Railway environment variables")
    payload = {
        "query": query,
        "top_k": top_k,
        "include_answer": False,
        "include_raw_content": False,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    response = httpx.post(
        "https://api.tavily.com/search",
        json=payload,
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in data.get("results", [])
    ]
