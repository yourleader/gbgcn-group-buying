"""
Authentication router for Group Buying API
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from src.database.connection import get_db
from src.database.models import User
from src.core.auth import (
    authenticate_user, 
    create_access_token, 
    create_refresh_token,
    get_password_hash,
    get_current_user,
    verify_token
)
from src.core.config import settings

router = APIRouter()

# Pydantic models for requests/responses
class UserCreate(BaseModel):
    """User registration request"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)

class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    username: str
    first_name: str
    last_name: str
    phone: Optional[str]
    avatar_url: Optional[str]
    is_verified: bool
    role: str
    reputation_score: float
    total_groups_created: int
    total_groups_joined: int
    success_rate: float
    
    class Config:
        from_attributes = True

class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user for the Group Buying system
    
    Creates a new user account with hashed password and default settings
    for GBGCN recommendations
    """
    # Check if user already exists
    from sqlalchemy import select
    
    # Check email
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check username
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        is_verified=False,  # Email verification can be added later
        is_active=True,
        role="USER"
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens
    
    Returns access and refresh tokens for authenticated requests
    """
    # Authenticate user
    user = await authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.id, "type": "refresh"}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/login/oauth", response_model=TokenResponse)
async def oauth_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible login endpoint
    
    Compatible with OAuth2PasswordRequestForm for automatic API docs integration
    """
    # Authenticate user
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.id, "type": "refresh"}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Allows users to get new access tokens without re-authenticating
    """
    # Verify refresh token
    payload = verify_token(token_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user from database
    from src.core.auth import get_user_by_id
    user = await get_user_by_id(db, user_id)
    if not user or not bool(user.is_active):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.id, "type": "refresh"}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information
    
    Returns user profile data for the authenticated user
    """
    return current_user

@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_user)
):
    """
    Logout user (token invalidation would be implemented with Redis blacklist)
    
    For now, this is a placeholder. In production, you would:
    1. Add token to blacklist in Redis
    2. Clear client-side tokens
    """
    return {"message": "Successfully logged out"}

@router.post("/verify-token")
async def verify_access_token(
    current_user: User = Depends(get_current_user)
):
    """
    Verify if the current access token is valid
    
    Returns user info if token is valid, otherwise raises 401
    """
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
            "role": current_user.role
        }
    } 