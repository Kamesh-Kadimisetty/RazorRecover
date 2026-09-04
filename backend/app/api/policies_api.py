from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.schemas import MerchantPolicyConfig, PolicyConfigIn
from backend.app.config import settings

router = APIRouter(prefix="/api/policies", tags=["Merchant Policies"])

@router.get("")
def get_merchant_policy(db: Session = Depends(get_db)):
    """Retrieve active merchant policy guardrails."""
    policy = db.query(MerchantPolicyConfig).first()
    if not policy:
        policy = MerchantPolicyConfig(
            max_retries=settings.MAX_RETRIES,
            min_retry_interval_hours=settings.MIN_RETRY_INTERVAL_HOURS,
            max_discount_pct=settings.MAX_DISCOUNT_PCT,
            max_messages_per_48h=settings.MAX_MESSAGES_PER_48H,
            quiet_hours_start=settings.QUIET_HOURS_START,
            quiet_hours_end=settings.QUIET_HOURS_END,
            human_escalation_threshold_inr=settings.HUMAN_ESCALATION_THRESHOLD_INR
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

    return {
        "max_retries": policy.max_retries,
        "min_retry_interval_hours": policy.min_retry_interval_hours,
        "max_discount_pct": policy.max_discount_pct,
        "max_messages_per_48h": policy.max_messages_per_48h,
        "quiet_hours_start": policy.quiet_hours_start,
        "quiet_hours_end": policy.quiet_hours_end,
        "human_escalation_threshold_inr": policy.human_escalation_threshold_inr
    }

@router.post("")
def update_merchant_policy(payload: PolicyConfigIn, db: Session = Depends(get_db)):
    """Update active merchant policy guardrails."""
    policy = db.query(MerchantPolicyConfig).first()
    if not policy:
        policy = MerchantPolicyConfig()
        db.add(policy)

    if payload.max_retries is not None:
        policy.max_retries = payload.max_retries
    if payload.min_retry_interval_hours is not None:
        policy.min_retry_interval_hours = payload.min_retry_interval_hours
    if payload.max_discount_pct is not None:
        policy.max_discount_pct = payload.max_discount_pct
    if payload.max_messages_per_48h is not None:
        policy.max_messages_per_48h = payload.max_messages_per_48h
    if payload.quiet_hours_start is not None:
        policy.quiet_hours_start = payload.quiet_hours_start
    if payload.quiet_hours_end is not None:
        policy.quiet_hours_end = payload.quiet_hours_end
    if payload.human_escalation_threshold_inr is not None:
        policy.human_escalation_threshold_inr = payload.human_escalation_threshold_inr

    db.commit()
    return {"status": "policy_updated"}
