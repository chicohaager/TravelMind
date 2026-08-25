"""
Notification model

A single in-app notification for a recipient user, raised by trip-sharing
events (invitation received / accepted / declined). Display strings are rendered
client-side from `type` + the denormalized `actor_name` / `trip_title`, so a
notification stays readable even if the trip is later renamed or deleted.
"""

from models.database import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    # Recipient.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event type: invite_received | invite_accepted | invite_declined
    type = Column(String(50), nullable=False)

    # Denormalized context for display + navigation.
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=True)
    actor_name = Column(String(200), nullable=True)  # who triggered it
    trip_title = Column(String(200), nullable=True)

    is_read = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User")

    def __repr__(self):
        return f"<Notification {self.id} {self.type} -> user {self.user_id}>"
