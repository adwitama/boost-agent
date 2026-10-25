# Feature Specification — tripla Boost Agent (MCP-first demo)

## 0. Metadata
- **Version:** 1.0, October 2026
- **Audience:** AI coding agent / Senior Product Manager assignment reviewer
- **Primary user:** tripla Boost internal advertising specialist, not a hotel operator
- **UX:** existing MCP-compatible LLM/chat host; no new dashboard
- **Data:** entirely fictional; account and reservation records must visibly be tagged `DEMO DATA`
- **Live integrations:** explicitly out of scope; demo must not send real advertising mutations

## 1. Problem, positioning and two value pillars
tripla Boost publicly describes a managed web advertising service with campaign planning, operations, performance analysis and optimization delivered by tripla for hotel customers. The internal tool stack is not publicly documented; manual cross-platform work is a hypothesis to validate. A chat-first MCP agent should minimize repeated routine agency work while using tripla Book outcomes (reservation value, cancellation, stay date, optional inventory and costs) to inform advertising decisions.

**Pillar 1 / Scale:** Reduce specialist manual effort to monitor accounts, prepare plans/actions and draft reports. Business linkage: lower Boost cost-to-serve, more hotel accounts handled per specialist subject to quality.

**Pillar 2 / Grow:** Compare campaign economics using retained hotel bookings, not only the ad platform's gross ROAS. Recommend limited experiments and measure *incremental* retained direct bookings and contribution, not just attributed volume. Business linkage: hotel contribution; potential Book eligible GMV and usage-based revenue, conditional on commercial contracts.

## 2. Scope
### Must-have / P0
- A real MCP tool server implementation (three logical namespaces/services: `ads`, `book`, `growth`) that the selected LLM host can call.
- User can ask for a 25-hotel portfolio audit; agent invokes tools, ranks exceptions using deterministic rule-based logic, and drafts an account report.
- User can ask for Kyoto campaign A/B comparison; tools return spend, bookings, cancellations, booking value and stay dates; deterministic analytics calculate gross ROAS, retained ROAS and contribution after variable costs and advertising.
- Agent proposes an explicit ¥30,000 *test* reallocation within the same hotel, subject to spend limits, without claiming historical results guarantee incremental ROI.
- Read tool outputs display sources and `DEMO DATA` markers; all writes require a human approval recorded by the backend. Merely saying "I approve" in text must not bypass a tool-enforced approval token/state.
- Execute mock budget changes only after approved, persist resulting state, return before/after, execution receipt and audit history.
- Guardrail errors work: cross-hotel budget transfer, budget above limit, stale/expired proposal, replay, missing approval, unknown hotel ID.
- Test coverage for contribution math, tenancy/authorization policies, idempotency and approval transaction.
- Reproducible demo reset to fixtures.

### Nice-to-have / P1
- Export monthly report as Markdown/CSV.
- CLI-driven scripted agent conversation and MCP tool trace for reliability during interview.
- Scheduled monitoring simulation as a CLI command (not a production scheduler).
- User-friendly fallback if the chosen chat host cannot render approval UI: print proposal code, call explicit approve tool, verify server policy.

### Not in scope
- A new operator dashboard or customer self-service portal.
- Real Google/Yahoo/Meta/TikTok ad access or live credentials; real tripla Book PMS/booking integration.
- Automatically adjusting room rates or discount policies.
- Actual hotel P&L calculations, personally identifiable guest records, or claims of proven uplift.
- Autonomous budget changes without explicit staff approval.

## 3. Actors and authorization
1. `specialist`: can read assigned hotel accounts, prepare recommendations, and approve simulated changes only within their assigned accounts and delegated budget rules.
2. `reviewer`: read-only user for inspecting decisions and reports.
3. `hotel client`: is not an agent user in MVP; hotel-approved budgets and constraints are input data, not chat commands.
4. `backend policy engine`: authoritative allow/deny gate for every write. It must not trust user-provided hotel IDs or LLM instructions without access-control verification.

