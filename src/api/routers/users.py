"""
Users router for Group Buying API
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import uuid
from datetime import datetime

from src.database.connection import get_db
from src.database.models import User, Group, GroupMember, UserItemInteraction, SocialConnection
from src.core.auth import get_current_user, admin_required, moderator_required
from src.core.config import settings

router = APIRouter()

# Pydantic models
class UserUpdate(BaseModel):
    """User profile update request"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)

class UserProfile(BaseModel):
    """Complete user profile response"""
    id: str
    email: str
    username: str
    first_name: str
    last_name: str
    phone: Optional[str]
    bio: Optional[str]
    location: Optional[str]
    avatar_url: Optional[str]
    is_verified: bool
    role: str
    reputation_score: float
    total_groups_created: int
    total_groups_joined: int
    success_rate: float
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class UserStats(BaseModel):
    """User statistics for GBGCN analytics"""
    user_id: str
    total_interactions: int
    successful_purchases: int
    groups_created: int
    groups_joined: int
    friends_count: int
    avg_group_size: float
    preferred_categories: List[str]
    social_influence_score: float
    recent_activity_count: int

class UserSearch(BaseModel):
    """User search/discovery response"""
    id: str
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str]
    reputation_score: float
    mutual_friends: int
    common_interests: List[str]

