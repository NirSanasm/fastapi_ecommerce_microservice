"""
Users Router - Profile management and CRUD operations
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserResponse, UserUpdate, PasswordChange
from app.services.user_service import UserService
from app.config import settings

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.auth import verify_token, TokenData, verify_password, hash_password
from shared.schemas import ResponseModel, PaginationParams


router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> TokenData:
    """
    Dependency to get and validate current user from JWT token.
    """
    try:
        token_data = verify_token(
            credentials.credentials,
            settings.jwt_secret_key,
            settings.jwt_algorithm,
            verify_type="access",
        )
        return token_data
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Dependency to require admin role."""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get("/me", response_model=ResponseModel[UserResponse])
async def get_current_user_profile(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current authenticated user's profile.
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(int(current_user.user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return ResponseModel(
        success=True,
        message="User profile retrieved",
        data=user,
    )


@router.put("/me", response_model=ResponseModel[UserResponse])
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current authenticated user's profile.
    
    - **first_name**: Optional new first name
    - **last_name**: Optional new last name
    - **phone**: Optional new phone number
    """
    user_service = UserService(db)
    user = await user_service.update_user(int(current_user.user_id), update_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return ResponseModel(
        success=True,
        message="Profile updated successfully",
        data=user,
    )


@router.post("/me/change-password", response_model=ResponseModel)
async def change_password(
    password_data: PasswordChange,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user's password.
    
    - **current_password**: Current password for verification
    - **new_password**: New password (min 8 characters)
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(int(current_user.user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Verify current password
    if not verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    # Update password
    await user_service.update_password(user.id, password_data.new_password)
    
    return ResponseModel(
        success=True,
        message="Password changed successfully",
    )


@router.delete("/me", response_model=ResponseModel)
async def delete_current_user(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete current user's account (soft delete by deactivating).
    """
    user_service = UserService(db)
    await user_service.deactivate_user(int(current_user.user_id))
    
    return ResponseModel(
        success=True,
        message="Account deleted successfully",
    )


# Admin-only endpoints

@router.get("/", response_model=ResponseModel[List[UserResponse]])
async def list_users(
    pagination: PaginationParams = Depends(),
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users (admin only).
    
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 10, max: 100)
    """
    user_service = UserService(db)
    users = await user_service.get_all(skip=pagination.skip, limit=pagination.limit)
    
    return ResponseModel(
        success=True,
        message=f"Retrieved {len(users)} users",
        data=users,
    )


@router.get("/{user_id}", response_model=ResponseModel[UserResponse])
async def get_user(
    user_id: int,
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user by ID (admin only).
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return ResponseModel(
        success=True,
        data=user,
    )


@router.delete("/{user_id}", response_model=ResponseModel)
async def delete_user(
    user_id: int,
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete user by ID (admin only).
    """
    user_service = UserService(db)
    success = await user_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return ResponseModel(
        success=True,
        message="User deleted successfully",
    )
