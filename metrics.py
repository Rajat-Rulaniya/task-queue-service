from prometheus_client import Counter, Histogram, Gauge

# Define custom metrics
JOBS_ENQUEUED = Counter(
    "jobs_enqueued_total", 
    "Total number of jobs enqueued"
)

JOBS_COMPLETED = Counter(
    "jobs_completed_total", 
    "Total number of jobs completed successfully"
)

JOB_DURATION = Histogram(
    "job_processing_duration_seconds", 
    "Time spent processing a job in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

QUEUE_DEPTH = Gauge(
    "job_queue_depth", 
    "Current number of jobs in the queue (pending/processing)"
)
