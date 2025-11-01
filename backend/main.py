"""
TravelMind Backend - FastAPI Application
A self-hosted travel planning app with Claude AI integration
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import structlog

# Import routes
from routes import trips, diary, places, timeline, budget, ai, auth, users, participants, admin, user_settings, routes as route_routes

# Import error handlers
from utils.error_handlers import (
    StandardError,
    standard_error_handler,
    validation_error_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    general_exception_handler
)

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🌍 TravelMind Backend starting...")

    # Validate required environment variables
    jwt_secret = os.getenv("JWT_SECRET")
    secret_key = os.getenv("SECRET_KEY")

    if not jwt_secret or jwt_secret == "your-super-secret-jwt-key-change-this-in-production":
        print("❌ ERROR: JWT_SECRET not configured or using default value!")
        print("   Please set a secure JWT_SECRET in your .env file.")
        print("   Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
        raise ValueError("JWT_SECRET must be configured with a secure value")

    if not secret_key or secret_key == "default-secret-key-change-this":
        print("❌ ERROR: SECRET_KEY not configured or using default value!")
        print("   Please set a secure SECRET_KEY in your .env file.")
        print("   Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
        raise ValueError("SECRET_KEY must be configured with a secure value")

    print("✅ Security keys validated")

    # Create necessary directories
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./uploads", exist_ok=True)

    # Initialize database
    from models.database import init_db
    await init_db()

    print("✅ Backend ready!")

    yield

    # Shutdown
    print("👋 Shutting down TravelMind Backend...")


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="TravelMind API",
    description="A self-hosted travel planning and diary app with AI assistance",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False  # Accept URLs with or without trailing slashes
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add standardized error handlers
app.add_exception_handler(StandardError, standard_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS Configuration
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (uploads)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(user_settings.router, prefix="/api/user", tags=["User Settings"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(trips.router, prefix="/api/trips", tags=["Trips"])
app.include_router(participants.router, prefix="/api/trips", tags=["Participants"])
app.include_router(diary.router, prefix="/api/diary", tags=["Diary"])
app.include_router(places.router, prefix="/api/places", tags=["Places"])
app.include_router(route_routes.router, tags=["Routes"])  # prefix already defined in router
app.include_router(timeline.router, prefix="/api/timeline", tags=["Timeline"])
app.include_router(budget.router, prefix="/api/budget", tags=["Budget"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Assistant"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": "TravelMind",
        "version": "1.0.0",
        "message": "Deine nächste Reise wartet schon!",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "travelmind-backend"
    }


@app.get("/api/status")
async def api_status():
    """API status endpoint with feature flags"""
    return {
        "status": "operational",
        "features": {
            "ai_enabled": os.getenv("ENABLE_AI_FEATURES", "true").lower() == "true",
            "collaboration": os.getenv("ENABLE_COLLABORATION", "true").lower() == "true",
            "offline_mode": os.getenv("ENABLE_OFFLINE_MODE", "true").lower() == "true"
        },
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    reload = os.getenv("BACKEND_RELOAD", "true").lower() == "true"

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
