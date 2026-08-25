"""
Media model

A single uploaded photo (and, later, video) with its metadata. Replaces the
plain ``photos`` JSON string-arrays on diary entries and places as the source of
truth, so each image can carry a caption, capture time, GPS position, dimensions
and an explicit ordering — and can be queried across a whole trip.

A media row always belongs to a trip and an owner, and to exactly one of a
diary entry or a place (the other FK is NULL).
"""

from models.database import Base
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)

    # Ownership / scoping
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)

    # Exactly one of these is set (the other is NULL).
    diary_entry_id = Column(Integer, ForeignKey("diary_entries.id", ondelete="CASCADE"), nullable=True, index=True)
    place_id = Column(Integer, ForeignKey("places.id", ondelete="CASCADE"), nullable=True, index=True)

    # File references (web-sized image + thumbnail), produced by utils.images.
    url = Column(String(500), nullable=False)
    thumb_url = Column(String(500), nullable=True)

    # Technical metadata
    mime_type = Column(String(50), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)

    # User / EXIF metadata
    caption = Column(String(500), nullable=True)
    taken_at = Column(DateTime, nullable=True)  # from EXIF DateTimeOriginal
    latitude = Column(Float, nullable=True)  # from EXIF GPS
    longitude = Column(Float, nullable=True)

    # Display order within its parent (diary entry / place)
    order_index = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    owner = relationship("User")
    trip = relationship("Trip")
    diary_entry = relationship("DiaryEntry", back_populates="media")
    place = relationship("Place", back_populates="media")

    def __repr__(self):
        return f"<Media {self.id} {self.url}>"
