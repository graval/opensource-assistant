import os
import json
import base64
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(title="OSS Contributor Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")


class RepoRequest(BaseModel):
    repo_url: str
    expert: Optional[bool] = False


CONTRIBUTION_STEPS = [
    {
        "step": 1,
        "title": "Fork the Repository",
        "summary": "Navigate to the project on GitHub and click 'Fork' to create an independent copy under your account."
    },
    {
        "step": 2,
        "title": "Change in Fork",
        "summary": "Clone your fork locally, branch off main (`git checkout -b fix/issue-name`), and make minimal, clean code changes."
    },
    {
        "step": 3,
        "title": "Test Thoroughly",
        "summary": "Run the project's test suite, linters, and type checkers locally to ensure no regressions or breakages."
    },
    {
        "step": 4,
        "title": "Capture Results & Evidence",
        "summary": "Record test execution logs, terminal outputs, or UI screenshots to provide concrete proof of verification."
    },
    {
        "step": 5,
        "title": "Raise PR with Test Evidence & Explanation",
        "summary": "Open a pull request from your branch to upstream, attaching your test evidence, problem explanation, and issue link."
    },
    {
        "step": 6,
        "title": "Address Review Comments",
        "summary": "Engage with maintainers, address feedback promptly, push updates to your PR branch, and ensure CI passes."
    }
]


def parse_github_url(url: str) -> tuple[str, str]:
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.replace("https://github.com/", "").replace("http://github.com/", "").split("/")
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL. Expected format: https://github.com/owner/repo")
    return parts[0], parts[1]


async def fetch_github(path: str) -> Any:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(f"https://api.github.com/{path}", headers={"Accept": "application/vnd.github+json"})
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail=f"GitHub resource not found: {path}")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"GitHub API error: {resp.text}")
        return resp.json()


async def fetch_readme(owner: str, repo: str, default_branch: str = "main") -> dict:
    try:
        data = await fetch_github(f"repos/{owner}/{repo}/readme")
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
        return {
            "content": content,
            "html_url": data.get("html_url") or f"https://github.com/{owner}/{repo}/blob/{default_branch}/README.md"
        }
    except Exception:
        return {
            "content": "",
            "html_url": f"https://github.com/{owner}/{repo}/blob/{default_branch}/README.md"
        }


async def fetch_contributing(owner: str, repo: str, default_branch: str = "main") -> dict:
    candidates = [
        "CONTRIBUTING.md",
        ".github/CONTRIBUTING.md",
        "docs/CONTRIBUTING.md",
        "contributing.md",
        "CONTRIBUTING.rst",
        "docs/contributing.rst",
        "oss-contributor-assistant/CONTRIBUTING.md",
    ]
    for path in candidates:
        try:
            data = await fetch_github(f"repos/{owner}/{repo}/contents/{path}")
            if isinstance(data, dict) and data.get("content"):
                content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
                return {
                    "content": content,
                    "html_url": data.get("html_url") or f"https://github.com/{owner}/{repo}/blob/{default_branch}/{path}"
                }
        except Exception:
            continue

    # Fallback to default expected URL if file isn't explicitly found
    return {
        "content": "",
        "html_url": f"https://github.com/{owner}/{repo}/blob/{default_branch}/CONTRIBUTING.md"
    }


async def fetch_license(owner: str, repo: str) -> str:
    try:
        data = await fetch_github(f"repos/{owner}/{repo}/license")
        return base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
    except Exception:
        return ""


async def fetch_issues(owner: str, repo: str) -> list[dict]:
    try:
        data = await fetch_github(f"repos/{owner}/{repo}/issues?state=open&per_page=25")
        if not isinstance(data, list):
            return []
        return [
            {
                "number": i.get("number"),
                "title": i.get("title"),
                "body": (i.get("body") or "")[:500],
                "labels": [l.get("name") for l in i.get("labels", []) if isinstance(l, dict)],
                "html_url": i.get("html_url"),
            }
            for i in data
            if "pull_request" not in i
        ]
    except Exception:
        return []


async def fetch_latest_commit(owner: str, repo: str, default_branch: str = "main") -> dict:
    try:
        data = await fetch_github(f"repos/{owner}/{repo}/commits?per_page=1")
        if isinstance(data, list) and len(data) > 0:
            c = data[0]
            sha = c.get("sha", "")
            commit_info = c.get("commit", {})
            committer = commit_info.get("committer", {}) or commit_info.get("author", {})
            return {
                "sha": sha,
                "short_sha": sha[:7] if sha else "N/A",
                "html_url": c.get("html_url") or f"https://github.com/{owner}/{repo}/commit/{sha}",
                "date": committer.get("date", ""),
                "message": (commit_info.get("message", "") or "").split("\n")[0],
            }
    except Exception:
        pass
    return {
        "sha": "",
        "short_sha": "N/A",
        "html_url": f"https://github.com/{owner}/{repo}/commits/{default_branch}",
        "date": "",
        "message": ""
    }


