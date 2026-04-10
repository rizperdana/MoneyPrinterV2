# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the application code. Use `src/main.py` as the interactive entrypoint.
- `src/classes/` holds provider-specific components (for example `YouTube.py`, `Twitter.py`, `Tts.py`, `AFM.py`, `Outreach.py`).
- Shared utilities and configuration live in modules like `src/config.py`, `src/utils.py`, `src/cache.py`, and `src/constants.py`.
- `src/research.py` — topic research via Tavily, Exa, Wikipedia, Google Trends, ddgs (Bing), Firecrawl.
- `src/llm_generate.py` — LLM prompt/response orchestration (topic, script, metadata, image prompts).
- `src/llm_provider.py` — cliproxyapi LLM client with model routing per job type.
- `src/db.py` — SQLite in-memory ORM for tracking topics, videos, and accounts.
- `scripts/` contains helper workflows such as setup, preflight checks, and upload helpers.
- `docs/` contains feature documentation; `assets/` and `fonts/` contain static resources.

## Build, Test, and Development Commands
- `bash scripts/setup_local.sh`: bootstrap local development (creates `venv`, installs deps, seeds `config.json`, runs preflight).
- `source venv/bin/activate && pip install -r requirements.txt`: manual dependency install/update.
- `python3 scripts/preflight_local.py`: validate local provider/config readiness before running tasks.
- `python3 src/main.py`: start the CLI app.
- `bash scripts/upload_video.sh`: run direct script-based upload flow from repo root.

## Coding Style & Naming Conventions
- Target Python 3.12 (project requirement in `README.md`).
- Use 4-space indentation and follow existing Python conventions:
  - `snake_case` for functions/variables
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants
- Keep new business logic in focused modules under `src/`; keep provider/integration code in `src/classes/`.
- Prefer small, explicit functions and preserve existing CLI-first behavior.

## Programming Practices

### Module Responsibilities
| Module | Responsibility |
|--------|----------------|
| `llm_provider.py` | Single API client for all LLM calls. Handles HTTP, retries, spinner, model selection. **No prompt logic here.** |
| `llm_generate.py` | Constructs prompts and parses responses. Calls `llm_provider` for generation. **No HTTP here.** |
| `research.py` | Topic/data gathering from external sources. Returns raw text for `llm_generate` to process. |
| `db.py` | SQLite ORM (in-memory). Tracks topics, videos, accounts. **No business logic.** |
| `config.py` | Configuration loading and access. |
| `classes/*.py` | Platform-specific integrations (YouTube, Twitter, etc.). |

### LLM Integration Pattern
1. **`llm_provider.py`** owns the API call: timeout, spinner, error handling, model routing.
2. **`llm_generate.py`** owns the prompt: system prompt, user prompt construction, response parsing.
3. Each public function in `llm_generate.py` maps to one `job` type used by `get_model_for_job()`.
4. Job types: `topic`, `script`, `seo_tags`, `image_prompts`, `title_desc`.
5. Model routing is defined in `MODEL_ROUTING` dict in `llm_provider.py` — fast/reliable models first, slow ones last.
6. Never call `generate_text()` directly from `llm_generate.py` — always through the job-specific helpers.

### Research Integration Pattern
1. `research.py` returns raw text from external sources.
2. `llm_generate.py` passes research context to LLM for topic/script generation.
3. Random angle modifiers in prompts ensure different results each run.
4. Fallback chain: Tavily → Exa → ddgs (Bing) → Wikipedia → Google Trends → Firecrawl.

### Database Pattern
- `db.py` uses SQLite in-memory only (no persistent `.db` file).
- Tables: `topics`, `videos`, `accounts`.
- Functions return typed results (`list[dict]`, `int`, `bool`).
- No raw SQL outside `db.py`.

### Error Handling
- Wrap LLM calls in try/except with user-friendly error messages.
- JSONDecodeError on large LLM responses → retry once with reduced prompt or increased parse tolerance.
- Never expose raw API keys or internal paths in error messages.

### Logging & Status Output
- Use `status.print_step()`, `status.print_info()`, `status.print_success()`, `status.print_error()` for consistent CLI output.
- No `print()` for normal flow — only `status.*` or `logging`.

### Configuration
- `config.json` is environment-specific; never commit secrets.
- Prefer environment variables over hardcoded keys (e.g., `CLIPROXY_API_KEY`, `GEMINI_API_KEY`).
- Use `config.example.json` as the template for new environments.

## Testing Guidelines
- There is currently no enforced automated test suite or coverage threshold.
- Minimum validation for changes:
  - Run `python3 scripts/preflight_local.py`
  - Smoke-test impacted flows via `python3 src/main.py`
- When adding tests, place them in a top-level `tests/` directory with names like `test_<module>.py`.

## Commit & Pull Request Guidelines
- Follow the existing commit style: imperative summaries like `Fix ...`, `Update ...`, optionally with issue refs (for example `(#128)`).
- Open PRs against `main`.
- Link each PR to an issue, keep scope to one feature/fix, and use a clear title + description.
- Mark not-ready PRs with `WIP` and remove it when ready for review.

## Security & Configuration Tips
- Treat `config.json` as environment-specific; do not commit real API keys or private profile paths.
- Start from `config.example.json` and prefer environment variables where supported (for example `GEMINI_API_KEY`).
