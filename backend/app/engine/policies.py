import datetime
from typing import Dict, Any, Tuple
from backend.app.config import settings

class PolicyGuardrailEngine:
    """
    Deterministic Financial & Communication Guardrails.
    Enforces merchant policy limits, regulatory compliance, and safe stopping rules.
    """
    def __init__(self, config=None):
        self.config = config or settings

    def check_high_value_escalation(self, amount: float) -> Tuple[bool, str]:
        """Check if amount exceeds autonomous ceiling requiring human ops review."""
        threshold = getattr(self.config, "HUMAN_ESCALATION_THRESHOLD_INR", 50000.0)
        if amount >= threshold:
            return True, f"Transaction amount ₹{amount:,.2f} exceeds autonomous threshold of ₹{threshold:,.2f}. Escalated to Human Ops."
        return False, "Amount within autonomous bounds."

    def is_in_quiet_hours(self, dt: datetime.datetime = None) -> bool:
        """Check if target time is within quiet hours (e.g. 22:00 to 08:00)."""
        check_time = dt or datetime.datetime.now()
        start = getattr(self.config, "QUIET_HOURS_START", 22)
        end = getattr(self.config, "QUIET_HOURS_END", 8)
        hour = check_time.hour
        return hour >= start or hour < end

    def get_adjusted_communication_time(self, scheduled_dt: datetime.datetime) -> datetime.datetime:
        """Shift communication to 08:30 AM next day if scheduled inside quiet hours."""
        if not self.is_in_quiet_hours(scheduled_dt):
            return scheduled_dt
        
        # If quiet hours (e.g. 23:00), shift to 08:30 next morning
        adjusted = scheduled_dt.replace(hour=8, minute=30, second=0, microsecond=0)
        if scheduled_dt.hour >= getattr(self.config, "QUIET_HOURS_START", 22):
            adjusted += datetime.timedelta(days=1)
        return adjusted

    def evaluate_action_compliance(
        self,
        action: str,
        customer: Dict[str, Any],
        event: Dict[str, Any],
        prior_actions_count: int = 0
    ) -> Dict[str, Any]:
        """
        Evaluate candidate action against all deterministic policy rules.
        Returns compliance status (True/False), reason, and any modifications.
        """
        amount = float(event.get("amount", 0.0))
        attempt = int(event.get("attempt_number", 1))
        opt_out = bool(customer.get("opt_out", False))

        # Check 1: Stopping rule on customer opt-out
        if opt_out and action in ["smart_reminder", "incentive_discount"]:
            return {
                "compliant": False,
                "reason": "Customer has opted out of marketing/recovery communications.",
                "policy_code": "CUSTOMER_OPT_OUT"
            }

        # Check 2: High value transaction escalation
        is_escalated, esc_reason = self.check_high_value_escalation(amount)
        if is_escalated and action != "human_escalation":
            return {
                "compliant": False,
                "reason": esc_reason,
                "policy_code": "HIGH_VALUE_THRESHOLD"
            }

        # Check 3: Max retry attempts guardrail
        max_retries = getattr(self.config, "MAX_RETRIES", 3)
        if action in ["retry_now", "delayed_retry"] and attempt >= max_retries:
            return {
                "compliant": False,
                "reason": f"Exceeded maximum allowed retry attempts ({max_retries}).",
                "policy_code": "MAX_RETRIES_EXCEEDED"
            }

        # Check 4: Max messages per 48 hours
        max_msgs = getattr(self.config, "MAX_MESSAGES_PER_48H", 2)
        if action in ["smart_reminder", "incentive_discount"] and prior_actions_count >= max_msgs:
            return {
                "compliant": False,
                "reason": f"Frequency cap reached: maximum {max_msgs} messages per 48 hours.",
                "policy_code": "MESSAGE_FREQUENCY_CAP"
            }

        # Check 5: Stopping rule for paid/refunded/cancelled orders
        order_status = str(event.get("order_status", "")).lower()
        if order_status in ["paid", "captured", "refunded", "cancelled"]:
            return {
                "compliant": False,
                "reason": f"Order status is '{order_status}'. Recovery workflow stopped.",
                "policy_code": "ORDER_ALREADY_TERMINATED"
            }

        return {
            "compliant": True,
            "reason": "Passed all policy guardrail checks.",
            "policy_code": "POLICY_PASSED"
        }

policy_engine = PolicyGuardrailEngine()
