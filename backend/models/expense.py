"""
Expense/Budget model
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from models.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)

    # Expense details
    title = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="EUR")
    category = Column(String(50), default="other")  # food, transport, accommodation, etc.
    date = Column(Date, nullable=False)

    # Who paid (foreign key to participants table)
    paid_by = Column(Integer, ForeignKey("participants.id", ondelete="SET NULL"), nullable=True)

    # Additional info
    notes = Column(Text, nullable=True)
    receipt_url = Column(String(500), nullable=True)

    # Cost splitting (JSON array of {participant_id: amount})
    splits = Column(JSON, default=list)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    trip = relationship("Trip", backref="expenses")

    def __repr__(self):
        return f"<Expense {self.title}: {self.amount} {self.currency}>"
