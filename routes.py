from fastapi import APIRouter, HTTPException, Request, Query
from beanie import PydanticObjectId
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from models import Job, JobStatus
from schemas import JobCreateRequest, JobResponse, JobListResponse
from tasks import parse_csv_task, send_email_task, process_data_task
from config import settings
from metrics import JOBS_ENQUEUED
import structlog

logger = structlog.get_logger("routes")

router = APIRouter()

# Rate limiter with Redis storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_STORAGE_URL,
    default_limits=["200/day", "50/hour"],
)


@router.post("/jobs", response_model=dict, status_code=202)
@limiter.limit("10/minute")
async def create_job(request: Request, job_create: JobCreateRequest):
    """
    Create and enqueue a new job
    
    Rate limited to 10 requests per minute per IP
    Returns immediately with job ID (HTTP 202 Accepted)
    """
    try:
        # Validate task type
        valid_tasks = ["parse_csv", "send_email", "process_data"]
        if job_create.task_type not in valid_tasks:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid task_type. Must be one of: {', '.join(valid_tasks)}"
            )
        
        # Inject request context into payload so Celery workers can log it
        ctx = structlog.contextvars.get_contextvars()
        job_create.payload["_meta"] = {
            "request_id": ctx.get("request_id", "unknown"),
            "user_id": ctx.get("user_id", "unknown")
        }
        
        # Create job document in MongoDB
        job = Job(
            task_id="",  # Will be set after task creation
            status=JobStatus.PENDING,
            task_type=job_create.task_type,
            payload=job_create.payload,
        )
        await job.save()
        
        # Bind job_id to current request context for logs
        structlog.contextvars.bind_contextvars(job_id=str(job.id))
        
        logger.info("Enqueuing job", task_type=job_create.task_type)
        
        # Enqueue task based on type
        if job_create.task_type == "parse_csv":
            celery_task = parse_csv_task.apply_async(
                args=[str(job.id), job_create.payload],
                task_id=f"job_{job.id}",
            )
        elif job_create.task_type == "send_email":
            celery_task = send_email_task.apply_async(
                args=[str(job.id), job_create.payload],
                task_id=f"job_{job.id}",
            )
        else:  # process_data
            celery_task = process_data_task.apply_async(
                args=[str(job.id), job_create.payload],
                task_id=f"job_{job.id}",
            )
        
        # Update job with Celery task ID
        job.task_id = celery_task.id
        await job.save()
        
        # Update metrics
        JOBS_ENQUEUED.inc()
        
        return {
            "id": str(job.id),
            "task_id": celery_task.id,
            "status": job.status,
            "message": "Job enqueued successfully"
        }
    
    except RateLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: 10 requests per minute per IP"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Get the status and details of a specific job
    """
    try:
        job = await Job.get(PydanticObjectId(job_id))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobResponse(
            id=str(job.id),
            task_id=job.task_id,
            status=job.status,
            task_type=job.task_type,
            payload=job.payload,
            result=job.result,
            error=job.error,
            retries=job.retries,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """
    Get paginated list of jobs
    
    Query parameters:
    - page: Page number (default 1)
    - page_size: Items per page (default 10, max 100)
    - status: Filter by status (pending, processing, completed, failed)
    """
    try:
        # Build query
        query = {}
        if status:
            if status not in ["pending", "processing", "completed", "failed"]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid status. Must be one of: pending, processing, completed, failed"
                )
            query["status"] = status
        
        # Get total count
        total = await Job.find(query).count()
        
        # Get paginated results
        skip = (page - 1) * page_size
        jobs = await Job.find(query).skip(skip).limit(page_size).to_list()
        
        # Convert to response format
        job_responses = [
            JobResponse(
                id=str(job.id),
                task_id=job.task_id,
                status=job.status,
                task_type=job.task_type,
                payload=job.payload,
                result=job.result,
                error=job.error,
                retries=job.retries,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
            )
            for job in jobs
        ]
        
        return JobListResponse(
            total=total,
            page=page,
            page_size=page_size,
            jobs=job_responses,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "job-processing-service"}
