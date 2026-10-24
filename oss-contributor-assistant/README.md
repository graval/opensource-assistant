# OSS Contributor Assistant

A Hacktoberfest 2026 project that helps newcomers find their first open-source contribution. 

Paste a GitHub repository URL, and the assistant will analyze the repo's README, LICENSE, and open issues using a local LLM (via [Ollama](https://ollama.com/)) to generate a beginner-friendly summary and suggest a suitable first issue to work on.

## Features

- **Repo Analysis**: Fetches README, LICENSE, repository metadata, and open issues from GitHub
- **AI-Powered Guidance**: Uses Ollama to generate actionable advice tailored to entry-level contributors
- **Beginner-Friendly Suggestions**: Prioritizes issues labeled `good first issue`, `beginner`, or `help wanted`
- **Caching**: Results are saved as JSON in the `data/` directory for quick retrieval
- **Simple UI**: Clean Tailwind CSS frontend with markdown rendering

## Prerequisites

- [Python 3.8+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/download) installed and running locally
- Internet connection (for GitHub API and initial model download)

## Installation & Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Ollama model

Pull the default model (run once):

```bash
ollama pull llama3.2:3b
```

You can use a different model by setting the `OLLAMA_MODEL` environment variable.

### 3. Start the backend

```bash
cd backend
python app.py
# or run with hot reload:
# uvicorn app:app --reload
```

The API will be available at `http://localhost:8000` by default.

### 4. Open the frontend

Open `frontend/index.html` directly in your browser, or serve it with a local web server:

```bash
# From the project root
python -m http.server 8080
# Then navigate to http://localhost:8080/frontend/
```

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/analyze` | Analyze a repo. Body: `{"repo_url": "https://github.com/owner/repo"}` |
| `GET` | `/analyze/{owner}/{repo}` | Retrieve cached analysis for a repo |
| `GET` | `/health` | Health check endpoint |

## Configuration

You can configure the app using environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `OLLAMA_HOST` | `http://localhost:11434` | URL of your Ollama instance |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model to use for analysis |

## Data Storage

Analysis results are persisted to `data/<owner>_<repo>.json` as JSON files for caching and offline access.

## Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/), [httpx](https://www.python-httpx.org/), [Uvicorn](https://www.uvicorn.org/)
- **Frontend**: Vanilla HTML/JS, [Tailwind CSS](https://tailwindcss.com/), [Marked.js](https://marked.js.org/)
- **LLM**: [Ollama](https://ollama.com/) (local inference)
