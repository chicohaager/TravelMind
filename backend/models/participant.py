"""
Participant model - Trip sharing and collaboration
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base
import enum


class PermissionLevel(str, enum.Enum):
    """Permission levels for trip access"""
    OWNER = "owner"      # Full access, can delete trip
    EDITOR = "editor"    # Can edit trip, places, diary
    VIEWER = "viewer"    # Read-only access


class InvitationStatus(str, enum.Enum):
    """Status of trip invitation"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)

    # Link to registered user (optional - for sharing with registered users)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Participant details (for display and for non-registered participants)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    role = Column(String(100), nullable=True)  # e.g., "Freund", "Familie", etc.
    photo_url = Column(String(500), nullable=True)

    # Permission system
    permission = Column(String(20), default=PermissionLevel.VIEWER.value)  # owner, editor, viewer
    invitation_status = Column(String(20), default=InvitationStatus.PENDING.value)  # pending, accepted, declined

    # Timestamps
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    trip = relationship("Trip", backref="participants")
    user = relationship("User", backref="trip_participations")

    def __repr__(self):
        return f"<Participant {self.name} ({self.permission})>"

    @property
    def is_registered_user(self) -> bool:
        """Check if participant is a registered user"""
        return self.user_id is not None

    @property
    def can_edit(self) -> bool:
        """Check if participant can edit the trip"""
        return self.permission in [PermissionLevel.OWNER.value, PermissionLevel.EDITOR.value]

    @property
    def is_owner(self) -> bool:
        """Check if participant is the owner"""
        return self.permission == PermissionLevel.OWNER.value
