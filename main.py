from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient

from config import settings
from database import init_db, close_db
from routes import router, limiter
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
import asyncio
from datetime import datetime
from models import Job, JobStatus
from metrics import JOBS_COMPLETED, JOB_DURATION, QUEUE_DEPTH

# Store db client in app state
db_client: AsyncIOMotorClient = None

async def metrics_poller():
    last_checked_time = datetime.utcnow()
    while True:
        try:
            await asyncio.sleep(2)
            
            # 1. Update Queue Depth
            pending = await Job.find({"status": JobStatus.PENDING}).count()
            processing = await Job.find({"status": JobStatus.PROCESSING}).count()
            QUEUE_DEPTH.set(pending + processing)
            
            # 2. Find newly completed jobs
            newly_completed = await Job.find(
                {"status": JobStatus.COMPLETED, "completed_at": {"$gt": last_checked_time}}
            ).to_list()
            
            for job in newly_completed:
                JOBS_COMPLETED.inc()
                if job.started_at and job.completed_at:
                    duration = (job.completed_at - job.started_at).total_seconds()
                    JOB_DURATION.observe(duration)
                
                if job.completed_at > last_checked_time:
                    last_checked_time = job.completed_at

        except Exception as e:
            print(f"Metrics poller error: {e}")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown
    """
    # Startup
    global db_client
    db_client = await init_db()
    print("✓ MongoDB initialized")
    
    # Start metrics poller
    poller_task = asyncio.create_task(metrics_poller())
    
    print("✓ Application startup complete")
    
    yield
    
    # Shutdown
    poller_task.cancel()
    await close_db(db_client)
    print("✓ Application shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Async job processing service with Celery and Redis",
    version="1.0.0",
    lifespan=lifespan,
)

# Add state limiter
app.state.limiter = limiter

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded: 10 requests per minute per IP"},
    )


# Include routes
app.include_router(router, prefix="/api/v1", tags=["jobs"])

# Instrument and expose prometheus metrics
Instrumentator().instrument(app).expose(app)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
