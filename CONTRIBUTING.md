# Contributing

Use Python 3.12 or newer. Create an isolated environment, install development dependencies, and keep all
network activity out of unit tests:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
uv venv --python 3.12
uv pip install --python .venv/bin/python -e '.[dev,markets]'
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy --strict src
.venv/bin/pytest
```

Preserve the architecture boundaries: domain code is pure; adapters own I/O; jobs depend on protocols; the
CLI composes dependencies. Put user-specific lists, schedules, prompts, and channel names in example config,
not Python. New source types register in `jobs/sources.py`; new collector types register in `jobs/registry.py`.
Public APIs need type hints and docstrings. Add fixtures and tests for behavior, failure isolation, and input
validation. Never add real credentials, account identifiers, server addresses, or personal information.

Run pre-commit before opening a pull request. By contributing, you agree that your contribution is licensed
under MIT.
