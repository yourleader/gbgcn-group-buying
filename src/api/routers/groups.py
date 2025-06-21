"""
Groups router for Group Buying API - Core GBGCN functionality
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum

from src.database.connection import get_db
from src.database.models import Group, GroupMember, User, Item, GroupStatus, MemberStatus
from src.core.auth import get_current_user
from src.core.config import settings

router = APIRouter()

# Pydantic models
class GroupCreateRequest(BaseModel):
    """Create group request"""
    item_id: str
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=1000)
    target_size: int = Field(..., ge=settings.MIN_GROUP_SIZE, le=settings.MAX_GROUP_SIZE)
    min_size: int = Field(..., ge=settings.MIN_GROUP_SIZE)
    target_price: float = Field(..., gt=0)
    duration_days: int = Field(default=7, ge=1, le=30)
    is_public: bool = True
    location: Optional[str] = Field(None, max_length=200)
    tags: List[str] = Field(default=[], max_items=10)

class GroupUpdate(BaseModel):
    """Update group request"""
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    target_size: Optional[int] = Field(None, ge=settings.MIN_GROUP_SIZE, le=settings.MAX_GROUP_SIZE)
    min_size: Optional[int] = Field(None, ge=settings.MIN_GROUP_SIZE)
    target_price: Optional[float] = Field(None, gt=0)
    duration_days: Optional[int] = Field(None, ge=1, le=30)
    is_public: Optional[bool] = None
    location: Optional[str] = Field(None, max_length=200)
    tags: Optional[List[str]] = Field(None, max_items=10)

class GroupResponse(BaseModel):
    """Group response model"""
    id: str
    title: str
    description: str
    item_id: str
    initiator_id: str
    initiator_username: str
    current_members: int
    target_size: int
    min_size: int
    target_price: float
    current_discount: float
    status: str
    success_probability: float
    deadline: datetime
    is_public: bool
    location: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GroupMemberResponse(BaseModel):
    """Group member response"""
    user_id: str
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str]
    status: str
    joined_at: datetime
    reputation_score: float
    social_influence: float

class GroupAnalytics(BaseModel):
    """Group analytics for GBGCN"""
    group_id: str
    formation_time_minutes: Optional[int]
    member_diversity_score: float
    social_connectivity_score: float
    price_sensitivity_avg: float
    success_prediction: float
    optimal_member_suggestions: List[str]
    risk_factors: List[str]

class JoinGroupRequest(BaseModel):
    """Join group request"""
    message: Optional[str] = Field(None, max_length=500)

@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: GroupCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new group buying group
    
    Initiates a group buying session with GBGCN optimization parameters
    """
    # Validate min_size <= target_size
    if group_data.min_size > group_data.target_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum size cannot be greater than target size"
        )
    
    # Check if item exists (would implement item validation here)
    # For now, assume item_id is valid
    
    # Calculate deadline
    deadline = datetime.utcnow() + timedelta(days=group_data.duration_days)
    
    # Create group
    new_group = Group(
        title=group_data.title,
        description=group_data.description,
        item_id=group_data.item_id,
        initiator_id=str(current_user.id),
        current_members=1,  # Initiator is automatically a member
        target_size=group_data.target_size,
        min_size=group_data.min_size,
        target_price=group_data.target_price,
        current_discount=0.0,  # Will be calculated based on current_members
        status=GroupStatus.FORMING,
        success_probability=0.5,  # Initial estimate, will be updated by GBGCN
        deadline=deadline,
        is_public=group_data.is_public,
        location=group_data.location,
        tags=group_data.tags or []
    )
    
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)
    
    # Add initiator as first member
    member = GroupMember(
        group_id=str(new_group.id),
        user_id=str(current_user.id),
        status=MemberStatus.ACTIVE,
        role="INITIATOR"
    )
    
    db.add(member)
    await db.commit()
    
    # Create response
    response = GroupResponse(
        id=str(new_group.id),
        title=new_group.title,
        description=new_group.description,
        item_id=str(new_group.item_id),
        initiator_id=str(new_group.initiator_id),
        initiator_username=str(current_user.username),
        current_members=new_group.current_members,
        target_size=new_group.target_size,
        min_size=new_group.min_size,
        target_price=float(new_group.target_price),
        current_discount=float(new_group.current_discount),
        status=str(new_group.status),
        success_probability=float(new_group.success_probability),
        deadline=new_group.deadline,
        is_public=bool(new_group.is_public),
        location=str(new_group.location) if new_group.location else None,
        tags=new_group.tags or [],
        created_at=new_group.created_at,
        updated_at=new_group.updated_at
    )
    
    return response

