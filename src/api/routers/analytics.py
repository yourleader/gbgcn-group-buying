"""
Analytics router for Group Buying API - GBGCN Performance Metrics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

from src.database.connection import get_db
from src.database.models import (
    User, Item, Group, GroupMember, UserItemInteraction, 
    SocialConnection, GroupStatus, InteractionType
)
from src.core.auth import get_current_user, admin_required, moderator_required
from src.core.config import settings

router = APIRouter()

class TimeRange(str, Enum):
    """Time range options for analytics"""
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"
    LAST_90D = "90d"
    LAST_YEAR = "1y"
    ALL_TIME = "all"

# Pydantic models
class SystemMetrics(BaseModel):
    """Overall system metrics"""
    total_users: int
    active_users_24h: int
    total_items: int
    total_groups: int
    active_groups: int
    successful_groups: int
    total_interactions: int
    success_rate: float
    avg_group_size: float
    revenue: float

class GBGCNMetrics(BaseModel):
    """GBGCN model performance metrics"""
    model_config = {"protected_namespaces": ()}  # Allow model_ fields
    
    model_accuracy: float
    recommendation_precision: float
    recommendation_recall: float
    group_success_prediction_accuracy: float
    social_influence_correlation: float
    avg_recommendation_time_ms: float
    model_last_trained: Optional[datetime]
    total_predictions: int
    successful_predictions: int

class UserAnalytics(BaseModel):
    """User behavior analytics"""
    user_growth_rate: float
    avg_session_duration_minutes: float
    user_retention_rate: float
    most_active_age_group: str
    top_user_locations: List[Dict[str, Any]]
    user_engagement_score: float

class GroupAnalytics(BaseModel):
    """Group formation and success analytics"""
    avg_formation_time_hours: float
    success_rate_by_size: Dict[str, float]
    most_popular_categories: List[Dict[str, Any]]
    optimal_group_size: int
    peak_formation_hours: List[int]
    completion_rate: float

class RecommendationAnalytics(BaseModel):
    """Recommendation system analytics"""
    click_through_rate: float
    conversion_rate: float
    avg_recommendations_per_user: float
    recommendation_diversity_score: float
    algorithm_performance: Dict[str, Dict[str, float]]
    user_satisfaction_score: float

class SocialNetworkAnalytics(BaseModel):
    """Social network analytics"""
    avg_connections_per_user: float
    network_density: float
    clustering_coefficient: float
    avg_path_length: float
    influence_distribution: Dict[str, int]
    viral_coefficient: float

@router.get("/system", response_model=SystemMetrics)
async def get_system_metrics(
    time_range: TimeRange = Query(TimeRange.LAST_30D),
    admin_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall system metrics
    
    Returns comprehensive system statistics for administrators
    """
    # Calculate time filter
    end_date = datetime.utcnow()
    if time_range == TimeRange.LAST_24H:
        start_date = end_date - timedelta(hours=24)
    elif time_range == TimeRange.LAST_7D:
        start_date = end_date - timedelta(days=7)
    elif time_range == TimeRange.LAST_30D:
        start_date = end_date - timedelta(days=30)
    elif time_range == TimeRange.LAST_90D:
        start_date = end_date - timedelta(days=90)
    elif time_range == TimeRange.LAST_YEAR:
        start_date = end_date - timedelta(days=365)
    else:  # ALL_TIME
        start_date = datetime(2020, 1, 1)  # Far past date
    
    # Get total users
    total_users_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= start_date)
    )
    total_users = total_users_result.scalar() or 0
    
    # Get active users in last 24h
    active_users_result = await db.execute(
        select(func.count(User.id)).where(
            User.last_login >= end_date - timedelta(hours=24)
        )
    )
    active_users_24h = active_users_result.scalar() or 0
    
    # Get total items
    total_items_result = await db.execute(
        select(func.count(Item.id)).where(Item.created_at >= start_date)
    )
    total_items = total_items_result.scalar() or 0
    
    # Get group statistics
    total_groups_result = await db.execute(
        select(func.count(Group.id)).where(Group.created_at >= start_date)
    )
    total_groups = total_groups_result.scalar() or 0
    
    active_groups_result = await db.execute(
        select(func.count(Group.id)).where(and_(
            Group.created_at >= start_date,
            Group.status == GroupStatus.FORMING
        ))
    )
    active_groups = active_groups_result.scalar() or 0
    
    successful_groups_result = await db.execute(
        select(func.count(Group.id)).where(and_(
            Group.created_at >= start_date,
            Group.status == GroupStatus.COMPLETED
        ))
    )
    successful_groups = successful_groups_result.scalar() or 0
    
    # Get interaction statistics
    total_interactions_result = await db.execute(
        select(func.count(UserItemInteraction.id)).where(
            UserItemInteraction.created_at >= start_date
        )
    )
    total_interactions = total_interactions_result.scalar() or 0
    
    # Calculate derived metrics
    success_rate = successful_groups / total_groups if total_groups > 0 else 0.0
    
    avg_group_size_result = await db.execute(
        select(func.avg(Group.current_members)).where(
            Group.created_at >= start_date
        )
    )
    avg_group_size = float(avg_group_size_result.scalar() or 0.0)
    
    # Calculate revenue (placeholder)
    revenue = successful_groups * 25.0  # Simplified calculation
    
    return SystemMetrics(
        total_users=total_users,
        active_users_24h=active_users_24h,
        total_items=total_items,
        total_groups=total_groups,
        active_groups=active_groups,
        successful_groups=successful_groups,
        total_interactions=total_interactions,
        success_rate=success_rate,
        avg_group_size=avg_group_size,
        revenue=revenue
    )

