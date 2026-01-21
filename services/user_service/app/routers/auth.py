"""
Authentication Router - Login, Register, Token Refresh
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    PasswordReset,
    PasswordResetConfirm,
)
from app.services.user_service import UserService
from app.config import settings

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
)
from shared.schemas import ResponseModel


router = APIRouter()


@router.post("/register", response_model=ResponseModel[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.
    
    - **email**: Unique email address
    - **password**: Minimum 8 characters
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **phone**: Optional phone number
    """
    user_service = UserService(db)
    
    # Check if user already exists
    existing_user = await user_service.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create user
    user = await user_service.create_user(user_data)
    
    # TODO: Send verification email
    # await send_verification_email(user.email, verification_token)
    
    return ResponseModel(
        success=True,
        message="User registered successfully. Please verify your email.",
        data=user,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return access/refresh tokens.
    
    - **email**: User's email address
    - **password**: User's password
    """
    user_service = UserService(db)
    
    # Get user by email
    user = await user_service.get_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
    
    access_token = create_access_token(
        subject=str(user.id),
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=access_token_expires,
        roles=[user.role.value],
    )
    
    refresh_token = create_refresh_token(
        subject=str(user.id),
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=refresh_token_expires,
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    """
    try:
        # Verify refresh token
        token_payload = verify_token(
            token_data.refresh_token,
            settings.jwt_secret_key,
            settings.jwt_algorithm,
            verify_type="refresh",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    # Get user
    user_service = UserService(db)
    user = await user_service.get_by_id(int(token_payload.user_id))
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Create new tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
    
    access_token = create_access_token(
        subject=str(user.id),
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=access_token_expires,
        roles=[user.role.value],
    )
    
    new_refresh_token = create_refresh_token(
        subject=str(user.id),
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=refresh_token_expires,
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/forgot-password", response_model=ResponseModel)
async def forgot_password(
    data: PasswordReset,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset email.
    
    - **email**: User's email address
    """
    user_service = UserService(db)
    user = await user_service.get_by_email(data.email)
    
    # Always return success to prevent email enumeration
    if user:
        # TODO: Generate password reset token and send email
        # reset_token = generate_reset_token(user.id)
        # await send_password_reset_email(user.email, reset_token)
        pass
    
    return ResponseModel(
        success=True,
        message="If the email exists, a password reset link has been sent.",
    )


@router.post("/reset-password", response_model=ResponseModel)
async def reset_password(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using reset token.
    
    - **token**: Password reset token from email
    - **new_password**: New password (min 8 characters)
    """
    # TODO: Implement password reset logic
    # 1. Verify reset token
    # 2. Get user from token
    # 3. Update password
    # 4. Invalidate all existing tokens
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset not yet implemented. TODO: Add your logic here.",
    )


@router.post("/verify-email/{token}", response_model=ResponseModel)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify user email with verification token.
    
    - **token**: Email verification token
    """
    # TODO: Implement email verification logic
    # 1. Verify token
    # 2. Get user from token
    # 3. Set is_verified = True
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Email verification not yet implemented. TODO: Add your logic here.",
    )
