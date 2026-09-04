import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.database import get_db
from backend.app.models.schemas import RecoveryCase, RecoveryAction, AuditLog, PaymentEvent, Customer
from backend.app.engine.optimizer import optimizer

router = APIRouter(prefix="/api/cases", tags=["Recovery Cases"])

class OverrideActionIn(BaseModel):
    new_action: str
    reason: str

@router.get("")
def list_cases(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List recovery cases ordered by latest with optional status filter."""
    query = db.query(RecoveryCase).order_by(RecoveryCase.created_at.desc())
    if status and status != "all":
        query = query.filter(RecoveryCase.status == status)
    cases = query.limit(limit).all()

    result = []
    for c in cases:
        cust = c.customer
        result.append({
            "id": c.id,
            "payment_id": c.payment_id,
            "customer_id": c.customer_id,
            "customer_name": cust.name if cust else "Unknown",
            "customer_cohort": cust.cohort if cust else "reliable",
            "amount_at_risk": c.amount_at_risk,
            "root_cause": c.root_cause,
            "status": c.status,
            "chosen_action": c.chosen_action,
            "recovery_probability": c.recovery_probability,
            "expected_net_value": c.expected_net_value,
            "policy_check_status": c.policy_check_status,
            "policy_notes": c.policy_notes,
            "recovered_amount": c.recovered_amount,
            "recovered_at": c.recovered_at.isoformat() if c.recovered_at else None,
            "recovery_time_hours": c.recovery_time_hours,
            "created_at": c.created_at.isoformat()
        })
    return result

@router.get("/{case_id}")
def get_case_detail(case_id: str, db: Session = Depends(get_db)):
    """Get full case inspection data including candidate scoring, policy checks, and audit trail."""
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    cust = case.customer
    pay = case.payment

    # Re-evaluate candidate options matrix for inspection visualization
    cust_dict = {
        "id": cust.id,
        "cohort": cust.cohort,
        "historical_recovery_rate": cust.historical_recovery_rate,
        "total_payments": cust.total_payments,
        "successful_payments": cust.successful_payments,
        "lifetime_value": cust.lifetime_value,
        "preferred_channel": cust.preferred_channel,
        "opt_out": cust.opt_out
    }
    event_dict = {
        "amount": case.amount_at_risk,
        "failure_code": pay.error_code if pay else "INSUFFICIENT_FUNDS",
        "attempt_number": pay.attempt_number if pay else 1,
        "root_cause": case.root_cause,
        "hour_of_day": 14
    }
    candidates_eval = optimizer.evaluate_candidate_actions(cust_dict, event_dict)

    actions = db.query(RecoveryAction).filter(RecoveryAction.case_id == case_id).all()
    audit_logs = db.query(AuditLog).filter(AuditLog.case_id == case_id).order_by(AuditLog.timestamp.asc()).all()

    return {
        "case": {
            "id": case.id,
            "payment_id": case.payment_id,
            "customer_id": case.customer_id,
            "amount_at_risk": case.amount_at_risk,
            "root_cause": case.root_cause,
            "status": case.status,
            "chosen_action": case.chosen_action,
            "recovery_probability": case.recovery_probability,
            "expected_net_value": case.expected_net_value,
            "policy_check_status": case.policy_check_status,
            "policy_notes": case.policy_notes,
            "recovered_amount": case.recovered_amount,
            "recovered_at": case.recovered_at.isoformat() if case.recovered_at else None,
            "recovery_time_hours": case.recovery_time_hours,
            "created_at": case.created_at.isoformat()
        },
        "customer": {
            "id": cust.id,
            "name": cust.name,
            "email": cust.email,
            "phone": cust.phone,
            "cohort": cust.cohort,
            "lifetime_value": cust.lifetime_value,
            "historical_recovery_rate": cust.historical_recovery_rate,
            "total_payments": cust.total_payments,
            "successful_payments": cust.successful_payments,
            "preferred_channel": cust.preferred_channel
        },
        "payment": {
            "id": pay.id if pay else "N/A",
            "order_id": pay.order_id if pay else "N/A",
            "method": pay.method if pay else "upi",
            "error_code": pay.error_code if pay else "N/A",
            "error_description": pay.error_description if pay else "N/A",
            "attempt_number": pay.attempt_number if pay else 1
        },
        "candidate_actions_matrix": candidates_eval["all_candidates"],
        "selection_reason": candidates_eval["selection_reason"],
        "actions": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "scheduled_for": a.scheduled_for.isoformat(),
                "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                "status": a.status,
                "cost": a.cost,
                "discount_offered": a.discount_offered,
                "discount_pct": a.discount_pct,
                "channel": a.channel,
                "message_content": a.message_content,
                "audit_rationale": a.audit_rationale
            } for a in actions
        ],
        "audit_logs": [
            {
                "id": l.id,
                "timestamp": l.timestamp.isoformat(),
                "actor": l.actor,
                "action": l.action,
                "input_summary": l.input_summary,
                "decision": l.decision,
                "details": l.details
            } for l in audit_logs
        ]
    }

@router.post("/{case_id}/simulate-recovery")
def simulate_case_recovery(case_id: str, db: Session = Depends(get_db)):
    """
    Simulate a customer payment completion for this case.
    Demonstrates the closed-loop recovery and immediate metrics update.
    """
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    now = datetime.datetime.utcnow()
    diff_hours = (now - case.created_at).total_seconds() / 3600.0

    case.status = "recovered"
    case.recovered_amount = case.amount_at_risk
    case.recovered_at = now
    case.recovery_time_hours = round(max(0.5, diff_hours), 2)

    # Cancel scheduled interventions (Stopping rule)
    actions = db.query(RecoveryAction).filter(RecoveryAction.case_id == case_id).all()
    for a in actions:
        if a.status == "scheduled":
            a.status = "completed"

    db.add(AuditLog(
        case_id=case.id,
        actor="SimulatorOutcomeTracker",
        action="PAYMENT_CAPTURED_EVENT",
        input_summary=f"Captured ₹{case.recovered_amount:,.2f} via Razorpay Checkout",
        decision=f"Revenue recovery confirmed after {case.recovery_time_hours:.1f} hours.",
        details="Customer completed transaction via smart link. Case closed as RECOVERED."
    ))
    db.commit()

    return {
        "status": "recovered",
        "case_id": case.id,
        "recovered_amount": case.recovered_amount,
        "recovery_time_hours": case.recovery_time_hours
    }

@router.post("/{case_id}/override-action")
def override_action(case_id: str, payload: OverrideActionIn, db: Session = Depends(get_db)):
    """Allows merchant operations to manually change action or escalate."""
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    old_action = case.chosen_action
    case.chosen_action = payload.new_action
    if payload.new_action == "human_escalation":
        case.status = "escalated"
    elif payload.new_action == "do_nothing":
        case.status = "stopped"
    else:
        case.status = "action_scheduled"

    db.add(AuditLog(
        case_id=case.id,
        actor="MerchantOps",
        action="MANUAL_ACTION_OVERRIDE",
        input_summary=f"Changed from '{old_action}' to '{payload.new_action}'",
        decision=f"Manual override applied. Reason: {payload.reason}",
        details="Merchant operator bypassed automated policy recommendation."
    ))
    db.commit()

    return {"status": "overridden", "new_action": payload.new_action}