async def fetch_repo_info(owner: str, repo: str) -> dict:
    return await fetch_github(f"repos/{owner}/{repo}")


def evaluate_ai_policy(readme_text: str, contributing_text: str) -> dict:
    combined = (readme_text + "\n" + contributing_text).lower()

    # Explicit ban/prohibition
    negative_signals = [
        "no ai", "no llm", "ai-generated code is not accepted", "do not use ai",
        "no chatgpt", "no copilot", "ai generated prs will be closed",
        "automated prs will be closed", "prohibit ai", "ban ai", "ai code prohibited"
    ]
    for signal in negative_signals:
        if signal in combined:
            return {
                "status": "No",
                "badge": "no",
                "reason": "Repository guidelines explicitly restrict or discourage AI/LLM-generated code submissions."
            }

    # Disclosure or limited conditions
    limited_signals = [
        "disclosure", "disclose", "must state if ai", "ai-assisted", "ai policy",
        "mention if you used", "transparency", "co-authored-by"
    ]
    for signal in limited_signals:
        if signal in combined:
            return {
                "status": "Limited",
                "badge": "limited",
                "reason": "AI-assisted contributions are permitted only with explicit disclosure and documentation of AI tools used."
            }

    # CLA / DCO copyright obligations
    if "cla" in combined or "contributor license agreement" in combined or "dco" in combined or "developer certificate of origin" in combined:
        return {
            "status": "Limited",
            "badge": "limited",
            "reason": "Project enforces a CLA / DCO sign-off; contributors must legally certify originality and right to license all submitted code."
        }

    # No mention found in guidelines
    return {
        "status": "Unknown",
        "badge": "unknown",
        "reason": "No explicit AI code policy stated in README or CONTRIBUTING guidelines. Follow standard quality, testing, and originality rules."
    }


def select_easy_issue(issues: list[dict]) -> dict:
    if not issues:
        return {
            "number": None,
            "title": "No open issues found",
            "html_url": "",
            "labels": [],
            "why": "This repository currently has no open issues. Consider opening an issue proposing a small enhancement or documentation clarification."
        }

    # 1. Look for beginner labels
    beginner_tags = ["good first issue", "beginner", "help wanted", "easy", "starter", "up-for-grabs", "documentation", "docs"]
    for issue in issues:
        labels = [l.lower() for l in issue.get("labels", [])]
        for tag in beginner_tags:
            if any(tag in l for l in labels):
                matching_label = next(l for l in issue.get("labels", []) if tag in l.lower())
                return {
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "html_url": issue.get("html_url"),
                    "labels": issue.get("labels", []),
                    "why": f"Labeled with '{matching_label}', indicating an accessible scope and clear expectations for first-time contributors."
                }

    # 2. Look for documentation / typos / tests
    for issue in issues:
        title_lower = (issue.get("title") or "").lower()
        if any(keyword in title_lower for keyword in ["doc", "readme", "typo", "fix", "clean", "test", "example"]):
            return {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "html_url": issue.get("html_url"),
                "labels": issue.get("labels", []),
                "why": "Targeted scope (documentation, testing, or cleanup) with low risk of architectural regression."
            }

    # 3. Fallback to first available issue
    first = issues[0]
    return {
        "number": first.get("number"),
        "title": first.get("title"),
        "html_url": first.get("html_url"),
        "labels": first.get("labels", []),
        "why": "Identified as an approachable open issue to start exploring the project."
    }


async def get_ollama_model() -> str:
    env_model = os.getenv("OLLAMA_MODEL")
    if env_model:
        return env_model
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_HOST}/api/tags")
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", [])]
                for preferred in ["llama3.2:1b", "llama3.2:3b", "llama3.2", "llama3"]:
                    for m in models:
                        if preferred in m:
                            return m
                if models:
                    return models[0]
    except Exception:
        pass
    return "llama3.2:1b"


async def ask_ollama(prompt: str) -> str:
    model = await get_ollama_model()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            if resp.status_code != 200:
                return f"Ollama error ({resp.status_code}): {resp.text}"
            return resp.json().get("response", "")
    except httpx.TimeoutException:
        return "Ollama inference timed out after waiting for model response."
    except Exception as e:
        return f"Ollama unavailable: {repr(e)}"


