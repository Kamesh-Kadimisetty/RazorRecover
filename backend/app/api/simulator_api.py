import uuid
import datetime
import random
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.schemas import Customer, PaymentEvent, RecoveryCase, RecoveryAction, AuditLog, SimulateEventIn
from backend.app.ml.cohorts import COHORTS
from backend.app.ml.dataset_generator import generate_customer_profile
from backend.app.engine.detector import classify_root_cause
from backend.app.engine.optimizer import optimizer
from backend.app.engine.executor import executor

router = APIRouter(prefix="/api/simulator", tags=["Event Simulator"])

@router.post("/trigger-failure")
def trigger_simulated_failure(payload: SimulateEventIn, db: Session = Depends(get_db)):
    """
    Simulates an incoming Razorpay 'payment.failed' webhook event matching
    Razorpay's documented entity payload schema.
    """
    cohort = payload.customer_cohort or "reliable"
    cohort_info = COHORTS.get(cohort, COHORTS["reliable"])
    amount = payload.amount or round(random.uniform(*cohort_info["typical_order_range"]), 2)

    payment_id = f"pay_sim_{uuid.uuid4().hex[:10]}"
    order_id = f"order_sim_{uuid.uuid4().hex[:8]}"
    fail_reason = payload.failure_reason or "INSUFFICIENT_FUNDS"

    # Find or generate customer
    customer = db.query(Customer).filter(Customer.cohort == cohort).first()
    if not customer:
        c_prof = generate_customer_profile(random.randint(100, 999), cohort_override=cohort)
        if payload.customer_name:
            c_prof["name"] = payload.customer_name
        customer = Customer(**c_prof)
        db.add(customer)
        db.commit()
        db.refresh(customer)

    # Classify root cause
    root_info = classify_root_cause({
        "error_code": fail_reason,
        "error_description": f"Simulation failure for {fail_reason}"
    })

    # Record payment event
    payment_event = PaymentEvent(
        id=payment_id,
        order_id=order_id,
        customer_id=customer.id,
        amount=amount,
        currency="INR",
        status="failed",
        method=payload.method or "upi",
        error_code=fail_reason,
        error_description=f"Transaction declined: {fail_reason}",
        error_source="customer",
        error_step="payment_authorization",
        error_reason=fail_reason.lower(),
        attempt_number=1
    )
    db.add(payment_event)

    # Create recovery case
    case_id = f"case_rec_{uuid.uuid4().hex[:8]}"
    case = RecoveryCase(
        id=case_id,
        payment_id=payment_id,
        customer_id=customer.id,
        amount_at_risk=amount,
        root_cause=root_info["root_cause"],
        status="evaluating"
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Initial detection audit log
    db.add(AuditLog(
        case_id=case_id,
        actor="RecoveryDetector",
        action="REVENUE_RISK_DETECTED",
        input_summary=f"Event: payment.failed | Amount: ₹{amount:,.2f} | Reason: {fail_reason}",
        decision=f"Root cause classified as '{root_info['root_cause']}'",
        details=root_info["explanation"]
    ))
    db.commit()

    # Evaluate actions
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
        "amount": amount,
        "failure_code": fail_reason,
        "attempt_number": 1,
        "root_cause": root_info["root_cause"],
        "hour_of_day": datetime.datetime.now().hour
    }
    decision = optimizer.evaluate_candidate_actions(cust_dict, event_dict)

    # Execute bounded action
    recovery_action = executor.execute_recovery_action(
        db=db,
        case=case,
        customer=customer,
        decision=decision
    )

    return {
        "status": "success",
        "case_id": case.id,
        "customer_name": customer.name,
        "customer_cohort": customer.cohort,
        "amount": amount,
        "root_cause": case.root_cause,
        "chosen_action": decision["chosen_action"],
        "recovery_probability": decision["chosen_action_details"]["probability"],
        "net_expected_value": decision["chosen_action_details"]["net_expected_value"],
        "selection_reason": decision["selection_reason"],
        "action_status": recovery_action.status
    }

@router.post("/seed-data")
def seed_demo_data(db: Session = Depends(get_db)):
    """Seed the database with 15 realistic historical and active recovery records."""
    existing_count = db.query(RecoveryCase).count()
    if existing_count >= 15:
        return {"status": "already_seeded", "count": existing_count}

    cohort_keys = list(COHORTS.keys())
    for idx, cohort in enumerate(cohort_keys * 3):
        cohort_info = COHORTS[cohort]
        c_prof = generate_customer_profile(100 + idx, cohort_override=cohort)
        customer = Customer(**c_prof)
        db.add(customer)
        db.commit()
        db.refresh(customer)

        amount = round(random.uniform(*cohort_info["typical_order_range"]), 2)
        if idx == 0:
            amount = 65000.0  # High value escalation case

        pay_id = f"pay_seed_{uuid.uuid4().hex[:8]}"
        order_id = f"order_seed_{uuid.uuid4().hex[:8]}"
        reasons = ["INSUFFICIENT_FUNDS", "GATEWAY_TIMEOUT", "CARD_NETWORK_DECLINE", "USER_DROPPED_OFF"]
        reason = random.choice(reasons)

        pay = PaymentEvent(
            id=pay_id,
            order_id=order_id,
            customer_id=customer.id,
            amount=amount,
            status="failed",
            method="upi",
            error_code=reason,
            error_description=f"Seed failure: {reason}",
            attempt_number=1
        )
        db.add(pay)

        case_id = f"case_seed_{uuid.uuid4().hex[:8]}"
        root_info = classify_root_cause({"error_code": reason})
        case = RecoveryCase(
            id=case_id,
            payment_id=pay_id,
            customer_id=customer.id,
            amount_at_risk=amount,
            root_cause=root_info["root_cause"],
            status="evaluating"
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        db.add(AuditLog(
            case_id=case_id,
            actor="RecoveryDetector",
            action="REVENUE_RISK_DETECTED",
            input_summary=f"Event: payment.failed | Amount: ₹{amount:,.2f} | Reason: {reason}",
            decision=f"Classified as '{root_info['root_cause']}'",
            details="Initial detection"
        ))
        db.commit()

        decision = optimizer.evaluate_candidate_actions(
            {"id": customer.id, "cohort": cohort, "historical_recovery_rate": customer.historical_recovery_rate, "preferred_channel": customer.preferred_channel},
            {"amount": amount, "failure_code": reason, "attempt_number": 1, "root_cause": root_info["root_cause"], "hour_of_day": 14}
        )
        executor.execute_recovery_action(db, case, customer, decision)

        # Mark approximately half as already recovered to show realistic past metrics
        if idx % 2 == 1 and case.status != "escalated":
            case.status = "recovered"
            case.recovered_amount = amount
            case.recovered_at = datetime.datetime.utcnow()
            case.recovery_time_hours = round(random.uniform(2.5, 11.0), 1)
            db.add(AuditLog(
                case_id=case_id,
                actor="SimulatorOutcomeTracker",
                action="PAYMENT_CAPTURED_EVENT",
                input_summary=f"Captured ₹{amount:,.2f}",
                decision=f"Recovered in {case.recovery_time_hours} hours",
                details="Completed payment link"
            ))
            db.commit()

    return {"status": "seeded_successfully", "total_cases": db.query(RecoveryCase).count()}
