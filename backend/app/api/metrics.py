from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models.schemas import RecoveryCase, RecoveryAction

router = APIRouter(prefix="/api/metrics", tags=["Metrics & Analytics"])

@router.get("/overview")
def get_metrics_overview(db: Session = Depends(get_db)):
    """Computes real-time merchant revenue recovery metrics."""
    total_cases = db.query(RecoveryCase).count()
    gross_at_risk = db.query(func.sum(RecoveryCase.amount_at_risk)).scalar() or 0.0
    gross_recovered = db.query(func.sum(RecoveryCase.recovered_amount)).scalar() or 0.0
    
    # Intervention costs and discounts
    costs_sum = db.query(func.sum(RecoveryAction.cost)).scalar() or 0.0
    discounts_sum = db.query(func.sum(RecoveryAction.discount_offered)).scalar() or 0.0
    total_spend = costs_sum + discounts_sum
    net_recovered = max(0.0, gross_recovered - total_spend)

    recovery_rate = (gross_recovered / gross_at_risk * 100.0) if gross_at_risk > 0 else 0.0

    active_cases = db.query(RecoveryCase).filter(RecoveryCase.status.in_(["detected", "evaluating", "action_scheduled", "action_executed"])).count()
    recovered_cases = db.query(RecoveryCase).filter(RecoveryCase.status == "recovered").count()
    escalated_cases = db.query(RecoveryCase).filter(RecoveryCase.status == "escalated").count()
    stopped_cases = db.query(RecoveryCase).filter(RecoveryCase.status == "stopped").count()

    # Average recovery time
    avg_time = db.query(func.avg(RecoveryCase.recovery_time_hours)).filter(RecoveryCase.status == "recovered").scalar() or 0.0

    return {
        "gross_at_risk": round(gross_at_risk, 2),
        "gross_recovered": round(gross_recovered, 2),
        "recovery_rate_pct": round(recovery_rate, 1),
        "net_recovered": round(net_recovered, 2),
        "intervention_cost_total": round(total_spend, 2),
        "total_cases_count": total_cases,
        "active_cases_count": active_cases,
        "recovered_cases_count": recovered_cases,
        "escalated_cases_count": escalated_cases,
        "stopped_cases_count": stopped_cases,
        "avg_recovery_time_hours": round(avg_time, 1)
    }
