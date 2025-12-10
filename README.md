# Customer Support Resolution Agent

An AI-powered customer support ticket resolution system that automatically handles common support issues like password resets, CSV upload crashes, and configuration fixes.

## Features

- **Automatic Ticket Processing**: Receives tickets via webhook and creates action plans
- **LLM-Powered Planning**: Uses LLM to analyze tickets and generate structured resolution plans
- **Human-in-the-Loop**: Requires approval for destructive actions (configurable)
- **Tool-Based Execution**: Modular tool system for information gathering and actions
- **Audit Trail**: Complete logging of all actions and decisions to PostgreSQL
- **Safety Features**: Sandbox mode, rate limiting, and permission checks
- **Metrics Dashboard**: Track resolution rates, escalations, and performance

## Architecture

```
┌─────────────┐
│   Webhook   │
│  /webhook/  │
│   ticket    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Planner   │
│  (LLM)      │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────┐
│  Executor   │─────▶│    Tools     │
│             │      │  (Stubs)     │
└──────┬──────┘      └──────────────┘
       │
       ▼
┌─────────────┐
│  Database   │
│  (Audit)    │
└─────────────┘
```

## Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Quick Start with Docker

1. Clone the repository:
```bash
git clone <repository-url>
cd Ernest-CM.github.io
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start services:
```bash
make start
```

The API will be available at `http://localhost:8000`

### Local Development Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export DATABASE_URL=postgresql://supportagent:supportagent@localhost:5432/supportagent
export REDIS_URL=redis://localhost:6379/0
export LLM_PROVIDER=mock
export AUTO_APPLY=false
export SANDBOX_MODE=true
```

4. Initialize database:
```bash
alembic upgrade head
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

## Configuration

Configuration is done via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | - | Redis connection string |
| `LLM_PROVIDER` | `mock` | LLM provider: `mock`, `openai`, or `local` |
| `OPENAI_API_KEY` | - | OpenAI API key (if using OpenAI) |
| `AUTO_APPLY` | `false` | Allow automatic execution of destructive actions |
| `SANDBOX_MODE` | `true` | Prevent actual data modifications |
| `RATE_LIMIT_PER_MINUTE` | `60` | API rate limit per client IP |

### Safety Modes

- **SANDBOX_MODE=true**: All destructive actions are simulated only
- **AUTO_APPLY=false**: Destructive actions require human approval
- **AUTO_APPLY=true + SANDBOX_MODE=false**: Full automation (use with caution!)

## API Endpoints

### POST /webhook/ticket

Receive a new support ticket and create an action plan.

**Request:**
```json
{
  "ticket_id": "t100",
  "user_id": "u123",
  "subject": "App crashes on CSV upload v2.1",
  "body": "When I upload CSV it crashes with stacktrace X..."
}
```

**Response:**
```json
{
  "ticket_id": "t100",
  "status": "executed",
  "plan_id": 1,
  "plan": {
    "ticket_id": "t100",
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
          "message": "Found bug, please update to v2.1.1. If you want, we can apply a temporary patch (requires approval)."
        },
        "destructive": false
      }
    ]
  },
  "execution_result": {
    "ticket_id": "t100",
    "plan_id": 1,
    "tool_results": [...],
    "status": "completed"
  },
  "requires_approval": false
}
```

### GET /ticket/{ticket_id}/plan

Get the action plan for a ticket.

**Response:**
```json
{
  "ticket_id": "t100",
  "plan_id": 1,
  "status": "awaiting_approval",
  "plan": {...},
  "requires_approval": true,
  "approved": false
}
```

### POST /ticket/{ticket_id}/approve

Approve and execute a ticket plan.

**Request:**
```json
{
  "approved": true
}
```

**Response:**
```json
{
  "ticket_id": "t100",
  "status": "executed",
  "plan_id": 1,
  "execution_result": {...}
}
```

### GET /metrics

Get system metrics.

**Response:**
```json
{
  "total_tickets": 42,
  "auto_resolved": 35,
  "escalated": 3,
  "awaiting_approval": 4,
  "avg_steps": 3.5,
  "auto_resolve_rate": 83.33
}
```

## Example Workflow

### 1. Submit a Ticket

```bash
curl -X POST http://localhost:8000/webhook/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "t100",
    "user_id": "u123",
    "subject": "App crashes on CSV upload v2.1",
    "body": "When I upload CSV it crashes with stacktrace X..."
  }'
```

### 2. View the Plan

```bash
curl http://localhost:8000/ticket/t100/plan
```

### 3. Approve and Execute (if needed)

