"""
PlaceList model - Custom categorization lists for places
"""

from models.database import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


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
    # KEINE delete-orphan-Kaskade.
    #
    # Die Spalte `places.list_id` traegt `ON DELETE SET NULL`, und der
    # Loeschendpunkt verliess sich darauf. Die ORM-Kaskade kommt der Datenbank
    # aber ZUVOR: `db.delete(liste)` laedt die Kinder und setzt ein
    # `DELETE FROM places` ab — die Fremdschluesselregel kam nie zum Zug.
    # Folge bis 2026-08-25: das Loeschen einer Liste loeschte alle Orte darin,
    # waehrend der Bestaetigungsdialog woertlich versprach "Orte werden nicht
    # geloescht". `passive_deletes=True` haelt die ORM davon ab, die Kinder
    # ueberhaupt anzufassen.
    places = relationship("Place", back_populates="place_list", passive_deletes=True)

    def __repr__(self):
        return f"<PlaceList {self.title}>"
