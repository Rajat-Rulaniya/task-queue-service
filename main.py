from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient

from config import settings
from celery_app import celery_app
from database import init_db, close_db
from routes import router, limiter
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

# Store db client in app state
db_client: AsyncIOMotorClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown
    """
    # Startup
    global db_client
    db_client = await init_db()
    print("✓ MongoDB initialized")
    print("✓ Application startup complete")
    
    yield
    
    # Shutdown
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
