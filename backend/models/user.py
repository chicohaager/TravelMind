"""
User model
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base
from passlib.context import CryptContext
import enum

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AIProvider(str, enum.Enum):
    """Supported AI providers"""
    GROQ = "GROQ"      # Default: Fast, free Llama models
    CLAUDE = "CLAUDE"
    OPENAI = "OPENAI"
    GEMINI = "GEMINI"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)

    # AI Configuration
    ai_provider = Column(Enum(AIProvider), default=AIProvider.GROQ, nullable=True)
    encrypted_api_key = Column(Text, nullable=True)  # Encrypted API key
    encryption_salt = Column(String(32), nullable=True)  # Unique salt for API key encryption

    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    password_changed_at = Column(DateTime(timezone=True), nullable=True)  # For token invalidation

    # Relationships
    trips = relationship("Trip", back_populates="owner", cascade="all, delete-orphan")
    diary_entries = relationship("DiaryEntry", back_populates="author", cascade="all, delete-orphan")

    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(password, self.hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    def __repr__(self):
        return f"<User {self.username}>"
