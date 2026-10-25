import tempfile
import unittest
from pathlib import Path

from boost_agent.errors import PolicyError
from boost_agent.server import ProtocolMCPServer
from boost_agent.service import BoostService


class BoostServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = BoostService(Path(self.tmp.name) / "state.sqlite")

    def tearDown(self): self.tmp.cleanup()

    def test_economics(self):
        e = {x["campaign_id"]: x for x in self.service.calculate_campaign_economics("JP-KYO-001")["campaign_economics"]}
        self.assertEqual((e["KYO-A"]["gross_roas"], e["KYO-A"]["historical_contribution_after_ads_jpy"]), (3.2, 12000))
        self.assertEqual((e["KYO-B"]["gross_roas"], e["KYO-B"]["historical_contribution_after_ads_jpy"]), (3.0, 110000))
        self.assertIsNone(e["KYO-B"]["incremental_net_contribution"])

    def test_audit_and_report(self):
        self.assertEqual(self.service.list_managed_hotels()["count"], 25)
        self.assertGreaterEqual(len(self.service.audit_portfolio()["alerts"]), 8)
        report = self.service.generate_monthly_report(output_dir=Path(self.tmp.name) / "reports")
        self.assertIn("fixture row:", Path(report["report_path"]).read_text())
        self.assertTrue(Path(report["csv_report_path"]).exists())
        self.assertIn("data_quality", self.service.audit_portfolio())

    def test_approval_and_replay(self):
        p = self.service.propose_reallocation("JP-KYO-001", "KYO-A", "KYO-B", 30000)
        with self.assertRaises(PolicyError): self.service.execute_mock_reallocation(p["proposal_id"], "key")
        self.service.approve_proposal(p["proposal_id"], True)
        receipt = self.service.execute_mock_reallocation(p["proposal_id"], "key")
        self.assertEqual(receipt["after"], {"KYO-A": 70000, "KYO-B": 130000})
        events = self.service.get_audit_log(proposal_id=p["proposal_id"])["events"]
        self.assertEqual(events[-1]["actor"], "demo-specialist-1")
        self.assertEqual(events[-1]["action"], "execute_mock_reallocation")
        with self.assertRaises(PolicyError): self.service.execute_mock_reallocation(p["proposal_id"], "key")

    def test_policies(self):
        with self.assertRaises(PolicyError): self.service.propose_reallocation("JP-KYO-001", "KYO-A", "C-001", 1000)
        p = self.service.propose_reallocation("JP-KYO-001", "KYO-A", "KYO-B", 30000)
        with self.assertRaises(PolicyError): self.service.approve_proposal(p["proposal_id"], False)

    def test_unknown_overspend_expired_stale_and_unauthorized(self):
        with self.assertRaises(PolicyError): self.service.get_campaign_budget("NOPE", "KYO-A")
        with self.assertRaises(PolicyError): self.service.propose_reallocation("JP-KYO-001", "KYO-A", "KYO-B", 100001)
        outsider = BoostService(Path(self.tmp.name) / "outsider.sqlite", actor_id="not-assigned")
        with self.assertRaises(PolicyError): outsider.get_campaign_performance("JP-KYO-001")
        p = self.service.propose_reallocation("JP-KYO-001", "KYO-A", "KYO-B", 30000)
        with self.service._conn() as db: db.execute("UPDATE proposals SET expires_at='2000-01-01T00:00:00+00:00' WHERE proposal_id=?", (p["proposal_id"],))
        with self.assertRaises(PolicyError): self.service.approve_proposal(p["proposal_id"], True)
        p = self.service.propose_reallocation("JP-KYO-001", "KYO-A", "KYO-B", 30000); self.service.approve_proposal(p["proposal_id"], True)
        with self.service._conn() as db: db.execute("UPDATE budgets SET version=version+1 WHERE campaign_id='KYO-A'")
        with self.assertRaises(PolicyError): self.service.execute_mock_reallocation(p["proposal_id"], "stale")

    def test_mcp_protocol(self):
        server = ProtocolMCPServer(Path(self.tmp.name) / "mcp.sqlite")
        init = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(init["result"]["serverInfo"]["name"], "tripla-boost-demo")
        tools = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
        self.assertEqual(len(tools), 14)
        result = server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "growth.calculate_campaign_economics", "arguments": {"hotel_id": "JP-KYO-001"}}})
        self.assertFalse(result["result"]["isError"])