def build_prompt(readme: str, license_text: str, issues: list[dict], repo_info: dict, user_level: str = "entry", contributing_text: str = "") -> str:
    issue_list = "\n".join(
        f"- #{i['number']}: {i['title']} | labels: {', '.join(i['labels']) or 'none'} | {i['html_url']}"
        for i in issues[:10]
    ) or "No open issues found."

    license_info = repo_info.get('license') or {}
    license_name = license_info.get('spdx_id') or 'N/A'

    return f"""
You are an open-source contributor assistant. The user level is "{user_level}".

Repository: {repo_info.get('full_name')}
Description: {repo_info.get('description') or 'N/A'}
Stars: {repo_info.get('stargazers_count', 0)}
License: {license_name}

README (truncated):
{readme[:2000]}

CONTRIBUTING (truncated):
{contributing_text[:1000]}

LICENSE (truncated):
{license_text[:1000]}

Open Issues:
{issue_list}

Tasks:
1. Summarize what this project does in 2-3 sentences.
2. Note if any AI/LLM code policies are mentioned or implied (Allowed, Limited, or Prohibited).
3. Explain how a {user_level} contributor can get started (build, test, first PR steps).
4. Suggest ONE beginner-friendly issue from the open issues above (prefer labels like "good first issue", "beginner", "help wanted"). If none match, pick the simplest-looking issue and explain why.
5. Give the exact steps to contribute (fork, clone, branch, commit, PR).

Be concise and practical. Output in clean markdown.
"""


@app.post("/analyze")
async def analyze(req: RepoRequest):
    try:
        owner, repo = parse_github_url(req.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Fetch repo metadata first to retrieve default_branch
    repo_info = await fetch_repo_info(owner, repo)
    default_branch = repo_info.get("default_branch") or "main"

    # Parallel fetch remaining assets
    readme_dict, contributing_dict, license_text, issues, latest_commit = await __import__("asyncio").gather(
        fetch_readme(owner, repo, default_branch),
        fetch_contributing(owner, repo, default_branch),
        fetch_license(owner, repo),
        fetch_issues(owner, repo),
        fetch_latest_commit(owner, repo, default_branch),
    )

    user_level = "intermediate/expert" if req.expert else "entry"
    prompt = build_prompt(
        readme_dict["content"],
        license_text,
        issues,
        repo_info,
        user_level=user_level,
        contributing_text=contributing_dict["content"]
    )
    summary = await ask_ollama(prompt)

    license_info = repo_info.get("license") or {}
    license_spdx = license_info.get("spdx_id") or "N/A"

    ai_policy = evaluate_ai_policy(readme_dict["content"], contributing_dict["content"])
    easy_issue = select_easy_issue(issues)

    now = datetime.now(timezone.utc)
    last_fetched = {
        "iso": now.isoformat(),
        "formatted": now.strftime("%b %d, %Y, %I:%M %p UTC")
    }

    result = {
        "repo": {
            "owner": owner,
            "name": repo,
            "full_name": repo_info.get("full_name") or f"{owner}/{repo}",
            "html_url": repo_info.get("html_url") or f"https://github.com/{owner}/{repo}",
            "default_branch": default_branch
        },
        "description": repo_info.get("description"),
        "stars": repo_info.get("stargazers_count", 0),
        "license": license_spdx,
        "last_fetched": last_fetched,
        "latest_commit": latest_commit,
        "ai_policy": ai_policy,
        "easy_issue": easy_issue,
        "contribution_steps": CONTRIBUTION_STEPS,
        "readme": readme_dict,
        "contributing": contributing_dict,
        "open_issues": issues,
        "summary": summary,
    }

    # Persist to filesystem
    safe_name = f"{owner}_{repo}".replace("/", "_")
    path = os.path.join(DATA_DIR, f"{safe_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


@app.get("/analyze/{owner}/{repo}")
async def get_cached(owner: str, repo: str):
    safe_name = f"{owner}_{repo}".replace("/", "_")
    path = os.path.join(DATA_DIR, f"{safe_name}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Not found")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Backfill fields for backwards compatibility with older cache files
    if "contribution_steps" not in data:
        data["contribution_steps"] = CONTRIBUTION_STEPS
    if "ai_policy" not in data:
        readme_c = data.get("readme", {}).get("content", "") if isinstance(data.get("readme"), dict) else ""
        contrib_c = data.get("contributing", {}).get("content", "") if isinstance(data.get("contributing"), dict) else ""
        data["ai_policy"] = evaluate_ai_policy(readme_c, contrib_c)
    if "easy_issue" not in data:
        data["easy_issue"] = select_easy_issue(data.get("open_issues", []))
    if "last_fetched" not in data:
        data["last_fetched"] = {"iso": "", "formatted": "Cached locally"}
    if "latest_commit" not in data:
        data["latest_commit"] = {"sha": "", "short_sha": "N/A", "html_url": "", "date": "", "message": ""}
    if "readme" not in data or isinstance(data.get("readme"), str):
        data["readme"] = {"content": data.get("readme") or "", "html_url": f"https://github.com/{owner}/{repo}"}
    if "contributing" not in data:
        data["contributing"] = {"content": "", "html_url": f"https://github.com/{owner}/{repo}"}

    return data


@app.get("/health")
async def health():
    return {"status": "ok"}


FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=True)
