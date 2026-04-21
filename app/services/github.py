import os
import logging
import subprocess
import tempfile
import shutil
import json
import urllib.request
from typing import Optional

logger = logging.getLogger("deepsearch.github")

GITHUB_PAT = os.environ.get("GITHUB_PAT", "")


def _require_pat() -> str:
    if not GITHUB_PAT:
        raise RuntimeError("GITHUB_PAT not set. Add it to Railway environment variables.")
    return GITHUB_PAT


def _git_config():
    return ["git", "-C"]


async def clone_repo(repo_url: str, target_dir: str) -> str:
    """Clone a GitHub repo to target_dir. Returns the repo name."""
    pat = _require_pat()
    auth_url = repo_url.replace("https://", f"https://x-access-token:{pat}@")
    logger.info(f"Cloning {repo_url} to {target_dir}")
    result = subprocess.run(
        ["git", "clone", "--depth=1", auth_url, target_dir],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr}")
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    logger.info(f"Cloned repo: {repo_name}")
    return repo_name


async def create_repo(repo_name: str, description: str = "") -> str:
    """Create a new public GitHub repo. Returns the repo URL."""
    pat = _require_pat()
    data = json.dumps({
        "name": repo_name,
        "description": description or f"Created by DeepSearch Coding Mode",
        "private": False,
        "auto_init": False,
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        data=data,
        headers={
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        return result["html_url"]
    except urllib.request.HTTPError as e:
        body = e.read().decode()
        if e.code == 422:
            raise RuntimeError(f"Repo '{repo_name}' already exists. Choose a different name.")
        raise RuntimeError(f"GitHub API error: {body}")


async def push_files(repo_url: str, branch: str, files: dict[str, str], commit_message: str, base_dir: Optional[str] = None):
    """
    Push files to a GitHub repo branch.
    repo_url: e.g. "https://github.com/user/repo" or "git@github.com:user/repo.git"
    files: {"/path/to/file.txt": "content", ...}
    base_dir: if provided, git operations happen inside this directory
    """
    pat = _require_pat()
    
    if base_dir is None:
        base_dir = tempfile.mkdtemp(prefix="deepsearch_push_")
        is_temp = True
    else:
        is_temp = False

    try:
        auth_url = repo_url.replace("https://github.com/", f"https://x-access-token:{pat}@github.com/")
        auth_url = auth_url.replace("git@github.com:", f"https://x-access-token:{pat}@github.com/")

        subprocess.run(["git", "-C", base_dir, "init"], capture_output=True, check=True)
        subprocess.run(
            ["git", "-C", base_dir, "remote", "add", "origin", auth_url],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "-C", base_dir, "config", "user.email", "deepsearch@coding.ai"],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "-C", base_dir, "config", "user.name", "DeepSearch Coding Mode"],
            capture_output=True, check=True,
        )

        for file_path, content in files.items():
            full_path = os.path.join(base_dir, file_path.lstrip("/"))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
            subprocess.run(["git", "-C", base_dir, "add", file_path.lstrip("/")], capture_output=True, check=True)

        subprocess.run(
            ["git", "-C", base_dir, "commit", "-m", commit_message],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "-C", base_dir, "push", "-u", "origin", f"HEAD:{branch}", "--force"],
            capture_output=True, check=True, timeout=60,
        )
        logger.info(f"Pushed {len(files)} files to {repo_url} branch {branch}")
    finally:
        if is_temp:
            shutil.rmtree(base_dir, ignore_errors=True)


async def init_new_repo(repo_name: str, description: str, files: dict[str, str], commit_message: str = "Initial commit from DeepSearch Coding Mode") -> str:
    """Create a new repo and push files. Returns the repo URL."""
    repo_url = await create_repo(repo_name, description)
    await push_files(repo_url, "main", files, commit_message)
    return repo_url


async def push_to_existing(repo_url: str, branch: str, files: dict[str, str], commit_message: str) -> str:
    """Clone existing repo, add files, push to branch. Returns the repo URL."""
    with tempfile.TemporaryDirectory(prefix="deepsearch_clone_") as tmpdir:
        repo_name = await clone_repo(repo_url, tmpdir)
        # Create branch if needed
        pat = _require_pat()
        user_resp = urllib.request.urlopen(
            urllib.request.Request(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"},
            )
        )
        user = json.loads(user_resp.read())
        username = user.get("login", "")
        repo_slug = repo_url.rstrip("/").replace("https://github.com/", "").replace(f"git@github.com:{username}/", "")
        
        # Check if branch exists
        check_req = urllib.request.Request(
            f"https://api.github.com/repos/{username}/{repo_slug}/branches/{branch}",
            headers={"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"},
        )
        branch_exists = True
        try:
            urllib.request.urlopen(check_req)
        except urllib.request.HTTPError:
            branch_exists = False

        await push_files(repo_url, branch, files, commit_message, base_dir=tmpdir)
        return repo_url
