"""
Audit Logging Service

Provides easy-to-use functions for logging security-relevant events.
Designed for async FastAPI usage with proper error handling.
"""

from typing import Optional, Any, Dict
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from models.audit_log import AuditLog

logger = structlog.get_logger(__name__)


class AuditService:
    """
    Centralized audit logging service.

    Usage:
        await audit_service.log_auth_event(db, "login", user, request)
        await audit_service.log_data_event(db, "create", "trip", trip.id, user, request)
    """

    # Event type definitions
    AUTH_EVENTS = {
        "login": "auth.login",
        "logout": "auth.logout",
        "login_failed": "auth.login_failed",
        "password_change": "auth.password_change",
        "token_refresh": "auth.token_refresh",
        "register": "auth.register",
    }

    DATA_EVENTS = {
        "create": "data.create",
        "update": "data.update",
        "delete": "data.delete",
        "view": "data.view",
        "export": "data.export",
    }

    ADMIN_EVENTS = {
        "user_create": "admin.user_create",
        "user_update": "admin.user_update",
        "user_delete": "admin.user_delete",
        "settings_change": "admin.settings_change",
        "role_change": "admin.role_change",
    }

    SECURITY_EVENTS = {
        "permission_denied": "security.permission_denied",
        "rate_limited": "security.rate_limited",
        "invalid_token": "security.invalid_token",
        "suspicious_activity": "security.suspicious_activity",
    }

    @staticmethod
    def _extract_request_info(request: Optional[Request]) -> Dict[str, Any]:
        """Extract useful information from the request object."""
        if not request:
            return {}

        # Get client IP (handle proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None

        return {
            "ip_address": ip_address,
            "user_agent": request.headers.get("User-Agent", "")[:500],
            "request_method": request.method,
            "request_path": str(request.url.path)[:500],
        }

    async def log_event(
        self,
        db: AsyncSession,
        event_type: str,
        category: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        description: Optional[str] = None,
        details: Optional[Dict] = None,
        status: str = "success",
        request: Optional[Request] = None,
    ) -> Optional[AuditLog]:
        """
        Log an audit event to the database.

        Returns the created AuditLog or None if logging failed.
        """
        try:
            request_info = self._extract_request_info(request)

            log_entry = AuditLog(
                event_type=event_type,
                event_category=category,
                user_id=user_id,
                username=username,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                details=details,
                status=status,
                **request_info,
            )

            db.add(log_entry)
            await db.commit()
            await db.refresh(log_entry)

            # Also log to structured logger for real-time monitoring
            logger.info(
                "audit_event",
                event_type=event_type,
                category=category,
                user_id=user_id,
                username=username,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
            )

            return log_entry

        except Exception as e:
            logger.error("audit_log_failed", error=str(e), event_type=event_type)
            # Don't let audit logging failure break the main operation
            await db.rollback()
            return None

    async def log_auth_event(
        self,
        db: AsyncSession,
        event: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        request: Optional[Request] = None,
        details: Optional[Dict] = None,
        status: str = "success",
    ) -> Optional[AuditLog]:
        """Log an authentication-related event."""
        event_type = self.AUTH_EVENTS.get(event, f"auth.{event}")
        description = f"Authentication event: {event}"

        return await self.log_event(
            db=db,
            event_type=event_type,
            category="auth",
            user_id=user_id,
            username=username,
            description=description,
            details=details,
            status=status,
            request=request,
        )

    async def log_data_event(
        self,
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: Optional[int],
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        request: Optional[Request] = None,
        details: Optional[Dict] = None,
        status: str = "success",
    ) -> Optional[AuditLog]:
        """Log a data modification event."""
        event_type = f"{resource_type}.{action}"
        description = f"{action.capitalize()} {resource_type}"
        if resource_id:
            description += f" (ID: {resource_id})"

        return await self.log_event(
            db=db,
            event_type=event_type,
            category="data",
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            details=details,
            status=status,
            request=request,
        )

    async def log_admin_event(
        self,
        db: AsyncSession,
        action: str,
        admin_user_id: int,
        admin_username: str,
        target_user_id: Optional[int] = None,
        request: Optional[Request] = None,
        details: Optional[Dict] = None,
        status: str = "success",
    ) -> Optional[AuditLog]:
        """Log an admin action."""
        event_type = self.ADMIN_EVENTS.get(action, f"admin.{action}")
        description = f"Admin action: {action}"
        if target_user_id:
            description += f" on user {target_user_id}"

        return await self.log_event(
            db=db,
            event_type=event_type,
            category="admin",
            user_id=admin_user_id,
            username=admin_username,
            resource_type="user" if target_user_id else None,
            resource_id=target_user_id,
            description=description,
            details=details,
            status=status,
            request=request,
        )

    async def log_security_event(
        self,
        db: AsyncSession,
        event: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        request: Optional[Request] = None,
        details: Optional[Dict] = None,
    ) -> Optional[AuditLog]:
        """Log a security-related event (always logged as warning/failure)."""
        event_type = self.SECURITY_EVENTS.get(event, f"security.{event}")
        description = f"Security event: {event}"

        return await self.log_event(
            db=db,
            event_type=event_type,
            category="security",
            user_id=user_id,
            username=username,
            description=description,
            details=details,
            status="warning",
            request=request,
        )


# Global singleton instance
audit_service = AuditService()
