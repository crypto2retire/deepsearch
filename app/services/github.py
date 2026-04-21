import os
import json
import logging
import base64
from typing import Optional

import httpx

logger = logging.getLogger("deepsearch.github")

GITHUB_PAT = os.environ.get("GITHUB_PAT", "")
GITHUB_API = "https://api.github.com"


def _require_pat() -> str:
    if not GITHUB_PAT:
        raise RuntimeError("GITHUB_PAT not set. Add it to Railway environment variables.")
    return GITHUB_PAT


def _headers(pat: str) -> dict:
    return {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }


def _parse_repo_slug(repo_url: str) -> str:
    slug = repo_url.rstrip("/").replace("https://github.com/", "").replace("git@github.com:", "")
    if slug.endswith(".git"):
        slug = slug[:-4]
    return slug


async def _get_user(pat: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{GITHUB_API}/user", headers=_headers(pat))
        resp.raise_for_status()
        return resp.json()["login"]


async def create_repo(repo_name: str, description: str = "") -> str:
    pat = _require_pat()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{GITHUB_API}/user/repos",
            headers=_headers(pat),
            json={
                "name": repo_name,
                "description": description or "Created by DeepSearch Coding Mode",
                "private": False,
                "auto_init": True,
            },
        )
        if resp.status_code == 422:
            raise RuntimeError(f"Repo '{repo_name}' already exists.")
        resp.raise_for_status()
        return resp.json()["html_url"]


async def push_files(repo_slug: str, branch: str, files: dict[str, str], commit_message: str) -> str:
    """
    Push files to a GitHub repo branch using the Git Data REST API.
    No git CLI required.

    repo_slug: "owner/repo" format
    files: {"path/to/file.py": "content", ...}
    """
    pat = _require_pat()
    headers = _headers(pat)

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Get the ref for the branch
        resp = await client.get(f"{GITHUB_API}/repos/{repo_slug}/git/ref/heads/{branch}", headers=headers)
        if resp.status_code == 404:
            # Branch doesn't exist, try main
            resp = await client.get(f"{GITHUB_API}/repos/{repo_slug}/git/ref/heads/main", headers=headers)
        resp.raise_for_status()
        ref = resp.json()
        base_commit_sha = ref["object"]["sha"]

        # 2. Get the commit to find its tree
        resp = await client.get(f"{GITHUB_API}/repos/{repo_slug}/git/commits/{base_commit_sha}", headers=headers)
        resp.raise_for_status()
        base_tree_sha = resp.json()["tree"]["sha"]

        # 3. Create blobs for each file
        blob_shas = {}
        for file_path, content in files.items():
            resp = await client.post(
                f"{GITHUB_API}/repos/{repo_slug}/git/blobs",
                headers=headers,
                json={"content": content, "encoding": "utf-8"},
            )
            resp.raise_for_status()
            blob_shas[file_path] = resp.json()["sha"]

        # 4. Create a new tree
        tree_items = [
            {
                "path": path.lstrip("/"),
                "mode": "100644",
                "type": "blob",
                "sha": sha,
            }
            for path, sha in blob_shas.items()
        ]
        resp = await client.post(
            f"{GITHUB_API}/repos/{repo_slug}/git/trees",
            headers=headers,
            json={"base_tree": base_tree_sha, "tree": tree_items},
        )
        resp.raise_for_status()
        new_tree_sha = resp.json()["sha"]

        # 5. Create a commit
        resp = await client.post(
            f"{GITHUB_API}/repos/{repo_slug}/git/commits",
            headers=headers,
            json={
                "message": commit_message,
                "tree": new_tree_sha,
                "parents": [base_commit_sha],
            },
        )
        resp.raise_for_status()
        new_commit_sha = resp.json()["sha"]

        # 6. Update the branch ref
        resp = await client.patch(
            f"{GITHUB_API}/repos/{repo_slug}/git/refs/heads/{branch}",
            headers=headers,
            json={"sha": new_commit_sha, "force": False},
        )
        resp.raise_for_status()

    logger.info(f"Pushed {len(files)} files to {repo_slug} branch {branch}")
    return f"https://github.com/{repo_slug}"


async def init_new_repo(repo_name: str, description: str, files: dict[str, str], commit_message: str = "Initial commit from DeepSearch Coding Mode") -> str:
    pat = _require_pat()
    username = await _get_user(pat)
    repo_url = await create_repo(repo_name, description)
    repo_slug = f"{username}/{repo_name}"
    await push_files(repo_slug, "main", files, commit_message)
    return repo_url


async def push_to_existing(repo_url: str, branch: str, files: dict[str, str], commit_message: str) -> str:
    repo_slug = _parse_repo_slug(repo_url)
    await push_files(repo_slug, branch, files, commit_message)
    return repo_url
