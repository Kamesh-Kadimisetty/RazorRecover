import hmac
import hashlib
import json
import uuid
import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.schemas import Customer, PaymentEvent, RecoveryCase, RecoveryAction, AuditLog
from backend.app.engine.detector import classify_root_cause
from backend.app.engine.optimizer import optimizer
from backend.app.engine.executor import executor

router = APIRouter(prefix="", tags=["Webhooks"])

# In-memory set for idempotency check (can also check DB)
PROCESSED_EVENT_IDS = set()

def verify_razorpay_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Validates Razorpay HMAC SHA256 webhook signature."""
    if not signature or not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

@router.post("/api/webhooks/razorpay")
@router.post("/webhooks/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Common Dual-Mode Webhook Handler.
    Ingests live Razorpay Test Mode events OR simulated Razorpay payloads with identical schema.
    """
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_id = payload.get("event_id") or payload.get("id") or str(uuid.uuid4())
    event_type = payload.get("event", "payment.failed")

    # Verify signature in live Razorpay mode if secret is configured
    if settings.MODE == "razorpay" and settings.RAZORPAY_WEBHOOK_SECRET:
        if not verify_razorpay_signature(raw_body, x_razorpay_signature, settings.RAZORPAY_WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Idempotency check: Ignore duplicate deliveries
    if event_id in PROCESSED_EVENT_IDS:
        return {"status": "duplicate_event_ignored", "event_id": event_id}
    PROCESSED_EVENT_IDS.add(event_id)

    entity_payload = payload.get("payload", {})
    
    # -------------------------------------------------------------
    # CASE A: Payment Failed Event
    # -------------------------------------------------------------
    if event_type == "payment.failed":
        payment_entity = entity_payload.get("payment", {}).get("entity", payload)
        payment_id = payment_entity.get("id") or f"pay_{uuid.uuid4().hex[:12]}"
        order_id = payment_entity.get("order_id") or f"order_{uuid.uuid4().hex[:10]}"
        raw_amount = float(payment_entity.get("amount", 250000))
        # Razorpay amounts are in paise (divide by 100)
        amount_inr = raw_amount / 100.0 if raw_amount > 1000 else raw_amount

        # Customer identification or creation
        contact = payment_entity.get("contact") or "+919876543210"
        email = payment_entity.get("email") or "customer@example.com"
        customer_name = payment_entity.get("notes", {}).get("customer_name") or "Retail Customer"
        cohort = payment_entity.get("notes", {}).get("cohort") or "reliable"

        customer = db.query(Customer).filter((Customer.email == email) | (Customer.phone == contact)).first()
        if not customer:
            customer = Customer(
                id=f"cust_{uuid.uuid4().hex[:8]}",
                name=customer_name,
                email=email,
                phone=contact,
                cohort=cohort,
                lifetime_value=amount_inr * 3.5,
                historical_recovery_rate=0.75 if cohort == "reliable" else 0.50,
                total_payments=5,
                successful_payments=4,
                failed_payments=1,
                preferred_channel="whatsapp"
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)

        # Record Payment Event
        err_code = payment_entity.get("error_code") or "INSUFFICIENT_FUNDS"
        err_desc = payment_entity.get("error_description") or "Payment failure detected"
        root_info = classify_root_cause({
            "error_code": err_code,
            "error_description": err_desc,
            "error_reason": payment_entity.get("error_reason", "")
        })

        payment_event = PaymentEvent(
            id=payment_id,
            order_id=order_id,
            customer_id=customer.id,
            amount=amount_inr,
            currency=payment_entity.get("currency", "INR"),
            status="failed",
            method=payment_entity.get("method", "upi"),
            error_code=err_code,
            error_description=err_desc,
            error_source=payment_entity.get("error_source", "gateway"),
            error_step=payment_entity.get("error_step", "payment_authorization"),
            error_reason=payment_entity.get("error_reason", "account_debit_failed"),
            attempt_number=payment_entity.get("notes", {}).get("attempt_number", 1),
            raw_payload=json.dumps(payload)
        )
        db.add(payment_event)

        # Create Recovery Case
        case_id = f"case_rec_{uuid.uuid4().hex[:8]}"
        recovery_case = RecoveryCase(
            id=case_id,
            payment_id=payment_id,
            customer_id=customer.id,
            amount_at_risk=amount_inr,
            root_cause=root_info["root_cause"],
            status="evaluating",
            recovery_probability=0.0,
            expected_net_value=0.0
        )
        db.add(recovery_case)
        db.commit()
        db.refresh(recovery_case)

        # Record initial Audit Log: Detection
        db.add(AuditLog(
            case_id=case_id,
            actor="RecoveryDetector",
            action="REVENUE_RISK_DETECTED",
            input_summary=f"Failed payment {payment_id} | Amount: ₹{amount_inr:,.2f} | Reason: {err_code}",
            decision=f"Root cause classified as '{root_info['root_cause']}' ({root_info['category']})",
            details=root_info["explanation"]
        ))
        db.commit()

        # Run Recovery Decision Engine (Optimizer + Policy Guardrails)
        cust_dict = {
            "id": customer.id,
            "cohort": customer.cohort,
            "historical_recovery_rate": customer.historical_recovery_rate,
            "total_payments": customer.total_payments,
            "successful_payments": customer.successful_payments,
            "lifetime_value": customer.lifetime_value,
            "preferred_channel": customer.preferred_channel,
            "opt_out": customer.opt_out
        }
        event_dict = {
            "amount": amount_inr,
            "failure_code": err_code,
            "attempt_number": payment_event.attempt_number,
            "root_cause": root_info["root_cause"],
            "hour_of_day": datetime.datetime.now().hour
        }

        decision = optimizer.evaluate_candidate_actions(cust_dict, event_dict)

        # Execute Chosen Bounded Action
        recovery_action = executor.execute_recovery_action(
            db=db,
            case=recovery_case,
            customer=customer,
            decision=decision
        )

        return {
            "status": "success",
            "case_id": case_id,
            "action_executed": decision["chosen_action"],
            "recovery_probability": decision["chosen_action_details"]["probability"],
            "net_expected_value": decision["chosen_action_details"]["net_expected_value"],
            "action_status": recovery_action.status
        }

    # -------------------------------------------------------------
    # CASE B: Payment Captured / Authorized / Link Paid Event
    # -------------------------------------------------------------
    elif event_type in ["payment.captured", "payment.authorized", "payment_link.paid"]:
        payment_entity = entity_payload.get("payment", {}).get("entity", payload)
        order_id = payment_entity.get("order_id")
        raw_amt = float(payment_entity.get("amount", 0.0))
        amt_inr = raw_amt / 100.0 if raw_amt > 1000 else raw_amt

        # Find active recovery case for this customer/order
        case = None
        if order_id:
            case = db.query(RecoveryCase).join(PaymentEvent).filter(
                PaymentEvent.order_id == order_id,
                RecoveryCase.status.in_(["detected", "evaluating", "action_scheduled", "action_executed"])
            ).first()

        if case:
            now = datetime.datetime.utcnow()
            diff_hours = (now - case.created_at).total_seconds() / 3600.0
            
            case.status = "recovered"
            case.recovered_amount = amt_inr or case.amount_at_risk
            case.recovered_at = now
            case.recovery_time_hours = round(max(0.1, diff_hours), 2)

            # Stopping rule: Cancel any remaining scheduled actions
            for act in case.actions:
                if act.status == "scheduled":
                    act.status = "cancelled"

            # Record Audit Log: Successful Recovery
            db.add(AuditLog(
                case_id=case.id,
                actor="RazorRecoverExecutor",
                action="REVENUE_RECOVERED_SUCCESS",
                input_summary=f"Incoming event: {event_type} | Amount: ₹{case.recovered_amount:,.2f}",
                decision=f"Case marked RECOVERED in {case.recovery_time_hours:.1f} hours.",
                details="Payment confirmed via webhook. Stopping rules activated; cancelled pending interventions."
            ))
            db.commit()

            return {
                "status": "recovery_confirmed",
                "case_id": case.id,
                "recovered_amount": case.recovered_amount
            }

        return {"status": "event_acknowledged_no_case_match", "event_type": event_type}

    return {"status": "ignored_event_type", "event_type": event_type}
