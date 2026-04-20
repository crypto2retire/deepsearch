import asyncio
from typing import AsyncGenerator
from app.agents.planner import call_planner
from app.agents.researcher import call_researcher
from app.agents.synthesizer import call_synthesizer


async def run_pipeline(
    query: str,
    api_key: str,
    planner_model: str,
    researcher_model_1: str,
    researcher_model_2: str,
    synthesizer_model: str,
    provider: str,
) -> AsyncGenerator[dict, None]:
    """
    Run the full pipeline: planner → 2 parallel researchers → synthesizer.
    Each researcher model processes every sub-task independently; findings are merged.
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
        "message": f"Planned {len(sub_tasks)} sub-tasks across 2 researcher tracks",
        "plan": plan,
    }

    # 2. Both researchers run all sub-tasks in parallel, findings are merged
    yield {
        "agent": "researcher",
        "status": "started",
        "message": f"Running 2 researcher models across {len(sub_tasks)} tasks...",
    }

    async def research_task(sub_task: dict, model: str) -> dict:
        try:
            return call_researcher(
                sub_task["description"],
                sub_task["search_query"],
                model,
                api_key,
                provider,
            )
        except Exception as e:
            return {"error": str(e), "sub_task": sub_task}

    # Fire all tasks for both models simultaneously
    tasks = (
        [research_task(st, researcher_model_1) for st in sub_tasks]
        + [research_task(st, researcher_model_2) for st in sub_tasks]
    )
    results = await asyncio.gather(*tasks)

    findings = []
    errors = []
    seen_urls = set()  # deduplicate by URL across both models

    for r in results:
        if "error" in r:
            errors.append(r["error"])
        else:
            # Deduplicate: skip facts from URLs already seen
            for fact in r.get("findings", []):
                src = fact.get("source", "")
                if src not in seen_urls:
                    seen_urls.add(src)
                    findings.append({**fact, "model": r.get("model", "unknown")})

    if findings:
        yield {
            "agent": "researcher",
            "status": "completed",
            "message": f"Merged {len(findings)} unique findings from both researchers",
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
