# Delivery Analytics Agent — Phase 2 Milestone 2

## 1. Overview

This project provides a conversational analytics agent for synthetic shipment-delivery data stored in Neon PostgreSQL Gold tables. Users ask operational questions in natural language, and the backend validates and executes read-only analytics queries before returning evidence-based answers.

The application consists of:
- **Streamlit UI** (`app.py`)
- **FastAPI backend** (`src/api.py`)
- **Analytics agent and query planning** (`src/agent.py`, `src/planner.py`, `src/llm_planner.py`)
- **SQL validation and query execution** (`src/sql_guard.py`, `src/query_service.py`, `src/db.py`)
- **Bearer-token demo authentication** (`src/auth.py`)
- **SQLite conversation storage** (`src/conversation_store.py`)

The Gold database is the source of business facts. SQLite stores conversation history; it is not an analytics data source.

## 2. Requirements

- Python 3.11 or newer
- Docker Engine/Desktop with Docker Compose v2 for container deployment
- A Neon PostgreSQL connection restricted to read-only access to the required Gold tables
- An OpenAI API key and configured model for LLM-backed operation

## 3. Configuration

Create a local `.env` file from `.env.example` and populate it with valid runtime values. Never commit `.env` or put credentials in source code, screenshots, logs, or the Docker image.

Required variables:

| Variable | Purpose |
|---|---|
| `GOLD_DATABASE_URL` | PostgreSQL connection string for a read-only Gold database role |
| `OPENAI_API_KEY` | API credential for the configured OpenAI provider |
| `OPENAI_MODEL` | Model name; the current example uses `gpt-5-mini` |
| `DEMO_TOKEN_A` | Non-empty bearer token for demo user A |
| `DEMO_TOKEN_B` | A distinct, non-empty bearer token for demo user B |
| `SQLITE_PATH` | Path to the SQLite conversation database |
| `AGENT_API_URL` | Backend URL used by the Streamlit UI |

For local execution, `AGENT_API_URL` normally uses `http://localhost:8000`.

The Docker Compose configuration sets the UI's backend URL to `http://api:8000` and directs SQLite storage to `/app/data/conversations.sqlite3`.

Use a read-only database role as well as backend SQL validation. Do not use an administrator connection for model-generated queries.

## 4. Run locally

Run commands from the `submission/` directory.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

Copy-Item .env.example .env
# Edit .env locally and supply valid credentials.

$env:AGENT_API_URL = "http://localhost:8000"

# Terminal 1: start the API
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000

# Terminal 2: activate the same environment and start the UI
python -m streamlit run app.py
```

If `.env` already exists, do not overwrite it with the template. Make sure its values are configured locally before starting the application.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

test -f .env || cp .env.example .env
# Edit .env locally and supply valid credentials.

export AGENT_API_URL=http://localhost:8000

# Terminal 1: start the API
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000

# Terminal 2: activate the same environment and start the UI
python -m streamlit run app.py
```

Open the Streamlit URL printed in the terminal, normally `http://localhost:8501`.

The API health endpoint is `http://localhost:8000/healthz`.

## 5. Run with Docker Compose

From the `submission/` directory:

1. Create `.env` from `.env.example` if it does not exist.
2. Fill in valid runtime credentials in `.env`.
3. Build and start both services.

### Windows PowerShell

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
# Edit .env before starting the services.
docker compose up --build
```

### macOS / Linux

```bash
test -f .env || cp .env.example .env
# Edit .env before starting the services.
docker compose up --build
```

Open:
- UI: `http://127.0.0.1:8501`
- API health: `http://127.0.0.1:8000/healthz`

The Compose configuration uses a named volume for SQLite conversation persistence. Restart the API and verify that an existing conversation remains accessible. Avoid `docker compose down -v` until persistence checks are complete, because removing volumes deletes their stored data.

## 6. Tests

The test files are standalone Python scripts. They are not a pytest test suite.

Install the project dependencies and configure the environment required by each test before running it. Run tests from the `submission/` directory.

### Windows PowerShell

```powershell
$env:PYTHONPATH = (Get-Location).Path

python tests\test_sql_guard.py
python tests\test_sql_functions.py
python tests\test_query_service.py
python tests\test_plan_guard.py
python tests\test_scope_guard.py
python tests\test_agent_scope.py
python tests\test_exception_injection.py
python tests\test_exception_notes.py
python tests\test_followup.py
python tests\test_agent.py
python tests\test_llm_planner.py
python tests\test_message_api.py
python tests\test_auth.py
```

Some tests require database or provider connectivity, valid environment configuration, or specific demo tokens. Record the actual output and result for each test in `evidence/test-output.txt` and `docs/evaluation.md`. Do not mark a test as passing unless it was executed successfully in the recorded environment.

## 7. Analytics data and metric definitions

The application uses these Gold tables:

- `gold.shipment_fact`: shipment-level details, timestamps, status, fees, refunds, and exception notes.
- `gold.carrier_daily`: daily aggregates by carrier.
- `gold.city_daily`: daily aggregates by destination city.

The dataset covers order dates from 1 July through 20 September 2026.

Important metric rules:
- On-time rate uses delivered shipments as the denominator.
- A shipment still in transit is not automatically classified as late.
- Refund rate is total refund amount divided by total shipping fees.
- Use the appropriate date and aggregation grain for the question.
- Never add carrier-level and city-level aggregates together, because doing so can double-count facts.
- If data is missing, outside the supported period, or ambiguous, abstain or ask for clarification instead of inventing a result.

Refer to `docs/architecture.md` and `docs/evaluation.md` for the implementation design and evaluation evidence.

## 8. Security boundaries

- The backend maps demo bearer tokens to user identities.
- Conversation access must be checked against the authenticated owner for list, read, and send operations.
- SQL must be validated before execution and restricted to approved Gold tables and columns.
- Database execution must remain read-only and use execution limits.
- Treat user messages and database `exception_note` values as untrusted input, never as instructions that override the agent's security rules.
- Out-of-scope requests must be refused without querying Gold.
- Keep database credentials and provider keys out of the UI, Docker build context, and submitted evidence.

These demo controls are not a substitute for production identity management or a formal security review.

## 9. Limitations and production considerations

This is a milestone implementation using demo bearer tokens, a local SQLite conversation store, and a constrained set of supported analytics queries.

Before production use, evaluate and implement as appropriate:
- Enterprise identity and token lifecycle management
- Shared, backed-up conversation storage with defined retention and deletion policies
- Secret management and credential rotation
- Centralized audit logging, monitoring, and alerting
- Stronger workload isolation, rate limits, and resource controls
- Expanded evaluation coverage and regression testing
- Privacy, security, availability, and operational reviews

The application should not be treated as a general-purpose assistant or as an interface for modifying shipment records.
