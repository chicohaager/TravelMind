"""
Global Settings Model
Stores application-wide configuration
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from models.database import Base


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=True)
    value_type = Column(String(20), default="string")  # string, boolean, integer, json
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Settings {self.key}={self.value}>"

    def get_typed_value(self):
        """Convert value to appropriate type"""
        if self.value is None:
            return None

        if self.value_type == "boolean":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "integer":
            return int(self.value)
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        else:
            return self.value
