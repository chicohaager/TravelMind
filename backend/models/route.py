"""
Route model - Connecting places to create itineraries
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Route visualization
    color = Column(String(7), default="#6366F1")  # Hex color for route line
    line_style = Column(String(20), default="solid")  # solid, dashed, dotted
    line_width = Column(Integer, default=3)  # Line thickness in pixels

    # Route data - array of place IDs in order
    place_ids = Column(JSON, default=list)  # [1, 3, 5, 2] - order of places in route

    # Route details
    total_distance = Column(Float, nullable=True)  # Total distance in km
    estimated_duration = Column(Integer, nullable=True)  # Estimated time in minutes
    transport_mode = Column(String(20), default="car")  # car, walk, bike, public_transport

    # Order (for multiple routes in same trip)
    order = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign Keys
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    trip = relationship("Trip", back_populates="routes")

    def __repr__(self):
        return f"<Route {self.name}>"
