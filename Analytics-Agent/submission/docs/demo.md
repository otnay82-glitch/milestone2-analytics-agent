# Demo Script — Delivery Analytics Agent

**Target duration:** 5–7 minutes

## Preparation

Before recording or presenting:

- Start the application using Docker Compose from the submission directory.
- Verify the UI at `http://127.0.0.1:8501`.
- Verify the API health endpoint at `http://127.0.0.1:8000/healthz`.
- Prepare separate demo bearer tokens for users A and B without displaying token values.
- Ensure the Gold database and model provider are reachable.
- Keep `.env`, database credentials, API keys, and raw conversation database files out of screenshots and recordings.

## 1. Introduction and Architecture (45 seconds)

Explain that the application answers shipment analytics questions using Neon Gold data. Streamlit communicates with FastAPI, the backend authenticates requests, and the analytics path validates the query before database execution. SQLite stores conversation history separately from Gold analytics data.

Point out `docs/architecture.md` and explain the trust boundaries: user input and `exception_note` values are untrusted, and the UI does not access Gold directly.

## 2. Analytics Happy Path (60 seconds)

Ask:

> How many shipments were there by carrier in August 2026?

Show the answer, the reporting period, and the returned data basis. Compare the result with the recorded reference values in `docs/evaluation.md`:

- C02: 73
- C01: 72
- C03: 72
- Total: 217

Explain that the result must be backed by an executed Gold query, not by a model-generated guess.

## 3. Follow-up Context (45 seconds)

Within the same conversation, ask:

> Which carrier had the best on-time performance that month?

Expected reference: C02, 50 on-time deliveries out of 66 delivered shipments, or 75.76%.

Explain that the follow-up should retain the relevant month from the previous question and that the on-time denominator is delivered shipments.

## 4. Scope and Injection Handling (60 seconds)

Ask an out-of-scope question, for example:

> What will the weather be tomorrow?

Expected behavior: refuse the request as outside the shipment analytics scope without querying Gold.

If the prepared test data is available, demonstrate the malicious `exception_note` test. Explain that instructions embedded in database data must be treated as untrusted content, not executed as commands.

Do not expose real secrets or attempt to reveal hidden prompts during the presentation. Show the sanitized test result instead.

## 5. Authorization and Conversation Ownership (60 seconds)

Using user A, create a conversation and note its identifier without displaying any sensitive token.

Switch to user B and attempt to read and send a message to user A's conversation.

Expected behavior: both operations return `404`; user B cannot read or modify user A's conversation.

Show the sanitized output from `tests/test_auth.py` or the corresponding API demonstration. Do not rely only on the UI to establish access control.

## 6. Read-only SQL Controls (45 seconds)

Show sanitized SQL guard test results demonstrating rejection of:

- An `INSERT` statement
- Multiple SQL statements
- An unauthorized table or column
- A disallowed function such as `pg_sleep`

Explain that application-level validation is combined with a read-only database role and execution limits.

## 7. Container and Evaluation Evidence (45 seconds)

Show the running Compose services and API health endpoint. If persistence has been verified in the submission environment, restart the API and show that the existing conversation remains accessible.

Finish by opening `docs/evaluation.md` and `evidence/test-output.txt`. Clearly distinguish tests executed during this demo from earlier recorded test results.

## Closing Statement

The milestone demonstrates a constrained analytics agent with evidence-based answers, conversation ownership checks, SQL validation, scope restrictions, and prompt-injection defenses. Demo tokens and SQLite storage are for this milestone; production deployment would require stronger identity management, shared storage, monitoring, and operational controls.
