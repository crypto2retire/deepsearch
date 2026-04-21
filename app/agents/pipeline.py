import asyncio
import logging
from typing import AsyncGenerator
from app.agents.planner import call_planner
from app.agents.researcher import call_researcher
from app.agents.synthesizer import call_synthesizer
from app.skills import get_skill

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
    default_api_key: str,
    default_provider: str,
    planner_model: str,
    planner_provider: str,
    planner_api_key: str,
    researcher_model_1: str,
    researcher_provider_1: str,
    researcher_api_key_1: str,
    researcher_model_2: str,
    researcher_provider_2: str,
    researcher_api_key_2: str,
    synthesizer_model: str,
    synthesizer_provider: str,
    synthesizer_api_key: str,
    skill_id: str = "general",
) -> AsyncGenerator[dict, None]:
    """
    Run the full pipeline: planner -> 2 parallel researchers -> synthesizer.
    Each agent can use its own provider and API key.
    """
    def _key(agent_key: str) -> str:
        return agent_key or default_api_key

    def _prov(agent_prov: str) -> str:
        return agent_prov or default_provider

    skill = get_skill(skill_id)
    logger.info(f"Pipeline started: query={query[:100]} skill={skill.id}")

    # 1. Planner
    yield {"agent": "planner", "status": "started", "message": "Planning research approach..."}
    try:
        plan = await call_planner(query, _key(planner_api_key), planner_model, _prov(planner_provider), system_prompt=skill.get_planner_prompt())
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

    researcher_prompt = skill.get_researcher_prompt()

    async def research_task(sub_task: dict, model: str, provider: str, api_key: str) -> dict:
        try:
            return await call_researcher(
                sub_task["description"],
                sub_task["search_query"],
                model,
                api_key,
                provider,
                system_prompt=researcher_prompt,
            )
        except Exception as e:
            logger.error(f"Research task failed: model={model} provider={provider} sub_task={sub_task.get('id','?')} error={e}")
            return {"error": str(e), "sub_task": sub_task}

    tasks = (
        [research_task(st, researcher_model_1, _prov(researcher_provider_1), _key(researcher_api_key_1)) for st in sub_tasks]
        + [research_task(st, researcher_model_2, _prov(researcher_provider_2), _key(researcher_api_key_2)) for st in sub_tasks]
    )
    results = await asyncio.gather(*tasks)

    # Build research bundles: group findings and snippets by sub-task
    # Each sub-task gets findings from both researchers + their search snippets
    sub_task_map = {}
    for r in results:
        if "error" in r:
            continue
        st_desc = r.get("sub_task", "")
        if st_desc not in sub_task_map:
            sub_task_map[st_desc] = {
                "sub_task": st_desc,
                "findings": [],
                "search_snippets": [],
                "sources_seen": set(),
            }
        bundle = sub_task_map[st_desc]
        # Deduplicate findings by source URL
        for fact in r.get("findings", []):
            src = fact.get("source", "")
            if src and src not in bundle["sources_seen"]:
                bundle["sources_seen"].add(src)
                bundle["findings"].append({**fact, "model": r.get("model", "unknown")})
        # Deduplicate snippets by URL
        for snippet in r.get("search_results", []):
            url = snippet.get("url", "")
            if url and url not in bundle["sources_seen"]:
                bundle["sources_seen"].add(url)
                bundle["search_snippets"].append(snippet)

    research_bundles = list(sub_task_map.values())
    # Clean up internal set before sending to synthesizer
    for bundle in research_bundles:
        del bundle["sources_seen"]

    all_findings = []
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
                    all_findings.append({**fact, "model": r.get("model", "unknown")})

    logger.info(f"Researchers done: {len(all_findings)} findings, {len(errors)} errors across {len(research_bundles)} sub-tasks")

    if all_findings:
        yield {
            "agent": "researcher",
            "status": "completed",
            "message": f"Merged {len(all_findings)} unique findings from both researchers",
            "findings": all_findings,
        }
    else:
        error_detail = "; ".join(errors[:3])
        logger.error(f"All researchers failed: {error_detail}")
        yield {"agent": "researcher", "status": "error", "message": f"All researchers failed: {error_detail}", "errors": errors}
        return

    # 3. Synthesizer -- two-pass: organize findings, then write report
    yield {"agent": "synthesizer", "status": "started", "message": "Synthesizing answer..."}
    try:
        result = await call_synthesizer(
            query,
            research_bundles,
            all_findings,
            synthesizer_model,
            _key(synthesizer_api_key),
            _prov(synthesizer_provider),
            system_prompt=skill.get_synthesizer_prompt(),
        )
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
