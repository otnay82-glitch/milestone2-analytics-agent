# Architecture and Trust Boundaries

## 1. System Overview

The Delivery Analytics Agent consists of a Streamlit user interface, a FastAPI backend, an analytics agent, a SQL validation layer, a Neon PostgreSQL Gold database, and a SQLite conversation store.

The application is designed for read-only shipment analytics. It is not intended to modify shipment records or act as a general-purpose assistant.

## 2. Data Flow

1. A user submits a question through the Streamlit UI.
2. The UI sends the request to the FastAPI backend using a bearer token.
3. The backend authenticates the token and resolves the user identity server-side.
4. For conversation operations, the backend verifies that the authenticated user owns the requested conversation.
5. The agent checks scope and constructs a plan for a supported analytics question.
6. The plan guard checks whether the proposed plan is allowed.
7. The SQL builder generates a query for the supported analytics intent.
8. The SQL guard validates the query before database execution.
9. The query service executes the validated query through the database layer.
10. The agent prepares an answer from the query result and returns the answer, data basis, and outcome to the UI.
11. Conversation messages are persisted in SQLite.

## 3. Trust Boundaries

### User and UI boundary

User messages are untrusted input. The UI is a client, not an authorization authority. A user-supplied conversation identifier must not bypass server-side ownership checks.

The UI must not connect directly to Neon or contain database credentials.

### API identity boundary

The backend maps configured demo bearer tokens to server-side user identities. Invalid or missing credentials are rejected. Conversation access must be scoped to the authenticated identity.

Demo tokens are suitable for the milestone demonstration only; they are not a production identity-management solution.

### Agent and model boundary

The language model may help interpret a question and plan a supported analytics query. Its output is not trusted SQL and must pass the plan guard, SQL builder, SQL guard, and query-service checks before execution.

Out-of-scope requests should be refused without querying Gold. If the required information is missing or ambiguous, the agent should abstain or ask for clarification rather than invent a result.

### Database and retrieved-data boundary

Neon Gold is the source of business facts. The database connection should use a role with read-only permissions limited to the required Gold tables.

Database validation and database permissions are separate controls: SQL validation does not replace least-privilege database access.

The `exception_note` column is untrusted data. Text in a note must not be treated as an instruction to override system rules, reveal secrets, or execute a write operation.

### Conversation-storage boundary

SQLite stores conversation history, not shipment analytics. Conversation operations must enforce ownership in the backend. The Docker Compose configuration mounts the SQLite database path on a named volume to support persistence across container restarts.

## 4. SQL and Execution Controls

The intended query path is:

`Question -> Scope Guard -> Planner -> Plan Guard -> SQL Builder -> SQL Guard -> Query Service -> Read-only Database`

The SQL guard checks that a query is a permitted single-statement `SELECT`, uses approved tables and columns, and excludes disallowed operations and functions. The database layer also configures read-only transaction behavior and a statement timeout. Query results are bounded.

The database role must independently restrict access to the approved Gold data. Do not use an administrative database credential for agent-generated queries.

## 5. Gold Data Sources

| Table | Grain | Purpose |
|---|---|---|
| `gold.shipment_fact` | One row per shipment | Shipment details, delivery timestamps, status, fees, refunds, and exception notes |
| `gold.carrier_daily` | Order date and carrier | Daily carrier aggregates |
| `gold.city_daily` | Order date and destination city | Daily destination-city aggregates |

Carrier and city aggregates must not be summed together. On-time rate uses delivered shipments as its denominator, and in-transit shipments must not automatically be classified as late.

## 6. Failure and Abstention Behavior

The agent should not fabricate an answer when data is missing, outside the supported period, or ambiguous. Out-of-scope requests should be refused without executing an analytics query.

Authentication failures, ownership failures, database errors, and provider failures should not expose credentials, connection strings, system prompts, or another user's conversation content.

## 7. Production Considerations

This milestone uses demo bearer tokens and SQLite conversation storage. Before production use, the design would need an appropriate identity provider, secure token lifecycle management, durable shared storage, defined retention and deletion policies, centralized audit logging, monitoring, rate limiting, secret management, and broader security and regression testing.
