import json
import logging
from typing import Optional

from app.services.openrouter import call_llm

logger = logging.getLogger("deepsearch.architect")

ARCHITECT_MODEL = "GLM-5.1"
ARCHITECT_PROVIDER = "z.ai"


async def run_architect(
    description: str,
    github_url: Optional[str],
    api_key: str,
) -> dict:
    logger.info("Architect: starting")

    context = ""
    if github_url:
        context += f"\n\nThe user wants to modify an existing GitHub repository:\n{github_url}\n"

    system_prompt = """You are a senior software architect. Your job is to analyze a user request and produce a detailed SPEC.md.

Output format -- return ONLY valid JSON (no markdown, no explanation):

{
  "project_name": "short-name",
  "overview": "2-3 sentence description of what this project does",
  "tech_stack": ["Python", "FastAPI", "React"],
  "file_structure": [
    {"path": "README.md", "type": "file", "description": "Project documentation"},
    {"path": "src/", "type": "folder", "description": "Source code"}
  ],
  "spec": "## Features\\n\\n- Feature 1\\n\\n## Technical Approach\\n\\n..."
}

Rules:
- project_name: lowercase-with-hyphens, max 50 chars
- tech_stack: list of technologies (max 8 items)
- file_structure: key files and folders needed (max 20 items)
- spec: markdown with ## Features and ## Technical Approach sections
- Do NOT invent competitor names or specific details not in the request
- Keep spec focused on what was actually requested"""

    user_prompt = f"""Analyze this request and produce a SPEC.md:

{context}

User Request:
{description}

Return ONLY valid JSON with the spec document."""

    try:
        result = await call_llm(
            model=ARCHITECT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=api_key,
            provider=ARCHITECT_PROVIDER,
            temperature=0.2,
        )

        result = result.strip()
        if result.startswith("```"):
            parts = result.split("```", 2)
            if len(parts) >= 3:
                result = parts[1]
                if result.startswith("json"):
                    result = result[4:]
                result = result.strip()

        spec_data = json.loads(result)
        spec_md = spec_data.get("spec", "")
        project_name = spec_data.get("project_name", "project")

        logger.info(f"Architect: completed for project {project_name}")

        return {
            "status": "completed",
            "project_name": project_name,
            "tech_stack": spec_data.get("tech_stack", []),
            "file_structure": spec_data.get("file_structure", []),
            "spec": spec_md,
            "github_url": github_url or "",
        }

    except json.JSONDecodeError as e:
        logger.error(f"Architect: JSON parse error {e}")
        raise RuntimeError(f"Architect returned invalid JSON: {str(e)[:200]}")
    except Exception as e:
        logger.error(f"Architect: error {e}")
        raise RuntimeError(f"Architect failed: {str(e)[:200]}")