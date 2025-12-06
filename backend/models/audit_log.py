"""
Audit Log Model

Records security-relevant events for compliance and debugging.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from models.database import Base


class AuditLog(Base):
    """
    Audit log entry for tracking security-relevant events.

    Events tracked:
    - Authentication: login, logout, password_change, token_refresh
    - User Management: user_create, user_update, user_delete
    - Data Access: trip_create, trip_update, trip_delete, etc.
    - Admin Actions: settings_change, user_role_change
    - Security: login_failed, permission_denied, rate_limited
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Event classification
    event_type = Column(String(50), nullable=False, index=True)
    # e.g., "auth.login", "trip.create", "admin.user_delete"

    event_category = Column(String(20), nullable=False, index=True)
    # Categories: auth, user, trip, diary, place, admin, security

    # Who performed the action
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(50), nullable=True)  # Stored separately in case user is deleted

    # What was affected
    resource_type = Column(String(50), nullable=True)  # e.g., "trip", "user", "diary_entry"
    resource_id = Column(Integer, nullable=True)

    # Request details
    ip_address = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)

    # Event details
    description = Column(String(500), nullable=True)
    details = Column(JSON, nullable=True)  # Additional structured data
    status = Column(String(20), default="success")  # success, failure, warning

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditLog {self.event_type} by {self.username} at {self.created_at}>"
