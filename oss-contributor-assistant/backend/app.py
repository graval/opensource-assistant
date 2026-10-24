import os
import json
import httpx
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


def parse_github_url(url: str) -> tuple[str, str]:
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL")
    return parts[0], parts[1]


async def fetch_github(path: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(f"https://api.github.com/{path}", headers={"Accept": "application/vnd.github+json"})
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail=f"GitHub resource not found: {path}")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"GitHub API error: {resp.text}")
        return resp.json()


async def fetch_readme(owner: str, repo: str) -> str:
    try:
        data = await fetch_github(f"repos/{owner}/{repo}/readme")
        import base64
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
        return content
    except HTTPException:
        return ""


async def fetch_license(owner: str, repo: str) -> str:
    try:
        data = await fetch_github(f"repos/{owner}/{repo}/license")
        import base64
        return base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
    except HTTPException:
        return ""


async def fetch_issues(owner: str, repo: str) -> list[dict]:
    try:
        data = await fetch_github(f"repos/{owner}/{repo}/issues?state=open&per_page=20")
        return [
            {
                "number": i.get("number"),
                "title": i.get("title"),
                "body": (i.get("body") or "")[:500],
                "labels": [l.get("name") for l in i.get("labels", [])],
                "html_url": i.get("html_url"),
            }
            for i in data
            if "pull_request" not in i
        ]
    except HTTPException:
        return []


async def fetch_repo_info(owner: str, repo: str) -> dict:
    return await fetch_github(f"repos/{owner}/{repo}")


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


def build_prompt(readme: str, license_text: str, issues: list[dict], repo_info: dict, user_level: str = "entry") -> str:
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

LICENSE (truncated):
{license_text[:1000]}

Open Issues:
{issue_list}

Tasks:
1. Summarize what this project does in 2-3 sentences.
2. Explain how a {user_level} contributor can get started (build, test, first PR steps).
3. Suggest ONE beginner-friendly issue from the open issues above (prefer labels like "good first issue", "beginner", "help wanted"). If none match, pick the simplest-looking issue.
4. Give the exact steps to contribute (fork, clone, branch, commit, PR).

Be concise and practical. Output in markdown.
"""


@app.post("/analyze")
async def analyze(req: RepoRequest):
    try:
        owner, repo = parse_github_url(req.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    repo_info, readme, license_text, issues = await __import__("asyncio").gather(
        fetch_repo_info(owner, repo),
        fetch_readme(owner, repo),
        fetch_license(owner, repo),
        fetch_issues(owner, repo),
    )

    user_level = "intermediate/expert" if req.expert else "entry"
    prompt = build_prompt(readme, license_text, issues, repo_info, user_level=user_level)
    summary = await ask_ollama(prompt)

    license_info = repo_info.get("license") or {}
    license_spdx = license_info.get("spdx_id") or "N/A"

    result = {
        "repo": {"owner": owner, "name": repo, "full_name": repo_info.get("full_name")},
        "description": repo_info.get("description"),
        "stars": repo_info.get("stargazers_count", 0),
        "license": license_spdx,
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
        return json.load(f)


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
