# Development Setup for Teammates

## Clone
```bash
git clone https://github.com/Magic-Chen-CZC/Yoyo
cd Yoyo
```

## Python environment
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Local environment variables
```bash
cp .env.example .env
```
Then fill in the required keys locally. Do **not** commit `.env`.

## Local infra
```bash
docker compose up -d
.venv/bin/alembic upgrade head
```

## Start app
```bash
.venv/bin/uvicorn yoyo.app:app --reload
```

## Tests
```bash
.venv/bin/pytest
```

## Required local keys (as needed)
- `TAVILY_API_KEY`
- `OPENROUTER_API_KEY`
- `EVAL_OPENROUTER_API_KEY`
- optionally other provider keys depending on current benchmark plan

## Read first
Before coding, read in this order:
1. `CLAUDE.md`
2. `README.md`
3. `docs/architecture.md`
4. `docs/contracts.md`
5. `docs/collaboration.md`
6. `docs/todo.md`
7. `docs/model-evaluation.md`

## Collaboration note
- Shared overlap contracts must stay stable.
- Avoid editing migrations, shared enums, or router wiring casually in parallel.
