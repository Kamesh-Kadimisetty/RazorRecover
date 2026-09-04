from typing import Dict, Any

COHORTS: Dict[str, Dict[str, Any]] = {
    "reliable": {
        "name": "Reliable Payer",
        "description": "Established history of timely payments; failures are typically transient bank network glitches or OTP expiry.",
        "base_success_rate": 0.92,
        "ltv_range": (35000, 150000),
        "typical_order_range": (2000, 15000),
        "action_recoveries": {
            "retry_now": 0.38,
            "delayed_retry": 0.82,
            "smart_reminder": 0.86,
            "incentive_discount": 0.88,
            "human_escalation": 0.85,
            "do_nothing": 0.20
        },
        "delay_sensitivity": "low",
        "best_action": "delayed_retry"
    },
    "cash_constrained": {
        "name": "Temporarily Cash-Constrained",
        "description": "Active users facing temporary liquidity issues; immediate retries fail repeatedly, but delayed interventions around payday or 24-48h succeed.",
        "base_success_rate": 0.68,
        "ltv_range": (8000, 45000),
        "typical_order_range": (1500, 8000),
        "action_recoveries": {
            "retry_now": 0.12,
            "delayed_retry": 0.65,
            "smart_reminder": 0.58,
            "incentive_discount": 0.74,
            "human_escalation": 0.62,
            "do_nothing": 0.10
        },
        "delay_sensitivity": "high",
        "best_action": "delayed_retry"
    },
    "subscription_loyalist": {
        "name": "Subscription Loyalist",
        "description": "High lifetime value subscribers; high churn risk if spammed aggressively, but responds immediately to a gentle payment link.",
        "base_success_rate": 0.94,
        "ltv_range": (50000, 250000),
        "typical_order_range": (999, 4999),
        "action_recoveries": {
            "retry_now": 0.42,
            "delayed_retry": 0.78,
            "smart_reminder": 0.91,
            "incentive_discount": 0.92,
            "human_escalation": 0.88,
            "do_nothing": 0.25
        },
        "delay_sensitivity": "medium",
        "best_action": "smart_reminder"
    },
    "churn_risk": {
        "name": "High Churn Risk",
        "description": "Users on the verge of abandoning the service; standard retries and generic reminders produce low recovery, but targeted discounts reactivate them.",
        "base_success_rate": 0.48,
        "ltv_range": (3000, 18000),
        "typical_order_range": (800, 3500),
        "action_recoveries": {
            "retry_now": 0.08,
            "delayed_retry": 0.18,
            "smart_reminder": 0.25,
            "incentive_discount": 0.48,
            "human_escalation": 0.35,
            "do_nothing": 0.04
        },
        "delay_sensitivity": "high",
        "best_action": "incentive_discount"
    },
    "habitual_late": {
        "name": "Habitual Late Payer",
        "description": "Regular customers who postpone payments until urgent reminders or personal follow-ups occur.",
        "base_success_rate": 0.62,
        "ltv_range": (15000, 60000),
        "typical_order_range": (2500, 12000),
        "action_recoveries": {
            "retry_now": 0.20,
            "delayed_retry": 0.45,
            "smart_reminder": 0.72,
            "incentive_discount": 0.75,
            "human_escalation": 0.78,
            "do_nothing": 0.12
        },
        "delay_sensitivity": "low",
        "best_action": "smart_reminder"
    }
}
