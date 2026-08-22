"""
SQLAlchemy ORM models for every table RiskLens AI needs:
transactions, alerts, investigations, evidence, agent_events,
risk_assessments, decisions, human_reviews, feedback, audit_logs.
"""
import uuid
import datetime as dt

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, JSON, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from app.database.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.utcnow()


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, default=_uuid)
    account_id = Column(String, index=True, nullable=False)
    merchant_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=_now, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    transaction_type = Column(String, nullable=False)
    payment_method = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    receiver = Column(String, nullable=False)
    account_balance_before = Column(Float, nullable=False)
    account_balance_after = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    device_id = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    transaction_status = Column(String, default="completed")
    is_fraud = Column(Boolean, default=False)  # ground-truth label, synthetic data only

    alerts = relationship("Alert", back_populates="transaction")


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(String, primary_key=True, default=_uuid)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False)
    account_id = Column(String, nullable=False)
    merchant_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=_now)
    transaction_type = Column(String)
    payment_method = Column(String)
    anomaly_score = Column(Float, nullable=False)
    flag_reason = Column(JSON, nullable=False)  # list[str]
    initial_risk = Column(String, nullable=False)  # LOW/MEDIUM/HIGH/CRITICAL
    status = Column(String, default="open")  # open / investigating / closed

    transaction = relationship("Transaction", back_populates="alerts")
    investigations = relationship("Investigation", back_populates="alert")


class Investigation(Base):
    __tablename__ = "investigations"

    investigation_id = Column(String, primary_key=True, default=_uuid)
    alert_id = Column(String, ForeignKey("alerts.alert_id"), nullable=False)
    case_id = Column(String, default=_uuid)
    status = Column(String, default="pending")  # pending/running/awaiting_review/completed/failed
    loops_used = Column(Integer, default=0)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)
    decision = Column(String, nullable=True)  # ALLOW/REVIEW/BLOCK
    explanation = Column(Text, nullable=True)
    llm_mode = Column(String, default="live")  # "live" or "mock"
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    alert = relationship("Alert", back_populates="investigations")
    evidence = relationship("Evidence", back_populates="investigation")
    agent_events = relationship("AgentEvent", back_populates="investigation")
    risk_assessments = relationship("RiskAssessment", back_populates="investigation")
    decisions = relationship("DecisionRecord", back_populates="investigation")
    human_reviews = relationship("HumanReview", back_populates="investigation")
    feedback_entries = relationship("Feedback", back_populates="investigation")
    audit_logs = relationship("AuditLog", back_populates="investigation")


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id = Column(String, primary_key=True, default=_uuid)
    investigation_id = Column(String, ForeignKey("investigations.investigation_id"), nullable=False)
    source = Column(String, nullable=False)  # evidence_agent / behavior_agent / network_agent / compliance_agent
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=_now)

    investigation = relationship("Investigation", back_populates="evidence")


class AgentEvent(Base):
    __tablename__ = "agent_events"

    event_id = Column(String, primary_key=True, default=_uuid)
    investigation_id = Column(String, ForeignKey("investigations.investigation_id"), nullable=False)
    agent_name = Column(String, nullable=False)
    status = Column(String, nullable=False)  # started/completed/skipped/failed
    finding_summary = Column(Text, nullable=True)
    detail = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=_now)

    investigation = relationship("Investigation", back_populates="agent_events")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    assessment_id = Column(String, primary_key=True, default=_uuid)
    investigation_id = Column(String, ForeignKey("investigations.investigation_id"), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    signal_breakdown = Column(JSON, nullable=False)  # {signal_name: weighted_contribution}
    loop_number = Column(Integer, default=0)
    sufficient_evidence = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)

    investigation = relationship("Investigation", back_populates="risk_assessments")


class DecisionRecord(Base):
    __tablename__ = "decisions"

    decision_id = Column(String, primary_key=True, default=_uuid)
    investigation_id = Column(String, ForeignKey("investigations.investigation_id"), nullable=False)
    decision = Column(String, nullable=False)  # ALLOW/REVIEW/BLOCK
    rationale = Column(Text, nullable=True)
    policy_version = Column(String, default="v1")
    created_at = Column(DateTime, default=_now)

    investigation = relationship("Investigation", back_populates="decisions")


class HumanReview(Base):
    __tablename__ = "human_reviews"

    review_id = Column(String, primary_key=True, default=_uuid)
    investigation_id = Column(String, ForeignKey("investigations.investigation_id"), nullable=False)
    reviewer_decision = Column(String, nullable=False)  # ALLOW/BLOCK/ESCALATE
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)

    investigation = relationship("Investigation", back_populates="human_reviews")


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id = Column(String, primary_key=True, default=_uuid)
    investigation_id = Column(String, ForeignKey("investigations.investigation_id"), nullable=False)
    was_correct = Column(Boolean, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)

    investigation = relationship("Investigation", back_populates="feedback_entries")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String, primary_key=True, default=_uuid)
    investigation_id = Column(String, ForeignKey("investigations.investigation_id"), nullable=False)
    stage = Column(String, nullable=False)
    actor = Column(String, nullable=False)  # e.g. "evidence_agent", "human:analyst1", "system"
    action = Column(String, nullable=False)
    detail = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=_now)

    investigation = relationship("Investigation", back_populates="audit_logs")
