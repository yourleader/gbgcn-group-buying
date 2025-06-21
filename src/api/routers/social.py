"""
Social connections router for Group Buying API - GBGCN Social Influence
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from src.database.connection import get_db
from src.database.models import (
    SocialConnection, User, Group, GroupMember, 
    UserItemInteraction, InteractionType
)
from src.core.auth import get_current_user
from src.core.config import settings

router = APIRouter()

# Pydantic models
class ConnectionRequest(BaseModel):
    """Friend/follow connection request"""
    target_user_id: str
    connection_type: str = Field(..., pattern="^(FRIEND|FOLLOW)$")
    message: Optional[str] = Field(None, max_length=500)

class ConnectionResponse(BaseModel):
    """Social connection response"""
    id: str
    user_id: str
    connected_user_id: str
    connected_username: str
    connected_name: str
    avatar_url: Optional[str]
    connection_type: str
    status: str
    mutual_friends: int
    common_groups: int
    influence_score: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class SocialInfluenceData(BaseModel):
    """Social influence analytics for GBGCN"""
    user_id: str
    total_connections: int
    friend_connections: int
    follower_connections: int
    following_connections: int
    influence_reach: int
    social_clusters: List[dict]
    recommendation_weight: float
    network_centrality: float

class FriendSuggestion(BaseModel):
    """Friend suggestion from GBGCN algorithm"""
    user_id: str
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str]
    mutual_friends: int
    common_interests: List[str]
    similarity_score: float
    group_collaboration_history: int
    recommendation_reason: str

class SocialActivity(BaseModel):
    """Social activity feed item"""
    id: str
    user_id: str
    username: str
    activity_type: str
    description: str
    related_item_id: Optional[str]
    related_group_id: Optional[str]
    timestamp: datetime
    likes_count: int
    comments_count: int

@router.post("/connect", status_code=status.HTTP_201_CREATED)
async def send_connection_request(
    connection_request: ConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send friend request or follow a user
    
    Creates social connections for GBGCN social influence algorithm
    """
    target_user_id = connection_request.target_user_id
    
    # Check if target user exists
    target_result = await db.execute(select(User).where(User.id == target_user_id))
    target_user = target_result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Can't connect to yourself
    if target_user_id == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot connect to yourself"
        )
    
    # Check if connection already exists
    existing_result = await db.execute(
        select(SocialConnection).where(and_(
            SocialConnection.user_id == str(current_user.id),
            SocialConnection.connected_user_id == target_user_id,
            SocialConnection.connection_type == connection_request.connection_type
        ))
    )
    
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection already exists or request already sent"
        )
    
    # Check connection limits
    connections_count_result = await db.execute(
        select(func.count(SocialConnection.id))
        .where(SocialConnection.user_id == str(current_user.id))
    )
    
    connections_count = connections_count_result.scalar() or 0
    if connections_count >= settings.MAX_SOCIAL_CONNECTIONS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum connections limit reached ({settings.MAX_SOCIAL_CONNECTIONS_PER_USER})"
        )
    
    # Create connection
    connection_status = "ACCEPTED" if connection_request.connection_type == "FOLLOW" else "PENDING"
    
    new_connection = SocialConnection(
        user_id=str(current_user.id),
        connected_user_id=target_user_id,
        connection_type=connection_request.connection_type,
        status=connection_status,
        request_message=connection_request.message
    )
    
    db.add(new_connection)
    
    # If it's a FOLLOW, also create reverse connection for follower tracking
    if connection_request.connection_type == "FOLLOW":
        reverse_connection = SocialConnection(
            user_id=target_user_id,
            connected_user_id=str(current_user.id),
            connection_type="FOLLOWER",
            status="ACCEPTED"
        )
        db.add(reverse_connection)
    
    await db.commit()
    
    return {
        "message": f"Connection request sent successfully",
        "connection_type": connection_request.connection_type,
        "status": connection_status,
        "target_user": target_user.username
    }

