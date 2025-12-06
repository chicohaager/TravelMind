"""
Health Check Router

Provides detailed health status for monitoring and orchestration.
Includes checks for database, external services, and system resources.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime, timezone
import os
import psutil
import asyncio

from models.database import get_db

router = APIRouter()


class ComponentHealth(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict] = None


class SystemResources(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_percent: float
    disk_free_gb: float


class HealthResponse(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    timestamp: datetime
    uptime_seconds: float
    components: Dict[str, ComponentHealth]
    system: Optional[SystemResources] = None


# Track application start time
APP_START_TIME = datetime.now(timezone.utc)


async def check_database(db: AsyncSession) -> ComponentHealth:
    """Check database connectivity and response time."""
    try:
        start = asyncio.get_event_loop().time()
        await db.execute(text("SELECT 1"))
        latency = (asyncio.get_event_loop().time() - start) * 1000

        return ComponentHealth(
            status="healthy",
            latency_ms=round(latency, 2),
            message="Database connection successful"
        )
    except Exception as e:
        return ComponentHealth(
            status="unhealthy",
            message=f"Database connection failed: {str(e)}"
        )


async def check_disk_space() -> ComponentHealth:
    """Check available disk space."""
    try:
        disk = psutil.disk_usage("/")
        free_gb = disk.free / (1024 ** 3)
        percent_used = disk.percent

        if percent_used > 95:
            status = "unhealthy"
            message = f"Critical: Only {free_gb:.1f}GB free ({percent_used}% used)"
        elif percent_used > 85:
            status = "degraded"
            message = f"Warning: {free_gb:.1f}GB free ({percent_used}% used)"
        else:
            status = "healthy"
            message = f"{free_gb:.1f}GB free ({percent_used}% used)"

        return ComponentHealth(
            status=status,
            message=message,
            details={"free_gb": round(free_gb, 2), "percent_used": percent_used}
        )
    except Exception as e:
        return ComponentHealth(
            status="degraded",
            message=f"Could not check disk: {str(e)}"
        )


async def check_memory() -> ComponentHealth:
    """Check available memory."""
    try:
        memory = psutil.virtual_memory()
        available_mb = memory.available / (1024 ** 2)
        percent_used = memory.percent

        if percent_used > 95:
            status = "unhealthy"
            message = f"Critical: {available_mb:.0f}MB available ({percent_used}% used)"
        elif percent_used > 85:
            status = "degraded"
            message = f"Warning: {available_mb:.0f}MB available ({percent_used}% used)"
        else:
            status = "healthy"
            message = f"{available_mb:.0f}MB available ({percent_used}% used)"

        return ComponentHealth(
            status=status,
            message=message,
            details={"available_mb": round(available_mb, 0), "percent_used": percent_used}
        )
    except Exception as e:
        return ComponentHealth(
            status="degraded",
            message=f"Could not check memory: {str(e)}"
        )


async def check_uploads_directory() -> ComponentHealth:
    """Check if uploads directory is writable."""
    try:
        uploads_path = "./uploads"
        if not os.path.exists(uploads_path):
            return ComponentHealth(
                status="unhealthy",
                message="Uploads directory does not exist"
            )

        if not os.access(uploads_path, os.W_OK):
            return ComponentHealth(
                status="unhealthy",
                message="Uploads directory is not writable"
            )

        return ComponentHealth(
            status="healthy",
            message="Uploads directory is accessible"
        )
    except Exception as e:
        return ComponentHealth(
            status="degraded",
            message=f"Could not check uploads: {str(e)}"
        )


def get_system_resources() -> SystemResources:
    """Get current system resource usage."""
    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return SystemResources(
        cpu_percent=cpu,
        memory_percent=memory.percent,
        memory_available_mb=round(memory.available / (1024 ** 2), 0),
        disk_percent=disk.percent,
        disk_free_gb=round(disk.free / (1024 ** 3), 2)
    )


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check endpoint.

    Returns comprehensive health status including:
    - Database connectivity
    - Disk space
    - Memory usage
    - File system access
    - System resources

    Status values:
    - **healthy**: All systems operational
    - **degraded**: Some non-critical issues detected
    - **unhealthy**: Critical issues, service may be impaired

    Use this endpoint for:
    - Kubernetes liveness/readiness probes
    - Load balancer health checks
    - Monitoring dashboards
    """
    # Run all checks concurrently
    db_check, disk_check, memory_check, uploads_check = await asyncio.gather(
        check_database(db),
        check_disk_space(),
        check_memory(),
        check_uploads_directory()
    )

    components = {
        "database": db_check,
        "disk": disk_check,
        "memory": memory_check,
        "uploads": uploads_check,
    }

    # Determine overall status
    statuses = [c.status for c in components.values()]
    if "unhealthy" in statuses:
        overall_status = "unhealthy"
    elif "degraded" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    # Calculate uptime
    uptime = (datetime.now(timezone.utc) - APP_START_TIME).total_seconds()

    return HealthResponse(
        status=overall_status,
        version=os.getenv("APP_VERSION", "1.0.0"),
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=round(uptime, 2),
        components=components,
        system=get_system_resources()
    )


@router.get("/health/live", tags=["System"])
async def liveness_probe():
    """
    Kubernetes liveness probe.

    Simple check that the application is running.
    Returns 200 if the app is alive, regardless of dependency status.
    """
    return {"status": "alive"}


@router.get("/health/ready", tags=["System"])
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """
    Kubernetes readiness probe.

    Checks if the application is ready to receive traffic.
    Returns 200 only if critical dependencies (database) are available.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service not ready")
