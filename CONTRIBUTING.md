# Contributing

## Development Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## Common Commands

```bash
make test
make build
make clean
```

If you do not want to use `make`:

```bash
python -m pytest
python -m build
```

## Guidelines

- Keep changes focused and reviewable.
- Add or update tests for behavior changes.
- Update `README.md` when CLI behavior or setup changes.
- Do not commit secrets, auth files, or local Codex state.
- Be conservative around login, resume, and shell execution behavior.

## Pull Requests

- Explain the user-facing change clearly.
- Mention any limitations or non-obvious tradeoffs.
- Include verification notes when possible.
