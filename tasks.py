import asyncio
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from beanie import PydanticObjectId
from models import Job, JobStatus
import csv
import io
from datetime import datetime
from metrics import JOBS_COMPLETED, JOB_DURATION, QUEUE_DEPTH


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,
)
def parse_csv_task(self, job_id: str, payload: dict):
    """
    Parse CSV data task with retry logic
    
    Args:
        job_id: MongoDB job document ID
        payload: Contains 'csv_data' with CSV content
    """
    try:
        # Reuse the event loop where the DB was initialized
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            _parse_csv_async(job_id, payload)
        )
        return result
    except SoftTimeLimitExceeded:
        # Re-queue task
        raise self.retry(exc=SoftTimeLimitExceeded())
    except Exception as exc:
        # Exponential backoff on failure
        raise self.retry(exc=exc)


async def _parse_csv_async(job_id: str, payload: dict):
    """Async implementation of CSV parsing"""
    job_doc = await Job.get(PydanticObjectId(job_id))
    
    try:
        job_doc.status = JobStatus.PROCESSING
        job_doc.started_at = datetime.utcnow()
        await job_doc.save()
        
        # Simulate CSV parsing with delay
        csv_data = payload.get("csv_data", "")
        await asyncio.sleep(2)  # Simulate work
        
        # Parse CSV
        csv_file = io.StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        
        # Store result
        job_doc.result = {
            "rows_processed": len(rows),
            "data": rows[:10],  # Store first 10 rows as sample
            "total_rows": len(rows)
        }
        job_doc.status = JobStatus.COMPLETED
        job_doc.completed_at = datetime.utcnow()
        await job_doc.save()
        
        # Update metrics
        JOBS_COMPLETED.inc()
        QUEUE_DEPTH.dec()
        if job_doc.started_at:
            duration = (job_doc.completed_at - job_doc.started_at).total_seconds()
            JOB_DURATION.observe(duration)
        
        return {"status": "success", "rows_processed": len(rows)}
        
    except Exception as e:
        job_doc.status = JobStatus.FAILED
        job_doc.error = str(e)
        job_doc.retries += 1
        job_doc.completed_at = datetime.utcnow()
        await job_doc.save()
        
        if job_doc.retries >= 3:
            QUEUE_DEPTH.dec()
            
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_email_task(self, job_id: str, payload: dict):
    """
    Send email task with retry logic
    
    Args:
        job_id: MongoDB job document ID
        payload: Contains 'to', 'subject', 'body'
    """
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            _send_email_async(job_id, payload)
        )
        return result
    except SoftTimeLimitExceeded:
        raise self.retry(exc=SoftTimeLimitExceeded())
    except Exception as exc:
        raise self.retry(exc=exc)


async def _send_email_async(job_id: str, payload: dict):
    """Async implementation of email sending"""
    job_doc = await Job.get(PydanticObjectId(job_id))
    
    try:
        job_doc.status = JobStatus.PROCESSING
        job_doc.started_at = datetime.utcnow()
        await job_doc.save()
        
        # Simulate email sending with delay
        await asyncio.sleep(1)
        
        # Mock email sending
        to = payload.get("to", "")
        subject = payload.get("subject", "")
        
        # Randomly fail for testing (optional)
        # if "fail@example.com" in to:
        #     raise Exception("Simulated email failure")
        
        job_doc.result = {
            "email_sent": True,
            "to": to,
            "subject": subject,
            "timestamp": datetime.utcnow().isoformat()
        }
        job_doc.status = JobStatus.COMPLETED
        job_doc.completed_at = datetime.utcnow()
        await job_doc.save()
        
        # Update metrics
        JOBS_COMPLETED.inc()
        QUEUE_DEPTH.dec()
        if job_doc.started_at:
            duration = (job_doc.completed_at - job_doc.started_at).total_seconds()
            JOB_DURATION.observe(duration)
        
        return {"status": "success", "email_sent": True}
        
    except Exception as e:
        job_doc.status = JobStatus.FAILED
        job_doc.error = str(e)
        job_doc.retries += 1
        job_doc.completed_at = datetime.utcnow()
        await job_doc.save()
        
        if job_doc.retries >= 3:
            QUEUE_DEPTH.dec()
            
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def process_data_task(self, job_id: str, payload: dict):
    """
    Generic data processing task
    
    Args:
        job_id: MongoDB job document ID
        payload: Contains 'data' to process
    """
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            _process_data_async(job_id, payload)
        )
        return result
    except SoftTimeLimitExceeded:
        raise self.retry(exc=SoftTimeLimitExceeded())
    except Exception as exc:
        raise self.retry(exc=exc)


async def _process_data_async(job_id: str, payload: dict):
    """Async implementation of data processing"""
    job_doc = await Job.get(PydanticObjectId(job_id))
    
    try:
        job_doc.status = JobStatus.PROCESSING
        job_doc.started_at = datetime.utcnow()
        await job_doc.save()
        
        # Simulate data processing with delay
        await asyncio.sleep(3)
        
        data = payload.get("data", {})
        processed = {
            "original": data,
            "processed_at": datetime.utcnow().isoformat(),
            "item_count": len(str(data))
        }
        
        job_doc.result = processed
        job_doc.status = JobStatus.COMPLETED
        job_doc.completed_at = datetime.utcnow()
        await job_doc.save()
        
        # Update metrics
        JOBS_COMPLETED.inc()
        QUEUE_DEPTH.dec()
        if job_doc.started_at:
            duration = (job_doc.completed_at - job_doc.started_at).total_seconds()
            JOB_DURATION.observe(duration)
        
        return {"status": "success", "processed": True}
        
    except Exception as e:
        job_doc.status = JobStatus.FAILED
        job_doc.error = str(e)
        job_doc.retries += 1
        job_doc.completed_at = datetime.utcnow()
        await job_doc.save()
        
        if job_doc.retries >= 3:
            QUEUE_DEPTH.dec()
            
        raise