## 4. Detailed scenario A — Pillar 1: 25-hotel operations audit
**Chat prompt:** "Review my 25 managed hotels for the last 30 days. Identify budget pacing and cancellation-adjusted booking issues; create an action queue and draft the monthly summary. Do not change budgets."

**Expected tool journey** (not mandated LLM exact ordering):
`ads.list_managed_hotels` → `ads.get_portfolio_campaign_summary` → `book.get_portfolio_retained_outcomes` → `growth.audit_portfolio` → `growth.generate_monthly_report`.

**Example outcomes:** 25 accounts audited, high priority alerts for overspend/missing booking attribution, medium priority cancellations, three report drafts; figures generated from fixtures rather than hallucinated. User can ask why an alert exists and get the exact metrics, threshold and source.

**Acceptance criteria:** 25 unique hotel IDs; no cross-account leakage; a report file produced; every alert grounded in source rows; repeat run produces deterministic identical alerts; no write tool called.

## 5. Detailed scenario B — Pillar 2: booking-aware budget test
**Chat prompt:** "Compare Campaign A and Campaign B for Kyoto Riverside. Use cancelled reservations and 30% variable room costs. What should we test with ¥30,000?"

**Fixture economics:**
- Campaign A: ¥100,000 spend; 8 reservations; 4 cancellations; gross booked GMV ¥320,000; retained booked revenue ¥160,000; room variable cost ¥48,000; historical contribution after ad spend **¥12,000**; gross ad ROAS **3.2x**.
- Campaign B: ¥100,000 spend; 6 reservations; 0 cancellations; gross booked GMV ¥300,000; retained booked revenue ¥300,000; room variable cost ¥90,000; historical contribution after ad spend **¥110,000**; gross ad ROAS **3.0x**.

**Key interpretation:** Campaign B produces higher *historical* cancellation-adjusted contribution. The agent must state that reallocation impact is unknown absent marginal-response estimation or holdout experiment; recommendation is a **bounded experiment**, not proof of +GMV.

**Proposed action:** shift ¥30,000 of the *monthly allocated campaign budget* as explicitly specified in the fixture from A to B, leaving Kyoto account-level budget unchanged. The demo should use **monthly campaign budget** in all related tools; don't confuse this with Google Ads daily budget semantics. Real integrations would require an adapter mapping monthly policy to platform-supported entities and pacing.

**Approval and execution:** `growth.propose_reallocation` returns immutable proposal ID/hash and both before/after values. `growth.approve_proposal` requires authorized specialist and explicit tool invocation. `ads.execute_mock_reallocation` fails if approval absent, policy invalid, stale, already executed, or hotel mismatched. On success, persist + verify using `ads.get_campaign_budget` and `growth.get_audit_log`.

**Acceptance criteria:** initial A monthly budget ¥100,000 and B ¥100,000, post-action ¥70,000 and ¥130,000; sum remains ¥200,000; no action if rejected; replay cannot double-apply. The 100k budget figures are deliberately aligned with fixture spend for easy arithmetic, not real platform budget state. Outcome measurement stays `NOT YET MEASURED` after action; never fabricate additional bookings.

## 6. Calculation definitions
- `gross_roas = attributed_gross_booking_value / ad_spend`.
- `retained_booking_value = sum(booking_value for reservations with status=retained)`.
- `retained_roas = retained_booking_value / ad_spend`.
- `variable_room_cost = retained_booking_value * assumed_variable_cost_ratio` (fixed 0.30 in demo).
- `historical_contribution_after_ads = retained_booking_value - variable_room_cost - ad_spend`.
- `incremental_net_contribution` requires experimental counterfactual; **not computable from these two campaign summaries alone**.
- For zero spend return `null`/undefined ROAS with a reason; don't divide by zero.
- All JPY currency values integers; do not infer decimal yen. Stay dates apply to bookings, not necessarily campaign targeting capabilities.

