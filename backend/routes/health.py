"""
Health Check Router

Provides detailed health status for monitoring and orchestration.
Includes checks for database, external services, and system resources.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, Optional

import psutil
import structlog
from fastapi import APIRouter, Depends, Request
from models.database import get_db
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from utils.rate_limits import RateLimits, limiter

logger = structlog.get_logger(__name__)

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

        return ComponentHealth(status="healthy", latency_ms=round(latency, 2), message="Database connection successful")
    except Exception as e:
        return ComponentHealth(status="unhealthy", message=f"Database connection failed: {str(e)}")


async def check_disk_space() -> ComponentHealth:
    """Check available disk space."""
    try:
        disk = psutil.disk_usage("/")
        free_gb = disk.free / (1024**3)
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
            status=status, message=message, details={"free_gb": round(free_gb, 2), "percent_used": percent_used}
        )
    except Exception as e:
        return ComponentHealth(status="degraded", message=f"Could not check disk: {str(e)}")


async def check_memory() -> ComponentHealth:
    """Check available memory."""
    try:
        memory = psutil.virtual_memory()
        available_mb = memory.available / (1024**2)
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
            details={"available_mb": round(available_mb, 0), "percent_used": percent_used},
        )
    except Exception as e:
        return ComponentHealth(status="degraded", message=f"Could not check memory: {str(e)}")


async def check_uploads_directory() -> ComponentHealth:
    """Check if uploads directory is writable."""
    try:
        uploads_path = "./uploads"
        if not os.path.exists(uploads_path):
            return ComponentHealth(status="unhealthy", message="Uploads directory does not exist")

        if not os.access(uploads_path, os.W_OK):
            return ComponentHealth(status="unhealthy", message="Uploads directory is not writable")

        return ComponentHealth(status="healthy", message="Uploads directory is accessible")
    except Exception as e:
        return ComponentHealth(status="degraded", message=f"Could not check uploads: {str(e)}")


def get_system_resources() -> SystemResources:
    """Get current system resource usage."""
    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return SystemResources(
        cpu_percent=cpu,
        memory_percent=memory.percent,
        memory_available_mb=round(memory.available / (1024**2), 0),
        disk_percent=disk.percent,
        disk_free_gb=round(disk.free / (1024**3), 2),
    )


@router.get("/health", response_model=HealthResponse, tags=["System"])
@limiter.limit(RateLimits.HEALTH_CHECK)
async def detailed_health_check(request: Request, db: AsyncSession = Depends(get_db)):
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
    # Run all checks concurrently.
    #
    # `return_exceptions=True` ist hier kein Verschlucken, sondern die
    # Voraussetzung dafuer, dass die Auskunft ueberhaupt eine ist: ohne das
    # reisst eine unerwartete Ausnahme in EINER Teilpruefung den ganzen
    # Endpunkt auf 500 — also genau die Auskunft weg, die sagen soll, WAS
    # kaputt ist. Der Ausfall wird unten in eine `unhealthy`-Komponente
    # uebersetzt und faerbt damit den Gesamtstatus; still wird nichts.
    ergebnisse = await asyncio.gather(
        check_database(db),
        check_disk_space(),
        check_memory(),
        check_uploads_directory(),
        return_exceptions=True,
    )

    namen = ("database", "disk", "memory", "uploads")
    components = {}
    for name, ergebnis in zip(namen, ergebnisse):
        if isinstance(ergebnis, BaseException):
            logger.error("health_check_failed", component=name, error=str(ergebnis))
            components[name] = ComponentHealth(
                status="unhealthy", message=f"Check raised {type(ergebnis).__name__}: {ergebnis}"
            )
        else:
            components[name] = ergebnis

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
        system=get_system_resources(),
    )


@router.get("/health/live", tags=["System"])
@limiter.limit(RateLimits.HEALTH_CHECK)
async def liveness_probe(request: Request):
    """
    Kubernetes liveness probe.

    Simple check that the application is running.
    Returns 200 if the app is alive, regardless of dependency status.
    """
    return {"status": "alive"}


@router.get("/capabilities", tags=["System"])
@limiter.limit(RateLimits.HEALTH_CHECK)
async def capabilities(request: Request):
    """Server feature flags the frontend adapts to (e.g. HEIC/HEIF support)."""
    from utils.images import heic_supported

    return {"heic_supported": heic_supported()}


@router.get("/health/ready", tags=["System"])
@limiter.limit(RateLimits.HEALTH_CHECK)
async def readiness_probe(request: Request, db: AsyncSession = Depends(get_db)):
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
