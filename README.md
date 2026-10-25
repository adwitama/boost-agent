# tripla Boost MCP Agent — DEMO DATA only

This is a local, fixture-only MCP demonstration for tripla Boost specialists. It contains no credentials, no live booking integration, and no real advertising mutation. Proposal and approval steps update local demo state, report generation writes local Markdown and CSV files, and simulated campaign budget execution requires server-enforced approval.

## Setup

Install **uv** first using the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/). For example, on macOS or Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows PowerShell, the official installer command is:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Open a new terminal if needed, then check that `uv --version` works. From the repository root, `uv sync` creates the project environment and installs its dependencies; it does not install uv itself.

```bash
uv sync --extra dev
```

The server uses stdio, so run it through your LLM client rather than leaving it running in a separate terminal. Add it from the repository root so the server uses this repo's SQLite state and report directory.

**Connection status:** Codex CLI has been verified with the current server: it connected and called `ads.list_managed_hotels`, returning 25 hotels marked **DEMO DATA**. That check used a temporary read-tool allowlist and approval override; it did not change saved Codex settings. MCP Inspector CLI has also been verified for tool discovery, the hotel-list call, and reading the hotel campaign resource template. Claude Code remains unverified. In interactive Codex, approve the tool call if the client asks.

The root [AGENTS.md](AGENTS.md) gives compatible coding agents persona, evidence, and workflow guidance. It guides the LLM client; it does not configure the MCP server or force every MCP host to follow the sequence. The server separately exposes reusable MCP prompts for clients that support them. For Claude Code, which uses `CLAUDE.md` for project instructions, copy or import the relevant guidance there if you want the same persistent instructions in Claude sessions.

### Codex CLI

```bash
codex mcp add tripla-boost-agent -- uv run --directory "$PWD" --project "$PWD" python -m boost_agent.server
codex mcp list
```

Start or restart Codex from this repository. In the Codex TUI, use `/mcp` to confirm the server is connected.

### Claude Code

```bash
claude mcp add --scope local tripla-boost-agent -- uv run --directory "$PWD" --project "$PWD" python -m boost_agent.server
claude mcp get tripla-boost-agent
```

Start Claude Code from this repository, approve the server if prompted, then use `/mcp` to confirm it is connected. The local scope keeps this server private to this project on your machine. See the [Codex MCP setup guide](https://developers.openai.com/codex/mcp/) and [Claude Code MCP guide](https://code.claude.com/docs/en/mcp) for client-specific options.

## Test

```bash
uv run python -m unittest discover -s tests -v
```

For Inspector, run `uv run mcp dev server.py` from the repository root. The available tools are `ads.list_managed_hotels`, `ads.get_portfolio_campaign_summary`, `ads.get_campaign_performance`, `ads.get_campaign_budget`, `book.get_reservations`, `book.get_portfolio_retained_outcomes`, `growth.calculate_campaign_economics`, `growth.audit_portfolio`, `growth.generate_monthly_report`, `growth.propose_reallocation`, `growth.approve_proposal`, `ads.execute_mock_reallocation`, `growth.get_audit_log`, and `growth.reset_demo`.

Inspector also exposes two reusable prompts: `review_managed_portfolio` for a read-only portfolio review, and `plan_kyoto_budget_test` for comparing the Kyoto campaigns and framing a proposed test without approving or executing it.

The Resources panel exposes `boost://demo/overview` (scope and safety notes), `boost://demo/managed-hotels` (the assigned hotel fixture), and `boost://demo/campaign-summary` (campaign rows for the default reporting window). These are read-only DEMO DATA resources. The Resource Templates panel exposes `boost://demo/hotels/{hotel_id}/campaign-performance`; substitute a managed hotel ID such as `JP-KYO-001` and read `boost://demo/hotels/JP-KYO-001/campaign-performance` to get that hotel's campaign performance. Unknown or unassigned hotel IDs are rejected by the same authorization checks used by the tools.

Reset a local database with `uv run boost-agent reset`. All responses carry `data_mode: demo` and a `DEMO DATA` marker.

`book.get_portfolio_retained_outcomes` accepts a single hotel (`{"hotel_id":"JP-KYO-001"}`), a list (`{"hotel_ids":["JP-KYO-001","JP-DEMO-002"]}`), or no arguments to return outcomes for all managed hotels.

## Portfolio review demonstration (no budget changes)

In Codex or Claude Code, ask these in order:

1. **List hotels:** “List all managed hotels. Include hotel IDs and names, and mark the results as DEMO DATA.” Expected tool: `ads.list_managed_hotels`.
2. **List campaigns:** “List all campaign fixture records. Include campaign IDs, hotel IDs, platform, the precomputed 30-day spend, and monthly budget. If the data does not include campaign status, say you cannot confirm which campaigns are running.” Expected tool: `ads.get_portfolio_campaign_summary`.
3. **Audit, draft reports, and actions:** “Audit all 25 hotels for the last 30 days; draft reports and actions—do not execute.” Expected read and report-generation workflow:

   ```text
   ads.list_managed_hotels
   ads.get_portfolio_campaign_summary
   book.get_portfolio_retained_outcomes
   growth.audit_portfolio(period="last_30_days")
   growth.generate_monthly_report(hotel_id="all", period="YYYY-MM")
   ```

   The campaign summary and audit scan the static synthetic fixtures. Campaign rows contain precomputed `spend_30d_jpy`; `date_from` and `date_to` are echoed as metadata and do not filter dated records. The audit's `last_30_days` is a period label, not a date-window filter. Have the assistant summarize alerts with hotel/campaign IDs, evidence, and suggested follow-up actions, while describing them as fixture-based findings. Label all results **DEMO DATA** and keep historical attribution separate from measured incremental results.

   The report tool writes local Markdown and CSV files. Its `YYYY-MM` argument labels the report and filenames; it does not filter the fixtures to that calendar month. State these limits clearly. Do not call `growth.propose_reallocation`, `growth.approve_proposal`, or `ads.execute_mock_reallocation` in this read-only demonstration.

The separate Kyoto budget-test prompt is for a later workflow. Historical campaign performance is not causal uplift, and incremental outcomes remain `NOT YET MEASURED`; any proposal, approval, and execution must be handled as separate steps.
