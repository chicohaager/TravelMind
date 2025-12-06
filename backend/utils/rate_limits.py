"""
Rate Limiting Configuration

Centralized rate limit definitions for all API endpoints.
Organized by sensitivity level and resource usage.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
import os


# Get custom key function that handles proxies better
def get_client_ip(request):
    """
    Get client IP address, handling reverse proxies.
    Prefers X-Forwarded-For if available, falls back to direct client IP.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP from the chain (original client)
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


# Initialize limiter with proxy-aware key function
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["200 per day", "50 per hour"]
)


# ==================== RATE LIMIT DEFINITIONS ====================
# Format: "requests per period" (e.g., "10/minute", "100/hour", "1000/day")

class RateLimits:
    """
    Centralized rate limit configuration.

    Categories:
    - CRITICAL: Security-sensitive endpoints (login, register, password)
    - WRITE: Data modification endpoints (create, update, delete)
    - READ: Data retrieval endpoints (get, list)
    - AI: AI-powered endpoints (expensive API calls)
    - ADMIN: Admin-only endpoints
    - PUBLIC: Public/unauthenticated endpoints
    """

    # ===== Authentication (CRITICAL - strict limits to prevent brute force) =====
    AUTH_LOGIN = os.getenv("RATE_LIMIT_AUTH_LOGIN", "10/minute")
    AUTH_REGISTER = os.getenv("RATE_LIMIT_AUTH_REGISTER", "5/minute")
    AUTH_PASSWORD_CHANGE = os.getenv("RATE_LIMIT_AUTH_PASSWORD", "5/minute")
    AUTH_REFRESH = os.getenv("RATE_LIMIT_AUTH_REFRESH", "30/minute")

    # ===== User Operations =====
    USER_PROFILE_READ = os.getenv("RATE_LIMIT_USER_READ", "60/minute")
    USER_PROFILE_UPDATE = os.getenv("RATE_LIMIT_USER_UPDATE", "20/minute")
    USER_DELETE = os.getenv("RATE_LIMIT_USER_DELETE", "5/minute")
    USER_AVATAR_UPLOAD = os.getenv("RATE_LIMIT_USER_AVATAR", "10/minute")

    # ===== Trip Operations =====
    TRIP_LIST = os.getenv("RATE_LIMIT_TRIP_LIST", "60/minute")
    TRIP_READ = os.getenv("RATE_LIMIT_TRIP_READ", "120/minute")
    TRIP_CREATE = os.getenv("RATE_LIMIT_TRIP_CREATE", "30/minute")
    TRIP_UPDATE = os.getenv("RATE_LIMIT_TRIP_UPDATE", "30/minute")
    TRIP_DELETE = os.getenv("RATE_LIMIT_TRIP_DELETE", "20/minute")
    TRIP_UPLOAD = os.getenv("RATE_LIMIT_TRIP_UPLOAD", "10/minute")

    # ===== Diary Operations =====
    DIARY_LIST = os.getenv("RATE_LIMIT_DIARY_LIST", "60/minute")
    DIARY_READ = os.getenv("RATE_LIMIT_DIARY_READ", "120/minute")
    DIARY_CREATE = os.getenv("RATE_LIMIT_DIARY_CREATE", "30/minute")
    DIARY_UPDATE = os.getenv("RATE_LIMIT_DIARY_UPDATE", "30/minute")
    DIARY_DELETE = os.getenv("RATE_LIMIT_DIARY_DELETE", "20/minute")
    DIARY_UPLOAD = os.getenv("RATE_LIMIT_DIARY_UPLOAD", "10/minute")

    # ===== Place Operations =====
    PLACE_LIST = os.getenv("RATE_LIMIT_PLACE_LIST", "60/minute")
    PLACE_READ = os.getenv("RATE_LIMIT_PLACE_READ", "120/minute")
    PLACE_CREATE = os.getenv("RATE_LIMIT_PLACE_CREATE", "60/minute")
    PLACE_UPDATE = os.getenv("RATE_LIMIT_PLACE_UPDATE", "60/minute")
    PLACE_DELETE = os.getenv("RATE_LIMIT_PLACE_DELETE", "30/minute")
    PLACE_BULK_IMPORT = os.getenv("RATE_LIMIT_PLACE_BULK", "10/minute")

    # ===== AI Endpoints (expensive - strict limits) =====
    AI_CHAT = os.getenv("RATE_LIMIT_AI_CHAT", "20/minute")
    AI_RECOMMENDATIONS = os.getenv("RATE_LIMIT_AI_RECO", "10/minute")
    AI_PLAN = os.getenv("RATE_LIMIT_AI_PLAN", "5/minute")
    AI_DESCRIBE = os.getenv("RATE_LIMIT_AI_DESCRIBE", "15/minute")
    AI_TIPS = os.getenv("RATE_LIMIT_AI_TIPS", "15/minute")

    # ===== Budget/Expense Operations =====
    BUDGET_READ = os.getenv("RATE_LIMIT_BUDGET_READ", "60/minute")
    EXPENSE_CREATE = os.getenv("RATE_LIMIT_EXPENSE_CREATE", "60/minute")
    EXPENSE_UPDATE = os.getenv("RATE_LIMIT_EXPENSE_UPDATE", "60/minute")
    EXPENSE_DELETE = os.getenv("RATE_LIMIT_EXPENSE_DELETE", "30/minute")

    # ===== Timeline =====
    TIMELINE_READ = os.getenv("RATE_LIMIT_TIMELINE", "60/minute")

    # ===== Geocoding (external API calls) =====
    GEOCODE = os.getenv("RATE_LIMIT_GEOCODE", "30/minute")

    # ===== Admin Endpoints =====
    ADMIN_READ = os.getenv("RATE_LIMIT_ADMIN_READ", "120/minute")
    ADMIN_WRITE = os.getenv("RATE_LIMIT_ADMIN_WRITE", "60/minute")
    ADMIN_DELETE = os.getenv("RATE_LIMIT_ADMIN_DELETE", "30/minute")
    ADMIN_BULK = os.getenv("RATE_LIMIT_ADMIN_BULK", "10/minute")

    # ===== Public/Utility Endpoints =====
    PUBLIC_STATUS = os.getenv("RATE_LIMIT_STATUS", "60/minute")
    HEALTH_CHECK = os.getenv("RATE_LIMIT_HEALTH", "120/minute")


# ==================== HELPER FUNCTIONS ====================

def get_rate_limit_status():
    """
    Get current rate limit configuration as a dictionary.
    Useful for exposing in admin API or debugging.
    """
    limits = {}
    for attr in dir(RateLimits):
        if not attr.startswith('_'):
            value = getattr(RateLimits, attr)
            if isinstance(value, str) and '/' in value:
                limits[attr] = value
    return limits
