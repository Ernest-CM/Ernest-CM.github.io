from typing import Dict, Any, List
from datetime import datetime, timedelta
import random
import os
from app.models import AccountInfo, LogEntry, KBArticle


# Define which tools are destructive and require approval
DESTRUCTIVE_TOOLS = {
    "reset_password",
    "apply_patch",
    "modify_config",
    "delete_data"
}


def is_destructive(tool_name: str) -> bool:
    """Check if a tool is destructive"""
    return tool_name in DESTRUCTIVE_TOOLS


def get_account_info(user_id: str) -> Dict[str, Any]:
    """
    Retrieve account information for a user
    
    Args:
        user_id: The user ID to look up
        
    Returns:
        Dictionary with account information
    """
    # Mock implementation - returns realistic fake data
    account = AccountInfo(
        user_id=user_id,
        email=f"user{user_id}@example.com",
        plan="premium" if hash(user_id) % 2 == 0 else "basic",
        account_status="active",
        created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365))
    )
    return account.model_dump()


def fetch_logs(user_id: str, last_hours: int = 24) -> Dict[str, Any]:
    """
    Fetch logs for a user from the last N hours
    
    Args:
        user_id: The user ID
        last_hours: Number of hours to look back
        
    Returns:
        Dictionary with log entries
    """
    # Mock implementation - returns realistic fake logs
    logs = []
    base_time = datetime.utcnow() - timedelta(hours=last_hours)
    
    error_messages = [
        "CSV parsing error: Invalid header format at line 523",
        "Memory allocation failed: OutOfMemoryError in CSVProcessor",
        "Database connection timeout after 30s",
        "Stacktrace: NullPointerException at CSVUploader.java:245"
    ]
    
    for i in range(random.randint(5, 15)):
        log_time = base_time + timedelta(hours=i, minutes=random.randint(0, 59))
        level = "ERROR" if i % 3 == 0 else "INFO"
        message = random.choice(error_messages) if level == "ERROR" else f"Processing batch {i}"
        
        log_entry = LogEntry(
            timestamp=log_time,
            level=level,
            message=message,
            metadata={
                "user_id": user_id,
                "session_id": f"sess-{random.randint(1000, 9999)}",
                "module": "csv_uploader"
            }
        )
        logs.append(log_entry.model_dump())
    
    return {
        "user_id": user_id,
        "period_hours": last_hours,
        "log_count": len(logs),
        "logs": logs
    }