@router.get("/profile/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user profile by ID
    
    Returns detailed user profile information including GBGCN statistics
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user can view this profile (privacy settings could be added)
    if user.id != current_user.id and not bool(user.is_active):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.get("/me/profile", response_model=UserProfile)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's own profile
    
    Returns the authenticated user's complete profile
    """
    return current_user

@router.put("/me/profile", response_model=UserProfile)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile
    
    Allows users to update their profile information for better GBGCN recommendations
    """
    # Check if username is taken (if being updated)
    if user_update.username and user_update.username != current_user.username:
        result = await db.execute(
            select(User).where(
                and_(User.username == user_update.username, User.id != current_user.id)
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user

@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload user avatar image
    
    Accepts image files and returns the URL for the uploaded avatar
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Validate file size (5MB limit)
    max_size = 5 * 1024 * 1024  # 5MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size too large. Maximum 5MB allowed."
        )
    
    # In production, save to cloud storage (AWS S3, etc.)
    # For now, return a placeholder URL
    file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
    avatar_filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{file_extension}"
    avatar_url = f"{settings.BASE_URL}/static/avatars/{avatar_filename}"
    
    # Update user avatar URL
    setattr(current_user, 'avatar_url', avatar_url)
    await db.commit()
    
    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url
    }

@router.get("/me/stats", response_model=UserStats)
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's statistics for GBGCN analytics
    
    Returns comprehensive statistics used by the GBGCN model for recommendations
    """
    user_id = str(current_user.id)
    
    # Get interaction stats
    interactions_result = await db.execute(
        select(func.count(UserItemInteraction.id))
        .where(UserItemInteraction.user_id == user_id)
    )
    total_interactions = interactions_result.scalar() or 0
    
    # Get successful purchases
    purchases_result = await db.execute(
        select(func.count(UserItemInteraction.id))
        .where(and_(
            UserItemInteraction.user_id == user_id,
            UserItemInteraction.interaction_type == "PURCHASE"
        ))
    )
    successful_purchases = purchases_result.scalar() or 0
    
    # Get groups created
    created_groups_result = await db.execute(
        select(func.count(Group.id))
        .where(Group.initiator_id == user_id)
    )
    groups_created = created_groups_result.scalar() or 0
    
    # Get groups joined
    joined_groups_result = await db.execute(
        select(func.count(GroupMember.id))
        .where(GroupMember.user_id == user_id)
    )
    groups_joined = joined_groups_result.scalar() or 0
    
    # Get friends count
    friends_result = await db.execute(
        select(func.count(SocialConnection.id))
        .where(and_(
            SocialConnection.user_id == user_id,
            SocialConnection.connection_type == "FRIEND"
        ))
    )
    friends_count = friends_result.scalar() or 0
    
    # Calculate average group size (for groups user created)
    avg_size_result = await db.execute(
        select(func.avg(Group.current_members))
        .where(Group.initiator_id == user_id)
    )
    avg_group_size = float(avg_size_result.scalar() or 0)
    
    # Get preferred categories (simplified - would be more complex in production)
    categories_result = await db.execute(
        select(UserItemInteraction.item_id, func.count())
        .where(UserItemInteraction.user_id == user_id)
        .group_by(UserItemInteraction.item_id)
        .order_by(func.count().desc())
        .limit(5)
    )
    preferred_categories = ["electronics", "fashion", "home"]  # Placeholder
    
    # Calculate social influence score (simplified)
    social_influence_score = min(float(current_user.reputation_score or 0) * 0.1, 1.0)
    
    # Recent activity count (last 30 days)
    from datetime import datetime, timedelta
    recent_date = datetime.utcnow() - timedelta(days=30)
    recent_activity_result = await db.execute(
        select(func.count(UserItemInteraction.id))
        .where(and_(
            UserItemInteraction.user_id == user_id,
            UserItemInteraction.created_at >= recent_date
        ))
    )
    recent_activity_count = recent_activity_result.scalar() or 0
    
    return UserStats(
        user_id=user_id,
        total_interactions=total_interactions,
        successful_purchases=successful_purchases,
        groups_created=groups_created,
        groups_joined=groups_joined,
        friends_count=friends_count,
        avg_group_size=avg_group_size,
        preferred_categories=preferred_categories,
        social_influence_score=social_influence_score,
        recent_activity_count=recent_activity_count
    )

@router.get("/search", response_model=List[UserSearch])
async def search_users(
    q: str = Query(..., description="Search query for username or name"),
    limit: int = Query(20, le=50, description="Maximum number of results"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for users by username or name
    
    Returns users matching the search query with social context
    """
    # Search users by username, first name, or last name
    search_pattern = f"%{q}%"
    
    result = await db.execute(
        select(User)
        .where(and_(
            User.is_active == True,
            or_(
                User.username.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                func.concat(User.first_name, ' ', User.last_name).ilike(search_pattern)
            )
        ))
        .order_by(User.reputation_score.desc())
        .limit(limit)
    )
    
    users = result.scalars().all()
    
    # Format response with social context
    user_searches = []
    for user in users:
        if str(user.id) == str(current_user.id):
            continue  # Skip current user
            
        # Calculate mutual friends (simplified)
        mutual_friends = 0  # Would implement proper calculation
        
        # Get common interests (simplified)
        common_interests = ["electronics", "books"]  # Placeholder
        
        user_searches.append(UserSearch(
            id=str(user.id),
            username=str(user.username),
            first_name=str(user.first_name),
            last_name=str(user.last_name),
            avatar_url=str(user.avatar_url) if user.avatar_url else None,
            reputation_score=float(user.reputation_score or 0),
            mutual_friends=mutual_friends,
            common_interests=common_interests
        ))
    
    return user_searches

@router.get("/leaderboard", response_model=List[UserSearch])
async def get_user_leaderboard(
    limit: int = Query(10, le=50, description="Number of top users to return"),
    period: str = Query("all", pattern="^(week|month|all)$", description="Time period for ranking"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user leaderboard based on reputation and activity
    
    Returns top users for gamification and social features
    """
    # Get top users by reputation score
    result = await db.execute(
        select(User)
        .where(User.is_active == True)
        .order_by(User.reputation_score.desc(), User.success_rate.desc())
        .limit(limit)
    )
    
    users = result.scalars().all()
    
    leaderboard = []
    for user in users:
        leaderboard.append(UserSearch(
            id=str(user.id),
            username=str(user.username),
            first_name=str(user.first_name),
            last_name=str(user.last_name),
            avatar_url=str(user.avatar_url) if user.avatar_url else None,
            reputation_score=float(user.reputation_score or 0),
            mutual_friends=0,  # Not relevant for leaderboard
            common_interests=[]
        ))
    
    return leaderboard

@router.get("/", response_model=List[UserProfile])
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, le=100, description="Page size"),
    admin_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users (Admin only)
    
    Returns paginated list of all users for administration
    """
    offset = (page - 1) * size
    
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    
    users = result.scalars().all()
    return users

@router.put("/{user_id}/activate")
async def activate_user(
    user_id: str,
    admin_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Activate/deactivate user account (Admin only)
    
    Allows administrators to manage user account status
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    setattr(user, 'is_active', not bool(user.is_active))
    await db.commit()
    
    return {
        "message": f"User {'activated' if bool(user.is_active) else 'deactivated'} successfully",
        "user_id": user_id,
        "is_active": bool(user.is_active)
    } 