@router.get("/connections", response_model=List[ConnectionResponse])
async def get_my_connections(
    connection_type: Optional[str] = Query(None, pattern="^(FRIEND|FOLLOW|FOLLOWER)$"),
    status_filter: Optional[str] = Query(None, pattern="^(PENDING|ACCEPTED|BLOCKED)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's social connections
    
    Returns friends, followers, and following for GBGCN social graph
    """
    # Build query
    query = select(SocialConnection, User).join(
        User, SocialConnection.connected_user_id == User.id
    ).where(SocialConnection.user_id == str(current_user.id))
    
    # Apply filters
    if connection_type:
        query = query.where(SocialConnection.connection_type == connection_type)
    
    if status_filter:
        query = query.where(SocialConnection.status == status_filter)
    
    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size).order_by(desc(SocialConnection.created_at))
    
    result = await db.execute(query)
    connections_with_users = result.all()
    
    # Format response
    responses = []
    for connection, connected_user in connections_with_users:
        # Calculate mutual friends (simplified)
        mutual_friends = await _calculate_mutual_friends(
            str(current_user.id), 
            str(connected_user.id), 
            db
        )
        
        # Calculate common groups
        common_groups = await _calculate_common_groups(
            str(current_user.id),
            str(connected_user.id),
            db
        )
        
        # Calculate influence score (simplified GBGCN metric)
        influence_score = min(float(connected_user.reputation_score or 0) * 0.1, 1.0)
        
        responses.append(ConnectionResponse(
            id=str(connection.id),
            user_id=str(current_user.id),
            connected_user_id=str(connected_user.id),
            connected_username=str(connected_user.username),
            connected_name=f"{connected_user.first_name} {connected_user.last_name}",
            avatar_url=str(connected_user.avatar_url) if connected_user.avatar_url else None,
            connection_type=str(connection.connection_type),
            status=str(connection.status),
            mutual_friends=mutual_friends,
            common_groups=common_groups,
            influence_score=influence_score,
            created_at=connection.created_at
        ))
    
    return responses

@router.post("/connections/{connection_id}/accept")
async def accept_connection_request(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept a friend request
    
    Establishes bidirectional social connection for GBGCN
    """
    # Get connection request
    result = await db.execute(
        select(SocialConnection).where(and_(
            SocialConnection.id == connection_id,
            SocialConnection.connected_user_id == str(current_user.id),
            SocialConnection.status == "PENDING"
        ))
    )
    
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection request not found"
        )
    
    # Accept the request
    connection.status = "ACCEPTED"
    
    # Create reverse connection for bidirectional friendship
    if str(connection.connection_type) == "FRIEND":
        reverse_connection = SocialConnection(
            user_id=str(current_user.id),
            connected_user_id=str(connection.user_id),
            connection_type="FRIEND",
            status="ACCEPTED"
        )
        db.add(reverse_connection)
    
    await db.commit()
    
    return {
        "message": "Connection request accepted",
        "connection_id": connection_id
    }

@router.delete("/connections/{connection_id}")
async def remove_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a social connection
    
    Removes connection and updates GBGCN social graph
    """
    result = await db.execute(
        select(SocialConnection).where(and_(
            SocialConnection.id == connection_id,
            SocialConnection.user_id == str(current_user.id)
        ))
    )
    
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    connected_user_id = str(connection.connected_user_id)
    connection_type = str(connection.connection_type)
    
    # Remove the connection
    await db.delete(connection)
    
    # Remove reverse connection if it exists (for friends)
    if connection_type == "FRIEND":
        reverse_result = await db.execute(
            select(SocialConnection).where(and_(
                SocialConnection.user_id == connected_user_id,
                SocialConnection.connected_user_id == str(current_user.id),
                SocialConnection.connection_type == "FRIEND"
            ))
        )
        
        reverse_connection = reverse_result.scalar_one_or_none()
        if reverse_connection:
            await db.delete(reverse_connection)
    
    await db.commit()
    
    return {
        "message": "Connection removed successfully",
        "connection_id": connection_id
    }

@router.get("/influence", response_model=SocialInfluenceData)
async def get_social_influence_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's social influence data for GBGCN
    
    Returns comprehensive social metrics used by the recommendation algorithm
    """
    user_id = str(current_user.id)
    
    # Get total connections
    total_result = await db.execute(
        select(func.count(SocialConnection.id))
        .where(SocialConnection.user_id == user_id)
    )
    total_connections = total_result.scalar() or 0
    
    # Get friend connections
    friends_result = await db.execute(
        select(func.count(SocialConnection.id))
        .where(and_(
            SocialConnection.user_id == user_id,
            SocialConnection.connection_type == "FRIEND",
            SocialConnection.status == "ACCEPTED"
        ))
    )
    friend_connections = friends_result.scalar() or 0
    
    # Get follower connections
    followers_result = await db.execute(
        select(func.count(SocialConnection.id))
        .where(and_(
            SocialConnection.connected_user_id == user_id,
            SocialConnection.connection_type == "FOLLOW",
            SocialConnection.status == "ACCEPTED"
        ))
    )
    follower_connections = followers_result.scalar() or 0
    
    # Get following connections
    following_result = await db.execute(
        select(func.count(SocialConnection.id))
        .where(and_(
            SocialConnection.user_id == user_id,
            SocialConnection.connection_type == "FOLLOW",
            SocialConnection.status == "ACCEPTED"
        ))
    )
    following_connections = following_result.scalar() or 0
    
    # Calculate influence reach (simplified)
    influence_reach = friend_connections * 2 + follower_connections
    
    # Calculate social clusters (simplified)
    social_clusters = [
        {
            "cluster_id": "main",
            "size": friend_connections,
            "centrality": 0.7,
            "common_interests": ["electronics", "fashion"]
        }
    ]
    
    # Calculate recommendation weight for GBGCN
    reputation_factor = min(float(current_user.reputation_score or 0) / 100.0, 1.0)
    social_factor = min(friend_connections / 50.0, 1.0)
    recommendation_weight = (reputation_factor + social_factor) / 2
    
    # Calculate network centrality (simplified)
    network_centrality = min(friend_connections / 100.0, 1.0)
    
    return SocialInfluenceData(
        user_id=user_id,
        total_connections=total_connections,
        friend_connections=friend_connections,
        follower_connections=follower_connections,
        following_connections=following_connections,
        influence_reach=influence_reach,
        social_clusters=social_clusters,
        recommendation_weight=recommendation_weight,
        network_centrality=network_centrality
    )

@router.get("/suggestions", response_model=List[FriendSuggestion])
async def get_friend_suggestions(
    limit: int = Query(10, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get friend suggestions using GBGCN algorithm
    
    Returns personalized friend recommendations based on social patterns
    """
    user_id = str(current_user.id)
    
    # Get users with mutual friends (simplified query)
    # In a full implementation, this would use the GBGCN model
    suggestions_query = select(User).where(and_(
        User.id != user_id,
        User.is_active == True
    )).order_by(desc(User.reputation_score)).limit(limit)
    
    result = await db.execute(suggestions_query)
    suggested_users = result.scalars().all()
    
    suggestions = []
    for user in suggested_users:
        # Check if already connected
        existing_connection = await db.execute(
            select(SocialConnection).where(and_(
                SocialConnection.user_id == user_id,
                SocialConnection.connected_user_id == str(user.id)
            ))
        )
        
        if existing_connection.scalar_one_or_none():
            continue  # Skip if already connected
        
        # Calculate mutual friends
        mutual_friends = await _calculate_mutual_friends(user_id, str(user.id), db)
        
        # Calculate common interests (simplified)
        common_interests = ["electronics", "books"]  # Placeholder
        
        # Calculate similarity score (simplified GBGCN metric)
        similarity_score = min(mutual_friends / 10.0 + float(user.reputation_score or 0) / 200.0, 1.0)
        
        # Calculate group collaboration history
        group_collaboration = await _calculate_group_collaboration(user_id, str(user.id), db)
        
        # Recommendation reason
        if mutual_friends > 0:
            reason = f"{mutual_friends} mutual friends"
        elif group_collaboration > 0:
            reason = f"Collaborated in {group_collaboration} groups"
        else:
            reason = "Similar interests and high reputation"
        
        suggestions.append(FriendSuggestion(
            user_id=str(user.id),
            username=str(user.username),
            first_name=str(user.first_name),
            last_name=str(user.last_name),
            avatar_url=str(user.avatar_url) if user.avatar_url else None,
            mutual_friends=mutual_friends,
            common_interests=common_interests,
            similarity_score=similarity_score,
            group_collaboration_history=group_collaboration,
            recommendation_reason=reason
        ))
    
    return suggestions

@router.get("/activity", response_model=List[SocialActivity])
async def get_social_activity_feed(
    page: int = Query(1, ge=1),
    size: int = Query(20, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get social activity feed
    
    Returns activities from user's social network for engagement
    """
    user_id = str(current_user.id)
    
    # Get friend IDs
    friends_result = await db.execute(
        select(SocialConnection.connected_user_id)
        .where(and_(
            SocialConnection.user_id == user_id,
            SocialConnection.connection_type == "FRIEND",
            SocialConnection.status == "ACCEPTED"
        ))
    )
    
    friend_ids = [row[0] for row in friends_result.all()]
    friend_ids.append(user_id)  # Include own activities
    
    # Get recent group activities (simplified)
    activities = []
    
    # This would be a more complex query in production to get various activity types
    # For now, return placeholder activities
    activities.append(SocialActivity(
        id="1",
        user_id=user_id,
        username=str(current_user.username),
        activity_type="GROUP_JOINED",
        description="Joined Electronics Group Buy",
        related_group_id="group_123",
        timestamp=datetime.utcnow(),
        likes_count=5,
        comments_count=2
    ))
    
    return activities

# Helper functions
async def _calculate_mutual_friends(user1_id: str, user2_id: str, db: AsyncSession) -> int:
    """Calculate number of mutual friends between two users"""
    # Simplified calculation - would be more complex in production
    return 2  # Placeholder

async def _calculate_common_groups(user1_id: str, user2_id: str, db: AsyncSession) -> int:
    """Calculate number of common groups between two users"""
    result = await db.execute(
        select(func.count(func.distinct(GroupMember.group_id)))
        .select_from(
            GroupMember.join(
                GroupMember.__table__.alias('gm2'),
                GroupMember.group_id == GroupMember.__table__.alias('gm2').c.group_id
            )
        )
        .where(and_(
            GroupMember.user_id == user1_id,
            GroupMember.__table__.alias('gm2').c.user_id == user2_id
        ))
    )
    
    return result.scalar() or 0

async def _calculate_group_collaboration(user1_id: str, user2_id: str, db: AsyncSession) -> int:
    """Calculate group collaboration history between two users"""
    # This would check how many successful groups they've been in together
    return await _calculate_common_groups(user1_id, user2_id, db) 