import uuid
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.schemas import Customer, PaymentEvent, RecoveryCase, AuditLog
from backend.app.engine.detector import classify_root_cause
from backend.app.engine.optimizer import optimizer
from backend.app.engine.executor import executor

router = APIRouter(prefix="/api/checkout", tags=["Live Razorpay Checkout"])

class CreateOrderIn(BaseModel):
    amount: float
    customer_name: str
    customer_email: str
    customer_phone: str

class RecordAttemptIn(BaseModel):
    order_id: str
    amount: float
    customer_name: str
    customer_email: str
    customer_phone: str
    outcome: str  # "failed" or "captured"
    failure_reason: str = "INSUFFICIENT_FUNDS"

@router.post("/create-order")
def create_razorpay_order(payload: CreateOrderIn):
    """Creates a real Razorpay Order on Razorpay's live servers."""
    amount_paise = int(payload.amount * 100)
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    if settings.MODE == "razorpay" and key_id and key_secret:
        try:
            url = "https://api.razorpay.com/v1/orders"
            order_data = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"rcpt_{uuid.uuid4().hex[:8]}",
                "notes": {
                    "customer_name": payload.customer_name,
                    "customer_email": payload.customer_email
                }
            }
            resp = requests.post(url, json=order_data, auth=(key_id, key_secret), timeout=10)
            if resp.status_code in [200, 201]:
                res = resp.json()
                return {
                    "order_id": res["id"],
                    "amount": payload.amount,
                    "currency": "INR",
                    "key_id": key_id,
                    "is_live_razorpay": True
                }
        except Exception:
            pass

    # Fallback order id if offline
    return {
        "order_id": f"order_live_{uuid.uuid4().hex[:10]}",
        "amount": payload.amount,
        "currency": "INR",
        "key_id": key_id or "rzp_test_mock",
        "is_live_razorpay": False
    }

@router.post("/record-attempt")
def record_checkout_attempt(payload: RecordAttemptIn, db: Session = Depends(get_db)):
    """
    Ingests the live payment attempt from the Razorpay checkout widget.
    Immediately dispatches to the Root-Cause Classifier, ML Optimizer, and Gemini Agent.
    """
    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    
    # Customer registration or lookup
    customer = db.query(Customer).filter((Customer.email == payload.customer_email) | (Customer.phone == payload.customer_phone)).first()
    if not customer:
        customer = Customer(
            id=f"cust_{uuid.uuid4().hex[:8]}",
            name=payload.customer_name,
            email=payload.customer_email,
            phone=payload.customer_phone,
            cohort="cash_constrained" if "INSUFFICIENT" in payload.failure_reason else "reliable",
            lifetime_value=payload.amount * 4.0,
            historical_recovery_rate=0.75,
            total_payments=6,
            successful_payments=5,
            failed_payments=1,
            preferred_channel="whatsapp"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    if payload.outcome == "failed":
        root_info = classify_root_cause({"error_code": payload.failure_reason})
        
        pay_event = PaymentEvent(
            id=payment_id,
            order_id=payload.order_id,
            customer_id=customer.id,
            amount=payload.amount,
            status="failed",
            method="upi",
            error_code=payload.failure_reason,
            error_description=f"Checkout attempt declined: {payload.failure_reason}",
            attempt_number=1
        )
        db.add(pay_event)

        case_id = f"case_{uuid.uuid4().hex[:8]}"
        case = RecoveryCase(
            id=case_id,
            payment_id=payment_id,
            customer_id=customer.id,
            amount_at_risk=payload.amount,
            root_cause=root_info["root_cause"],
            status="evaluating"
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        db.add(AuditLog(
            case_id=case_id,
            actor="RazorpayLiveGateway",
            action="REAL_PAYMENT_FAILURE",
            input_summary=f"Payment {payment_id} declined. Amount: ₹{payload.amount:,.2f}",
            decision=f"Root cause diagnosed: '{root_info['root_cause']}'",
            details=f"Live customer transaction for {payload.customer_name} ({payload.customer_email})"
        ))
        db.commit()

        # Run Optimizer & Guardrails
        cust_dict = {
            "id": customer.id,
            "name": customer.name,
            "cohort": customer.cohort,
            "lifetime_value": customer.lifetime_value,
            "historical_recovery_rate": customer.historical_recovery_rate,
            "preferred_channel": customer.preferred_channel
        }
        event_dict = {
            "amount": payload.amount,
            "failure_code": payload.failure_reason,
            "attempt_number": 1,
            "root_cause": root_info["root_cause"],
            "hour_of_day": 14
        }
        decision = optimizer.evaluate_candidate_actions(cust_dict, event_dict)
        executor.execute_recovery_action(db, case, customer, decision)

        return {
            "status": "failure_processed",
            "case_id": case_id,
            "payment_id": payment_id,
            "customer_name": payload.customer_name,
            "amount": payload.amount,
            "chosen_action": decision["chosen_action"],
            "expected_net_value": decision["chosen_action_details"]["net_expected_value"]
        }

    return {"status": "success_acknowledged"}
