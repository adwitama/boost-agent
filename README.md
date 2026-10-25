# tripla Boost MCP Agent — DEMO DATA only

This is a local, fixture-only MCP demonstration for tripla Boost specialists. It contains no credentials, no live booking integration, and no real advertising mutation. The only mutating operation updates a local SQLite demo database after server-enforced approval.

## Setup and test

```bash
uv sync --extra dev
uv run python -m unittest discover -s tests -v
```

Start the local stdio server with `uv run python -m boost_agent.server`, or launch it in MCP Inspector with `uv run mcp dev server.py`. The available tools are `ads.list_managed_hotels`, `ads.get_portfolio_campaign_summary`, `ads.get_campaign_performance`, `ads.get_campaign_budget`, `book.get_reservations`, `book.get_portfolio_retained_outcomes`, `growth.calculate_campaign_economics`, `growth.audit_portfolio`, `growth.generate_monthly_report`, `growth.propose_reallocation`, `growth.approve_proposal`, `ads.execute_mock_reallocation`, `growth.get_audit_log`, and `growth.reset_demo`.

Reset a local database with `uv run boost-agent reset`. All responses carry `data_mode: demo` and a `DEMO DATA` marker.

## Five-minute demonstration

1. Ask: “Review my 25 managed hotels for the last 30 days. Do not change budgets.” Call `ads.list_managed_hotels`, `ads.get_portfolio_campaign_summary`, `book.get_portfolio_retained_outcomes`, `growth.audit_portfolio`, then `growth.generate_monthly_report`.
2. Ask: “Compare Kyoto Campaign A and B, using 30% variable costs. What should we test with ¥30,000?” Call `growth.calculate_campaign_economics`, then propose, explicitly approve, execute, read back the budgets, and inspect the audit log. Explain that the result is a bounded experiment and that incremental outcome is `NOT YET MEASURED`.