@router.get("/", response_model=List[GroupResponse])
async def list_groups(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, le=100, description="Page size"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    item_category: Optional[str] = Query(None, description="Filter by item category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List groups with filtering and pagination
    
    Returns groups based on user preferences and GBGCN recommendations
    """
    # Build query
    query = select(Group, User).join(User, Group.initiator_id == User.id)
    
    # Apply filters
    filters = [Group.is_public == True]  # Only public groups for general listing
    
    if status_filter:
        filters.append(Group.status == status_filter)
    
    if location:
        filters.append(Group.location.ilike(f"%{location}%"))
    
    query = query.where(and_(*filters))
    
    # Apply sorting
    sort_column = getattr(Group, sort_by, Group.created_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    
    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)
    
    result = await db.execute(query)
    groups_with_initiators = result.all()
    
    # Format response
    responses = []
    for group, initiator in groups_with_initiators:
        responses.append(GroupResponse(
            id=str(group.id),
            title=group.title,
            description=group.description,
            item_id=str(group.item_id),
            initiator_id=str(group.initiator_id),
            initiator_username=str(initiator.username),
            current_members=group.current_members,
            target_size=group.target_size,
            min_size=group.min_size,
            target_price=float(group.target_price),
            current_discount=float(group.current_discount),
            status=str(group.status),
            success_probability=float(group.success_probability),
            deadline=group.deadline,
            is_public=bool(group.is_public),
            location=str(group.location) if group.location else None,
            tags=group.tags or [],
            created_at=group.created_at,
            updated_at=group.updated_at
        ))
    
    return responses

@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get group details by ID
    
    Returns detailed group information including GBGCN analytics
    """
    # Get group with initiator info
    result = await db.execute(
        select(Group, User)
        .join(User, Group.initiator_id == User.id)
        .where(Group.id == group_id)
    )
    
    group_with_initiator = result.first()
    if not group_with_initiator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    group, initiator = group_with_initiator
    
    # Check if user can view this group
    if not bool(group.is_public):
        # Check if user is a member
        member_result = await db.execute(
            select(GroupMember)
            .where(and_(
                GroupMember.group_id == group_id,
                GroupMember.user_id == str(current_user.id)
            ))
        )
        if not member_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to private group"
            )
    
    return GroupResponse(
        id=str(group.id),
        title=group.title,
        description=group.description,
        item_id=str(group.item_id),
        initiator_id=str(group.initiator_id),
        initiator_username=str(initiator.username),
        current_members=group.current_members,
        target_size=group.target_size,
        min_size=group.min_size,
        target_price=float(group.target_price),
        current_discount=float(group.current_discount),
        status=str(group.status),
        success_probability=float(group.success_probability),
        deadline=group.deadline,
        is_public=bool(group.is_public),
        location=str(group.location) if group.location else None,
        tags=group.tags or [],
        created_at=group.created_at,
        updated_at=group.updated_at
    )

@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    group_update: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update group details (Initiator only)
    
    Allows group initiator to modify group parameters
    """
    # Get group
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if user is the initiator
    if str(group.initiator_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group initiator can update group"
        )
    
    # Check if group can be updated (only in FORMING status)
    if str(group.status) != "FORMING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update groups in FORMING status"
        )
    
    # Update fields
    update_data = group_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    
    # Validate min_size <= target_size if both are being updated
    if hasattr(group, 'min_size') and hasattr(group, 'target_size'):
        if group.min_size > group.target_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum size cannot be greater than target size"
            )
    
    await db.commit()
    await db.refresh(group)
    
    # Get initiator info for response
    initiator_result = await db.execute(select(User).where(User.id == group.initiator_id))
    initiator = initiator_result.scalar_one()
    
    return GroupResponse(
        id=str(group.id),
        title=group.title,
        description=group.description,
        item_id=str(group.item_id),
        initiator_id=str(group.initiator_id),
        initiator_username=str(initiator.username),
        current_members=group.current_members,
        target_size=group.target_size,
        min_size=group.min_size,
        target_price=float(group.target_price),
        current_discount=float(group.current_discount),
        status=str(group.status),
        success_probability=float(group.success_probability),
        deadline=group.deadline,
        is_public=bool(group.is_public),
        location=str(group.location) if group.location else None,
        tags=group.tags or [],
        created_at=group.created_at,
        updated_at=group.updated_at
    )

@router.post("/{group_id}/join")
async def join_group(
    group_id: str,
    join_request: JoinGroupRequest = JoinGroupRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Join a group buying group
    
    Adds user to group with GBGCN compatibility scoring
    """
    # Get group
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if group can accept new members
    if str(group.status) != "FORMING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group is not accepting new members"
        )
    
    if group.current_members >= group.target_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group is already full"
        )
    
    # Check if user is already a member
    existing_member = await db.execute(
        select(GroupMember)
        .where(and_(
            GroupMember.group_id == group_id,
            GroupMember.user_id == str(current_user.id)
        ))
    )
    
    if existing_member.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this group"
        )
    
    # Add user to group
    new_member = GroupMember(
        group_id=group_id,
        user_id=str(current_user.id),
        status=MemberStatus.ACTIVE,
        role="MEMBER",
        join_message=join_request.message
    )
    
    db.add(new_member)
    
    # Update group member count
    group.current_members += 1
    
    # Update success probability (placeholder - would use GBGCN model)
    group.success_probability = min(group.current_members / group.target_size, 1.0)
    
    # Update discount based on current members (simplified calculation)
    progress_ratio = group.current_members / group.target_size
    max_discount = 0.3  # 30% max discount
    group.current_discount = progress_ratio * max_discount
    
    await db.commit()
    
    return {
        "message": "Successfully joined group",
        "group_id": group_id,
        "current_members": group.current_members,
        "success_probability": float(group.success_probability),
        "current_discount": float(group.current_discount)
    }

