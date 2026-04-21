import asyncio
import logging
import tempfile
import os
from typing import Optional, AsyncIterator

from app.agents.architect import run_architect
from app.agents.coder import run_coder
from app.services.github import clone_repo, push_to_existing, init_new_repo

logger = logging.getLogger("deepsearch.coding_pipeline")


async def run_coding_pipeline(
    description: str,
    github_url: Optional[str],
    zai_api_key: str,
    moonshot_api_key: str,
    github_pat: str,
) -> AsyncIterator[dict]:
    files = {}
    repo_dir = None
    repo_url = None

    try:
        yield {
            "agent": "pipeline",
            "status": "started",
            "message": "Starting coding pipeline...",
        }

        if github_url:
            yield {
                "agent": "pipeline",
                "status": "progress",
                "message": f"Cloning repo: {github_url}",
            }
            repo_dir = tempfile.mkdtemp(prefix="deepsearch_clone_")
            await clone_repo(github_url, repo_dir)
            yield {
                "agent": "pipeline",
                "status": "progress",
                "message": "Repo cloned successfully",
            }

        yield {
            "agent": "architect",
            "status": "started",
            "message": "Architect is analyzing request and writing SPEC.md...",
        }
        arch_result = await run_architect(
            description=description,
            github_url=github_url,
            api_key=zai_api_key,
        )
        yield {
            "agent": "architect",
            "status": "completed",
            "project_name": arch_result.get("project_name", ""),
            "tech_stack": arch_result.get("tech_stack", []),
            "spec": arch_result.get("spec", ""),
        }

        yield {
            "agent": "coder",
            "status": "started",
            "message": "Coder is implementing files...",
        }
        coder_result = await run_coder(
            description=description,
            spec=arch_result.get("spec", ""),
            github_url=github_url,
            repo_dir=repo_dir,
            api_key=moonshot_api_key,
        )
        files = coder_result.get("files", {})
        yield {
            "agent": "coder",
            "status": "completed",
            "file_count": len(files),
            "files": files,
        }

        if files:
            yield {
                "agent": "github",
                "status": "started",
                "message": "Pushing to GitHub...",
            }

            if github_url:
                repo_url = await push_to_existing(
                    repo_url=github_url,
                    branch="main",
                    files=files,
                    commit_message=f"Update from DeepSearch Coding Mode: {description[:100]}",
                )
            else:
                project_name = arch_result.get("project_name", "deepsearch-project")
                repo_url = await init_new_repo(
                    repo_name=project_name,
                    description=description[:200],
                    files=files,
                    commit_message=f"Initial commit from DeepSearch Coding Mode: {description[:100]}",
                )

            yield {
                "agent": "github",
                "status": "completed",
                "repo_url": repo_url,
            }

        yield {
            "agent": "pipeline",
            "status": "completed",
            "repo_url": repo_url,
            "files": files,
        }

    except Exception as e:
        logger.error(f"Coding pipeline error: {e}", exc_info=True)
        yield {
            "agent": "pipeline",
            "status": "error",
            "message": str(e),
        }
    finally:
        if repo_dir and os.path.exists(repo_dir):
            import shutil
            shutil.rmtree(repo_dir, ignore_errors=True)