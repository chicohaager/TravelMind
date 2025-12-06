"""
Authentication Router
User authentication and authorization with JWT
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
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
from services.audit_service import audit_service
from utils.rate_limits import limiter, RateLimits

load_dotenv()

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


# Pydantic Models
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, example="johndoe")
    email: EmailStr = Field(..., example="john@example.com")
    password: str = Field(..., min_length=8, example="securepassword123")
    full_name: Optional[str] = Field(None, example="John Doe")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "securepassword123",
                "full_name": "John Doe"
            }
        }


class UserLogin(BaseModel):
    username: str = Field(..., example="johndoe")
    password: str = Field(..., example="securepassword123")


class Token(BaseModel):
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(default="bearer", example="bearer")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huZG9lIiwiZXhwIjoxNzA3MDAwMDAwfQ.signature",
                "token_type": "bearer"
            }
        }


class TokenData(BaseModel):
    username: Optional[str] = Field(None, example="johndoe")


class UserResponse(BaseModel):
    id: int = Field(..., example=1)
    username: str = Field(..., example="johndoe")
    email: str = Field(..., example="john@example.com")
    full_name: Optional[str] = Field(None, example="John Doe")
    avatar_url: Optional[str] = Field(None, example="/uploads/avatars/user_1_abc123.jpg")
    bio: Optional[str] = Field(None, example="Travel enthusiast and photographer")
    is_active: bool = Field(..., example=True)
    is_superuser: bool = Field(..., example=False)
    created_at: datetime = Field(..., example="2025-01-15T10:30:00Z")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "johndoe",
                "email": "john@example.com",
                "full_name": "John Doe",
                "avatar_url": "/uploads/avatars/user_1_abc123.jpg",
                "bio": "Travel enthusiast and photographer",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


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
@limiter.limit(RateLimits.AUTH_REGISTER)
async def register(
    request: Request,
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
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

    # Audit log: user registration
    await audit_service.log_auth_event(
        db=db,
        event="register",
        user_id=new_user.id,
        username=new_user.username,
        request=request,
        details={"email": new_user.email}
    )

    # Generate access token
    access_token = create_access_token(data={"sub": new_user.username})

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
@limiter.limit(RateLimits.AUTH_LOGIN)
async def login(
    request: Request,
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
        # Audit log: failed login attempt
        await audit_service.log_auth_event(
            db=db,
            event="login_failed",
            username=form_data.username,
            request=request,
            status="failure",
            details={"reason": "invalid_credentials"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        # Audit log: inactive user login attempt
        await audit_service.log_auth_event(
            db=db,
            event="login_failed",
            user_id=user.id,
            username=user.username,
            request=request,
            status="failure",
            details={"reason": "user_inactive"}
        )
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )

    # Audit log: successful login
    await audit_service.log_auth_event(
        db=db,
        event="login",
        user_id=user.id,
        username=user.username,
        request=request
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
@limiter.limit(RateLimits.AUTH_REFRESH)
async def refresh_token(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Refresh access token

    Generates a new access token from a valid existing token.
    """
    access_token = create_access_token(data={"sub": current_user.username})
    return {"access_token": access_token, "token_type": "bearer"}
