import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from backend.app.database import Base

# ==========================================
# SQLAlchemy ORM Models
# ==========================================

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    cohort = Column(String, default="reliable")  # reliable, cash_constrained, subscription_loyalist, churn_risk, habitual_late
    lifetime_value = Column(Float, default=0.0)
    historical_recovery_rate = Column(Float, default=0.5)
    total_payments = Column(Integer, default=0)
    successful_payments = Column(Integer, default=0)
    failed_payments = Column(Integer, default=0)
    preferred_channel = Column(String, default="whatsapp")
    opt_out = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    payments = relationship("PaymentEvent", back_populates="customer")
    cases = relationship("RecoveryCase", back_populates="customer")


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id = Column(String, primary_key=True, index=True)  # pay_...
    order_id = Column(String, index=True, nullable=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)  # in INR
    currency = Column(String, default="INR")
    status = Column(String, default="failed")  # failed, captured, authorized
    method = Column(String, default="upi")     # upi, card, netbanking, mandate
    error_code = Column(String, nullable=True)
    error_description = Column(String, nullable=True)
    error_source = Column(String, nullable=True)
    error_step = Column(String, nullable=True)
    error_reason = Column(String, nullable=True)
    attempt_number = Column(Integer, default=1)
    raw_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="payments")
    case = relationship("RecoveryCase", back_populates="payment", uselist=False)


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id = Column(String, primary_key=True, index=True)  # case_...
    payment_id = Column(String, ForeignKey("payment_events.id"), nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    amount_at_risk = Column(Float, nullable=False)
    root_cause = Column(String, default="unknown")
    status = Column(String, default="detected")  # detected, evaluating, action_scheduled, action_executed, recovered, escalated, stopped
    chosen_action = Column(String, nullable=True)
    recovery_probability = Column(Float, default=0.0)
    expected_net_value = Column(Float, default=0.0)
    policy_check_status = Column(String, default="pending")  # passed, escalated, blocked
    policy_notes = Column(Text, nullable=True)
    
    recovered_amount = Column(Float, default=0.0)
    recovered_at = Column(DateTime, nullable=True)
    recovery_time_hours = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="cases")
    payment = relationship("PaymentEvent", back_populates="case")
    actions = relationship("RecoveryAction", back_populates="case", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="case", cascade="all, delete-orphan")


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("recovery_cases.id"), nullable=False)
    action_type = Column(String, nullable=False)  # retry_now, delayed_retry, smart_reminder, incentive_discount, human_escalation, stop
    scheduled_for = Column(DateTime, nullable=False)
    executed_at = Column(DateTime, nullable=True)
    status = Column(String, default="scheduled")  # scheduled, executed, cancelled, completed
    cost = Column(Float, default=0.0)
    discount_offered = Column(Float, default=0.0)
    discount_pct = Column(Float, default=0.0)
    channel = Column(String, default="in_app")
    message_content = Column(Text, nullable=True)
    audit_rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("RecoveryCase", back_populates="actions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, ForeignKey("recovery_cases.id"), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    actor = Column(String, nullable=False)  # RecoveryDetector, ModelScorer, Optimizer, PolicyGuardrail, Executor, LLMExplainer, MerchantOps
    action = Column(String, nullable=False)
    input_summary = Column(Text, nullable=True)
    decision = Column(Text, nullable=True)
    details = Column(Text, nullable=True)

    case = relationship("RecoveryCase", back_populates="audit_logs")


class MerchantPolicyConfig(Base):
    __tablename__ = "merchant_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(String, default="mer_default")
    max_retries = Column(Integer, default=3)
    min_retry_interval_hours = Column(Integer, default=6)
    max_discount_pct = Column(Float, default=10.0)
    max_messages_per_48h = Column(Integer, default=2)
    quiet_hours_start = Column(Integer, default=22)
    quiet_hours_end = Column(Integer, default=8)
    human_escalation_threshold_inr = Column(Float, default=50000.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


# ==========================================
# Pydantic Schemas (API Requests/Responses)
# ==========================================

class CustomerOut(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    cohort: str
    lifetime_value: float
    historical_recovery_rate: float
    preferred_channel: str

    class Config:
        from_attributes = True

class AuditLogOut(BaseModel):
    id: int
    case_id: str
    timestamp: datetime.datetime
    actor: str
    action: str
    input_summary: Optional[str] = None
    decision: Optional[str] = None
    details: Optional[str] = None

    class Config:
        from_attributes = True

class RecoveryActionOut(BaseModel):
    id: str
    action_type: str
    scheduled_for: datetime.datetime
    executed_at: Optional[datetime.datetime] = None
    status: str
    cost: float
    discount_offered: float
    channel: str
    message_content: Optional[str] = None
    audit_rationale: Optional[str] = None

    class Config:
        from_attributes = True

class RecoveryCaseOut(BaseModel):
    id: str
    payment_id: str
    customer_id: str
    amount_at_risk: float
    root_cause: str
    status: str
    chosen_action: Optional[str] = None
    recovery_probability: float
    expected_net_value: float
    policy_check_status: str
    policy_notes: Optional[str] = None
    recovered_amount: float
    recovered_at: Optional[datetime.datetime] = None
    recovery_time_hours: Optional[float] = None
    created_at: datetime.datetime
    customer: Optional[CustomerOut] = None
    actions: List[RecoveryActionOut] = []
    audit_logs: List[AuditLogOut] = []

    class Config:
        from_attributes = True

class OverviewMetricsOut(BaseModel):
    gross_at_risk: float
    gross_recovered: float
    recovery_rate_pct: float
    net_recovered: float
    intervention_cost_total: float
    active_cases_count: int
    recovered_cases_count: int
    escalated_cases_count: int
    stopped_cases_count: int
    avg_recovery_time_hours: float
    baseline_comparison: Dict[str, Any]

class PolicyConfigIn(BaseModel):
    max_retries: Optional[int] = 3
    min_retry_interval_hours: Optional[int] = 6
    max_discount_pct: Optional[float] = 10.0
    max_messages_per_48h: Optional[int] = 2
    quiet_hours_start: Optional[int] = 22
    quiet_hours_end: Optional[int] = 8
    human_escalation_threshold_inr: Optional[float] = 50000.0

class SimulateEventIn(BaseModel):
    customer_cohort: Optional[str] = "reliable"  # reliable, cash_constrained, subscription_loyalist, churn_risk, habitual_late
    amount: Optional[float] = 4999.0
    method: Optional[str] = "upi"
    failure_reason: Optional[str] = "INSUFFICIENT_FUNDS"
    customer_name: Optional[str] = "Aditya Sharma"
