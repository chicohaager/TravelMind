"""
Security Middleware
Adds security headers and CSRF protection to all responses
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import secrets
import hmac
import hashlib
import os
from typing import Callable
import structlog

logger = structlog.get_logger(__name__)

# CSRF token settings
CSRF_SECRET = os.getenv("SECRET_KEY", "default-secret-key")
CSRF_TOKEN_LENGTH = 32
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def sign_csrf_token(token: str) -> str:
    """Sign a CSRF token with HMAC."""
    return hmac.new(
        CSRF_SECRET.encode(),
        token.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_csrf_token(token: str, signature: str) -> bool:
    """Verify a CSRF token signature."""
    expected_signature = sign_csrf_token(token)
    return hmac.compare_digest(expected_signature, signature)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Legacy XSS protection for older browsers
    - Strict-Transport-Security: Enforces HTTPS
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Restricts browser features
    - Cache-Control: Prevents caching of sensitive data
    """

    def __init__(self, app: ASGIApp, enable_hsts: bool = True):
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(self), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=()"
        )

        # HSTS - only enable in production with HTTPS
        if self.enable_hsts and os.getenv("ENABLE_HSTS", "false").lower() == "true":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Cache control for API responses (prevent caching of sensitive data)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware.

    - Sets a CSRF token cookie on all responses
    - Validates CSRF token header on state-changing requests (POST, PUT, DELETE, PATCH)
    - Exempts authentication endpoints (login, register) and API token-based requests
    """

    EXEMPT_PATHS = {
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip CSRF for safe methods
        if request.method in CSRF_SAFE_METHODS:
            response = await call_next(request)
            return self._set_csrf_cookie(request, response)

        # Skip CSRF for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            response = await call_next(request)
            return self._set_csrf_cookie(request, response)

        # Skip CSRF if request has valid JWT (API clients)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            response = await call_next(request)
            return self._set_csrf_cookie(request, response)

        # Validate CSRF token for state-changing requests from browser
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        csrf_header = request.headers.get(CSRF_TOKEN_NAME)

        if not csrf_cookie or not csrf_header:
            logger.warning(
                "csrf_token_missing",
                path=request.url.path,
                method=request.method,
                has_cookie=bool(csrf_cookie),
                has_header=bool(csrf_header)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing"
            )

        # Verify token matches
        if not hmac.compare_digest(csrf_cookie, csrf_header):
            logger.warning(
                "csrf_token_mismatch",
                path=request.url.path,
                method=request.method
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token invalid"
            )

        response = await call_next(request)
        return self._set_csrf_cookie(request, response)

    def _set_csrf_cookie(self, request: Request, response: Response) -> Response:
        """Set or refresh the CSRF token cookie."""
        # Only set cookie if not already present or if it's a new session
        if CSRF_COOKIE_NAME not in request.cookies:
            csrf_token = generate_csrf_token()
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=csrf_token,
                httponly=False,  # Must be readable by JavaScript
                secure=os.getenv("SECURE_COOKIES", "false").lower() == "true",
                samesite="strict",
                max_age=86400  # 24 hours
            )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size.
    Prevents DoS attacks via large payloads.
    """

    def __init__(self, app: ASGIApp, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")

        if content_length:
            content_length = int(content_length)
            if content_length > self.max_size:
                logger.warning(
                    "request_too_large",
                    path=request.url.path,
                    content_length=content_length,
                    max_size=self.max_size
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Request body too large. Maximum size: {self.max_size / (1024*1024):.1f}MB"
                )

        return await call_next(request)
