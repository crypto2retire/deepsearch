import json
import logging
from typing import Optional

from app.services.openrouter import call_llm

logger = logging.getLogger("deepsearch.coder")

CODER_MODEL = "moonshotai/kimi-k2.6"
CODER_PROVIDER = "moonshot"


async def run_coder(
    description: str,
    spec: str,
    github_url: Optional[str],
    repo_dir: Optional[str],
    api_key: str,
) -> dict:
    logger.info("Coder: starting")

    context = ""
    if github_url:
        context += f"\nClone and modify existing repo: {github_url}\n"
    if repo_dir:
        context += f"\nRepo directory: {repo_dir}\n"

    system_prompt = """You are an expert programmer. Given a SPEC.md and user description, generate complete, working code files.

Output format -- return ONLY valid JSON (no markdown, no explanation):
{
  "files": {
    "src/main.py": "print('hello world')",
    "requirements.txt": "fastapi\\nuvicorn"
  }
}

Rules:
- Output ALL files needed to make the project runnable
- Use proper file paths and extensions
- Write COMPLETE, working code -- not placeholders
- Do NOT explain what you're doing
- Max 50 files
- For each file, the content should be complete and functional"""

    user_prompt = f"""{context}

User Request:
{description}

---
SPEC.md:
{spec}
---

Return ONLY valid JSON with complete implementation files."""

    try:
        result = await call_llm(
            model=CODER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=api_key,
            provider=CODER_PROVIDER,
            temperature=0.1,
        )

        result = result.strip()
        if result.startswith("```"):
            parts = result.split("```", 2)
            if len(parts) >= 3:
                result = parts[1]
                if result.startswith("json"):
                    result = result[4:]
                result = result.strip()

        coder_output = json.loads(result)
        files = coder_output.get("files", {})

        if not files:
            raise RuntimeError("Coder returned no files")

        logger.info(f"Coder: generated {len(files)} files")

        return {
            "status": "completed",
            "files": files,
            "github_url": github_url or "",
        }

    except json.JSONDecodeError as e:
        logger.error(f"Coder: JSON parse error {e}")
        raise RuntimeError(f"Coder returned invalid JSON: {str(e)[:200]}")
    except Exception as e:
        logger.error(f"Coder: error {e}")
        raise RuntimeError(f"Coder failed: {str(e)[:200]}")