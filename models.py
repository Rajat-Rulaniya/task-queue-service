from enum import Enum
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field
from typing import Optional, Any, Dict


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Document):
    """Job model for MongoDB"""
    
    task_id: Indexed(str)  # Celery task ID
    status: JobStatus = JobStatus.PENDING
    task_type: str  # e.g., "parse_csv", "send_email"
    payload: Dict[str, Any] = Field(default_factory=dict)  # Input data
    result: Optional[Dict[str, Any]] = None  # Output data
    error: Optional[str] = None  # Error message if failed
    retries: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Settings:
        name = "jobs"
