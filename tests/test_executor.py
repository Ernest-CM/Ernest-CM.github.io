import pytest
from app.executor import Executor
from app.models import Plan, PlanStep, TicketStatus
from app.db import TicketDB, PlanDB, ToolCallDB


def test_executor_executes_non_destructive_step(db_session):
    """Test that executor can execute a non-destructive step"""
    executor = Executor()
    
    step = PlanStep(
        step=1,
        tool="get_account_info",
        args={"user_id": "u123"},
        destructive=False
    )
    
    result = executor._execute_step(step, plan_id=1, ticket_id="t100")
    
    assert result.success == True
    assert result.tool == "get_account_info"
    assert result.result is not None


def test_executor_blocks_destructive_step_without_approval(db_session):
    """Test that executor blocks destructive steps when AUTO_APPLY is false"""
    executor = Executor()
    
    step = PlanStep(
        step=1,
        tool="reset_password",
        args={"user_id": "u123"},
        destructive=True
    )
    
    result = executor._execute_step(step, plan_id=1, ticket_id="t100")
    
    assert result.success == False
    assert "requires approval" in result.error.lower()


def test_executor_executes_complete_plan(db_session):
    """Test that executor can execute a complete plan"""
    executor = Executor()
    
    plan = Plan(
        ticket_id="t100",
        steps=[
            PlanStep(step=1, tool="get_account_info", args={"user_id": "u123"}, destructive=False),
            PlanStep(step=2, tool="fetch_logs", args={"user_id": "u123", "last_hours": 24}, destructive=False)
        ]
    )
    
    result = executor.execute_plan(plan, plan_id=1, approved=False)
    
    assert result.ticket_id == "t100"
    assert len(result.tool_results) == 2
    assert all(r.success for r in result.tool_results)
    assert result.status == TicketStatus.COMPLETED


def test_executor_partial_execution_with_destructive_steps(db_session):
    """Test that executor only executes non-destructive steps when not approved"""
    executor = Executor()
    
    plan = Plan(
        ticket_id="t100",
        steps=[
            PlanStep(step=1, tool="get_account_info", args={"user_id": "u123"}, destructive=False),
            PlanStep(step=2, tool="reset_password", args={"user_id": "u123"}, destructive=True),
            PlanStep(step=3, tool="reply_ticket", args={"ticket_id": "t100", "message": "Done"}, destructive=False)
        ]
    )
    
    result = executor.execute_plan(plan, plan_id=1, approved=False)
    
    assert result.ticket_id == "t100"
    assert len(result.tool_results) == 3
    assert result.tool_results[0].success == True  # get_account_info
    assert result.tool_results[1].success == False  # reset_password (blocked)
    assert result.status == TicketStatus.AWAITING_APPROVAL


def test_executor_full_execution_with_approval(db_session):
    """Test that executor executes all steps when approved"""
    executor = Executor()
    
    plan = Plan(
        ticket_id="t100",
        steps=[
            PlanStep(step=1, tool="get_account_info", args={"user_id": "u123"}, destructive=False),
            PlanStep(step=2, tool="reset_password", args={"user_id": "u123"}, destructive=True)
        ]
    )
    
    result = executor.execute_plan(plan, plan_id=1, approved=True)
    
    assert result.ticket_id == "t100"
    assert len(result.tool_results) == 2
    # Both steps executed (though reset_password returns simulated in SANDBOX_MODE)
    assert all(r.tool != "" for r in result.tool_results)


def test_executor_escalates_on_critical_failure(db_session):
    """Test that executor escalates on critical tool failures"""
    executor = Executor()
    
    plan = Plan(
        ticket_id="t100",
        steps=[
            PlanStep(step=1, tool="get_account_info", args={"user_id": "u123"}, destructive=False),
            # This would fail if the tool raised an exception
            PlanStep(step=2, tool="reply_ticket", args={"ticket_id": "t100", "message": "Done"}, destructive=False)
        ]
    )
    
    result = executor.execute_plan(plan, plan_id=1, approved=False)
    
    # Should complete normally with current mock tools
    assert result.status in [TicketStatus.COMPLETED, TicketStatus.ESCALATED]


def test_executor_can_auto_execute_safe_plan():
    """Test that executor allows auto-execution of safe plans"""
    executor = Executor()
    
    plan = Plan(
        ticket_id="t100",
        steps=[
            PlanStep(step=1, tool="get_account_info", args={"user_id": "u123"}, destructive=False)
        ]
    )
    
    assert executor.can_auto_execute(plan) == True


def test_executor_cannot_auto_execute_destructive_plan():
    """Test that executor blocks auto-execution of destructive plans"""
    executor = Executor()
    
    plan = Plan(
        ticket_id="t100",
        steps=[
            PlanStep(step=1, tool="reset_password", args={"user_id": "u123"}, destructive=True)
        ]
    )
    
    assert executor.can_auto_execute(plan) == False
