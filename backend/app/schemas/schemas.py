"""Pydantic response/request schemas for the FastAPI layer."""
from __future__ import annotations
import datetime as dt
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    transaction_id: str
    account_id: str
    merchant_id: str
    timestamp: dt.datetime
    amount: float
    currency: str
    transaction_type: str
    payment_method: str
    sender: str
    receiver: str
    account_balance_before: float
    account_balance_after: float
    location: str
    device_id: str
    ip_address: str
    transaction_status: str
    is_fraud: bool


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    alert_id: str
    transaction_id: str
    account_id: str
    merchant_id: str
    amount: float
    timestamp: dt.datetime
    transaction_type: Optional[str] = None
    payment_method: Optional[str] = None
    anomaly_score: float
    flag_reason: list[str]
    initial_risk: str
    status: str


class InvestigationCreate(BaseModel):
    alert_id: str


class AgentEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    agent_name: str
    status: str
    finding_summary: Optional[str] = None
    detail: Optional[Any] = None
    timestamp: dt.datetime


class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    investigation_id: str
    alert_id: str
    case_id: str
    status: str
    loops_used: int
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    decision: Optional[str] = None
    explanation: Optional[str] = None
    llm_mode: str
    created_at: dt.datetime
    updated_at: dt.datetime
    agent_events: list[AgentEventOut] = []


class ReviewIn(BaseModel):
    reviewer_decision: str  # ALLOW / BLOCK / ESCALATE
    notes: Optional[str] = None


class FeedbackIn(BaseModel):
    was_correct: bool
    comment: Optional[str] = None


class DashboardSummary(BaseModel):
    total_transactions: int
    suspicious_transactions: int
    high_risk: int
    blocked: int
    pending_review: int
    fraud_precision: float
    fraud_recall: float
    f1_score: float
    false_positive_rate: float
    false_positive_cost: float
