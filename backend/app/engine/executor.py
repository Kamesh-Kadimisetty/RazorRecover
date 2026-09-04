import uuid
import datetime
from typing import Dict, Any, Optional
import requests
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models.schemas import RecoveryCase, RecoveryAction, AuditLog, Customer
from backend.app.engine.explainer import explainer
from backend.app.engine.policies import policy_engine

class ActionExecutor:
    """
    Executes bounded recovery interventions either via live Razorpay API (in 'razorpay' mode)
    or simulated receipts (in 'simulator' mode). Records immutable audit logs.
    """
    def __init__(self):
        self.mode = settings.MODE
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET

    def _create_razorpay_payment_link(self, amount: float, customer: Customer, description: str) -> Dict[str, Any]:
        """Creates an official Razorpay Payment Link if live credentials exist."""
        if self.mode == "razorpay" and self.key_id and self.key_secret:
            try:
                url = "https://api.razorpay.com/v1/payment_links"
                payload = {
                    "amount": int(amount * 100),  # In paise
                    "currency": "INR",
                    "accept_partial": False,
                    "description": description,
                    "customer": {
                        "name": customer.name,
                        "email": customer.email,
                        "contact": customer.phone
                    },
                    "notify": {"sms": True, "email": True},
                    "reminder_enable": True
                }
                resp = requests.post(url, json=payload, auth=(self.key_id, self.key_secret), timeout=10)
                if resp.status_code in [200, 201]:
                    return resp.json()
            except Exception:
                pass
        
        # Simulator Mode / Fallback Receipt
        return {
            "id": f"plink_sim_{uuid.uuid4().hex[:10]}",
            "short_url": f"https://rzp.io/i/sim_{uuid.uuid4().hex[:8]}",
            "status": "created",
            "amount": int(amount * 100)
        }

    def execute_recovery_action(
        self,
        db: Session,
        case: RecoveryCase,
        customer: Customer,
        decision: Dict[str, Any]
    ) -> RecoveryAction:
        """
        Executes the chosen recovery action, generates audit rationale,
        crafts the customer message, and schedules or fires the intervention.
        """
        chosen = decision["chosen_action_details"]
        action_type = decision["chosen_action"]
        now = datetime.datetime.utcnow()

        # Calculate scheduled execution time
        delay_hours = chosen.get("delay_hours", 0.0)
        scheduled_for = now + datetime.timedelta(hours=delay_hours)

        # Apply quiet-hours policy adjustment for communications
        if action_type in ["smart_reminder", "incentive_discount"]:
            scheduled_for = policy_engine.get_adjusted_communication_time(scheduled_for)

        # Generate human-readable audit rationale via LLM / Fallback
        audit_rationale = explainer.generate_audit_explanation(
            customer={"cohort": customer.cohort, "preferred_channel": customer.preferred_channel},
            event={"amount": case.amount_at_risk, "root_cause": case.root_cause},
            decision=decision
        )

        # Generate customer message copy
        message_content = explainer.generate_customer_message(
            customer={"name": customer.name, "preferred_channel": customer.preferred_channel},
            event={"amount": case.amount_at_risk, "order_id": case.id},
            decision=decision
        )

        # Execute channel-specific action
        action_id = f"act_{uuid.uuid4().hex[:10]}"
        action_status = "scheduled" if delay_hours > 0 else "executed"

        if action_type in ["smart_reminder", "incentive_discount"]:
            link_receipt = self._create_razorpay_payment_link(
                amount=case.amount_at_risk,
                customer=customer,
                description=f"RazorRecover Payment Recovery for {case.id}"
            )
            # Link short url embedded in message
            if link_receipt.get("short_url"):
                message_content = message_content.replace("https://rzp.io/i/pay_rec_link", link_receipt["short_url"])

        # Create database record for recovery action
        recovery_action = RecoveryAction(
            id=action_id,
            case_id=case.id,
            action_type=action_type,
            scheduled_for=scheduled_for,
            executed_at=now if delay_hours == 0 else None,
            status=action_status,
            cost=chosen.get("direct_cost", 0.0),
            discount_offered=chosen.get("discount_offered", 0.0),
            discount_pct=chosen.get("discount_pct", 0.0),
            channel=chosen.get("channel", "in_app"),
            message_content=message_content,
            audit_rationale=audit_rationale
        )
        db.add(recovery_action)

        # Update case state
        if action_type == "human_escalation":
            case.status = "escalated"
            case.policy_check_status = "escalated"
        elif action_type == "do_nothing":
            case.status = "stopped"
            case.policy_check_status = "blocked"
        else:
            case.status = "action_scheduled" if delay_hours > 0 else "action_executed"
            case.policy_check_status = "passed"

        case.chosen_action = action_type
        case.recovery_probability = chosen.get("probability", 0.0)
        case.expected_net_value = chosen.get("net_expected_value", 0.0)
        case.policy_notes = chosen.get("policy_reason")

        # Record immutable Audit Log entry
        audit_entry = AuditLog(
            case_id=case.id,
            timestamp=now,
            actor="RazorRecoverExecutor",
            action=f"EXECUTE_{action_type.upper()}",
            input_summary=f"P(Recovery)={case.recovery_probability:.2f} | NetValue=₹{case.expected_net_value:,.2f}",
            decision=f"Scheduled {action_type} for {scheduled_for.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            details=audit_rationale
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(case)

        return recovery_action

executor = ActionExecutor()
