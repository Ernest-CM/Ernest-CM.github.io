from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


class TicketStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class ToolType(str, Enum):
    FETCH_LOGS = "fetch_logs"
    GET_ACCOUNT_INFO = "get_account_info"
    KB_SEARCH = "kb_search"
    CHECK_KNOWN_ISSUES = "check_known_issues"
    RUN_DIAGNOSTIC = "run_diagnostic"
    REPLY_TICKET = "reply_ticket"
    RESET_PASSWORD = "reset_password"
    APPLY_PATCH = "apply_patch"


class TicketWebhook(BaseModel):
    ticket_id: str
    user_id: str
    subject: str
    body: str


class PlanStep(BaseModel):
    step: int
    tool: str
    args: Dict[str, Any]
    destructive: bool = False


class Plan(BaseModel):
    ticket_id: str
    steps: List[PlanStep]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "ticket_id": "t100",
                "steps": [
                    {
                        "step": 1,
                        "tool": "fetch_logs",
                        "args": {"user_id": "u123", "last_hours": 24},
                        "destructive": False
                    },
                    {
                        "step": 2,
                        "tool": "check_known_issues",
                        "args": {"query": "CSV upload v2.1"},
                        "destructive": False
                    }
                ]
            }
        }
    }


class ToolResult(BaseModel):
    tool: str
    args: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionResult(BaseModel):
    ticket_id: str
    plan_id: int
    tool_results: List[ToolResult]
    status: TicketStatus
    completed_at: Optional[datetime] = None


class TicketPlanResponse(BaseModel):
    ticket_id: str
    plan_id: int
    status: TicketStatus
    plan: Plan
    requires_approval: bool


class ApprovalRequest(BaseModel):
    approved: bool = True


class MetricsResponse(BaseModel):
    total_tickets: int
    auto_resolved: int
    escalated: int
    awaiting_approval: int
    avg_steps: float
    auto_resolve_rate: float


class AccountInfo(BaseModel):
    user_id: str
    email: str
    plan: str
    account_status: str
    created_at: datetime


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str
    metadata: Dict[str, Any]


class KBArticle(BaseModel):
    id: str
    title: str
    content: str
    relevance_score: float
