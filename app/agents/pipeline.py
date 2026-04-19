import asyncio
from typing import AsyncGenerator
from app.agents.planner import call_planner
from app.agents.researcher import call_researcher
from app.agents.synthesizer import call_synthesizer


async def run_pipeline(
    query: str,
    api_key: str,
    planner_model: str,
    researcher_model: str,
    synthesizer_model: str,
    provider: str,
) -> AsyncGenerator[dict, None]:
    """
    Run the full 4-agent pipeline and yield SSE-like events.
    Returns (answer_text, citations_json, follow_ups_json)
    """
    # 1. Planner
    yield {"agent": "planner", "status": "started", "message": "Planning research approach..."}
    try:
        plan = call_planner(query, api_key, planner_model, provider)
    except Exception as e:
        yield {"agent": "planner", "status": "error", "message": f"Planner failed: {e}"}
        return

    sub_tasks = plan.get("sub_tasks", [])
    yield {
        "agent": "planner",
        "status": "completed",
        "message": f"Planned {len(sub_tasks)} sub-tasks",
        "plan": plan,
    }

    # 2. Researchers (parallel)
    yield {"agent": "researcher", "status": "started", "message": "Running researchers in parallel..."}
    findings = []
    errors = []

    async def research_task(sub_task: dict) -> dict:
        try:
            return call_researcher(
                sub_task["description"],
                sub_task["search_query"],
                researcher_model,
                api_key,
                provider,
            )
        except Exception as e:
            return {"error": str(e), "sub_task": sub_task}

    results = await asyncio.gather(*[research_task(st) for st in sub_tasks])

    for r in results:
        if "error" in r:
            errors.append(r["error"])
        else:
            findings.append(r)

    if findings:
        yield {
            "agent": "researcher",
            "status": "completed",
            "message": f"Got findings from {len(findings)} researcher(s)",
            "findings": findings,
        }
    else:
        yield {"agent": "researcher", "status": "error", "message": "All researchers failed", "errors": errors}
        return

    # 3. Synthesizer
    yield {"agent": "synthesizer", "status": "started", "message": "Synthesizing answer..."}
    try:
        result = call_synthesizer(query, findings, synthesizer_model, api_key, provider)
        yield {
            "agent": "synthesizer",
            "status": "completed",
            "message": "Synthesis complete",
            "result": result,
        }
    except Exception as e:
        yield {"agent": "synthesizer", "status": "error", "message": f"Synthesizer failed: {e}"}
