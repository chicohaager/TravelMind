"""
Sentry Error Tracking Integration

Provides error tracking, performance monitoring, and user context for debugging.
"""

import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging
import structlog

logger = structlog.get_logger(__name__)


def init_sentry() -> bool:
    """
    Initialize Sentry SDK if DSN is configured.

    Returns True if Sentry was initialized, False otherwise.

    Environment variables:
    - SENTRY_DSN: Sentry Data Source Name (required)
    - SENTRY_ENVIRONMENT: Environment name (production, staging, development)
    - SENTRY_RELEASE: Release/version identifier
    - SENTRY_TRACES_SAMPLE_RATE: Performance monitoring sample rate (0.0-1.0)
    - SENTRY_PROFILES_SAMPLE_RATE: Profiling sample rate (0.0-1.0)
    """
    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        logger.info("sentry_disabled", reason="SENTRY_DSN not configured")
        return False

    environment = os.getenv("SENTRY_ENVIRONMENT", "development")
    release = os.getenv("SENTRY_RELEASE", "travelmind@1.0.0")
    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,

        # Performance Monitoring
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,

        # Integrations
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint"
            ),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            ),
        ],

        # Data scrubbing - remove sensitive data
        send_default_pii=False,

        # Before send hook for additional filtering
        before_send=before_send_filter,

        # Ignore certain errors
        ignore_errors=[
            KeyboardInterrupt,
            SystemExit,
        ],
    )

    logger.info(
        "sentry_initialized",
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate
    )

    return True


def before_send_filter(event, hint):
    """
    Filter events before sending to Sentry.

    - Remove sensitive data
    - Filter out non-critical errors
    - Add additional context
    """
    # Don't send 4xx client errors (they're not bugs)
    if "exception" in event:
        exc_info = hint.get("exc_info")
        if exc_info:
            exc_type, exc_value, _ = exc_info

            # Filter out expected HTTP exceptions
            from fastapi import HTTPException
            if isinstance(exc_value, HTTPException):
                if 400 <= exc_value.status_code < 500:
                    return None  # Don't send client errors

    # Scrub sensitive headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[Filtered]"

    return event


def set_user_context(user_id: int, username: str, email: str = None):
    """
    Set user context for Sentry events.

    Call this after successful authentication to attach user info to errors.
    """
    sentry_sdk.set_user({
        "id": str(user_id),
        "username": username,
        "email": email,
    })


def clear_user_context():
    """Clear user context (call on logout)."""
    sentry_sdk.set_user(None)


def capture_message(message: str, level: str = "info", **extra):
    """
    Capture a message to Sentry.

    Useful for tracking non-exception events.
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in extra.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_message(message, level=level)


def capture_exception(exception: Exception, **extra):
    """
    Capture an exception to Sentry with extra context.
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in extra.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_exception(exception)


def add_breadcrumb(message: str, category: str = "custom", level: str = "info", **data):
    """
    Add a breadcrumb for debugging context.

    Breadcrumbs are logged events that lead up to an error.
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data
    )
