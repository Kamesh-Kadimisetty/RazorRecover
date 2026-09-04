import random
import datetime
from typing import List, Dict, Any
from backend.app.ml.cohorts import COHORTS

INDIAN_NAMES = [
    ("Rahul Verma", "rahul.verma@example.com", "+919876543210"),
    ("Priya Nair", "priya.nair@example.com", "+919812345678"),
    ("Aditya Sharma", "aditya.s@example.com", "+919988776655"),
    ("Sneha Patel", "sneha.p@example.com", "+919123456789"),
    ("Vikram Reddy", "vikram.r@example.com", "+919765432100"),
    ("Ananya Iyer", "ananya.i@example.com", "+919654321098"),
    ("Rohan Mehta", "rohan.m@example.com", "+919543210987"),
    ("Pooja Kulkarni", "pooja.k@example.com", "+919432109876"),
    ("Siddharth Das", "siddharth.d@example.com", "+919321098765"),
    ("Divya Gupta", "divya.g@example.com", "+919210987654")
]

FAILURE_REASONS = [
    {"code": "INSUFFICIENT_FUNDS", "desc": "Customer account has insufficient balance", "cause": "insufficient_funds"},
    {"code": "GATEWAY_TIMEOUT", "desc": "Bank gateway timed out during processing", "cause": "temporary_bank_outage"},
    {"code": "CARD_NETWORK_DECLINE", "desc": "Issuing bank declined debit request", "cause": "card_network_failure"},
    {"code": "MANDATE_EXECUTION_FAILED", "desc": "Scheduled recurring mandate was rejected", "cause": "mandate_decline"},
    {"code": "USER_DROPPED_OFF", "desc": "Customer closed payment window before OTP", "cause": "user_dropoff"}
]

def generate_customer_profile(index: int, cohort_override: str = None) -> Dict[str, Any]:
    """Generate a realistic customer profile with historical transaction metrics."""
    cohort_keys = list(COHORTS.keys())
    cohort = cohort_override or random.choice(cohort_keys)
    cohort_info = COHORTS[cohort]
    
    base_name, base_email_prefix, base_phone = random.choice(INDIAN_NAMES)
    name = f"{base_name} {index}"
    email = f"{base_name.lower().replace(' ', '.')}_{index}@example.com"
    phone = f"+9198{random.randint(10000000, 99999999)}"
    
    min_ltv, max_ltv = cohort_info["ltv_range"]
    ltv = round(random.uniform(min_ltv, max_ltv), 2)
    
    total_payments = random.randint(5, 40)
    base_rate = cohort_info["base_success_rate"]
    successes = int(total_payments * base_rate)
    failures = total_payments - successes
    recovery_rate = round(cohort_info["action_recoveries"]["delayed_retry"] + random.uniform(-0.05, 0.05), 3)
    recovery_rate = max(0.1, min(0.98, recovery_rate))
    
    preferred_channel = random.choice(["whatsapp", "sms", "email"])
    
    return {
        "id": f"cust_{1000 + index}",
        "name": name,
        "email": email,
        "phone": phone,
        "cohort": cohort,
        "lifetime_value": ltv,
        "historical_recovery_rate": recovery_rate,
        "total_payments": total_payments,
        "successful_payments": successes,
        "failed_payments": failures,
        "preferred_channel": preferred_channel,
        "opt_out": False
    }

def generate_evaluation_batch(size: int = 1000, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Generate a locked, held-out evaluation batch with ground-truth counterfactual outcomes.
    For every revenue-at-risk record, ground truth recovery (True/False) is simulated
    under every possible intervention based on cohort behavioral response curves.
    """
    rng = random.Random(seed)
    cases = []
    
    cohort_distribution = ["reliable", "cash_constrained", "subscription_loyalist", "churn_risk", "habitual_late"]
    
    for i in range(size):
        cohort = cohort_distribution[i % len(cohort_distribution)]
        cohort_info = COHORTS[cohort]
        
        min_amt, max_amt = cohort_info["typical_order_range"]
        amount = round(rng.uniform(min_amt, max_amt), 2)
        # Occasionally inject high-value cases for escalation testing
        if i % 40 == 0:
            amount = round(rng.uniform(55000, 95000), 2)
            
        fail_spec = rng.choice(FAILURE_REASONS)
        attempt_number = rng.choice([1, 1, 1, 2, 3])
        hour_of_day = rng.randint(0, 23)
        
        # Ground-truth counterfactual simulation for this exact case under each action
        counterfactuals = {}
        for action, base_prob in cohort_info["action_recoveries"].items():
            # Adjust probability based on attempt number and time
            prob = base_prob
            if attempt_number > 1:
                prob = max(0.05, prob * (0.85 ** (attempt_number - 1)))
            if action == "retry_now" and fail_spec["code"] == "INSUFFICIENT_FUNDS":
                prob = min(0.08, prob * 0.3)
            if action == "delayed_retry" and fail_spec["code"] == "INSUFFICIENT_FUNDS":
                prob = min(0.90, prob * 1.15)
                
            # Random draw against probability to determine true outcome if this action were picked
            recovered = rng.random() < prob
            counterfactuals[action] = {
                "recovered": recovered,
                "true_probability": round(prob, 3),
                "recovery_delay_hours": round(rng.uniform(1.5, 14.0), 1) if recovered else None
            }
            
        cases.append({
            "case_id": f"EVAL_{1000 + i}",
            "customer_id": f"cust_eval_{1000 + i}",
            "cohort": cohort,
            "amount": amount,
            "failure_code": fail_spec["code"],
            "failure_description": fail_spec["desc"],
            "root_cause": fail_spec["cause"],
            "attempt_number": attempt_number,
            "hour_of_day": hour_of_day,
            "counterfactuals": counterfactuals
        })
        
    return cases
