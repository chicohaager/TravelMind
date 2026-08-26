"""
Place model - Locations/POIs in a trip
"""

from models.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Location data
    address = Column(String(500), nullable=True)
    # NULL bedeutet "Position unbekannt".
    #
    # Bis 2026-08-26 waren diese Spalten NOT NULL. "Unbekannt" liess sich
    # dadurch gar nicht ausdruecken, und fehlgeschlagene Geokodierungen
    # landeten als 0.0/0.0 in der Datenbank — der Null-Insel im Golf von
    # Guinea. Auf der Karte sah das aus wie ein gueltiger Ort im Atlantik,
    # nicht wie ein fehlender Wert. Siehe utils/geocoding.py.
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    # NULL = ungeprueft, True = nur ortsgenau (Gemeindemittelpunkt),
    # False = objektgenau. Am 2026-08-26 gemessen: 9 von 16 Positionen einer
    # echten Reise waren Gemeindemittelpunkte und auf der Karte nicht von
    # einem echten Fund zu unterscheiden. Siehe utils/geocoding.py.
    position_nur_ort = Column(Boolean, nullable=True)

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
    media = relationship(
        "Media",
        back_populates="place",
        cascade="all, delete-orphan",
        order_by="Media.order_index",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Place {self.name}>"
