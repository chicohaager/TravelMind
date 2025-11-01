"""
Diary Entry model
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)  # Markdown content

    # Entry date (when the experience happened)
    entry_date = Column(DateTime, nullable=True)

    # Location data
    location_name = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Media (stored as JSON array of file paths)
    photos = Column(JSON, default=list)

    # Tags
    tags = Column(JSON, default=list)

    # Mood/rating
    mood = Column(String(50), nullable=True)  # e.g., "happy", "excited", "relaxed"
    rating = Column(Integer, nullable=True)  # 1-5 stars

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign Keys
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    trip = relationship("Trip", back_populates="diary_entries")
    author = relationship("User", back_populates="diary_entries")

    def __repr__(self):
        return f"<DiaryEntry {self.title}>"
