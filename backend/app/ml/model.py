import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, List
from backend.app.ml.cohorts import COHORTS
from backend.app.ml.dataset_generator import generate_evaluation_batch

class RecoveryProbabilityModel:
    """
    Calibrated ML model estimating P(Recovery | Customer, Event, Action, Timing).
    Trained on historical event features and counterfactual action outcomes.
    """
    def __init__(self):
        self.actions = [
            "retry_now",
            "delayed_retry",
            "smart_reminder",
            "incentive_discount",
            "human_escalation",
            "do_nothing"
        ]
        self.model = None
        self._train_initial_model()

    def _extract_features(self, customer: Dict[str, Any], event: Dict[str, Any], action: str) -> List[float]:
        """Extract normalized numeric features for tabular ML modeling."""
        amount = float(event.get("amount", 2000.0))
        attempt = int(event.get("attempt_number", 1))
        hour = int(event.get("hour_of_day", 14))
        
        hist_rec_rate = float(customer.get("historical_recovery_rate", 0.6))
        total_p = max(1, int(customer.get("total_payments", 10)))
        succ_p = int(customer.get("successful_payments", 8))
        succ_rate = succ_p / total_p
        ltv = float(customer.get("lifetime_value", 25000.0))

        fail_code = str(event.get("failure_code", "")).upper()
        is_insufficient_funds = 1.0 if "INSUFFICIENT" in fail_code else 0.0
        is_timeout = 1.0 if "TIMEOUT" in fail_code or "GATEWAY" in fail_code else 0.0
        is_quiet_hour = 1.0 if (hour >= 22 or hour < 8) else 0.0

        # One-hot action encoding
        action_ohe = [1.0 if a == action else 0.0 for a in self.actions]

        return [
            np.log1p(amount),
            attempt,
            hist_rec_rate,
            succ_rate,
            np.log1p(ltv),
            is_insufficient_funds,
            is_timeout,
            is_quiet_hour
        ] + action_ohe

    def _train_initial_model(self):
        """Train baseline calibrated model on simulated historical customer trajectories."""
        training_cases = generate_evaluation_batch(size=1200, seed=101)
        X = []
        y = []

        for case in training_cases:
            cohort_info = COHORTS[case["cohort"]]
            dummy_customer = {
                "historical_recovery_rate": cohort_info["action_recoveries"]["delayed_retry"],
                "total_payments": 20,
                "successful_payments": int(20 * cohort_info["base_success_rate"]),
                "lifetime_value": (cohort_info["ltv_range"][0] + cohort_info["ltv_range"][1]) / 2
            }
            dummy_event = {
                "amount": case["amount"],
                "attempt_number": case["attempt_number"],
                "hour_of_day": case["hour_of_day"],
                "failure_code": case["failure_code"]
            }

            for action, cf in case["counterfactuals"].items():
                feats = self._extract_features(dummy_customer, dummy_event, action)
                X.append(feats)
                y.append(1 if cf["recovered"] else 0)

        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=1.0, max_iter=200, random_state=42))
        ])
        pipe.fit(X, y)
        self.model = pipe

    def predict_probabilities(self, customer: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, float]:
        """
        Predict P(Recovery) for each candidate intervention.
        Combines ML model predictions with cohort priors.
        """
        predictions = {}
        for action in self.actions:
            feats = [self._extract_features(customer, event, action)]
            if self.model is not None:
                # Probability of recovery (class 1)
                prob = float(self.model.predict_proba(feats)[0][1])
            else:
                prob = 0.5

            # Root cause calibration
            fail_code = str(event.get("failure_code", "")).upper()
            if action == "retry_now" and "INSUFFICIENT" in fail_code:
                prob = min(prob, 0.12)
            elif action == "delayed_retry" and "INSUFFICIENT" in fail_code:
                prob = max(prob, 0.65)
                
            predictions[action] = round(max(0.01, min(0.99, prob)), 3)

        return predictions

# Singleton instance
recovery_model = RecoveryProbabilityModel()
