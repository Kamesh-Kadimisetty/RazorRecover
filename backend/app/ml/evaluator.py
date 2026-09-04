from typing import Dict, Any, List
from backend.app.ml.dataset_generator import generate_evaluation_batch
from backend.app.engine.optimizer import optimizer
from backend.app.config import settings

def run_batch_evaluation(num_cases: int = 1000, seed: int = 42) -> Dict[str, Any]:
    """
    Executes a locked, held-out evaluation across 1,000 cases comparing:
    - Baseline A: Always Retry (Naïve instant retry on all failures)
    - Baseline B: Generic Reminder (Generic message to every customer)
    - Baseline C: Static Rules (Hardcoded if-else heuristics)
    - RazorRecover: Calibrated ML + Expected Net Value Optimizer + Policy Guardrails
    """
    batch = generate_evaluation_batch(size=num_cases, seed=seed)
    gross_at_risk = sum(c["amount"] for c in batch)

    strategies = {
        "baseline_always_retry": {
            "name": "Baseline A (Always Retry)",
            "gross_recovered": 0.0,
            "costs": 0.0,
            "discounts": 0.0,
            "interventions": 0,
            "recovered_count": 0,
            "unnecessary_interventions": 0
        },
        "baseline_generic_reminder": {
            "name": "Baseline B (Generic Reminder)",
            "gross_recovered": 0.0,
            "costs": 0.0,
            "discounts": 0.0,
            "interventions": 0,
            "recovered_count": 0,
            "unnecessary_interventions": 0
        },
        "baseline_static_rules": {
            "name": "Baseline C (Static Rules)",
            "gross_recovered": 0.0,
            "costs": 0.0,
            "discounts": 0.0,
            "interventions": 0,
            "recovered_count": 0,
            "unnecessary_interventions": 0
        },
        "razorrecover": {
            "name": "RazorRecover (AI Decision Engine)",
            "gross_recovered": 0.0,
            "costs": 0.0,
            "discounts": 0.0,
            "interventions": 0,
            "recovered_count": 0,
            "unnecessary_interventions": 0
        }
    }

    for case in batch:
        amt = case["amount"]
        cf = case["counterfactuals"]
        cohort = case["cohort"]
        fail_code = case["failure_code"]

        # -------------------------------------------------------------
        # 1. Baseline A: Always Retry
        # -------------------------------------------------------------
        s_a = strategies["baseline_always_retry"]
        s_a["interventions"] += 1
        s_a["costs"] += settings.COST_RETRY_NOW
        is_rec_a = cf["retry_now"]["recovered"]
        if is_rec_a:
            s_a["gross_recovered"] += amt
            s_a["recovered_count"] += 1
        else:
            s_a["unnecessary_interventions"] += 1

        # -------------------------------------------------------------
        # 2. Baseline B: Generic Reminder
        # -------------------------------------------------------------
        s_b = strategies["baseline_generic_reminder"]
        s_b["interventions"] += 1
        s_b["costs"] += settings.COST_REMINDER_WHATSAPP
        is_rec_b = cf["smart_reminder"]["recovered"]
        if is_rec_b:
            s_b["gross_recovered"] += amt
            s_b["recovered_count"] += 1
        else:
            s_b["unnecessary_interventions"] += 1

        # -------------------------------------------------------------
        # 3. Baseline C: Static Rules
        # (Rule: if timeout -> retry_now; if insufficient funds -> delayed_retry; else reminder)
        # -------------------------------------------------------------
        s_c = strategies["baseline_static_rules"]
        if "TIMEOUT" in fail_code or "GATEWAY" in fail_code:
            action_c = "retry_now"
            cost_c = settings.COST_RETRY_NOW
        elif "INSUFFICIENT" in fail_code:
            action_c = "delayed_retry"
            cost_c = settings.COST_RETRY_DELAYED
        else:
            action_c = "smart_reminder"
            cost_c = settings.COST_REMINDER_WHATSAPP

        s_c["interventions"] += 1
        s_c["costs"] += cost_c
        is_rec_c = cf[action_c]["recovered"]
        if is_rec_c:
            s_c["gross_recovered"] += amt
            s_c["recovered_count"] += 1
        else:
            s_c["unnecessary_interventions"] += 1

        # -------------------------------------------------------------
        # 4. RazorRecover: AI Decision Engine
        # -------------------------------------------------------------
        s_ai = strategies["razorrecover"]
        cust_dict = {
            "id": case["customer_id"],
            "cohort": cohort,
            "historical_recovery_rate": 0.65,
            "total_payments": 15,
            "successful_payments": 12,
            "lifetime_value": 35000,
            "preferred_channel": "whatsapp",
            "opt_out": False
        }
        event_dict = {
            "amount": amt,
            "failure_code": fail_code,
            "attempt_number": case["attempt_number"],
            "root_cause": case["root_cause"],
            "hour_of_day": case["hour_of_day"]
        }
        decision = optimizer.evaluate_candidate_actions(cust_dict, event_dict)
        chosen = decision["chosen_action"]
        chosen_details = decision["chosen_action_details"]

        if chosen != "do_nothing":
            s_ai["interventions"] += 1
            s_ai["costs"] += chosen_details.get("direct_cost", 0.0)
            s_ai["discounts"] += chosen_details.get("discount_offered", 0.0)

            is_rec_ai = cf.get(chosen, cf["do_nothing"])["recovered"]
            if is_rec_ai:
                s_ai["gross_recovered"] += amt
                s_ai["recovered_count"] += 1
            else:
                s_ai["unnecessary_interventions"] += 1

    # Aggregate summaries
    results = {}
    for key, data in strategies.items():
        net_rec = max(0.0, data["gross_recovered"] - data["costs"] - data["discounts"])
        rec_rate = (data["gross_recovered"] / gross_at_risk * 100.0) if gross_at_risk > 0 else 0.0
        results[key] = {
            "name": data["name"],
            "gross_at_risk": round(gross_at_risk, 2),
            "gross_recovered": round(data["gross_recovered"], 2),
            "net_recovered": round(net_rec, 2),
            "total_costs": round(data["costs"] + data["discounts"], 2),
            "recovery_rate_pct": round(rec_rate, 2),
            "interventions_count": data["interventions"],
            "recovered_cases_count": data["recovered_count"],
            "unnecessary_interventions": data["unnecessary_interventions"]
        }

    # Uplift calculations of RazorRecover vs Baseline C (Static Rules)
    rr_net = results["razorrecover"]["net_recovered"]
    rules_net = results["baseline_static_rules"]["net_recovered"]
    uplift_inr = round(rr_net - rules_net, 2)
    uplift_pct = round(((rr_net - rules_net) / rules_net * 100.0), 2) if rules_net > 0 else 0.0

    return {
        "num_cases": num_cases,
        "gross_at_risk": round(gross_at_risk, 2),
        "strategies": results,
        "uplift_vs_rules": {
            "net_revenue_lift_inr": uplift_inr,
            "net_revenue_lift_pct": uplift_pct,
            "wasteful_interventions_reduced": results["baseline_static_rules"]["unnecessary_interventions"] - results["razorrecover"]["unnecessary_interventions"]
        }
    }