## 7. Data model and provenance
Required entities: `Hotel {hotel_id,name,assigned_specialist_id,monthly_budget_cap,allowed_platforms}`; `Campaign {campaign_id,hotel_id,platform,monthly_budget,spend_30d,clicks_30d}`; `Booking {booking_id,hotel_id,campaign_id,booking_date,check_in,check_out,gross_value_jpy,status,cancelled_at?}`; `Proposal {proposal_id,hotel_id,action_type,preconditions,from_campaign,to_campaign,amount_jpy,status,expires_at,version,created_by,approved_by?,executed_at?}`; `AuditEvent {event_id,timestamp,actor,action,result,old_state?,new_state?,proposal_id?}`. A production system would use server-verified identity and tenant filtering, not `assigned_specialist_id` supplied freely by chat.

No guest names/emails/phone numbers. Each MCP response must include `source_system`, `data_mode: demo`, `generated_at`, `hotel_id`, and `data_quality` metadata where meaningful. Booking attribution is mocked and 100% complete in the Kyoto fixture; in production attribution gaps must be surfaced explicitly.

## 8. Tool design
See `contracts/tools.json` for named operations, argument schemas, example return fields, and read/write classifications.
- `ads.list_managed_hotels` (read)
- `ads.get_portfolio_campaign_summary` (read)
- `ads.get_campaign_performance` (read)
- `ads.get_campaign_budget` (read)
- `book.get_reservations` (read)
- `book.get_portfolio_retained_outcomes` (read)
- `growth.calculate_campaign_economics` (read)
- `growth.audit_portfolio` (read)
- `growth.generate_monthly_report` (file writing to local demo reports only)
- `growth.propose_reallocation` (create pending proposal, does NOT mutate budget)
- `growth.approve_proposal` (approve once after verified specialist context)
- `ads.execute_mock_reallocation` (write; approved proposal only)
- `growth.get_audit_log` (read)
- `growth.reset_demo` (special demo administration, disabled in production)

## 9. Nonfunctional criteria
- **Safe:** all accounts synthetic, all mutation tools mock; explicit confirmation; no secrets inside LLM logs; hotel isolation and per-user scopes.
- **Auditable:** persist immutable append-only event history (SQLite demo acceptable); include before/after and policy decisions.
- **Repeatable:** same seed data and same deterministic analysis; a reset command restores state.
- **Testable:** local integration tests do not need a paid LLM API, external ad credentials, or tripla Book.
- **Reliable:** if host/tool fails, report failure and stop. Never invent successful executions.
- **Fast:** a standard local fixture audit should complete quickly (target <5 seconds excluding host latency; a demo target, not SLA).

## 10. Success measurement
**Demo acceptance:** two fully working chat journeys, visible tool traces, exact contribution arithmetic, explicit approval, persistent verified budget delta, report generated, and negative-policy tests passing.

**Pillar 1 pilot KPI:** minutes per hotel per month spent on monitoring/reporting/setup; rate of completed operations; account capacity per specialist; error/rework rate; Boost cost to serve.

**Pillar 2 pilot KPI:** incremental retained booking contribution in controlled tests; cost per incremental retained booking; incremental eligible direct GMV. Report attributed GMV separately from causal incremental value. Changes in tripla Book take rate are not attributed to this automation without separate evidence.

## 11. Discovery risks
- tripla may already use external agency management automation; verify operational gaps.
- tripla Book data/API access may not include individual funnel events, cancellation histories, inventory or contribution costs.
- Google official Ads MCP server is read-only as of October 2026; demo writes must use a custom mock adapter; real writes require Google Ads API integration and policy mapping.
- LLM chat interface lacks automatic scheduling, durable state and tenant security by itself; the supporting services must implement these separately.
- Booking attribution is not equivalent to incrementality; include a holdout and reporting plan.

## 12. Reference sources
- tripla Boost managed service launch: https://tripla.io/2023/11/15/triplaboost/
- tripla FY2026 Q3 results (Sep 14, 2026): https://disclosure.catr.jp/companies/2f3a8/32258/tdnet/6e48c/782738
- Google Ads official read-only MCP: https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server
- MCP tool safety guidelines: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx
- MCP Python SDK v2: https://py.sdk.modelcontextprotocol.io/
- GitHub Spec Kit: https://github.github.io/spec-kit/
