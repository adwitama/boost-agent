# Implementation Plan

## Architecture choice
Use **Python 3.11+ with official `mcp` Python SDK v2** (`from mcp.server import MCPServer`). Use stdio locally for the minimal demonstration and the MCP Inspector for verification. An MCP-compatible LLM host is an optional presentation layer; the tool services and tests should run independently of the host. Use SQLite for budget state, proposals and audit logs; JSON seed files for fixture data. Add `pytest` and Pydantic for deterministic validation.

Three logical MCP tool groups may be implemented as **one local MCP process** for minimal demo friction, namespaced tools (`ads_*`, `book_*`, `growth_*`). The conceptual deck shows three services as modular boundaries; deployment as separate server processes is not necessary for the MVP. Explain this choice in README. Do not create a new custom web dashboard.

## Layers
1. **Adapters**: `MockAdsRepository` and `MockBookRepository` read fixtures; mutable campaign budgets live in SQLite. Real adapters are separate interfaces, unimplemented.
2. **Domain/analytics**: `campaign_economics`, `audit_rules`, `recommendations`; pure functions, no LLM numeric calculations.
3. **Policy/execution**: verifies actor scopes, hotel budget, proposal freshness and optimistic version; records approval; executes mock update transaction; audit log + verification.
4. **MCP presentation**: typed tool schemas, grounded structured responses, explicit `data_mode=demo`.
5. **Optional LLM host**: agent instructions route tasks to tools and label evidence, estimates and approvals.

## Policies
- The backend is the source of truth for `actor_id`, `roles`, `assigned_hotels`; for demo a fixed authenticated local persona is acceptable, but it must not be overwritable by user prompts.
- A proposal requires existing campaign IDs in **same hotel** and matching budget snapshot/version; amount positive and ≤ authorized maximum; unchanged sum and nonnegative final balances.
- Approval records an approval event and locks proposal intent. Execution requires approved proposal ID and idempotency key; don't accept free-form target budgets from the LLM write call.
- Proposals expire after configurable time (e.g., 15min), and cannot be executed after state version changes.
- Reset only with local dev flag; warning printed when reset.

## Data fixture strategy
Populate 25 fictional Japanese hotels. Kyoto Riverside must have two meaningful campaigns with explicit bookings meeting the numeric example. Other 24 have small fabricated campaigns; inject at least 8 deterministic issue cases (pacing, cancellation rate, missing attribution, report due). Each issue includes a rule ID and evidence fields. Avoid PII. Mark all files demo-only.

## Test strategy
- Unit: ROAS, cancellation filters, contribution.
- Policy: cross-hotel, large amount, insufficient budget, unauthorized actor, stale version, repeat, expired, not approved.
- Integration: MCP tool invocation via SDK in-memory client or Inspector; state changes via SQLite verified.
- End-to-end transcript: two prompts lead to expected tool usage, reports, receipts; AI text grounded in returned data.

## Build order
Tools/fixtures → deterministic calculations → portfolio audit → proposal/approval/write state machine → MCP transport → example prompts, report generator, tests.

## Deliverable structure recommendation
```
tripla-boost-agent/
  pyproject.toml
  README.md
  src/boost_agent/server.py
  src/boost_agent/domain/{analytics,policies}.py
  src/boost_agent/adapters/{ads_mock,book_mock}.py
  src/boost_agent/storage.py
  data/{hotels,campaigns,bookings}.json
  tests/{test_economics,test_policies,test_mcp}.py
  reports/                  # ignored demo output
  .env.example             # only if LLM integration used
```

## Open technical decisions for coder
1. Use either SDK in-memory client or Inspector tests for MCP v2. Avoid v1 `FastMCP` imports unless pinned intentionally.
2. Internal identity: local mocked specialist principal; no real user login in MVP. Server enforces hardcoded authorized hotel IDs.
3. Monthly-budget mapping: mock uses monthly allocation; production platform APIs require mapping to actual daily/shared budget semantics.
4. If LLM host lacks ability to connect local stdio tools, validate with MCP Inspector and record the tool trace; do not invent a host connection.
