from typing import Dict, Any, List
from backend.app.config import settings
from backend.app.ml.model import recovery_model
from backend.app.engine.policies import policy_engine

class ActionOptimizer:
    """
    Optimizes expected net recovery value subject to merchant policy guardrails.
    E(Net Value) = Amount * P(Recovery | Action) - DirectCost - Discount - ChurnPenalty
    """
    def __init__(self):
        pass

    def evaluate_candidate_actions(
        self,
        customer: Dict[str, Any],
        event: Dict[str, Any],
        prior_actions_count: int = 0
    ) -> Dict[str, Any]:
        amount = float(event.get("amount", 1000.0))
        probabilities = recovery_model.predict_probabilities(customer, event)
        
        # High value escalation check
        is_escalated, esc_reason = policy_engine.check_high_value_escalation(amount)

        candidates = []
        discount_pct = min(settings.MAX_DISCOUNT_PCT, 8.0)  # Standard 8% discount incentive
        discount_inr = round(amount * (discount_pct / 100.0), 2)

        action_configs = {
            "retry_now": {
                "direct_cost": settings.COST_RETRY_NOW,
                "discount": 0.0,
                "penalty": 5.0, # Slight customer annoyance if it fails again
                "delay_hours": 0.0,
                "channel": "gateway_autopay"
            },
            "delayed_retry": {
                "direct_cost": settings.COST_RETRY_DELAYED,
                "discount": 0.0,
                "penalty": 0.0,
                "delay_hours": 12.0,
                "channel": "gateway_autopay"
            },
            "smart_reminder": {
                "direct_cost": settings.COST_REMINDER_WHATSAPP if customer.get("preferred_channel") == "whatsapp" else settings.COST_REMINDER_SMS,
                "discount": 0.0,
                "penalty": 0.0,
                "delay_hours": 2.0,
                "channel": customer.get("preferred_channel", "whatsapp")
            },
            "incentive_discount": {
                "direct_cost": settings.COST_REMINDER_WHATSAPP,
                "discount": discount_inr,
                "penalty": 0.0,
                "delay_hours": 1.0,
                "channel": customer.get("preferred_channel", "whatsapp")
            },
            "human_escalation": {
                "direct_cost": settings.COST_ESCALATION_OPS,
                "discount": 0.0,
                "penalty": 0.0,
                "delay_hours": 0.0,
                "channel": "internal_ops"
            },
            "do_nothing": {
                "direct_cost": 0.0,
                "discount": 0.0,
                "penalty": 0.0,
                "delay_hours": 0.0,
                "channel": "none"
            }
        }

        for action_name, config in action_configs.items():
            prob = probabilities.get(action_name, 0.1)
            gross_expected = amount * prob
            total_cost = config["direct_cost"] + config["discount"] + config["penalty"]
            net_expected = round(gross_expected - total_cost, 2)

            # Policy compliance check
            compliance = policy_engine.evaluate_action_compliance(
                action=action_name,
                customer=customer,
                event=event,
                prior_actions_count=prior_actions_count
            )

            candidates.append({
                "action": action_name,
                "probability": prob,
                "gross_expected_value": round(gross_expected, 2),
                "direct_cost": config["direct_cost"],
                "discount_offered": config["discount"],
                "discount_pct": discount_pct if action_name == "incentive_discount" else 0.0,
                "customer_penalty": config["penalty"],
                "net_expected_value": net_expected,
                "delay_hours": config["delay_hours"],
                "channel": config["channel"],
                "compliant": compliance["compliant"],
                "policy_reason": compliance["reason"],
                "policy_code": compliance["policy_code"]
            })

        # Decision selection logic
        if is_escalated:
            chosen = next((c for c in candidates if c["action"] == "human_escalation"), candidates[0])
            selection_reason = esc_reason
        else:
            # Filter compliant candidates with positive net expected value
            eligible = [c for c in candidates if c["compliant"] and c["net_expected_value"] > 0 and c["action"] != "human_escalation"]
            if eligible:
                # Pick action maximizing Net Expected Value
                eligible.sort(key=lambda x: x["net_expected_value"], reverse=True)
                chosen = eligible[0]
                selection_reason = (
                    f"Selected '{chosen['action']}' yielding highest net expected recovery of "
                    f"₹{chosen['net_expected_value']:,.2f} (P={chosen['probability']:.2f}) while strictly complying with all merchant guardrails."
                )
            else:
                # If no eligible positive action, stop
                chosen = next((c for c in candidates if c["action"] == "do_nothing"), candidates[-1])
                selection_reason = "No intervention yielded positive expected net recovery under current policy limits. Workflow halted to prevent losses."

        return {
            "chosen_action": chosen["action"],
            "chosen_action_details": chosen,
            "selection_reason": selection_reason,
            "all_candidates": candidates
        }

optimizer = ActionOptimizer()
