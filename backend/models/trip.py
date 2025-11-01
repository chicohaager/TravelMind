"""
Trip model
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Dates
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Location data
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Interests & preferences (stored as JSON array)
    interests = Column(JSON, default=list)  # e.g., ["nature", "culture", "food"]

    # Budget
    budget = Column(Float, nullable=True)
    currency = Column(String(3), default="EUR")

    # Cover image
    cover_image = Column(String(500), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign Keys
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="trips")
    places = relationship("Place", back_populates="trip", cascade="all, delete-orphan")
    place_lists = relationship("PlaceList", back_populates="trip", cascade="all, delete-orphan")
    diary_entries = relationship("DiaryEntry", back_populates="trip", cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="trip", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Trip {self.title} to {self.destination}>"
