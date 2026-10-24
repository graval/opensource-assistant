# Agentic Development Guide (`AGENTS.md`)

This document outlines the operational rules, architecture standards, coding principles, and guidelines for AI coding agents and automated workflows contributing to the **OSS Contributor Assistant** repository.

---

## 1. Core Mission & Scope

The **OSS Contributor Assistant** is designed to reduce the barrier of entry for open-source newcomers by:
1. Fetching project metadata, documentation, license, and open issues from git repositories (GitHub).
2. Leveraging local or remote LLMs (Ollama, Gemini, etc.) to analyze repo context.
3. Generating tailored, step-by-step onboarding guidance and recommending beginner-friendly issues (`good first issue`, `help wanted`).
4. Caching analysis runs to prevent redundant remote requests and enable offline retrieval.

---

## 2. Architectural Blueprint

The application follows a clean 3-tier structure with separation between interface, service logic, and storage:

```
[ Frontend: Tailwind + Marked.js ]
              │ (HTTP JSON)
              ▼
[ FastAPI Application (backend/app.py) ]
    ├── Router & Static File Mount
    ├── GitHub Client & Ingestion Service
    ├── Prompt Builder & Context Synthesizer
    └── LLM Provider Client (Ollama / Local Inference)
              │
              ▼
[ Local Persistence (`data/<owner>_<repo>.json`) ]
```

---

## 3. SOLID Principles & Engineering Standards

When expanding or refactoring this codebase, autonomous agents must adhere to standard object-oriented and functional software design principles:

### S — Single Responsibility Principle (SRP)
- **Problem to avoid**: Monolithic route handlers doing network calls, prompt building, formatting, and disk writes in one function.
- **Guideline**: Keep concerns separated into distinct modules:
  - `GitHubClient`: Interacts with GitHub REST API endpoints.
  - `PromptBuilder`: Structures input prompt text from repository signals.
  - `LLMProvider`: Manages communication, timeouts, and fallbacks with the language model runtime.
  - `AnalysisRepository`: Handles reading/writing cache files under `data/`.

### O — Open/Closed Principle (OCP)
- Core workflow logic must be open for extension but closed for modification.
- Adding a new LLM provider (e.g., Google Gemini, OpenAI, Claude, or llama.cpp directly) must not require modifying existing route definitions. Providers should adhere to a shared abstract protocol or base class (`BaseLLMProvider`).

### L — Liskov Substitution Principle (LSP)
- Any LLM provider implementation (e.g. `OllamaProvider`, `GeminiProvider`, `MockLLMProvider`) must be interchangeable without breaking expectations or changing route contract behavior.

### I — Interface Segregation Principle (ISP)
- Do not force clients or services to depend on methods they do not use. Keep client protocols targeted:
  - `LLMClientProtocol`: `async def generate(self, prompt: str) -> str`
  - `GitHostProtocol`: `async def fetch_repository(self, owner: str, repo: str) -> RepoData`

### D — Dependency Inversion Principle (DIP)
- High-level business logic must depend on abstractions, not concrete implementations.
- Utilize FastAPI's `Depends(...)` dependency injection mechanism to inject `LLMProvider` and `GitHostClient` into route endpoints.

---

## 4. Recommended Design Patterns

| Pattern | Application in this Codebase |
| :--- | :--- |
| **Factory Pattern** | Used to instantiate the active LLM provider (e.g. `LLMProviderFactory.create(config)`) based on environment configuration (`OLLAMA_MODEL`, `LLM_BACKEND`). |
| **Repository Pattern** | Decouples filesystem JSON caching from HTTP route handlers, enabling seamless migration to Redis, SQLite, or object storage if needed. |
| **Strategy Pattern** | Varies prompt generation strategies based on user proficiency (`entry` vs `expert`). |
| **Adapter Pattern** | Normalizes differences between multiple git hosts (e.g., GitHub, GitLab, Gitea) into a unified internal data model. |

---

## 5. Agent Workflow & Operational Protocol

When executing autonomous development tasks:

1. **Understand Before Modifying**:
   - Inspect existing files, configuration defaults, and tests before making code changes.
   - Retain backward compatibility with existing endpoints (`/analyze`, `/health`, `/analyze/{owner}/{repo}`).

2. **Sandbox & Network Awareness**:
   - Remember that local servers running in isolated environments must have proper host/port binding (`127.0.0.1` or `0.0.0.0`).
   - Always verify that LLM requests have appropriate timeouts (`timeout=60.0` or higher) and handle network timeouts (`httpx.TimeoutException`) gracefully without crashing the server.

3. **Data Integrity & Git Hygiene**:
   - **Never** commit generated analysis data (`data/*.json`) or logs to git.
   - Verify changes with `.gitignore` before concluding tasks.
   - Never write hardcoded credentials, tokens, or API keys into source files.

4. **Preserve Documentation**:
   - Maintain docstrings and clear comments explaining non-trivial logic.
   - Update `README.md` whenever new features, endpoints, or environment variables are introduced.

---

## 6. Testing & Quality Assurance

- Always verify that the FastAPI backend starts without syntax or import errors.
- Test endpoints with both valid inputs and edge cases:
  - Repositories without README files.
  - Repositories without open issues or licenses (`NoneType` safety).
  - Malformed GitHub URLs (`400 Bad Request`).
  - Model timeout or connection failure (graceful fallback message).
- For automated testing, use `pytest` with `pytest-asyncio` and `httpx.AsyncClient`. Mock external network calls to GitHub and Ollama.