@router.delete("/{group_id}/leave")
async def leave_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Leave a group buying group
    
    Removes user from group and updates group statistics
    """
    # Get group and membership
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    member_result = await db.execute(
        select(GroupMember)
        .where(and_(
            GroupMember.group_id == group_id,
            GroupMember.user_id == str(current_user.id)
        ))
    )
    
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of this group"
        )
    
    # Check if user is the initiator
    if str(member.role) == "INITIATOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group initiator cannot leave the group. Delete the group instead."
        )
    
    # Remove member
    await db.delete(member)
    
    # Update group member count
    group.current_members -= 1
    
    # Update success probability
    group.success_probability = min(group.current_members / group.target_size, 1.0)
    
    # Update discount
    progress_ratio = group.current_members / group.target_size
    max_discount = 0.3
    group.current_discount = progress_ratio * max_discount
    
    await db.commit()
    
    return {
        "message": "Successfully left group",
        "group_id": group_id,
        "current_members": group.current_members
    }

@router.get("/{group_id}/members", response_model=List[GroupMemberResponse])
async def get_group_members(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get group members with social context
    
    Returns member list with GBGCN social influence scores
    """
    # Check if group exists and user can view it
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Get members with user info
    result = await db.execute(
        select(GroupMember, User)
        .join(User, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at)
    )
    
    members_with_users = result.all()
    
    # Format response
    members = []
    for member, user in members_with_users:
        # Calculate social influence (placeholder)
        social_influence = min(float(user.reputation_score or 0) * 0.1, 1.0)
        
        members.append(GroupMemberResponse(
            user_id=str(member.user_id),
            username=str(user.username),
            first_name=str(user.first_name),
            last_name=str(user.last_name),
            avatar_url=str(user.avatar_url) if user.avatar_url else None,
            status=str(member.status),
            joined_at=member.joined_at,
            reputation_score=float(user.reputation_score or 0),
            social_influence=social_influence
        ))
    
    return members

@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a group (Initiator only)
    
    Removes group and all associated data
    """
    # Get group
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if user is the initiator
    if str(group.initiator_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group initiator can delete group"
        )
    
    # Check if group can be deleted (only FORMING or FAILED groups)
    if str(group.status) not in ["FORMING", "FAILED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete groups in FORMING or FAILED status"
        )
    
    # Delete all members first
    await db.execute(
        GroupMember.__table__.delete().where(GroupMember.group_id == group_id)
    )
    
    # Delete group
    await db.delete(group)
    await db.commit()
    
    return {"message": "Group deleted successfully", "group_id": group_id} 