@router.get("/gbgcn", response_model=GBGCNMetrics)
async def get_gbgcn_metrics(
    admin_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Get GBGCN model performance metrics
    
    Returns detailed ML model performance statistics
    """
    # In a full implementation, these would come from model evaluation
    # and prediction logs. For now, using placeholder values.
    
    return GBGCNMetrics(
        model_accuracy=0.84,
        recommendation_precision=0.76,
        recommendation_recall=0.82,
        group_success_prediction_accuracy=0.79,
        social_influence_correlation=0.68,
        avg_recommendation_time_ms=45.3,
        model_last_trained=datetime.utcnow() - timedelta(hours=12),
        total_predictions=12547,
        successful_predictions=10234
    )

@router.get("/users", response_model=UserAnalytics)
async def get_user_analytics(
    time_range: TimeRange = Query(TimeRange.LAST_30D),
    moderator_user: User = Depends(moderator_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user behavior analytics
    
    Returns user engagement and demographic insights
    """
    # Calculate time filter
    end_date = datetime.utcnow()
    if time_range == TimeRange.LAST_30D:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = end_date - timedelta(days=7)
    
    # Get user count at start and end of period
    start_users_result = await db.execute(
        select(func.count(User.id)).where(User.created_at <= start_date)
    )
    start_users = start_users_result.scalar() or 1
    
    end_users_result = await db.execute(
        select(func.count(User.id)).where(User.created_at <= end_date)
    )
    end_users = end_users_result.scalar() or 1
    
    # Calculate growth rate
    user_growth_rate = ((end_users - start_users) / start_users) * 100 if start_users > 0 else 0.0
    
    # Placeholder values for other metrics
    avg_session_duration_minutes = 24.5
    user_retention_rate = 72.3
    most_active_age_group = "26-35"
    top_user_locations = [
        {"location": "New York", "count": 234},
        {"location": "Los Angeles", "count": 189},
        {"location": "Chicago", "count": 156}
    ]
    user_engagement_score = 7.8
    
    return UserAnalytics(
        user_growth_rate=user_growth_rate,
        avg_session_duration_minutes=avg_session_duration_minutes,
        user_retention_rate=user_retention_rate,
        most_active_age_group=most_active_age_group,
        top_user_locations=top_user_locations,
        user_engagement_score=user_engagement_score
    )

@router.get("/groups", response_model=GroupAnalytics)
async def get_group_analytics(
    time_range: TimeRange = Query(TimeRange.LAST_30D),
    moderator_user: User = Depends(moderator_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Get group formation and success analytics
    
    Returns insights about group buying patterns
    """
    # Calculate average formation time
    # This would require tracking when groups reach target size
    avg_formation_time_hours = 48.7  # Placeholder
    
    # Get success rate by group size
    success_rate_by_size = {}
    for size in range(2, 21):  # Group sizes 2-20
        size_groups_result = await db.execute(
            select(func.count(Group.id)).where(
                Group.target_size == size
            )
        )
        total_size_groups = size_groups_result.scalar() or 0
        
        if total_size_groups > 0:
            successful_size_groups_result = await db.execute(
                select(func.count(Group.id)).where(and_(
                    Group.target_size == size,
                    Group.status == GroupStatus.COMPLETED
                ))
            )
            successful_size_groups = successful_size_groups_result.scalar() or 0
            success_rate_by_size[str(size)] = successful_size_groups / total_size_groups
    
    # Get most popular categories (would need item categories)
    most_popular_categories = [
        {"category": "Electronics", "groups": 156},
        {"category": "Fashion", "groups": 134},
        {"category": "Home & Garden", "groups": 98}
    ]
    
    # Calculate optimal group size (size with highest success rate)
    optimal_group_size = 8  # Placeholder
    
    # Peak formation hours (would analyze group creation times)
    peak_formation_hours = [19, 20, 21]  # 7-9 PM
    
    # Calculate completion rate
    total_groups_result = await db.execute(
        select(func.count(Group.id))
    )
    total_groups = total_groups_result.scalar() or 1
    
    completed_groups_result = await db.execute(
        select(func.count(Group.id)).where(
            Group.status == GroupStatus.COMPLETED
        )
    )
    completed_groups = completed_groups_result.scalar() or 0
    
    completion_rate = completed_groups / total_groups
    
    return GroupAnalytics(
        avg_formation_time_hours=avg_formation_time_hours,
        success_rate_by_size=success_rate_by_size,
        most_popular_categories=most_popular_categories,
        optimal_group_size=optimal_group_size,
        peak_formation_hours=peak_formation_hours,
        completion_rate=completion_rate
    )

@router.get("/recommendations", response_model=RecommendationAnalytics)
async def get_recommendation_analytics(
    time_range: TimeRange = Query(TimeRange.LAST_30D),
    moderator_user: User = Depends(moderator_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommendation system analytics
    
    Returns performance metrics for the recommendation algorithms
    """
    # These would be calculated from actual recommendation logs
    # For now, using placeholder values
    
    return RecommendationAnalytics(
        click_through_rate=0.12,
        conversion_rate=0.08,
        avg_recommendations_per_user=8.3,
        recommendation_diversity_score=0.76,
        algorithm_performance={
            "GBGCN": {
                "precision": 0.76,
                "recall": 0.82,
                "f1_score": 0.79
            },
            "Collaborative_Filtering": {
                "precision": 0.68,
                "recall": 0.74,
                "f1_score": 0.71
            },
            "Content_Based": {
                "precision": 0.62,
                "recall": 0.69,
                "f1_score": 0.65
            }
        },
        user_satisfaction_score=7.2
    )

@router.get("/social", response_model=SocialNetworkAnalytics)
async def get_social_network_analytics(
    moderator_user: User = Depends(moderator_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Get social network analytics
    
    Returns insights about the social graph and influence patterns
    """
    # Get average connections per user
    total_connections_result = await db.execute(
        select(func.count(SocialConnection.id))
    )
    total_connections = total_connections_result.scalar() or 0
    
    total_users_result = await db.execute(
        select(func.count(User.id))
    )
    total_users = total_users_result.scalar() or 1
    
    avg_connections_per_user = total_connections / total_users
    
    # Calculate network density (simplified)
    max_possible_connections = total_users * (total_users - 1) / 2
    network_density = total_connections / max_possible_connections if max_possible_connections > 0 else 0.0
    
    # Placeholder values for complex network metrics
    clustering_coefficient = 0.34
    avg_path_length = 3.8
    influence_distribution = {
        "low": 1245,
        "medium": 634,
        "high": 189,
        "very_high": 42
    }
    viral_coefficient = 1.23
    
    return SocialNetworkAnalytics(
        avg_connections_per_user=avg_connections_per_user,
        network_density=network_density,
        clustering_coefficient=clustering_coefficient,
        avg_path_length=avg_path_length,
        influence_distribution=influence_distribution,
        viral_coefficient=viral_coefficient
    )

@router.get("/dashboard")
async def get_dashboard_data(
    time_range: TimeRange = Query(TimeRange.LAST_30D),
    moderator_user: User = Depends(moderator_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive dashboard data
    
    Returns all key metrics for the admin dashboard
    """
    # Get all analytics in parallel
    system_metrics = await get_system_metrics(time_range, moderator_user, db)
    gbgcn_metrics = await get_gbgcn_metrics(moderator_user, db)
    user_analytics = await get_user_analytics(time_range, moderator_user, db)
    group_analytics = await get_group_analytics(time_range, moderator_user, db)
    recommendation_analytics = await get_recommendation_analytics(time_range, moderator_user, db)
    social_analytics = await get_social_network_analytics(moderator_user, db)
    
    return {
        "system": system_metrics,
        "gbgcn": gbgcn_metrics,
        "users": user_analytics,
        "groups": group_analytics,
        "recommendations": recommendation_analytics,
        "social": social_analytics,
        "generated_at": datetime.utcnow(),
        "time_range": time_range
    }

@router.get("/trends/daily")
async def get_daily_trends(
    days: int = Query(30, ge=7, le=365),
    metric: str = Query("groups", pattern="^(users|groups|interactions|revenue)$"),
    moderator_user: User = Depends(moderator_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Get daily trends for specific metrics
    
    Returns time series data for dashboard charts
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Generate daily data points
    trends = []
    current_date = start_date
    
    while current_date <= end_date:
        day_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        if metric == "groups":
            result = await db.execute(
                select(func.count(Group.id)).where(and_(
                    Group.created_at >= day_start,
                    Group.created_at < day_end
                ))
            )
        elif metric == "users":
            result = await db.execute(
                select(func.count(User.id)).where(and_(
                    User.created_at >= day_start,
                    User.created_at < day_end
                ))
            )
        elif metric == "interactions":
            result = await db.execute(
                select(func.count(UserItemInteraction.id)).where(and_(
                    UserItemInteraction.created_at >= day_start,
                    UserItemInteraction.created_at < day_end
                ))
            )
        else:  # revenue
            groups_result = await db.execute(
                select(func.count(Group.id)).where(and_(
                    Group.created_at >= day_start,
                    Group.created_at < day_end,
                    Group.status == GroupStatus.COMPLETED
                ))
            )
            count = groups_result.scalar() or 0
            result = type('MockResult', (), {'scalar': lambda: count * 25.0})()
        
        value = result.scalar() or 0
        
        trends.append({
            "date": day_start.isoformat(),
            "value": value
        })
        
        current_date += timedelta(days=1)
    
    return {
        "metric": metric,
        "period": f"{days}_days",
        "trends": trends
    }

@router.get("/export")
async def export_analytics(
    format: str = Query("json", pattern="^(json|csv)$"),
    time_range: TimeRange = Query(TimeRange.LAST_30D),
    admin_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Export analytics data
    
    Returns analytics data in specified format for external analysis
    """
    # Get comprehensive analytics data
    dashboard_data = await get_dashboard_data(time_range, admin_user, db)
    
    if format == "json":
        return dashboard_data
    else:  # CSV format
        # Would implement CSV export here
        return {
            "message": "CSV export not implemented yet",
            "data": dashboard_data
        } 