```bash
curl -X POST http://localhost:8000/ticket/t100/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

### 4. Check Metrics

```bash
curl http://localhost:8000/metrics
```

## Example Ticket Flows

### CSV Upload Issue (Auto-Resolved)

**Ticket:**
```json
{
  "ticket_id": "t100",
  "user_id": "u123",
  "subject": "App crashes on CSV upload v2.1",
  "body": "When I upload CSV it crashes with stacktrace X..."
}
```

**Generated Plan:**
```json
[
  {"step": 1, "tool": "fetch_logs", "args": {"user_id": "u123", "last_hours": 24}},
  {"step": 2, "tool": "check_known_issues", "args": {"query": "CSV upload v2.1"}},
  {"step": 3, "tool": "run_diagnostic", "args": {"session_id": "sess-abc"}},
  {"step": 4, "tool": "reply_ticket", "args": {"ticket_id": "t100", "message": "Found bug..."}}
]
```

**Outcome:** Automatically executed, ticket resolved.

### Password Reset (Requires Approval)

**Ticket:**
```json
{
  "ticket_id": "t200",
  "user_id": "u456",
  "subject": "Password reset request",
  "body": "I forgot my password and need to reset it."
}
```

**Generated Plan:**
```json
[
  {"step": 1, "tool": "get_account_info", "args": {"user_id": "u456"}},
  {"step": 2, "tool": "reset_password", "args": {"user_id": "u456"}},
  {"step": 3, "tool": "reply_ticket", "args": {"ticket_id": "t200", "message": "Password reset initiated..."}}
]
```

**Outcome:** Awaits approval due to destructive `reset_password` action.

## Available Tools

### Information Gathering (Non-Destructive)

- **get_account_info(user_id)**: Retrieve user account details
- **fetch_logs(user_id, last_hours)**: Fetch recent application logs
- **kb_search(query, top_k)**: Search knowledge base articles
- **check_known_issues(query)**: Check for known bugs
- **run_diagnostic(session_id)**: Run diagnostic checks

### Actions (Non-Destructive)

- **reply_ticket(ticket_id, message)**: Send reply to ticket

### Actions (Destructive - Requires Approval)

- **reset_password(user_id)**: Reset user password
- **apply_patch(patch_id, target)**: Apply bug fix patch

## Testing

Run all tests:
```bash
make test-local
```

Or with pytest directly:
```bash
pytest -v
```

Run specific test file:
```bash
pytest tests/test_planner.py -v
```

## Database Schema

### Tables

- **tickets**: Stores ticket information and status
- **plans**: Stores generated action plans
- **tool_calls**: Audit log of all tool executions
- **metrics**: Performance metrics per ticket

### Audit Trail

Every tool execution is logged with:
- Timestamp
- Tool name and arguments
- Result or error
- Success/failure status

Query audit logs:
```sql
SELECT * FROM tool_calls WHERE ticket_id = 't100' ORDER BY timestamp;
```

## Development

### Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── api.py           # API endpoints
│   ├── models.py        # Pydantic models
│   ├── db.py            # Database models and setup
│   ├── llm.py           # LLM provider interface
│   ├── planner.py       # Plan generation logic
│   ├── executor.py      # Plan execution logic
│   └── tools.py         # Tool implementations
├── prompts/
│   └── planner_prompt.txt  # LLM prompt template
├── tests/
│   ├── conftest.py
│   ├── test_planner.py
│   ├── test_executor.py
│   └── test_tools.py
├── alembic/             # Database migrations
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

### Adding New Tools

1. Add function to `app/tools.py`:
```python
def my_new_tool(arg1: str, arg2: int) -> Dict[str, Any]:
    """Tool description"""
    # Implementation
    return {"result": "..."}
```

2. Register in `TOOL_REGISTRY`:
```python
TOOL_REGISTRY = {
    ...
    "my_new_tool": my_new_tool
}
```

3. If destructive, add to `DESTRUCTIVE_TOOLS`:
```python
DESTRUCTIVE_TOOLS = {
    ...
    "my_new_tool"
}
```

4. Update prompt template in `prompts/planner_prompt.txt`

### Swapping LLM Providers

Change the `LLM_PROVIDER` environment variable:

- `mock`: Mock responses for development/testing
- `openai`: Use OpenAI API (requires `OPENAI_API_KEY`)
- `local`: Use local LLM endpoint

To add a new provider:
1. Create a class inheriting from `LLMProvider` in `app/llm.py`
2. Implement the `generate()` method
3. Register in `get_llm_provider()` factory

## Makefile Commands

- `make start`: Start all services with Docker Compose
- `make stop`: Stop all services
- `make test`: Run tests in Docker
- `make test-local`: Run tests locally
- `make clean`: Clean up containers and Python cache
- `make logs`: View application logs
- `make migrate`: Run database migrations
- `make shell`: Open Python shell in container

## Security Considerations

1. **Sandbox Mode**: Always test with `SANDBOX_MODE=true` first
2. **Auto-Apply**: Only enable `AUTO_APPLY=true` for well-tested scenarios
3. **Rate Limiting**: Configured per-IP to prevent abuse
4. **Permission Checks**: All destructive tools check sandbox/auto-apply flags
5. **Audit Trail**: Complete logging of all actions for accountability

## Limitations

This is an MVP implementation with the following limitations:

- Tools are stubs that return mock data (not connected to real systems)
- Mock LLM provider for development (requires OpenAI API key for production)
- Simple in-memory rate limiting (use Redis in production)
- Basic vector store simulation (use real vector DB for production)
- No authentication/authorization (add JWT/OAuth for production)

## Future Enhancements

- [ ] Connect tools to real backend systems
- [ ] Implement real vector store for KB search
- [ ] Add authentication and RBAC
- [ ] Build web UI for ticket management
- [ ] Add more sophisticated error handling and retries
- [ ] Implement async task processing with Celery
- [ ] Add monitoring and alerting
- [ ] Support multi-step approval workflows

## License

MIT

## Contributing

Pull requests welcome! Please ensure:
- Tests pass: `make test`
- Code follows existing style
- Documentation updated
- Commit messages are clear