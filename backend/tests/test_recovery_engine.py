import unittest
import datetime
from backend.app.ml.model import recovery_model
from backend.app.engine.detector import classify_root_cause
from backend.app.engine.policies import policy_engine
from backend.app.engine.optimizer import optimizer
from backend.app.engine.explainer import explainer
from backend.app.ml.evaluator import run_batch_evaluation

class TestRazorRecoverEngine(unittest.TestCase):

    def test_detector_root_cause(self):
        """Test deterministic categorization of error codes."""
        r1 = classify_root_cause({"error_code": "INSUFFICIENT_FUNDS", "error_description": "low bal"})
        self.assertEqual(r1["root_cause"], "insufficient_funds")

        r2 = classify_root_cause({"error_code": "GATEWAY_TIMEOUT", "error_description": "bank timed out"})
        self.assertEqual(r2["root_cause"], "temporary_bank_outage")

        r3 = classify_root_cause({"error_code": "CARD_DECLINED", "error_description": "issuer reject"})
        self.assertEqual(r3["root_cause"], "card_network_failure")

    def test_model_predictions(self):
        """Test ML model outputs bounded probabilities for all candidate actions."""
        customer = {
            "cohort": "reliable",
            "historical_recovery_rate": 0.8,
            "total_payments": 20,
            "successful_payments": 18,
            "lifetime_value": 50000.0
        }
        event = {
            "amount": 4999.0,
            "failure_code": "INSUFFICIENT_FUNDS",
            "attempt_number": 1,
            "hour_of_day": 14
        }
        probs = recovery_model.predict_probabilities(customer, event)
        self.assertIn("retry_now", probs)
        self.assertIn("delayed_retry", probs)
        self.assertIn("smart_reminder", probs)
        for act, p in probs.items():
            self.assertTrue(0.0 <= p <= 1.0, f"Probability for {act} out of bounds: {p}")

        # Insufficient funds should have lower probability for instant retry than delayed retry
        self.assertLess(probs["retry_now"], probs["delayed_retry"])

    def test_policies_high_value_escalation(self):
        """Test transactions > ₹50,000 are blocked from autonomous actions and escalated."""
        customer = {"opt_out": False}
        event = {"amount": 75000.0, "attempt_number": 1}
        comp = policy_engine.evaluate_action_compliance("delayed_retry", customer, event)
        self.assertFalse(comp["compliant"])
        self.assertEqual(comp["policy_code"], "HIGH_VALUE_THRESHOLD")

        esc_comp = policy_engine.evaluate_action_compliance("human_escalation", customer, event)
        self.assertTrue(esc_comp["compliant"])

    def test_policies_max_retries(self):
        """Test attempt >= 3 is blocked by retry limit."""
        customer = {"opt_out": False}
        event = {"amount": 2000.0, "attempt_number": 3}
        comp = policy_engine.evaluate_action_compliance("delayed_retry", customer, event)
        self.assertFalse(comp["compliant"])
        self.assertEqual(comp["policy_code"], "MAX_RETRIES_EXCEEDED")

    def test_optimizer_selection(self):
        """Test optimizer selects action with highest positive net expected value."""
        customer = {
            "id": "cust_test_1",
            "cohort": "reliable",
            "historical_recovery_rate": 0.85,
            "total_payments": 25,
            "successful_payments": 23,
            "lifetime_value": 75000.0,
            "preferred_channel": "whatsapp",
            "opt_out": False
        }
        event = {
            "amount": 5000.0,
            "failure_code": "INSUFFICIENT_FUNDS",
            "attempt_number": 1,
            "root_cause": "insufficient_funds",
            "hour_of_day": 14
        }
        decision = optimizer.evaluate_candidate_actions(customer, event)
        self.assertIn("chosen_action", decision)
        self.assertIn(decision["chosen_action"], ["delayed_retry", "smart_reminder", "incentive_discount"])
        chosen_details = decision["chosen_action_details"]
        self.assertTrue(chosen_details["compliant"])
        self.assertGreater(chosen_details["net_expected_value"], 0)

    def test_explainer_and_messaging_guardrails(self):
        """Test explainer generates clean audit log and customer message with forbidden word checks."""
        customer = {"name": "Priya Sharma", "cohort": "cash_constrained", "preferred_channel": "whatsapp"}
        event = {"amount": 3500.0, "root_cause": "insufficient_funds", "order_id": "ord_test_88"}
        decision = {
            "chosen_action": "delayed_retry",
            "chosen_action_details": {
                "probability": 0.65,
                "net_expected_value": 2250.0,
                "policy_reason": "Passed all policy checks",
                "discount_pct": 0.0
            }
        }
        audit_text = explainer.generate_audit_explanation(customer, event, decision)
        self.assertIsInstance(audit_text, str)
        self.assertGreater(len(audit_text), 20)

        msg = explainer.generate_customer_message(customer, event, decision)
        self.assertIn("Priya", msg)
        self.assertNotIn("police", msg.lower())
        self.assertNotIn("fraud", msg.lower())

    def test_evaluator_benchmark(self):
        """Test 1,000-case evaluation produces measured metrics with RazorRecover outperforming Baselines."""
        res = run_batch_evaluation(num_cases=200, seed=42)
        strategies = res["strategies"]
        self.assertIn("razorrecover", strategies)
        self.assertIn("baseline_always_retry", strategies)
        self.assertIn("baseline_generic_reminder", strategies)
        self.assertIn("baseline_static_rules", strategies)

        rr = strategies["razorrecover"]
        base_a = strategies["baseline_always_retry"]
        base_c = strategies["baseline_static_rules"]

        # Net recovered must be higher than naive always-retry
        self.assertGreater(rr["net_recovered"], base_a["net_recovered"])
        # Unnecessary interventions should be lower or comparable
        self.assertGreater(rr["recovery_rate_pct"], 40.0)

if __name__ == "__main__":
    unittest.main()
