# Single Prompt for Cursor / Claude Code / Copilot / Codex

Copy everything below into your coding agent **with this entire spec pack placed in the project folder**:

---

You are a senior AI platform engineer. Build the **tripla Boost Agent MCP-first DEMO**, not a dashboard or a slide mockup. Read and obey `specs/001-boost-mcp-agent/spec.md`, `plan.md`, `tasks.md`, `contracts/tools.json` and all JSON fixtures before coding.

**Your deliverable is running code, not just documentation.** Use Python 3.11+, the current official MCP Python SDK v2 (`MCPServer` import), standard local `stdio` transport, SQLite, Pydantic and pytest. Expose real MCP tools via one local process organized into three named groups: Ads, Book, Growth. It is fine to implement one physical MCP server as long as all tool boundaries are clear. Never build an operator UI. Make it testable with MCP Inspector, and optionally connect to an MCP-compatible LLM host where the environment supports it.

A. Pillar 1 must work: audit 25 fictional hotel accounts, join mock ad and booking metrics, explain anomalies with evidence, prioritize actions, and export a monthly report. No actual ad campaign mutations.

B. Pillar 2 must work: for Kyoto Riverside compare two real fixture-derived campaigns, calculate gross ROAS, cancellation-adjusted retained value and contribution; generate an explicit ¥30k *experimental* within-hotel monthly budget shift proposal; require a server-enforced approval; execute only through a mock Ads adapter; verify persisted budgets and append audit events. Never claim incremental bookings were generated just because a budget changed.

C. Add negative cases: missing approval, replay, cross-hotel action, overspend, stale version, unauthorized user, expired proposal. Ensure all tests pass. Currency is integer JPY. Data is always tagged `DEMO DATA` and contains no PII. Tool outputs distinguish observed mock metrics, estimates and not-yet-measured outcomes.

D. Do not use a live Google Ads write tool. Google's official Ads MCP is currently read-only. Keep all external platform connectors simulated. Do not invent tripla Book API endpoints.

E. Finish with a README containing exact setup and run steps, the full MCP tool list, a reproducible test command, a reset command, and a scripted 5-minute interview demonstration with two user prompts and expected tool calls. If an LLM client cannot connect to local tools in your environment, show the equivalent workflow using MCP Inspector instead of claiming chat integration.

Run the tests and report their real results. Do not stop after scaffolding; implement the entire P0 acceptance criteria.

---
