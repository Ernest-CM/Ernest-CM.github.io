import pytest
from app.planner import Planner, PlannerError
from app.models import TicketWebhook, PlanStep


def test_planner_loads_template():
    """Test that planner can load the prompt template"""
    planner = Planner()
    assert planner.prompt_template is not None
    assert "Available tools:" in planner.prompt_template
    assert "{ticket_id}" in planner.prompt_template


def test_planner_formats_prompt(sample_ticket):
    """Test that planner correctly formats prompt with ticket data"""
    planner = Planner()
    prompt = planner._format_prompt(sample_ticket)
    
    assert sample_ticket.ticket_id in prompt
    assert sample_ticket.user_id in prompt
    assert sample_ticket.subject in prompt
    assert sample_ticket.body in prompt


def test_planner_parses_valid_json():
    """Test that planner can parse valid LLM JSON response"""
    planner = Planner()
    
    response = '''[
        {"step": 1, "tool": "fetch_logs", "args": {"user_id": "u123", "last_hours": 24}},
        {"step": 2, "tool": "kb_search", "args": {"query": "CSV upload", "top_k": 3}}
    ]'''
    
    steps = planner._parse_llm_response(response)
    assert len(steps) == 2
    assert steps[0]["tool"] == "fetch_logs"
    assert steps[1]["tool"] == "kb_search"


def test_planner_parses_json_with_extra_text():
    """Test that planner can extract JSON from response with extra text"""
    planner = Planner()
    
    response = '''Here is the plan:
    [
        {"step": 1, "tool": "fetch_logs", "args": {"user_id": "u123", "last_hours": 24}}
    ]
    This should resolve the issue.'''
    
    steps = planner._parse_llm_response(response)
    assert len(steps) == 1


def test_planner_validates_valid_steps():
    """Test that planner validates valid plan steps"""
    planner = Planner()
    
    steps_data = [
        {"step": 1, "tool": "fetch_logs", "args": {"user_id": "u123", "last_hours": 24}},
        {"step": 2, "tool": "reply_ticket", "args": {"ticket_id": "t100", "message": "Hello"}}
    ]
    
    validated = planner._validate_plan_steps(steps_data)
    assert len(validated) == 2
    assert isinstance(validated[0], PlanStep)
    assert validated[0].destructive == False
    assert validated[1].destructive == False


def test_planner_marks_destructive_tools():
    """Test that planner correctly marks destructive tools"""
    planner = Planner()
    
    steps_data = [
        {"step": 1, "tool": "fetch_logs", "args": {"user_id": "u123", "last_hours": 24}},
        {"step": 2, "tool": "reset_password", "args": {"user_id": "u123"}}
    ]
    
    validated = planner._validate_plan_steps(steps_data)
    assert validated[0].destructive == False
    assert validated[1].destructive == True


def test_planner_rejects_unknown_tool():
    """Test that planner rejects unknown tools"""
    planner = Planner()
    
    steps_data = [
        {"step": 1, "tool": "unknown_tool", "args": {}}
    ]
    
    with pytest.raises(PlannerError) as exc_info:
        planner._validate_plan_steps(steps_data)
    
    assert "Unknown tool" in str(exc_info.value)
    assert "escalated" in str(exc_info.value).lower()


def test_planner_creates_plan_for_csv_issue(sample_ticket):
    """Test that planner creates a valid plan for CSV upload issue"""
    planner = Planner()
    plan = planner.create_plan(sample_ticket)
    
    assert plan.ticket_id == sample_ticket.ticket_id
    assert len(plan.steps) > 0
    assert any(step.tool == "fetch_logs" for step in plan.steps)


def test_planner_creates_plan_for_password_reset(password_reset_ticket):
    """Test that planner creates a valid plan for password reset"""
    planner = Planner()
    plan = planner.create_plan(password_reset_ticket)
    
    assert plan.ticket_id == password_reset_ticket.ticket_id
    assert len(plan.steps) > 0
    # Should include reset_password which is destructive
    assert any(step.tool == "reset_password" for step in plan.steps)


def test_planner_requires_approval_for_destructive_plan(password_reset_ticket):
    """Test that planner correctly identifies plans requiring approval"""
    planner = Planner()
    plan = planner.create_plan(password_reset_ticket)
    
    requires_approval = planner.requires_approval(plan)
    assert requires_approval is True


def test_planner_does_not_require_approval_for_safe_plan(sample_ticket):
    """Test that planner correctly identifies plans not requiring approval"""
    planner = Planner()
    plan = planner.create_plan(sample_ticket)
    
    requires_approval = planner.requires_approval(plan)
    # CSV upload issue shouldn't have destructive steps in mock LLM
    assert requires_approval is False
