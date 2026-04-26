from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime
from models import JobStatus


class JobCreateRequest(BaseModel):
    """Request to create a new job"""
    task_type: str = Field(..., description="Type of task: parse_csv, send_email, process_data")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task-specific payload")


class JobResponse(BaseModel):
    """Response with job details"""
    id: str = Field(..., description="Job ID")
    task_id: str = Field(..., description="Celery task ID")
    status: JobStatus
    task_type: str
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retries: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    """Paginated job list response"""
    total: int
    page: int
    page_size: int
    jobs: List[JobResponse]


class JobStatusResponse(BaseModel):
    """Simple status response"""
    id: str
    status: JobStatus
    task_type: str
    error: Optional[str] = None
