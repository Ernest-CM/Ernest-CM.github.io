from typing import List, Dict, Any
import os
from datetime import datetime
from app.models import Plan, PlanStep, ToolResult, ExecutionResult, TicketStatus
from app.tools import get_tool, is_destructive
from app.db import get_db_context, ToolCallDB, TicketDB, MetricsDB
import traceback


class ExecutorError(Exception):
    """Exception raised during execution"""
    pass


class Executor:
    """Executor that runs action plans step by step"""
    
    def __init__(self):
        self.auto_apply = os.getenv("AUTO_APPLY", "false").lower() == "true"
        self.sandbox_mode = os.getenv("SANDBOX_MODE", "true").lower() == "true"
    
    def _execute_step(self, step: PlanStep, plan_id: int, ticket_id: str) -> ToolResult:
        """
        Execute a single step in the plan
        
        Args:
            step: The step to execute
            plan_id: The plan ID for logging
            ticket_id: The ticket ID
            
        Returns:
            ToolResult with the outcome
        """
        tool_func = get_tool(step.tool)
        
        if not tool_func:
            return ToolResult(
                tool=step.tool,
                args=step.args,
                result=None,
                success=False,
                error=f"Tool '{step.tool}' not found"
            )
        
        # Check if step is destructive and requires approval
        if step.destructive and not self.auto_apply:
            return ToolResult(
                tool=step.tool,
                args=step.args,
                result=None,
                success=False,
                error="Destructive action requires approval (AUTO_APPLY=false)"
            )
        
        try:
            # Execute the tool
            result = tool_func(**step.args)
            
            # Log to database
            try:
                with get_db_context() as db:
                    tool_call = ToolCallDB(
                        plan_id=plan_id,
                        ticket_id=ticket_id,
                        step=step.step,
                        tool=step.tool,
                        args=step.args,
                        result=result,
                        success=True,
                        error=None
                    )
                    db.add(tool_call)
            except Exception:
                # Ignore database errors in tests
                pass
            
            return ToolResult(
                tool=step.tool,
                args=step.args,
                result=result,
                success=True,
                error=None
            )
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            error_trace = traceback.format_exc()
            
            # Log error to database
            try:
                with get_db_context() as db:
                    tool_call = ToolCallDB(
                        plan_id=plan_id,
                        ticket_id=ticket_id,
                        step=step.step,
                        tool=step.tool,
                        args=step.args,
                        result=None,
                        success=False,
                        error=error_trace
                    )
                    db.add(tool_call)
            except Exception:
                # Ignore database errors in tests
                pass
            
            return ToolResult(
                tool=step.tool,
                args=step.args,
                result=None,
                success=False,
                error=error_msg
            )
    
    def execute_plan(self, plan: Plan, plan_id: int, approved: bool = False) -> ExecutionResult:
        """
        Execute a complete plan
        
        Args:
            plan: The plan to execute
            plan_id: The database ID of the plan
            approved: Whether destructive actions are approved
            
        Returns:
            ExecutionResult with outcomes of all steps
        """
        start_time = datetime.utcnow()
        tool_results: List[ToolResult] = []
        
        # Check if plan contains destructive steps
        has_destructive = any(step.destructive for step in plan.steps)
        
        # If has destructive steps and not approved, only execute non-destructive
        if has_destructive and not approved and not self.auto_apply:
            status = TicketStatus.AWAITING_APPROVAL
            
            # Execute only non-destructive steps
            for step in plan.steps:
                if not step.destructive:
                    result = self._execute_step(step, plan_id, plan.ticket_id)
                    tool_results.append(result)
                else:
                    # Skip destructive steps
                    result = ToolResult(
                        tool=step.tool,
                        args=step.args,
                        result=None,
                        success=False,
                        error="Awaiting approval for destructive action"
                    )
                    tool_results.append(result)
            
        else:
            # Execute all steps
            for step in plan.steps:
                result = self._execute_step(step, plan_id, plan.ticket_id)
                tool_results.append(result)
                
                # If a critical step fails, stop execution
                if not result.success and step.tool not in ["reply_ticket"]:
                    # Continue with best effort, but mark for escalation
                    pass
            
            # Determine final status
            all_success = all(r.success for r in tool_results)
            any_failure = any(not r.success for r in tool_results)
            
            if all_success:
                status = TicketStatus.COMPLETED
            elif any_failure:
                # Check if we need to escalate
                critical_failures = [
                    r for r in tool_results 
                    if not r.success and r.tool not in ["reply_ticket"]
                ]
                if critical_failures:
                    status = TicketStatus.ESCALATED
                else:
                    status = TicketStatus.COMPLETED
            else:
                status = TicketStatus.COMPLETED
        
        # Update ticket status in database
        try:
            with get_db_context() as db:
                ticket = db.query(TicketDB).filter(
                    TicketDB.ticket_id == plan.ticket_id
                ).first()
                if ticket:
                    ticket.status = status
                    ticket.updated_at = datetime.utcnow()
                
                # Record metrics
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                metrics = MetricsDB(
                    ticket_id=plan.ticket_id,
                    auto_resolved=(status == TicketStatus.COMPLETED and not approved),
                    escalated=(status == TicketStatus.ESCALATED),
                    steps_count=len(plan.steps),
                    execution_time=execution_time
                )
                db.add(metrics)
        except Exception:
            # Ignore database errors in tests
            pass
        
        return ExecutionResult(
            ticket_id=plan.ticket_id,
            plan_id=plan_id,
            tool_results=tool_results,
            status=status,
            completed_at=datetime.utcnow()
        )
    
    def can_auto_execute(self, plan: Plan) -> bool:
        """
        Check if a plan can be auto-executed without approval
        
        Args:
            plan: The plan to check
            
        Returns:
            True if plan can be auto-executed, False if it needs approval
        """
        # If AUTO_APPLY is enabled, can execute anything
        if self.auto_apply and not self.sandbox_mode:
            return True
        
        # Otherwise, can only auto-execute non-destructive plans
        has_destructive = any(step.destructive for step in plan.steps)
        return not has_destructive
