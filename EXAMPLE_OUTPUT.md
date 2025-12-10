# Example Run Transcript

## Test 1: CSV Upload Issue (Auto-Resolved)

### Step 1: Submit Ticket
```bash
curl -X POST http://localhost:8000/webhook/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "t103",
    "user_id": "u123",
    "subject": "App crashes on CSV upload v2.1",
    "body": "When I upload CSV it crashes with stacktrace X..."
  }'
```

### Response:
```json
{
  "ticket_id": "t103",
  "status": "executed",
  "plan_id": 1,
  "plan": {
    "ticket_id": "t103",
    "steps": [
      {
        "step": 1,
        "tool": "fetch_logs",
        "args": {"user_id": "u123", "last_hours": 24},
        "destructive": false
      },
      {
        "step": 2,
        "tool": "check_known_issues",
        "args": {"query": "CSV upload v2.1"},
        "destructive": false
      },
      {
        "step": 3,
        "tool": "run_diagnostic",
        "args": {"session_id": "sess-abc"},
        "destructive": false
      },
      {
        "step": 4,
        "tool": "reply_ticket",
        "args": {
          "ticket_id": "t100",
          "message": "Found bug, please update to v2.1.1..."
        },
        "destructive": false
      }
    ],
    "created_at": "2025-12-10T21:33:13.370240"
  },
  "execution_result": {
    "ticket_id": "t103",
    "plan_id": 1,
    "status": "completed",
    "tool_results": [
      {
        "tool": "fetch_logs",
        "success": true,
        "result": {
          "user_id": "u123",
          "period_hours": 24,
          "log_count": 5,
          "logs": [...]
        }
      },
      {
        "tool": "check_known_issues",
        "success": true,
        "result": {
          "found": true,
          "issue": {
            "issue_id": "BUG-2341",
            "severity": "high",
            "description": "CSV uploads fail with special characters in v2.1",
            "status": "fixed",
            "fix_version": "v2.1.1",
            "workaround": "Upgrade to v2.1.1 or remove special characters from CSV"
          }
        }
      }
    ]
  },
  "requires_approval": false
}
```

**Result**: ✅ Ticket auto-resolved (no destructive actions)

---

## Database Audit Trail

After execution, the database contains:

### Tickets Table
```sql
SELECT * FROM tickets WHERE ticket_id = 't103';
```
| ticket_id | user_id | subject                            | status    |
|-----------|---------|-------------------------------------|-----------|
| t103      | u123    | App crashes on CSV upload v2.1     | completed |

### Plans Table
```sql
SELECT * FROM plans WHERE ticket_id = 't103';
```
| plan_id | ticket_id | requires_approval | approved |
|---------|-----------|-------------------|----------|
| 1       | t103      | false             | false    |

### Tool Calls Table (Audit Log)
```sql
SELECT step, tool, success FROM tool_calls WHERE ticket_id = 't103' ORDER BY step;
```
| step | tool                 | success |
|------|----------------------|---------|
| 1    | fetch_logs           | true    |
| 2    | check_known_issues   | true    |
| 3    | run_diagnostic       | true    |
| 4    | reply_ticket         | true    |

---

## Test 2: Password Reset (Requires Approval)

### Step 1: Submit Ticket
```bash
curl -X POST http://localhost:8000/webhook/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "t200",
    "user_id": "u456",
    "subject": "Password reset request",
    "body": "I forgot my password and need to reset it."
  }'
```

### Response:
```json
{
  "ticket_id": "t200",
  "status": "awaiting_approval",
  "plan_id": 2,
  "plan": {
    "ticket_id": "t200",
    "steps": [
      {
        "step": 1,
        "tool": "get_account_info",
        "args": {"user_id": "u456"},
        "destructive": false
      },
      {
        "step": 2,
        "tool": "reset_password",
        "args": {"user_id": "u456"},
        "destructive": true
      },
      {
        "step": 3,
        "tool": "reply_ticket",
        "args": {
          "ticket_id": "t200",
          "message": "Password reset initiated. Check your email for reset link."
        },
        "destructive": false
      }
    ]
  },
  "requires_approval": true,
  "message": "Plan contains destructive actions and requires approval"
}
```

### Step 2: Get Plan
```bash
curl http://localhost:8000/ticket/t200/plan
```

### Response:
```json
{
  "ticket_id": "t200",
  "plan_id": 2,
  "status": "awaiting_approval",
  "requires_approval": true,
  "approved": false
}
```

### Step 3: Approve Plan
```bash
curl -X POST http://localhost:8000/ticket/t200/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

### Response:
```json
{
  "ticket_id": "t200",
  "status": "executed",
  "plan_id": 2,
  "execution_result": {
    "ticket_id": "t200",
    "status": "completed",
    "tool_results": [
      {
        "tool": "reset_password",
        "success": true,
        "result": {
          "user_id": "u456",
          "status": "simulated",
          "note": "SANDBOX/NO-AUTO-APPLY: Password not actually reset"
        }
      }
    ]
  }
}
```

**Result**: ✅ Plan approved and executed (SANDBOX mode prevented actual password reset)

---

## Metrics

```bash
curl http://localhost:8000/metrics
```

### Response:
```json
{
  "total_tickets": 2,
  "auto_resolved": 1,
  "escalated": 0,
  "awaiting_approval": 0,
  "avg_steps": 3.5,
  "auto_resolve_rate": 50.0
}
```

---

## Safety Features Demonstrated

1. **SANDBOX_MODE=true**: Destructive actions are simulated only
2. **AUTO_APPLY=false**: Destructive actions require human approval
3. **Rate Limiting**: API endpoints are rate-limited per client IP
4. **Audit Trail**: Complete logging of all actions to database
5. **Escalation**: Unknown tools or failures trigger escalation

---

## Configuration Used

```env
DATABASE_URL=sqlite:///./supportagent.db
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=mock
AUTO_APPLY=false
SANDBOX_MODE=true
RATE_LIMIT_PER_MINUTE=60
```
