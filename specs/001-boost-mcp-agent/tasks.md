# Build Tasks (dependency ordered)

- [X] T01 Create Python 3.11+ project with pinned MCP Python SDK v2 and `pytest`.
- [X] T02 Add fixture validator; seed 25 unique hotels, campaigns, and bookings; include Kyoto A/B expected values and zero PII.
- [X] T03 Define typed domain models and read-only repositories; include tenant/source metadata.
- [X] T04 Implement pure campaign metrics and `pytest` arithmetic expectations (A: ¥12k, B: ¥110k contribution; ROAS 3.2x / 3.0x).
- [X] T05 Implement rule-based portfolio audit with at least eight fixture-driven alerts and evidence codes.
- [X] T06 Implement local monthly report exporter (Markdown/CSV) and ensure no invented results.
- [X] T07 Implement SQLite persistence for budget state, proposals, approval status, and audit trail.
- [X] T08 Implement immutable pending proposal generation for ¥30k Kyoto within-account *monthly* budget test.
- [X] T09 Implement permission and hotel policy validation; reject unauthorized, stale, cross-hotel, overspend, expired and unapproved actions.
- [X] T10 Implement idempotent transactional mock mutation; read back and log before/after state; tests.
- [X] T11 Expose all tools in a real MCP v2 server; test with Inspector or in-memory client.
- [X] T12 Add `DEMO DATA` and attribution-versus-incrementality disclosures to every relevant response/report.
- [X] T13 Create optional agent instructions for selected chat host; no unverified host/tool compatibility assumptions.
- [X] T14 Write 2-minute Pillar 1 and 3-minute Pillar 2 demo scripts, plus reset command.
- [X] T15 Run all unit, policy and integration tests, lint, verify README quick start from clean environment.

## Completion checklist
- [ ] `mcp dev` or equivalent Inspector call lists tools (SDK v2 path is implemented; execution awaits PyPI connectivity)
- [X] Portfolio query returns exactly 25 authorized accounts and at least 8 explainable alerts
- [X] Monthly report is saved and citations/fixture row IDs appear
- [X] Kyoto metrics are accurate before change
- [X] Mutating before approval fails
- [X] Approval performs no mutation
- [X] Execution changes budgets A 100k→70k, B ¥100k→¥130k and total remains ¥200k
- [X] Second execution cannot alter budgets again
- [X] Verification and audit trail display approved actor and action receipt
- [X] Assistant never claims projected booking lift is observed

## Phase 1: Convergence

- [X] T016 Add `data_quality` metadata and fixture row-level provenance to responses and alerts per spec §7 (missing)
- [X] T017 Add fixture validation and typed domain/request-response models per T02/T03 and plan architecture (partial)
- [X] T018 Export CSV reports and include cited fixture row IDs in report output per T06 and completion checklist (partial)
- [X] T019 Add automated negative tests for unauthorized actors, overspend, stale and expired proposals, and unknown hotel IDs per spec §2 and T09/T10 (partial)
- [ ] T020 Validate the official MCP SDK v2 server path using MCP Inspector; implementation is present but package installation and Inspector run are blocked by sandbox DNS access to PyPI (partial)
- [X] T021 Extract `MockAdsRepository` and `MockBookRepository` interfaces from the service per plan layer decision (missing)
