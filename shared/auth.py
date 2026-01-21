"""
Authentication utilities for JWT tokens and password hashing.
Used by all microservices that require authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel


# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload(BaseModel):
    """JWT Token payload schema."""
    sub: str  # Subject (usually user ID)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    type: str  # Token type: "access" or "refresh"
    roles: list[str] = []  # User roles


class TokenData(BaseModel):
    """Extracted token data after verification."""
    user_id: str
    roles: list[str] = []
    token_type: str


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hash to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None,
    roles: list[str] = None,
    extra_claims: dict[str, Any] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: Token subject (usually user ID)
        secret_key: Secret key for encoding
        algorithm: JWT algorithm (default: HS256)
        expires_delta: Token expiration time delta
        roles: User roles to include in token
        extra_claims: Additional claims to include
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=30)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    to_encode = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access",
        "roles": roles or [],
    }
    
    if extra_claims:
        to_encode.update(extra_claims)
    
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def create_refresh_token(
    subject: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: Token subject (usually user ID)
        secret_key: Secret key for encoding
        algorithm: JWT algorithm (default: HS256)
        expires_delta: Token expiration time delta
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta is None:
        expires_delta = timedelta(days=7)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    to_encode = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }
    
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def verify_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
    verify_type: Optional[str] = None,
) -> TokenData:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        secret_key: Secret key for decoding
        algorithm: JWT algorithm (default: HS256)
        verify_type: Expected token type ("access" or "refresh")
        
    Returns:
        TokenData with extracted user information
        
    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid
        ValueError: If token type doesn't match expected type
    """
    payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    
    token_type = payload.get("type", "access")
    
    if verify_type and token_type != verify_type:
        raise ValueError(f"Expected {verify_type} token, got {token_type}")
    
    return TokenData(
        user_id=payload["sub"],
        roles=payload.get("roles", []),
        token_type=token_type,
    )


# FastAPI dependency for getting current user
# This is a template - each service should implement its own version
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    try:
        token_data = verify_token(
            credentials.credentials,
            settings.jwt_secret_key,
            settings.jwt_algorithm,
            verify_type="access",
        )
        return token_data
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

def require_roles(required_roles: list[str]):
    async def role_checker(current_user: TokenData = Depends(get_current_user)):
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return role_checker
"""