def kb_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Search the knowledge base for relevant articles
    
    Args:
        query: Search query
        top_k: Number of results to return
        
    Returns:
        Dictionary with KB articles
    """
    # Mock implementation - returns realistic fake KB articles
    articles_pool = [
        {
            "id": "kb001",
            "title": "CSV Upload Troubleshooting Guide",
            "content": "Common issues with CSV uploads include: invalid file format, memory limits exceeded, special characters in headers. Solution: Update to latest version v2.1.1 which fixes these issues.",
            "relevance_score": 0.95
        },
        {
            "id": "kb002",
            "title": "Password Reset Procedures",
            "content": "To reset a password: 1. Navigate to account settings 2. Click 'Forgot Password' 3. Check email for reset link. Link expires in 24 hours.",
            "relevance_score": 0.87
        },
        {
            "id": "kb003",
            "title": "Configuration Best Practices",
            "content": "Recommended configuration settings for optimal performance: Enable caching, set batch size to 1000, use connection pooling.",
            "relevance_score": 0.76
        },
        {
            "id": "kb004",
            "title": "Known Issues in v2.1",
            "content": "Version 2.1 has a known bug with CSV uploads containing special characters. Fixed in v2.1.1. Workaround: remove special chars before upload.",
            "relevance_score": 0.92
        },
        {
            "id": "kb005",
            "title": "Database Connection Timeouts",
            "content": "If experiencing timeouts: 1. Check network connectivity 2. Verify database server status 3. Increase timeout in config.",
            "relevance_score": 0.68
        }
    ]
    
    # Simple relevance filtering based on query
    if "csv" in query.lower() or "upload" in query.lower():
        relevant_articles = [a for a in articles_pool if "CSV" in a["title"] or "upload" in a["content"].lower()]
    elif "password" in query.lower():
        relevant_articles = [a for a in articles_pool if "password" in a["title"].lower()]
    else:
        relevant_articles = articles_pool
    
    # Sort by relevance and limit
    relevant_articles = sorted(relevant_articles, key=lambda x: x["relevance_score"], reverse=True)[:top_k]
    
    return {
        "query": query,
        "results_count": len(relevant_articles),
        "articles": relevant_articles
    }


def check_known_issues(query: str) -> Dict[str, Any]:
    """
    Check for known issues matching the query
    
    Args:
        query: Description of the issue
        
    Returns:
        Dictionary with known issues
    """
    known_issues = {
        "CSV upload v2.1": {
            "issue_id": "BUG-2341",
            "severity": "high",
            "description": "CSV uploads fail with special characters in v2.1",
            "status": "fixed",
            "fix_version": "v2.1.1",
            "workaround": "Upgrade to v2.1.1 or remove special characters from CSV"
        },
        "password reset": {
            "issue_id": "KNOWN-1234",
            "severity": "low",
            "description": "Password reset emails delayed during peak hours",
            "status": "investigating",
            "fix_version": "pending",
            "workaround": "Wait 5-10 minutes for email or use SMS reset"
        }
    }
    
    # Simple keyword matching
    for key, issue in known_issues.items():
        if key.lower() in query.lower():
            return {
                "found": True,
                "issue": issue
            }
    
    return {
        "found": False,
        "message": "No known issues found matching the query"
    }


def run_diagnostic(session_id: str) -> Dict[str, Any]:
    """
    Run diagnostic checks for a session
    
    Args:
        session_id: The session ID to diagnose
        
    Returns:
        Dictionary with diagnostic results
    """
    return {
        "session_id": session_id,
        "checks_performed": [
            {"check": "memory_usage", "status": "ok", "value": "45%"},
            {"check": "database_connection", "status": "ok", "latency_ms": 23},
            {"check": "csv_processor", "status": "warning", "message": "Using deprecated parser"},
            {"check": "file_permissions", "status": "ok"}
        ],
        "overall_status": "warning",
        "recommendation": "Update CSV processor to latest version"
    }


def reply_ticket(ticket_id: str, message: str) -> Dict[str, Any]:
    """
    Reply to a ticket with a message
    
    Args:
        ticket_id: The ticket ID
        message: The reply message
        
    Returns:
        Dictionary with reply status
    """
    # Check sandbox mode
    sandbox_mode = os.getenv("SANDBOX_MODE", "true").lower() == "true"
    
    if sandbox_mode:
        return {
            "ticket_id": ticket_id,
            "status": "simulated",
            "message": message,
            "note": "SANDBOX MODE: Reply not actually sent"
        }
    
    return {
        "ticket_id": ticket_id,
        "status": "sent",
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }


def reset_password(user_id: str) -> Dict[str, Any]:
    """
    Reset password for a user (DESTRUCTIVE)
    
    Args:
        user_id: The user ID
        
    Returns:
        Dictionary with reset status
    """
    # This is a destructive action
    sandbox_mode = os.getenv("SANDBOX_MODE", "true").lower() == "true"
    auto_apply = os.getenv("AUTO_APPLY", "false").lower() == "true"
    
    if sandbox_mode or not auto_apply:
        return {
            "user_id": user_id,
            "status": "simulated",
            "note": "SANDBOX/NO-AUTO-APPLY: Password not actually reset",
            "action_required": "Enable AUTO_APPLY and disable SANDBOX_MODE to execute"
        }
    
    # In production, this would actually reset the password
    return {
        "user_id": user_id,
        "status": "reset",
        "reset_link": f"https://example.com/reset/{user_id}/token123",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }


def apply_patch(patch_id: str, target: str) -> Dict[str, Any]:
    """
    Apply a patch to fix an issue (DESTRUCTIVE)
    
    Args:
        patch_id: The patch identifier
        target: The target to patch
        
    Returns:
        Dictionary with patch status
    """
    sandbox_mode = os.getenv("SANDBOX_MODE", "true").lower() == "true"
    auto_apply = os.getenv("AUTO_APPLY", "false").lower() == "true"
    
    if sandbox_mode or not auto_apply:
        return {
            "patch_id": patch_id,
            "target": target,
            "status": "simulated",
            "note": "SANDBOX/NO-AUTO-APPLY: Patch not actually applied",
            "action_required": "Enable AUTO_APPLY and disable SANDBOX_MODE to execute"
        }
    
    return {
        "patch_id": patch_id,
        "target": target,
        "status": "applied",
        "timestamp": datetime.utcnow().isoformat()
    }


# Tool registry - maps tool names to functions
TOOL_REGISTRY = {
    "get_account_info": get_account_info,
    "fetch_logs": fetch_logs,
    "kb_search": kb_search,
    "check_known_issues": check_known_issues,
    "run_diagnostic": run_diagnostic,
    "reply_ticket": reply_ticket,
    "reset_password": reset_password,
    "apply_patch": apply_patch
}


def get_tool(tool_name: str):
    """Get a tool function by name"""
    return TOOL_REGISTRY.get(tool_name)


def validate_tool(tool_name: str) -> bool:
    """Check if a tool exists"""
    return tool_name in TOOL_REGISTRY
