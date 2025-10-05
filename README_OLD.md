# labyrinth-temporal-hunt

Production-grade Python 3.11 project scaffold with Streamlit UI, LangGraph skeleton, and pluggable LLM agents (Mistral, Gemini). Uses pip tooling and Docker.

## Structure

- `src/gsm/` — Core domain models and simulation/temporal logic
- `src/agents/` — Agent interfaces and implementations + prompts
- `src/graph/` — LangGraph-based orchestration stubs
- `src/ui/` — Streamlit UI entrypoint
- `src/infra/` — Settings and shared infrastructure
- `tests/` — Test skeletons
- `ADRs/` — Architecture Decision Records

## Quickstart

1) Install Python 3.11 and pip.

2) Create a virtual environment and install dependencies:
```
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

3) Configure environment:
```
cp .env.example .env
# Edit .env with your keys and settings
```

4) Run Streamlit app:
```
export PYTHONPATH=$(pwd)/src
streamlit run src/ui/app.py
```

5) Run tests:
```
export PYTHONPATH=$(pwd)/src
pytest -q
```

## Docker

Build and run with Docker:
```
docker build -t labyrinth-temporal-hunt:latest .
docker run --rm -it -p 8501:8501 --env-file .env labyrinth-temporal-hunt:latest
```

Or via Compose:
```
docker compose up --build
```

## Makefile-like Commands

- Install:
```
pip install -r requirements.txt
```

- Lint (placeholder):
```
python -m pip install ruff && ruff check src tests
```

- Format (placeholder):
```
python -m pip install ruff black && black src tests && ruff check --fix src tests
```

- Test:
```
pytest -q --cov=src --cov-report=term-missing
```

- Run UI:
```
streamlit run src/ui/app.py
```

- Run UI with performance (optional uvloop on Unix):
```
PYTHONASYNCIODEBUG=0 streamlit run src/ui/app.py
```

## Notes

- `uvloop` is included and will be enabled automatically on compatible platforms at runtime.
- LangGraph usage is scaffolded; fill in real nodes/edges and handlers in `src/graph/turn_loop.py`.
- Agents require API keys (`.env`) to function.
