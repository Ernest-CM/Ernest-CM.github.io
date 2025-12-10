from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import time
import os
import json
from typing import Dict

from app.models import (
    TicketWebhook, 
    TicketPlanResponse, 
    ApprovalRequest,
    MetricsResponse,
    TicketStatus
)
from app.db import get_db, TicketDB, PlanDB, MetricsDB
from app.planner import Planner, PlannerError
from app.executor import Executor
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting storage (in production, use Redis)
request_counts: Dict[str, list] = {}


def rate_limit_middleware(request: Request):
    """Simple rate limiting middleware"""
    client_ip = request.client.host
    current_time = time.time()
    rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    if client_ip not in request_counts:
        request_counts[client_ip] = []
    
    # Remove old requests (older than 1 minute)
    request_counts[client_ip] = [
        t for t in request_counts[client_ip] 
        if current_time - t < 60
    ]
    
    # Check rate limit
    if len(request_counts[client_ip]) >= rate_limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    
    request_counts[client_ip].append(current_time)


@router.post("/webhook/ticket")
async def receive_ticket(
    ticket: TicketWebhook,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receive a new support ticket and create an action plan
    
    Args:
        ticket: The ticket webhook data
        db: Database session
        
    Returns:
        The created plan and ticket information
    """
    try:
        # Apply rate limiting
        rate_limit_middleware(request)
        
        logger.info(f"Received ticket: {ticket.ticket_id}")
        
        # Check if ticket already exists
        existing_ticket = db.query(TicketDB).filter(
            TicketDB.ticket_id == ticket.ticket_id
        ).first()
        
        if existing_ticket:
            raise HTTPException(
                status_code=400,
                detail=f"Ticket {ticket.ticket_id} already exists"
            )
        
        # Save ticket to database
        ticket_db = TicketDB(
            ticket_id=ticket.ticket_id,
            user_id=ticket.user_id,
            subject=ticket.subject,
            body=ticket.body,
            status=TicketStatus.PLANNING
        )
        db.add(ticket_db)
        db.commit()
        
        # Create planner and generate plan
        planner = Planner()
        
        try:
            plan = planner.create_plan(ticket)
            requires_approval = planner.requires_approval(plan)
            
            # Save plan to database
            plan_dict = plan.model_dump(mode='json')  # mode='json' handles datetime serialization
            plan_db = PlanDB(
                ticket_id=ticket.ticket_id,
                plan_data=plan_dict,
                requires_approval=requires_approval,
                approved=False
            )
            db.add(plan_db)
            db.commit()
            db.refresh(plan_db)
            
            # Update ticket status
            if requires_approval:
                ticket_db.status = TicketStatus.AWAITING_APPROVAL
            else:
                ticket_db.status = TicketStatus.EXECUTING
            db.commit()
            
            # If plan doesn't require approval, execute it automatically
            executor = Executor()
            if executor.can_auto_execute(plan):
                logger.info(f"Auto-executing plan for ticket {ticket.ticket_id}")
                execution_result = executor.execute_plan(plan, plan_db.id, approved=False)
                
                return {
                    "ticket_id": ticket.ticket_id,
                    "status": "executed",
                    "plan_id": plan_db.id,
                    "plan": plan.model_dump(),
                    "execution_result": execution_result.model_dump(),
                    "requires_approval": False
                }
            else:
                logger.info(f"Plan requires approval for ticket {ticket.ticket_id}")
                return {
                    "ticket_id": ticket.ticket_id,
                    "status": "awaiting_approval",
                    "plan_id": plan_db.id,
                    "plan": plan.model_dump(),
                    "requires_approval": True,
                    "message": "Plan contains destructive actions and requires approval"
                }
                
        except PlannerError as e:
            logger.error(f"Planning failed for ticket {ticket.ticket_id}: {e}")
            ticket_db.status = TicketStatus.ESCALATED
            db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Planning failed: {str(e)}. Ticket escalated to human."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing ticket {ticket.ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticket/{ticket_id}/plan")
async def get_ticket_plan(
    ticket_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the action plan for a ticket
    
    Args:
        ticket_id: The ticket ID
        db: Database session
        
    Returns:
        The ticket plan information
    """
    try:
        # Get ticket
        ticket = db.query(TicketDB).filter(
            TicketDB.ticket_id == ticket_id
        ).first()
        
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail=f"Ticket {ticket_id} not found"
            )
        
        # Get plan
        plan_db = db.query(PlanDB).filter(
            PlanDB.ticket_id == ticket_id
        ).order_by(PlanDB.created_at.desc()).first()
        
        if not plan_db:
            raise HTTPException(
                status_code=404,
                detail=f"No plan found for ticket {ticket_id}"
            )
        
        return {
            "ticket_id": ticket_id,
            "plan_id": plan_db.id,
            "status": ticket.status,
            "plan": plan_db.plan_data,
            "requires_approval": plan_db.requires_approval,
            "approved": plan_db.approved,
            "created_at": plan_db.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving plan for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ticket/{ticket_id}/approve")
async def approve_ticket_plan(
    ticket_id: str,
    approval: ApprovalRequest,
    db: Session = Depends(get_db)
):
    """
    Approve and execute a ticket plan
    
    Args:
        ticket_id: The ticket ID
        approval: Approval decision
        db: Database session
        
    Returns:
        Execution result
    """
    try:
        # Get ticket
        ticket = db.query(TicketDB).filter(
            TicketDB.ticket_id == ticket_id
        ).first()
        
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail=f"Ticket {ticket_id} not found"
            )
        
        # Get plan
        plan_db = db.query(PlanDB).filter(
            PlanDB.ticket_id == ticket_id
        ).order_by(PlanDB.created_at.desc()).first()
        
        if not plan_db:
            raise HTTPException(
                status_code=404,
                detail=f"No plan found for ticket {ticket_id}"
            )
        
        if not plan_db.requires_approval:
            raise HTTPException(
                status_code=400,
                detail="This plan does not require approval"
            )
        
        if plan_db.approved:
            raise HTTPException(
                status_code=400,
                detail="Plan has already been approved and executed"
            )
        
        if not approval.approved:
            # Escalate ticket
            ticket.status = TicketStatus.ESCALATED
            db.commit()
            return {
                "ticket_id": ticket_id,
                "status": "escalated",
                "message": "Plan rejected. Ticket escalated to human agent."
            }
        
        # Mark as approved
        plan_db.approved = True
        ticket.status = TicketStatus.EXECUTING
        db.commit()
        
        # Execute plan
        from app.models import Plan
        plan = Plan(**plan_db.plan_data)
        
        executor = Executor()
        execution_result = executor.execute_plan(plan, plan_db.id, approved=True)
        
        return {
            "ticket_id": ticket_id,
            "status": "executed",
            "plan_id": plan_db.id,
            "execution_result": execution_result.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving plan for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """
    Get system metrics
    
    Args:
        db: Database session
        
    Returns:
        Metrics summary
    """
    try:
        # Get all metrics
        metrics = db.query(MetricsDB).all()
        
        if not metrics:
            return MetricsResponse(
                total_tickets=0,
                auto_resolved=0,
                escalated=0,
                awaiting_approval=0,
                avg_steps=0.0,
                auto_resolve_rate=0.0
            )
        
        total_tickets = len(metrics)
        auto_resolved = sum(1 for m in metrics if m.auto_resolved)
        escalated = sum(1 for m in metrics if m.escalated)
        
        # Count tickets awaiting approval
        awaiting_approval = db.query(TicketDB).filter(
            TicketDB.status == TicketStatus.AWAITING_APPROVAL
        ).count()
        
        # Calculate average steps
        avg_steps = sum(m.steps_count for m in metrics) / total_tickets
        
        # Calculate auto-resolve rate
        auto_resolve_rate = (auto_resolved / total_tickets) * 100 if total_tickets > 0 else 0
        
        return MetricsResponse(
            total_tickets=total_tickets,
            auto_resolved=auto_resolved,
            escalated=escalated,
            awaiting_approval=awaiting_approval,
            avg_steps=round(avg_steps, 2),
            auto_resolve_rate=round(auto_resolve_rate, 2)
        )
        
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
