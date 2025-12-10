import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import TicketWebhook


# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["AUTO_APPLY"] = "false"
os.environ["SANDBOX_MODE"] = "true"


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine"""
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a new database session for a test"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_ticket():
    """Sample ticket for testing"""
    return TicketWebhook(
        ticket_id="t100",
        user_id="u123",
        subject="App crashes on CSV upload v2.1",
        body="When I upload CSV it crashes with stacktrace X..."
    )


@pytest.fixture
def password_reset_ticket():
    """Sample password reset ticket"""
    return TicketWebhook(
        ticket_id="t200",
        user_id="u456",
        subject="Password reset request",
        body="I forgot my password and need to reset it."
    )
