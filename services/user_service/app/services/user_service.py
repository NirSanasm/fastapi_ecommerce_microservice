"""
User Service - Business Logic Layer

This is where you implement the core business logic for user management.
The service layer separates business logic from the routing layer.
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from shared.auth import hash_password


class UserService:
    """
    User service for handling user-related business logic.
    
    TODO: This is where you'll implement the core user management logic.
    Each method has placeholder implementation - extend as needed.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User's primary key ID
            
        Returns:
            User object or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User's email address
            
        Returns:
            User object or None if not found
        """
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """
        Get all users with optional filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            role: Optional filter by role
            is_active: Optional filter by active status
            
        Returns:
            List of User objects
        """
        query = select(User)
        
        if role:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created User object
            
        TODO: Add additional logic here:
        - Email uniqueness validation (done in router)
        - Password policy enforcement
        - Email verification token generation
        - Welcome email sending
        """
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create user
        user = User(
            email=user_data.email.lower(),
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            role=UserRole.CUSTOMER,
            is_active=True,
            is_verified=False,  # TODO: Set to True after email verification
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        
        return user
    
    async def update_user(self, user_id: int, update_data: UserUpdate) -> Optional[User]:
        """
        Update user profile.
        
        Args:
            user_id: User's ID
            update_data: Fields to update
            
        Returns:
            Updated User object or None if not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        # Update only provided fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(user, field, value)
        
        await self.db.flush()
        await self.db.refresh(user)
        
        return user
    
    async def update_password(self, user_id: int, new_password: str) -> bool:
        """
        Update user's password.
        
        Args:
            user_id: User's ID
            new_password: New plain text password
            
        Returns:
            True if successful, False if user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.hashed_password = hash_password(new_password)
        await self.db.flush()
        
        return True
    
    async def verify_email(self, user_id: int) -> bool:
        """
        Mark user's email as verified.
        
        Args:
            user_id: User's ID
            
        Returns:
            True if successful, False if user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_verified = True
        await self.db.flush()
        
        return True
    
    async def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate user account (soft delete).
        
        Args:
            user_id: User's ID
            
        Returns:
            True if successful, False if user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        await self.db.flush()
        
        return True
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Permanently delete user (hard delete).
        
        Args:
            user_id: User's ID
            
        Returns:
            True if successful, False if user not found
            
        TODO: Consider implications:
        - Associated orders
        - Associated reviews
        - Associated payment methods
        - GDPR compliance
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        await self.db.delete(user)
        await self.db.flush()
        
        return True
    
    async def change_role(self, user_id: int, new_role: UserRole) -> Optional[User]:
        """
        Change user's role.
        
        Args:
            user_id: User's ID
            new_role: New role to assign
            
        Returns:
            Updated User object or None if not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        user.role = new_role
        await self.db.flush()
        await self.db.refresh(user)
        
        return user
