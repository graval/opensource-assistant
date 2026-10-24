# OSS Contributor Assistant

Hacktoberfest 2026 project — helps newcomers find their first open-source contribution.

Paste a GitHub repo URL → get README/LICENSE summary + beginner-friendly issue suggestion.

## Run

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Pull a local model (run once)
ollama pull llama3.2:3b

# 3. Start backend
cd backend
python app.py   # or: uvicorn app:app --reload

# 4. Open frontend/index.html in your browser
```

## Endpoints

- `POST /analyze` — body: `{ "repo_url": "https://github.com/owner/repo" }`
- `GET /analyze/{owner}/{repo}` — cached result
- `GET /health`

Data is persisted to `data/<owner>_<repo>.json`.
