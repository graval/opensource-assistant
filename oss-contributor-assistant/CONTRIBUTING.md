# Contributing to OSS Contributor Assistant

Thank you for your interest in contributing to **OSS Contributor Assistant**! Whether you are participating in Hacktoberfest, making your very first open-source pull request, or adding major architectural enhancements, we welcome your contributions.

---

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for everyone, regardless of experience level, gender identity, sexual orientation, disability, personal appearance, race, ethnicity, or religion. Please be respectful and constructive in all discussions and pull requests.

---

## Quick Start Development Setup

### 1. Prerequisites
- **Python 3.8+**
- **Git**
- **Ollama** installed and running locally ([Download Ollama](https://ollama.com/download))

### 2. Fork and Clone
```bash
# Clone your fork
git clone https://github.com/<your-username>/oss-contributor-assistant.git
cd oss-contributor-assistant
```

### 3. Create a Virtual Environment & Install Dependencies
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 4. Pull a Recommended Local LLM
For fast, responsive local inference on CPU or GPU, pull `llama3.2:1b` (or `llama3.2:3b`):
```bash
ollama pull llama3.2:1b
```

### 5. Start the Application
```bash
cd backend
python app.py
```
Open your browser to **[http://localhost:8001](http://localhost:8001)**. The web UI and backend API will both be live and ready for testing!

---

## How to Contribute

### 1. Find or Propose an Issue
- Check open issues with labels like `good first issue`, `help wanted`, or `enhancement`.
- If proposing a new feature or reporting a bug, please open an issue first so we can discuss the approach.

### 2. Branching & Commits
- Create a focused branch off `main`:
  ```bash
  git checkout -b feature/your-feature-name
  ```
- Write clear, concise commit messages following [Conventional Commits](https://www.conventionalcommits.org/):
  - `feat: add support for gitlab repository URLs`
  - `fix: handle repositories with no license gracefully`
  - `docs: update setup instructions in README`
  - `refactor: extract LLM client into dedicated module`

### 3. Development Guidelines
- **SOLID Principles**: Keep components modular and single-purpose. Refer to [`AGENTS.md`](file:///C:/workspaceai/opencode/hacktober/oss-contributor-assistant/AGENTS.md) for architecture guidelines.
- **Error Handling**: Handle external API failures (GitHub rate limits, missing files, network timeouts) gracefully.
- **Git Hygiene**: Do not commit cached JSON files in `data/`, virtual environments, or logs. Ensure your `.gitignore` is respected.

### 4. Pull Request Checklist
Before submitting your PR:
- [ ] Code runs locally without errors.
- [ ] Both `/health` and `/analyze` endpoints function correctly.
- [ ] No temporary files or caches (`data/*.json`, `.env`) are staged.
- [ ] Relevant documentation or comments have been updated.
- [ ] PR title is descriptive and references any related issue (e.g. `Fixes #12`).

---

## Community & Questions

Have questions or need help getting started? Feel free to open a discussion or ask questions directly on your issue or pull request. Happy hacking!
