"""
Request ID Middleware

Adds unique request IDs to all requests for tracing and debugging.
The request ID is:
- Generated if not provided by client
- Added to response headers
- Available in request state for logging
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable
import uuid
import structlog

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.

    The request ID can be:
    - Provided by client via X-Request-ID header
    - Auto-generated if not provided

    The ID is:
    - Stored in request.state.request_id
    - Returned in X-Request-ID response header
    - Used for correlating logs across services
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get request ID from header or generate new one
        request_id = request.headers.get(self.HEADER_NAME)

        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for access in route handlers
        request.state.request_id = request_id

        # Bind request ID to structured logger context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        # Log request start
        logger.info(
            "request_started",
            client_ip=request.client.host if request.client else None,
        )

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.HEADER_NAME] = request_id

        # Log request completion
        logger.info(
            "request_completed",
            status_code=response.status_code,
        )

        return response


def get_request_id(request: Request) -> str:
    """
    Helper function to get request ID from request state.

    Usage in route handlers:
        request_id = get_request_id(request)
    """
    return getattr(request.state, "request_id", "unknown")
