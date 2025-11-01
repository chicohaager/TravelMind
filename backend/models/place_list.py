"""
PlaceList model - Custom categorization lists for places
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base


class PlaceList(Base):
    __tablename__ = "place_lists"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    icon = Column(String(10), default="📍")  # Emoji icon
    color = Column(String(7), default="#6366F1")  # Hex color
    is_collapsed = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign Keys
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    trip = relationship("Trip", back_populates="place_lists")
    places = relationship("Place", back_populates="place_list", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PlaceList {self.title}>"
