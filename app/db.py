from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Generator
import os
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://supportagent:supportagent@localhost:5432/supportagent")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TicketDB(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlanDB(Base):
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, index=True, nullable=False)
    plan_data = Column(JSON, nullable=False)
    requires_approval = Column(Boolean, default=False)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ToolCallDB(Base):
    __tablename__ = "tool_calls"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, index=True, nullable=False)
    ticket_id = Column(String, index=True, nullable=False)
    step = Column(Integer, nullable=False)
    tool = Column(String, nullable=False)
    args = Column(JSON, nullable=False)
    result = Column(JSON)
    success = Column(Boolean, nullable=False)
    error = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


class MetricsDB(Base):
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, index=True, nullable=False)
    auto_resolved = Column(Boolean, default=False)
    escalated = Column(Boolean, default=False)
    steps_count = Column(Integer, default=0)
    execution_time = Column(Float)  # in seconds
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database session"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
