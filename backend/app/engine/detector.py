from typing import Dict, Any

def classify_root_cause(event: Dict[str, Any]) -> Dict[str, str]:
    """
    Deterministic root-cause classification from gateway failure codes and error steps.
    Does not rely on LLM hallucinations for structured financial fields.
    """
    code = str(event.get("error_code") or event.get("code") or "").lower()
    desc = str(event.get("error_description") or event.get("description") or "").lower()
    reason = str(event.get("error_reason") or "").lower()

    if any(k in code or k in desc or k in reason for k in ["insufficient", "balance", "funds", "low_bal"]):
        return {
            "root_cause": "insufficient_funds",
            "category": "Customer Financial Constraint",
            "explanation": "Customer account balance was insufficient at the time of charge."
        }
    elif any(k in code or k in desc or k in reason for k in ["timeout", "gateway_error", "bank_down", "npci", "timed_out", "server_error"]):
        return {
            "root_cause": "temporary_bank_outage",
            "category": "Intermittent Banking Infrastructure",
            "explanation": "Bank gateway or NPCI network timed out during authorization."
        }
    elif any(k in code or k in desc or k in reason for k in ["card_declined", "card_network", "issuer_declined", "blocked", "expired_card"]):
        return {
            "root_cause": "card_network_failure",
            "category": "Card / Issuer Policy",
            "explanation": "Issuing bank declined debit request or card limits exceeded."
        }
    elif any(k in code or k in desc or k in reason for k in ["mandate", "autopay", "preauth"]):
        return {
            "root_cause": "mandate_decline",
            "category": "Recurring Autopay Decline",
            "explanation": "Standing instruction or e-mandate execution failed."
        }
    elif any(k in code or k in desc or k in reason for k in ["user_dropped", "cancelled_by_user", "otp_timeout"]):
        return {
            "root_cause": "user_dropoff",
            "category": "Checkout Drop-off",
            "explanation": "Customer closed checkout modal or let OTP timer expire."
        }
    else:
        return {
            "root_cause": "generic_payment_failure",
            "category": "Payment Processing Error",
            "explanation": desc or "Payment could not be completed by issuing bank."
        }
