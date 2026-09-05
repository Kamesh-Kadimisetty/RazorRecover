from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models.schemas import RecoveryCase, RecoveryAction
from backend.app.engine.explainer import explainer

router = APIRouter(prefix="/api/copilot", tags=["AI Merchant Copilot"])

class CopilotQueryIn(BaseModel):
    query: str

@router.post("/chat")
def chat_with_copilot(payload: CopilotQueryIn, db: Session = Depends(get_db)):
    """Interactive AI Merchant Copilot powered by Gemini 2.5 Flash."""
    gross_at_risk = db.query(func.sum(RecoveryCase.amount_at_risk)).scalar() or 0.0
    gross_recovered = db.query(func.sum(RecoveryCase.recovered_amount)).scalar() or 0.0
    costs_sum = db.query(func.sum(RecoveryAction.cost)).scalar() or 0.0
    discounts_sum = db.query(func.sum(RecoveryAction.discount_offered)).scalar() or 0.0
    net_recovered = max(0.0, gross_recovered - costs_sum - discounts_sum)
    rec_rate = (gross_recovered / gross_at_risk * 100.0) if gross_at_risk > 0 else 0.0

    active_cases = db.query(RecoveryCase).filter(RecoveryCase.status.in_(["detected", "evaluating", "action_scheduled", "action_executed"])).count()
    escalated_cases = db.query(RecoveryCase).filter(RecoveryCase.status == "escalated").count()

    context = {
        "gross_at_risk": gross_at_risk,
        "gross_recovered": gross_recovered,
        "net_recovered": net_recovered,
        "recovery_rate_pct": round(rec_rate, 1),
        "active_cases_count": active_cases,
        "escalated_cases_count": escalated_cases
    }

    answer = explainer.copilot_query(payload.query, context)
    return {
        "query": payload.query,
        "answer": answer,
        "model": "Gemini 2.5 Flash",
        "live_metrics_context": context
    }
