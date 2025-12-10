import pytest
from app.tools import (
    get_account_info,
    fetch_logs,
    kb_search,
    check_known_issues,
    run_diagnostic,
    reply_ticket,
    reset_password,
    is_destructive,
    validate_tool
)


def test_get_account_info():
    """Test get_account_info returns valid data"""
    result = get_account_info("u123")
    
    assert result["user_id"] == "u123"
    assert "email" in result
    assert "plan" in result
    assert "account_status" in result


def test_fetch_logs():
    """Test fetch_logs returns valid log data"""
    result = fetch_logs("u123", last_hours=24)
    
    assert result["user_id"] == "u123"
    assert result["period_hours"] == 24
    assert "logs" in result
    assert len(result["logs"]) > 0


def test_kb_search():
    """Test kb_search returns relevant articles"""
    result = kb_search("CSV upload", top_k=3)
    
    assert result["query"] == "CSV upload"
    assert "articles" in result
    assert len(result["articles"]) <= 3


def test_kb_search_filters_by_query():
    """Test kb_search filters results by query"""
    result = kb_search("password", top_k=5)
    
    # Should find password-related article
    articles = result["articles"]
    assert any("password" in a["title"].lower() or "password" in a["content"].lower() for a in articles)


def test_check_known_issues_finds_match():
    """Test check_known_issues finds matching issues"""
    result = check_known_issues("CSV upload v2.1")
    
    assert result["found"] == True
    assert "issue" in result
    assert result["issue"]["issue_id"] == "BUG-2341"


def test_check_known_issues_no_match():
    """Test check_known_issues returns no match for unknown issues"""
    result = check_known_issues("some random issue")
    
    assert result["found"] == False


def test_run_diagnostic():
    """Test run_diagnostic returns diagnostic results"""
    result = run_diagnostic("sess-123")
    
    assert result["session_id"] == "sess-123"
    assert "checks_performed" in result
    assert len(result["checks_performed"]) > 0


def test_reply_ticket_in_sandbox_mode():
    """Test reply_ticket in sandbox mode"""
    result = reply_ticket("t100", "Test message")
    
    assert result["ticket_id"] == "t100"
    assert result["status"] == "simulated"
    assert "SANDBOX" in result["note"]


def test_reset_password_in_sandbox_mode():
    """Test reset_password is blocked in sandbox mode"""
    result = reset_password("u123")
    
    assert result["user_id"] == "u123"
    assert result["status"] == "simulated"
    assert "SANDBOX" in result["note"]


def test_is_destructive():
    """Test is_destructive correctly identifies destructive tools"""
    assert is_destructive("reset_password") == True
    assert is_destructive("apply_patch") == True
    assert is_destructive("fetch_logs") == False
    assert is_destructive("get_account_info") == False


def test_validate_tool():
    """Test validate_tool correctly validates tool names"""
    assert validate_tool("fetch_logs") == True
    assert validate_tool("get_account_info") == True
    assert validate_tool("unknown_tool") == False
