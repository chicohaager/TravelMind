"""
Authentication Router
User authentication and authorization with JWT
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import os
from dotenv import load_dotenv

from models.database import get_db
from models.user import User

load_dotenv()

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


# Pydantic Models
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Helper Functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user from JWT token"""
    if not token:
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user is active"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Optional: For endpoints that don't require auth but benefit from it
async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if token is provided, None otherwise"""
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


# Endpoints
@router.get("/registration-status")
async def get_registration_status(db: AsyncSession = Depends(get_db)):
    """
    Check if registration is currently allowed
    Public endpoint - no authentication required
    """
    from utils.settings_manager import can_register_new_user, get_setting

    can_register, reason = await can_register_new_user(db)
    app_name = await get_setting(db, "app_name", "TravelMind")

    return {
        "registration_open": can_register,
        "message": reason if not can_register else "Registrierung ist geöffnet",
        "app_name": app_name
    }


@router.post("/register", response_model=Token, status_code=201)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Register a new user

    Creates a new user account and returns an authentication token.
    """
    # Check if registration is allowed
    from utils.settings_manager import can_register_new_user

    can_register, reason = await can_register_new_user(db)
    if not can_register:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )

    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=User.hash_password(user_data.password),
        full_name=user_data.full_name,
        is_active=True
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate access token
    access_token = create_access_token(data={"sub": new_user.username})

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login with username and password

    Returns a JWT access token on successful authentication.
    """
    # Find user by username
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    # Verify credentials
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )

    # Generate access token
    access_token = create_access_token(data={"sub": user.username})

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout():
    """
    Logout (invalidate token)

    In a stateless JWT system, this is handled client-side by removing the token.
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information

    Returns profile information of the authenticated user.
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_active_user)):
    """
    Refresh access token

    Generates a new access token from a valid existing token.
    """
    access_token = create_access_token(data={"sub": current_user.username})
    return {"access_token": access_token, "token_type": "bearer"}
