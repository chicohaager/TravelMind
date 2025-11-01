"""
Place model - Locations/POIs in a trip
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base


class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Location data
    address = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Category
    category = Column(String(50), nullable=True)  # e.g., "restaurant", "hotel", "sight", "activity"

    # Visit details
    visit_date = Column(DateTime, nullable=True)
    visited = Column(Boolean, default=False)

    # Additional data
    website = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    opening_hours = Column(JSON, nullable=True)

    # Cost/budget
    cost = Column(Float, nullable=True)
    currency = Column(String(3), default="EUR")

    # Rating & notes
    rating = Column(Integer, nullable=True)  # 1-5 stars
    notes = Column(Text, nullable=True)

    # Photos
    photos = Column(JSON, default=list)
    image_url = Column(String(1000), nullable=True)  # Main thumbnail image URL

    # Order in trip (for sorting)
    order = Column(Integer, default=0)

    # Map visualization
    color = Column(String(7), default="#6366F1")  # Hex color for pin
    icon_type = Column(String(50), default="location")  # Icon type: location, hotel, restaurant, coffee, museum, etc.

    # External data
    tags = Column(JSON, default=list)  # e.g., ["National park", "Nature & Parks", "Hiking"]
    external_links = Column(JSON, default=dict)  # Links to Google Maps, Tripadvisor, AllTrails, etc.
    google_place_id = Column(String(200), nullable=True)  # Google Places ID for caching
    external_rating = Column(Float, nullable=True)  # External rating (e.g., from Google)
    review_count = Column(Integer, nullable=True)  # Number of reviews

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign Keys
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    list_id = Column(Integer, ForeignKey("place_lists.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    trip = relationship("Trip", back_populates="places")
    place_list = relationship("PlaceList", back_populates="places")

    def __repr__(self):
        return f"<Place {self.name}>"
