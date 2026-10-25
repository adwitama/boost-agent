from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .errors import PolicyError
from .adapters import MockAdsRepository, MockBookRepository

DEMO = "DEMO DATA"
DEFAULT_ACTOR = "demo-specialist-1"


class BoostService:
    """Authoritative fixture and policy service. It never calls an ad platform."""

    def __init__(self, state_path: str | Path = "boost_demo.sqlite", actor_id: str = DEFAULT_ACTOR):
        self.actor_id = actor_id
        self.state_path = Path(state_path)
        self.fixture_dir = Path(__file__).resolve().parents[2] / "specs/001-boost-mcp-agent/data"
        self.hotels = self._read_fixture("hotels.json")
        self.campaigns = self._read_fixture("campaigns.json")
        self.bookings = self._read_fixture("bookings.json")
        self._validate_fixtures()
        self._init_db()

    def _read_fixture(self, name: str) -> list[dict[str, Any]]:
        repository = MockBookRepository if name == "bookings.json" else MockAdsRepository
        return repository(self.fixture_dir / name).rows()

    def _validate_fixtures(self) -> None:
        requirements = ((self.hotels, {"hotel_id", "name", "assigned_specialist_id", "monthly_budget_cap_jpy"}), (self.campaigns, {"campaign_id", "hotel_id", "monthly_budget_jpy", "spend_30d_jpy", "rule_tags"}), (self.bookings, {"booking_id", "hotel_id", "campaign_id", "gross_value_jpy", "status"}))
        if any(not isinstance(rows, list) or any(not fields <= row.keys() for row in rows) for rows, fields in requirements): raise ValueError("invalid fixture shape")
        if len({h["hotel_id"] for h in self.hotels}) != 25: raise ValueError("fixture must have 25 unique hotels")
        hotels, campaigns = {h["hotel_id"] for h in self.hotels}, {c["campaign_id"] for c in self.campaigns}
        if any(c["hotel_id"] not in hotels for c in self.campaigns) or any(b["campaign_id"] not in campaigns for b in self.bookings): raise ValueError("invalid fixture relationship")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.state_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS budgets (
                  campaign_id TEXT PRIMARY KEY, hotel_id TEXT NOT NULL,
                  monthly_budget_jpy INTEGER NOT NULL, version INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS proposals (
                  proposal_id TEXT PRIMARY KEY, hotel_id TEXT NOT NULL, from_campaign_id TEXT NOT NULL,
                  to_campaign_id TEXT NOT NULL, amount_jpy INTEGER NOT NULL, from_version INTEGER NOT NULL,
                  to_version INTEGER NOT NULL, status TEXT NOT NULL, created_by TEXT NOT NULL,
                  approved_by TEXT, expires_at TEXT NOT NULL, proposal_hash TEXT NOT NULL, executed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS executions (
                  idempotency_key TEXT PRIMARY KEY, proposal_id TEXT NOT NULL, receipt_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                  event_id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
                  result TEXT NOT NULL, hotel_id TEXT, proposal_id TEXT, old_state TEXT, new_state TEXT
                );
            """)
            if not db.execute("SELECT 1 FROM budgets LIMIT 1").fetchone():
                db.executemany("INSERT INTO budgets VALUES (?, ?, ?, 1)", [
                    (c["campaign_id"], c["hotel_id"], c["monthly_budget_jpy"]) for c in self.campaigns
                ])

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _meta(self, hotel_id: str | None = None) -> dict[str, Any]:
        return {"source_system": "tripla_boost_mock", "data_mode": "demo", "demo_marker": DEMO,
                "generated_at": self._now(), "hotel_id": hotel_id,
                "data_quality": {"attribution": "mocked", "coverage": 1.0, "contains_pii": False}}

    def _hotel(self, hotel_id: str) -> dict[str, Any]:
        for hotel in self.hotels:
            if hotel["hotel_id"] == hotel_id:
                return hotel
        raise PolicyError("unknown hotel ID")

    def _authorize(self, hotel_id: str) -> None:
        hotel = self._hotel(hotel_id)
        if hotel["assigned_specialist_id"] != self.actor_id:
            raise PolicyError("actor is not assigned to this hotel")

    def _budget(self, campaign_id: str) -> sqlite3.Row:
        with self._conn() as db:
            row = db.execute("SELECT * FROM budgets WHERE campaign_id = ?", (campaign_id,)).fetchone()
        if not row:
            raise PolicyError("unknown campaign ID")
        return row

    def _audit(self, action: str, result: str, hotel_id: str | None = None, proposal_id: str | None = None,
               old_state: Any = None, new_state: Any = None) -> None:
        with self._conn() as db:
            db.execute("INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                str(uuid.uuid4()), self._now(), self.actor_id, action, result, hotel_id, proposal_id,
                json.dumps(old_state) if old_state is not None else None,
                json.dumps(new_state) if new_state is not None else None,
            ))

    def list_managed_hotels(self, limit: int | None = None) -> dict[str, Any]:
        rows = [h for h in self.hotels if h["assigned_specialist_id"] == self.actor_id]
        rows = rows[:limit] if limit else rows
        return {**self._meta(), "hotels": rows, "count": len(rows)}

    def get_portfolio_campaign_summary(self, date_from: str = "2026-09-01", date_to: str = "2026-09-30") -> dict[str, Any]:
        allowed = {h["hotel_id"] for h in self.hotels if h["assigned_specialist_id"] == self.actor_id}
        rows = [c for c in self.campaigns if c["hotel_id"] in allowed]
        return {**self._meta(), "date_from": date_from, "date_to": date_to, "rows": rows}

    def get_campaign_performance(self, hotel_id: str, campaign_ids: list[str] | None = None) -> dict[str, Any]:
        self._authorize(hotel_id)
        rows = [c for c in self.campaigns if c["hotel_id"] == hotel_id and (not campaign_ids or c["campaign_id"] in campaign_ids)]
        return {**self._meta(hotel_id), "campaigns": rows}

    def get_campaign_budget(self, hotel_id: str, campaign_id: str) -> dict[str, Any]:
        self._authorize(hotel_id)
        row = self._budget(campaign_id)
        if row["hotel_id"] != hotel_id:
            raise PolicyError("campaign does not belong to hotel")
        return {**self._meta(hotel_id), "campaign_id": campaign_id, "monthly_budget_jpy": row["monthly_budget_jpy"], "budget_version": row["version"]}

    def get_reservations(self, hotel_id: str, campaign_ids: list[str] | None = None) -> dict[str, Any]:
        self._authorize(hotel_id)
        rows = [b for b in self.bookings if b["hotel_id"] == hotel_id and (not campaign_ids or b["campaign_id"] in campaign_ids)]
        return {**self._meta(hotel_id), "reservations": rows, "attribution_coverage": 1.0}

    def get_portfolio_retained_outcomes(self, hotel_ids: list[str]) -> dict[str, Any]:
        for hotel_id in hotel_ids: self._authorize(hotel_id)
        rows = []
        for hotel_id in hotel_ids:
            bookings = [b for b in self.bookings if b["hotel_id"] == hotel_id]
            rows.append({"hotel_id": hotel_id, "retained_booking_value_jpy": sum(b["gross_value_jpy"] for b in bookings if b["status"] == "retained"), "data_mode": "demo"})
        return {**self._meta(), "rows": rows}

    def calculate_campaign_economics(self, hotel_id: str, variable_cost_ratio: float = 0.30) -> dict[str, Any]:
        self._authorize(hotel_id)
        if not 0 <= variable_cost_ratio <= 1: raise PolicyError("variable cost ratio must be between 0 and 1")
        items = []
        for campaign in [c for c in self.campaigns if c["hotel_id"] == hotel_id]:
            campaign_bookings = [b for b in self.bookings if b["campaign_id"] == campaign["campaign_id"]]
            retained = sum(b["gross_value_jpy"] for b in campaign_bookings if b["status"] == "retained")
            spend = campaign["spend_30d_jpy"]
            items.append({"campaign_id": campaign["campaign_id"], "ad_spend_jpy": spend,
                "gross_booking_value_jpy": campaign["gross_attributed_booking_value_jpy"],
                "retained_booking_value_jpy": retained, "gross_roas": campaign["gross_attributed_booking_value_jpy"] / spend if spend else None,
                "retained_roas": retained / spend if spend else None,
                "variable_room_cost_jpy": int(retained * variable_cost_ratio),
                "historical_contribution_after_ads_jpy": int(retained - retained * variable_cost_ratio - spend),
                "incremental_net_contribution": None, "incrementality_status": "NOT COMPUTABLE FROM ATTRIBUTED HISTORY"})
        return {**self._meta(hotel_id), "campaign_economics": items, "historical_not_incremental": True}

    def audit_portfolio(self, period: str = "last_30_days") -> dict[str, Any]:
        allowed = {h["hotel_id"] for h in self.hotels if h["assigned_specialist_id"] == self.actor_id}
        alerts = []
        for c in self.campaigns:
            if c["hotel_id"] not in allowed: continue
            bookings = [b for b in self.bookings if b["campaign_id"] == c["campaign_id"]]
            cancelled = [b for b in bookings if b["status"] == "cancelled"]
            retained = [b for b in bookings if b["status"] == "retained"]
            evidence = {"monthly_budget_jpy": c["monthly_budget_jpy"], "spend_30d_jpy": c["spend_30d_jpy"],
                        "attributed_bookings": c["attributed_bookings"], "retained_bookings": len(retained),
                        "cancelled_bookings": len(cancelled), "booking_row_ids": [b["booking_id"] for b in bookings]}
            if c["spend_30d_jpy"] > c["monthly_budget_jpy"]:
                alerts.append({"rule_id": "pacing_high", "priority": "high", "hotel_id": c["hotel_id"], "campaign_id": c["campaign_id"],
                    "source_row_ids": [c["campaign_id"]], "evidence": {**evidence, "threshold": "spend_30d_jpy > monthly_budget_jpy"}})
            if c["spend_30d_jpy"] > 0 and c["attributed_bookings"] == 0:
                alerts.append({"rule_id": "missing_attribution", "priority": "high", "hotel_id": c["hotel_id"], "campaign_id": c["campaign_id"],
                    "source_row_ids": [c["campaign_id"]], "evidence": {**evidence, "threshold": "spend_30d_jpy > 0 and attributed_bookings == 0"}})
            cancellation_rate = len(cancelled) / len(bookings) if bookings else 0.0
            if bookings and cancellation_rate > 0.30:
                alerts.append({"rule_id": "cancellation_high", "priority": "medium", "hotel_id": c["hotel_id"], "campaign_id": c["campaign_id"],
                    "source_row_ids": [b["booking_id"] for b in bookings], "evidence": {**evidence, "cancellation_rate": cancellation_rate, "threshold": "> 0.30"}})
        return {**self._meta(), "period": period, "hotels_analyzed": len(allowed), "alerts": alerts}

    def generate_monthly_report(self, hotel_id: str = "all", period: str = "2026-09", output_dir: str | Path = "reports") -> dict[str, Any]:
        if hotel_id != "all": self._authorize(hotel_id)
        audit = self.audit_portfolio()
        if hotel_id != "all":
            audit["alerts"] = [a for a in audit["alerts"] if a["hotel_id"] == hotel_id]
            audit["hotels_analyzed"] = 1
        path = Path(output_dir); path.mkdir(parents=True, exist_ok=True)
        file = path / f"boost-report-{hotel_id}-{period}.md"; csv_file = path / f"boost-report-{hotel_id}-{period}.csv"
        lines = [f"# tripla Boost report — {period}", "", DEMO, "", f"Hotels analyzed: {audit['hotels_analyzed']}", "", "## Alerts"]
        lines += [f"- {a['priority']}: {a['rule_id']} ({a['campaign_id']}); fixture row: {a['campaign_id']}" for a in audit["alerts"]]
        lines += ["", "Historical attribution is not causal incrementality."]
        file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with csv_file.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=["priority", "rule_id", "hotel_id", "campaign_id", "fixture_row_id"]); writer.writeheader()
            writer.writerows({"priority": a["priority"], "rule_id": a["rule_id"], "hotel_id": a["hotel_id"], "campaign_id": a["campaign_id"], "fixture_row_id": a["campaign_id"]} for a in audit["alerts"])
        return {**self._meta(None if hotel_id == "all" else hotel_id), "report_path": str(file), "csv_report_path": str(csv_file), "included_sources": ["campaigns.json", "bookings.json"]}

    def propose_reallocation(self, hotel_id: str, from_campaign_id: str, to_campaign_id: str, amount_jpy: int, budget_type: str = "monthly") -> dict[str, Any]:
        self._authorize(hotel_id)
        if budget_type != "monthly" or not isinstance(amount_jpy, int) or amount_jpy <= 0: raise PolicyError("only positive integer monthly reallocations are allowed")
        source, destination = self._budget(from_campaign_id), self._budget(to_campaign_id)
        if source["hotel_id"] != hotel_id or destination["hotel_id"] != hotel_id: raise PolicyError("cross-hotel transfer is forbidden")
        if source["monthly_budget_jpy"] < amount_jpy: raise PolicyError("amount exceeds source campaign budget")
        hotel = self._hotel(hotel_id)
        with self._conn() as db:
            total = db.execute("SELECT COALESCE(SUM(monthly_budget_jpy), 0) FROM budgets WHERE hotel_id=?", (hotel_id,)).fetchone()[0]
        if total > hotel["monthly_budget_cap_jpy"]: raise PolicyError("existing allocation exceeds hotel budget cap")
        proposal_id = str(uuid.uuid4()); expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        digest = hashlib.sha256(f"{proposal_id}:{hotel_id}:{from_campaign_id}:{to_campaign_id}:{amount_jpy}:{source['version']}:{destination['version']}".encode()).hexdigest()
        with self._conn() as db:
            db.execute("INSERT INTO proposals VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, NULL, ?, ?, NULL)", (proposal_id, hotel_id, from_campaign_id, to_campaign_id, amount_jpy, source["version"], destination["version"], self.actor_id, expires, digest))
        before = {from_campaign_id: source["monthly_budget_jpy"], to_campaign_id: destination["monthly_budget_jpy"]}
        after = {from_campaign_id: source["monthly_budget_jpy"] - amount_jpy, to_campaign_id: destination["monthly_budget_jpy"] + amount_jpy}
        self._audit("propose_reallocation", "PENDING_APPROVAL", hotel_id, proposal_id, before, after)
        return {**self._meta(hotel_id), "proposal_id": proposal_id, "proposal_hash": digest, "status": "PENDING_APPROVAL", "before": before, "after": after, "expires_at": expires, "warning": "Historical performance is not causal uplift; outcome is NOT YET MEASURED."}

    def approve_proposal(self, proposal_id: str, explicit_confirmation: bool) -> dict[str, Any]:
        if not explicit_confirmation: raise PolicyError("explicit tool confirmation is required")
        with self._conn() as db:
            proposal = db.execute("SELECT * FROM proposals WHERE proposal_id = ?", (proposal_id,)).fetchone()
            if not proposal: raise PolicyError("unknown proposal")
            self._authorize(proposal["hotel_id"])
            if proposal["status"] != "PENDING_APPROVAL": raise PolicyError("proposal cannot be approved in its current state")
            if datetime.fromisoformat(proposal["expires_at"]) <= datetime.now(timezone.utc): raise PolicyError("proposal has expired")
            db.execute("UPDATE proposals SET status='APPROVED', approved_by=? WHERE proposal_id=?", (self.actor_id, proposal_id))
        self._audit("approve_proposal", "APPROVED", proposal["hotel_id"], proposal_id)
        return {**self._meta(proposal["hotel_id"]), "proposal_id": proposal_id, "status": "APPROVED", "approved_by": self.actor_id}

    def execute_mock_reallocation(self, proposal_id: str, idempotency_key: str) -> dict[str, Any]:
        if not idempotency_key: raise PolicyError("idempotency key is required")
        with self._conn() as db:
            prior = db.execute("SELECT receipt_id FROM executions WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if prior: raise PolicyError("replay blocked: idempotency key already used")
            p = db.execute("SELECT * FROM proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if not p: raise PolicyError("unknown proposal")
            self._authorize(p["hotel_id"])
            if p["status"] != "APPROVED": raise PolicyError("proposal is not approved")
            if datetime.fromisoformat(p["expires_at"]) <= datetime.now(timezone.utc): raise PolicyError("proposal has expired")
            a = db.execute("SELECT * FROM budgets WHERE campaign_id=?", (p["from_campaign_id"],)).fetchone(); b = db.execute("SELECT * FROM budgets WHERE campaign_id=?", (p["to_campaign_id"],)).fetchone()
            if a["version"] != p["from_version"] or b["version"] != p["to_version"]: raise PolicyError("proposal is stale")
            before = {a["campaign_id"]: a["monthly_budget_jpy"], b["campaign_id"]: b["monthly_budget_jpy"]}
            after = {a["campaign_id"]: a["monthly_budget_jpy"] - p["amount_jpy"], b["campaign_id"]: b["monthly_budget_jpy"] + p["amount_jpy"]}
            if after[a["campaign_id"]] < 0: raise PolicyError("negative budget is forbidden")
            db.execute("UPDATE budgets SET monthly_budget_jpy=?, version=version+1 WHERE campaign_id=?", (after[a["campaign_id"]], a["campaign_id"]))
            db.execute("UPDATE budgets SET monthly_budget_jpy=?, version=version+1 WHERE campaign_id=?", (after[b["campaign_id"]], b["campaign_id"]))
            receipt = str(uuid.uuid4()); db.execute("UPDATE proposals SET status='EXECUTED', executed_at=? WHERE proposal_id=?", (self._now(), proposal_id)); db.execute("INSERT INTO executions VALUES (?, ?, ?)", (idempotency_key, proposal_id, receipt))
        self._audit("execute_mock_reallocation", "EXECUTED", p["hotel_id"], proposal_id, before, after)
        return {**self._meta(p["hotel_id"]), "receipt_id": receipt, "status": "EXECUTED", "before": before, "after": after, "sum_unchanged": sum(before.values()) == sum(after.values()), "outcome_measurement": "NOT YET MEASURED"}

    def get_audit_log(self, hotel_id: str | None = None, proposal_id: str | None = None) -> dict[str, Any]:
        if hotel_id: self._authorize(hotel_id)
        query, args = "SELECT * FROM audit_events WHERE 1=1", []
        if hotel_id: query += " AND hotel_id=?"; args.append(hotel_id)
        if proposal_id: query += " AND proposal_id=?"; args.append(proposal_id)
        with self._conn() as db: events = [dict(row) for row in db.execute(query + " ORDER BY timestamp", args)]
        return {**self._meta(hotel_id), "events": events}

    def reset_demo(self, confirm: str) -> dict[str, Any]:
        if confirm != "RESET DEMO": raise PolicyError("reset requires literal RESET DEMO")
        with self._conn() as db:
            db.execute("DELETE FROM budgets"); db.execute("DELETE FROM proposals"); db.execute("DELETE FROM executions"); db.execute("DELETE FROM audit_events")
            db.executemany("INSERT INTO budgets VALUES (?, ?, ?, 1)", [(c["campaign_id"], c["hotel_id"], c["monthly_budget_jpy"]) for c in self.campaigns])
        return {**self._meta(), "reset": True, "warning": "DEMO DATA reset completed"}
