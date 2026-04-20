import asyncio
import logging
from typing import AsyncGenerator
from app.agents.planner import call_planner
from app.agents.researcher import call_researcher
from app.agents.synthesizer import call_synthesizer

logger = logging.getLogger("deepsearch.pipeline")

KEEPALIVE_INTERVAL = 15


async def _with_keepalive(aw, agent_name):
    async def _ping():
        while True:
            await asyncio.sleep(KEEPALIVE_INTERVAL)
    ping_task = asyncio.create_task(_ping())
    try:
        return await aw
    finally:
        ping_task.cancel()


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
    logger.info(f"Pipeline started: query={query[:100]}")
    try:
        plan = await call_planner(query, api_key, planner_model, provider)
    except RuntimeError as e:
        logger.error(f"Planner failed: {e}")
        yield {"agent": "planner", "status": "error", "message": str(e)}
        return
    except Exception as e:
        logger.error(f"Planner failed unexpectedly: {e}")
        yield {"agent": "planner", "status": "error", "message": f"Planner failed unexpectedly: {e}"}
        return

    sub_tasks = plan.get("sub_tasks", [])
    logger.info(f"Planner completed: {len(sub_tasks)} sub-tasks")
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
            return await call_researcher(
                sub_task["description"],
                sub_task["search_query"],
                model,
                api_key,
                provider,
            )
        except Exception as e:
            logger.error(f"Research task failed: model={model} sub_task={sub_task.get('id','?')} error={e}")
            return {"error": str(e), "sub_task": sub_task}

    # Fire all tasks for both models simultaneously
    tasks = (
        [research_task(st, researcher_model_1) for st in sub_tasks]
        + [research_task(st, researcher_model_2) for st in sub_tasks]
    )
    results = await asyncio.gather(*tasks)

    findings = []
    errors = []
    seen_urls = set()

    for r in results:
        if "error" in r:
            errors.append(r["error"])
        else:
            for fact in r.get("findings", []):
                src = fact.get("source", "")
                if src not in seen_urls:
                    seen_urls.add(src)
                    findings.append({**fact, "model": r.get("model", "unknown")})

    logger.info(f"Researchers done: {len(findings)} findings, {len(errors)} errors")

    if findings:
        yield {
            "agent": "researcher",
            "status": "completed",
            "message": f"Merged {len(findings)} unique findings from both researchers",
            "findings": findings,
        }
    else:
        error_detail = "; ".join(errors[:3])
        logger.error(f"All researchers failed: {error_detail}")
        yield {"agent": "researcher", "status": "error", "message": f"All researchers failed: {error_detail}", "errors": errors}
        return

    # 3. Synthesizer
    yield {"agent": "synthesizer", "status": "started", "message": "Synthesizing answer..."}
    try:
        result = await call_synthesizer(query, findings, synthesizer_model, api_key, provider)
        logger.info(f"Synthesizer completed")
        yield {
            "agent": "synthesizer",
            "status": "completed",
            "message": "Synthesis complete",
            "result": result,
        }
    except RuntimeError as e:
        logger.error(f"Synthesizer failed: {e}")
        yield {"agent": "synthesizer", "status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Synthesizer failed unexpectedly: {e}")
        yield {"agent": "synthesizer", "status": "error", "message": f"Synthesizer failed unexpectedly: {e}"}
