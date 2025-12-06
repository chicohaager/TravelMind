"""
Participant model
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)

    # Participant details
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    role = Column(String(100), nullable=True)  # e.g., "Freund", "Familie", etc.
    photo_url = Column(String(500), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    trip = relationship("Trip", backref="participants")

    def __repr__(self):
        return f"<Participant {self.name}>"
