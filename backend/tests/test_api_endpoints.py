import unittest
from starlette.testclient import TestClient
from backend.app.main import app

class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("mode", data)

    def test_metrics_overview(self):
        resp = self.client.get("/api/metrics/overview")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("gross_at_risk", data)
        self.assertIn("gross_recovered", data)
        self.assertIn("recovery_rate_pct", data)

    def test_list_cases(self):
        resp = self.client.get("/api/cases")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_simulator_trigger_failure_and_closed_loop(self):
        # 1. Trigger failure
        sim_payload = {
            "customer_cohort": "cash_constrained",
            "amount": 4999.0,
            "failure_reason": "INSUFFICIENT_FUNDS",
            "customer_name": "Test Vikram"
        }
        resp = self.client.post("/api/simulator/trigger-failure", json=sim_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        case_id = data["case_id"]
        self.assertIn(data["chosen_action"], ["delayed_retry", "smart_reminder", "incentive_discount"])

        # 2. Inspect case
        detail_resp = self.client.get(f"/api/cases/{case_id}")
        self.assertEqual(detail_resp.status_code, 200)
        detail = detail_resp.json()
        self.assertEqual(detail["case"]["id"], case_id)
        self.assertIn("candidate_actions_matrix", detail)
        self.assertGreater(len(detail["audit_logs"]), 0)

        # 3. Simulate recovery
        rec_resp = self.client.post(f"/api/cases/{case_id}/simulate-recovery")
        self.assertEqual(rec_resp.status_code, 200)
        rec_data = rec_resp.json()
        self.assertEqual(rec_data["status"], "recovered")
        self.assertEqual(rec_data["recovered_amount"], 4999.0)

        # 4. Verify case status is now recovered
        post_rec_resp = self.client.get(f"/api/cases/{case_id}")
        self.assertEqual(post_rec_resp.json()["case"]["status"], "recovered")

    def test_evaluation_benchmark_endpoint(self):
        resp = self.client.get("/api/evaluation/benchmark")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["num_cases"], 1000)
        self.assertIn("razorrecover", data["strategies"])
        self.assertIn("uplift_vs_rules", data)
        self.assertGreater(data["uplift_vs_rules"]["net_revenue_lift_inr"], 0)

if __name__ == "__main__":
    unittest.main()
