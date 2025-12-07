"""
Password Reset Router

Secure password reset flow with token-based verification.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import os
import secrets
import structlog

from models.database import get_db
from models.user import User
from services.audit_service import audit_service
from utils.rate_limits import limiter, RateLimits

router = APIRouter()
logger = structlog.get_logger(__name__)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production")
ALGORITHM = "HS256"
RESET_TOKEN_EXPIRE_MINUTES = 60  # 1 hour


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    new_password: str = Field(..., min_length=8, example="newSecurePassword123")


class PasswordResetResponse(BaseModel):
    message: str
    email_sent: bool = False
    expires_in_minutes: Optional[int] = None


def create_reset_token(email: str, user_id: int) -> str:
    """
    Create a secure password reset token.

    The token contains:
    - User email
    - User ID
    - Expiration time
    - Random nonce for uniqueness
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    nonce = secrets.token_hex(16)

    to_encode = {
        "sub": email,
        "user_id": user_id,
        "exp": expire,
        "type": "password_reset",
        "nonce": nonce
    }

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_reset_token(token: str, password_changed_at: datetime = None) -> dict:
    """
    Verify and decode a password reset token.

    Returns the token payload if valid.
    Raises HTTPException if invalid, expired, or already used.

    Args:
        token: The JWT reset token
        password_changed_at: User's password_changed_at timestamp (for invalidation check)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=400,
                detail="Invalid token type"
            )

        # Check if token was issued before password was changed (token already used)
        if password_changed_at:
            token_issued_at = datetime.fromtimestamp(
                payload.get("exp") - (RESET_TOKEN_EXPIRE_MINUTES * 60),
                tz=timezone.utc
            )
            if token_issued_at < password_changed_at:
                logger.warning("password_reset_token_already_used", token_issued=token_issued_at, password_changed=password_changed_at)
                raise HTTPException(
                    status_code=400,
                    detail="Reset token has already been used"
                )

        return payload

    except JWTError as e:
        logger.warning("password_reset_token_invalid", error=str(e))
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )


async def send_reset_email(email: str, reset_token: str, username: str):
    """
    Send password reset email.

    In production, this should use a proper email service.
    Currently logs the reset link for development.
    """
    # Build reset URL
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    reset_url = f"{frontend_url}/reset-password?token={reset_token}"

    # In production, send actual email
    smtp_host = os.getenv("SMTP_HOST")

    if smtp_host:
        # TODO: Implement actual email sending
        # For now, we'll just log that we would send an email
        logger.info(
            "password_reset_email_would_send",
            email=email,
            username=username
        )
    else:
        # Development mode - log the reset link
        logger.info(
            "password_reset_link_generated",
            email=email,
            username=username,
            reset_url=reset_url
        )
        print(f"\n{'='*60}")
        print(f"PASSWORD RESET LINK (Development Mode)")
        print(f"{'='*60}")
        print(f"User: {username} ({email})")
        print(f"Reset URL: {reset_url}")
        print(f"Expires in: {RESET_TOKEN_EXPIRE_MINUTES} minutes")
        print(f"{'='*60}\n")


@router.post("/forgot-password", response_model=PasswordResetResponse)
@limiter.limit("5/hour")
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Request a password reset.

    Sends a password reset link to the user's email address.

    **Rate limited to 5 requests per hour per IP.**

    Note: For security, this endpoint always returns success
    even if the email doesn't exist in the system.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == reset_request.email)
    )
    user = result.scalar_one_or_none()

    if user:
        # Generate reset token
        reset_token = create_reset_token(user.email, user.id)

        # Send email in background
        background_tasks.add_task(
            send_reset_email,
            user.email,
            reset_token,
            user.username
        )

        # Audit log
        await audit_service.log_auth_event(
            db=db,
            event="password_reset_requested",
            user_id=user.id,
            username=user.username,
            request=request,
            details={"email": user.email}
        )

        logger.info("password_reset_requested", user_id=user.id, email=user.email)
    else:
        # Log attempt but don't reveal if email exists
        logger.info("password_reset_requested_unknown_email", email=reset_request.email)

    # Always return success for security (don't reveal if email exists)
    return PasswordResetResponse(
        message="If an account with this email exists, a password reset link has been sent.",
        email_sent=True,
        expires_in_minutes=RESET_TOKEN_EXPIRE_MINUTES
    )


@router.post("/reset-password", response_model=PasswordResetResponse)
@limiter.limit("10/hour")
async def confirm_password_reset(
    request: Request,
    reset_confirm: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm password reset with token.

    Verifies the reset token and updates the user's password.
    Token is invalidated after successful use via password_changed_at timestamp.

    **Rate limited to 10 requests per hour per IP.**
    """
    # First decode token to get user_id (basic validation)
    try:
        payload = jwt.decode(reset_confirm.token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if payload.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid token type")

    user_id = payload.get("user_id")
    email = payload.get("sub")

    # Find user
    result = await db.execute(
        select(User).where(User.id == user_id, User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid reset token"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="User account is disabled"
        )

    # Verify token with password_changed_at check (prevents token reuse)
    verify_reset_token(reset_confirm.token, user.password_changed_at)

    # Update password and set password_changed_at to invalidate all existing reset tokens
    now = datetime.now(timezone.utc)
    user.hashed_password = User.hash_password(reset_confirm.new_password)
    user.password_changed_at = now
    user.updated_at = now

    await db.commit()

    # Audit log
    await audit_service.log_auth_event(
        db=db,
        event="password_reset_completed",
        user_id=user.id,
        username=user.username,
        request=request
    )

    logger.info("password_reset_completed", user_id=user.id)

    return PasswordResetResponse(
        message="Password has been successfully reset. You can now login with your new password.",
        email_sent=False
    )


@router.get("/verify-reset-token")
@limiter.limit("30/minute")
async def verify_token_validity(
    request: Request,
    token: str
):
    """
    Verify if a reset token is still valid.

    Use this to check token validity before showing the reset form.
    """
    try:
        payload = verify_reset_token(token)

        # Calculate remaining time
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        remaining = exp - datetime.now(timezone.utc)
        remaining_minutes = max(0, int(remaining.total_seconds() / 60))

        return {
            "valid": True,
            "expires_in_minutes": remaining_minutes,
            "email": payload.get("sub", "")[:3] + "***"  # Partially hide email
        }

    except HTTPException:
        return {
            "valid": False,
            "expires_in_minutes": 0,
            "email": None
        }
