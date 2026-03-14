# Contributing to SkyFi Remote MCP Server

Thank you for your interest in contributing. This document gives a short overview of how to contribute.

## Development setup

1. **Clone and install**
   - Python 3.10+ required.
   - `python3 -m venv .venv && source .venv/bin/activate` (or equivalent on Windows).
   - `pip install -r requirements.txt`
   - Copy `.env.example` to `.env` and set `X_SKYFI_API_KEY` and `SKYFI_API_BASE_URL` (or use `config/credentials.json`; see `config/credentials.json.example`).

2. **Run tests**
   - `pytest` (from project root; `pytest.ini` sets `pythonpath = .`).
   - Target coverage is ≥80%. Use `pytest --cov=src --cov-report=term-missing` to check.

3. **Code style**
   - Keep the **thin MCP layer** rule: tool handlers in `src/tools/` should only validate input and delegate to `src/services/`. No business logic in tool files.
   - Use type hints and docstrings for public functions. See existing `src/services/` and `src/tools/` modules for patterns.
   - Lint and format: `ruff check . --fix` and `ruff format .` (config in `pyproject.toml`). The hygiene ratchet is `pytest tests/test_hygiene.py`; keep budgets monotonic.

## What to contribute

- **Bug fixes:** Prefer a small, focused change with a test that reproduces the bug and passes after the fix.
- **New behavior or tools:** Align with the PRD and execution plan in `docs/`. For new MCP tools, add:
  - Service layer in `src/services/` (or extend an existing service).
  - Thin tool handler in `src/tools/`.
  - Registration in `src/server.py`.
  - Tests in `tests/` (service tests and tool registration at minimum).
- **Docs:** Integration guides live under `docs/integrations/`; index is `docs/integrations.md`. Keep README and integration docs in sync with the tool list.

## Submitting changes

1. Open an issue or discussion first if the change is large or ambiguous.
2. Make your changes on a branch; run `pytest` and fix any regressions.
3. Submit a pull request with a clear description of what changed and why.
4. Maintainers will review and may request edits.

## Security

Please do **not** report security vulnerabilities in public issues. See [SECURITY.md](SECURITY.md) for how to report them privately.

## License

By contributing, you agree that your contributions will be licensed under the same [MIT License](LICENSE) that covers this project.
