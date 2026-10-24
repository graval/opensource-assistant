# OSS Contributor Assistant

A modern open-source tool built to help newcomers find their first open-source contribution and navigate codebases with confidence.

Paste any public GitHub repository URL, and the assistant fetches the repository's README, license, metadata, and open issues, then uses a local LLM (via [Ollama](https://ollama.com/)) to generate a beginner-friendly summary, contribution steps, and suggest an accessible first issue to tackle.

---

## Features

- **Automated Repo Analysis**: Fetches repository metadata, README, LICENSE, and open issues via the GitHub API.
- **AI-Powered Contributor Guidance**: Uses a local LLM via Ollama to generate actionable advice tailored to your experience level (entry-level or expert).
- **First Issue Recommendations**: Identifies issues with labels like `good first issue`, `beginner`, or `help wanted`.
- **Offline Caching**: Results are stored as structured JSON in the `data/` directory for fast re-access.
- **Single-Server Deployment**: FastAPI automatically mounts and serves the Tailwind CSS web interface at the root URL.
- **Dynamic Model Selection**: Auto-detects installed Ollama models (`llama3.2:1b`, `llama3.2:3b`, etc.) with intelligent fallback.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│               Frontend (Tailwind + Marked.js)          │
│               Served at http://localhost:8001/         │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP POST /analyze
                           ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Server (backend/app.py)          │
│  ├── StaticFiles (mounts frontend)                     │
│  ├── GitHub Ingestion (httpx async client)             │
│  ├── Context Synthesizer & Prompt Builder              │
│  └── Dynamic Ollama LLM Client                         │
└──────────────┬───────────────────────────┬─────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   Ollama Local Runtime   │  │   Cached File Storage    │
│   (llama3.2:1b / 3b)     │  │   data/<owner>_<repo>.json│
└──────────────────────────┘  └──────────────────────────┘
```

The codebase is structured following **SOLID principles** and standard design patterns to facilitate autonomous agentic and human development. See [`AGENTS.md`](./AGENTS.md) for architectural details.

---

## Prerequisites

- [Python 3.8+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/download) installed and running locally
- Internet connection (for GitHub API queries and initial model download)

---

## Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/oss-contributor-assistant.git
cd oss-contributor-assistant
```

### 2. Set up virtual environment & install dependencies
```bash
# Create virtual environment
python -m venv .venv

# Activate it:
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Pull a recommended local model
For lightweight and fast local inference on CPU or GPU, pull `llama3.2:1b` (or `llama3.2:3b`):
```bash
ollama pull llama3.2:1b
```
*Note: The assistant will automatically detect installed models, or you can override it with the `OLLAMA_MODEL` environment variable.*

### 4. Start the application
```bash
cd backend
python app.py
```

The application is now accessible at **[http://localhost:8001](http://localhost:8001)** (serving both the interactive web UI and API).

---

## Configuration

You can customize the application using environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8001` | Port on which the FastAPI application and UI will listen |
| `OLLAMA_HOST` | `http://localhost:11434` | URL of your local Ollama instance |
| `OLLAMA_MODEL` | `llama3.2:1b` | Target Ollama model name (auto-detects if unset) |

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web UI (served via FastAPI static files) |
| `GET` | `/health` | Health check endpoint returning `{"status": "ok"}` |
| `POST` | `/analyze` | Analyze a repository (`{"repo_url": "https://github.com/owner/repo", "expert": false}`) |
| `GET` | `/analyze/{owner}/{repo}` | Retrieve cached JSON analysis for a previously analyzed repository |

---

## Project Structure

```
oss-contributor-assistant/
├── backend/
│   └── app.py            # FastAPI server, GitHub fetching, Ollama integration, static mount
├── frontend/
│   └── index.html        # Responsive web interface with Tailwind CSS and Marked.js
├── data/
│   ├── .gitkeep          # Directory placeholder (cached JSON ignored by git)
│   └── ...               # Persisted analysis results (e.g. octocat_Hello-World.json)
├── AGENTS.md             # Autonomous development guide & SOLID principles documentation
├── CONTRIBUTING.md       # Contribution guidelines, workflow, and PR checklist
├── LICENSE               # MIT License
├── README.md             # Project documentation and setup guide
├── requirements.txt      # Python dependencies
└── .gitignore            # Git exclusion rules ensuring only code is tracked
```

---

## Contributing

We welcome contributions! Please review [`CONTRIBUTING.md`](./CONTRIBUTING.md) for development workflows, coding standards, and pull request guidelines.

If you are developing autonomously using AI agents, please consult [`AGENTS.md`](./AGENTS.md) for architectural and safety specifications.

---

## License

This project is licensed under the [MIT License](./LICENSE).
