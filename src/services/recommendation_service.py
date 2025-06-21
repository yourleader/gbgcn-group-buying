"""
Recommendation Service for Group Buying System
Integrates GBGCN model with database operations
"""

import torch
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_

from src.database.models import (
    User, Item, Group, GroupMember, UserItemInteraction, 
    SocialConnection, GBGCNEmbedding, GroupRecommendation
)
from src.ml.gbgcn_trainer import GBGCNTrainer
from src.core.config import settings
from src.core.logging import get_model_logger
from src.database.connection import get_db

logger = get_model_logger()

class RecommendationService:
    """
    Service layer for GBGCN-based recommendations
    """
    
    def __init__(self, gbgcn_trainer: GBGCNTrainer):
        self.gbgcn_trainer = gbgcn_trainer
        self.cache_duration = timedelta(minutes=30)
        self.logger = logger
    
    async def get_item_recommendations(
        self, 
        user_id: str, 
        k: int = 10,
        category_filter: Optional[str] = None,
        price_range: Optional[Tuple[float, float]] = None,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        Get personalized item recommendations for a user using GBGCN
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Check if user exists
            user = await db.get(User, user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Get GBGCN recommendations
            gbgcn_recommendations = await self.gbgcn_trainer.predict_item_recommendations(
                user_id, k * 2  # Get more to filter
            )
            
            # Get item details from database
            item_ids = [rec['item_id'] for rec in gbgcn_recommendations]
            
            # Build query with filters
            query = select(Item).where(Item.id.in_(item_ids))
            
            if category_filter:
                query = query.where(Item.category == category_filter)
            
            if price_range:
                min_price, max_price = price_range
                query = query.where(and_(Item.price >= min_price, Item.price <= max_price))
            
            result = await db.execute(query)
            items = result.scalars().all()
            
            # Create item lookup
            item_lookup = {item.id: item for item in items}
            
            # Combine GBGCN scores with item details
            recommendations = []
            for rec in gbgcn_recommendations[:k]:
                item_id = rec['item_id']
                if item_id in item_lookup:
                    item = item_lookup[item_id]
                    
                    # Calculate group buying potential
                    group_potential = await self._calculate_group_buying_potential(
                        item_id, user_id, db
                    )
                    
                    recommendations.append({
                        'item_id': item_id,
                        'title': item.title,
                        'category': item.category,
                        'price': float(item.price),
                        'discount_percentage': float(item.discount_percentage or 0),
                        'gbgcn_score': rec['score'],
                        'group_buying_potential': group_potential,
                        'recommendation_reason': self._generate_recommendation_reason(
                            rec, group_potential
                        ),
                        'algorithm': 'GBGCN'
                    })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting item recommendations for user {user_id}: {e}")
            raise
    
    async def get_group_recommendations(
        self, 
        user_id: str, 
        k: int = 10,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        Recommend groups for a user to join based on GBGCN
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Get active groups that user hasn't joined
            query = select(Group).options(
                selectinload(Group.members),
                selectinload(Group.item)
            ).where(
                and_(
                    Group.status == 'active',
                    Group.end_time > datetime.utcnow(),
                    ~Group.members.any(GroupMember.user_id == user_id)
                )
            )
            
            result = await db.execute(query)
            candidate_groups = result.scalars().all()
            
            group_recommendations = []
            
            for group in candidate_groups:
                # Predict user's interest in this group's item
                item_score = await self._predict_user_item_interest(
                    user_id, group.item_id, db
                )
                
                # Predict group success probability
                success_prob = await self.gbgcn_trainer.predict_group_success(group.id)
                
                # Calculate social influence from current members
                social_influence = await self._calculate_social_influence(
                    user_id, group.id, db
                )
                
                # Calculate composite score
                composite_score = (
                    0.4 * item_score + 
                    0.3 * success_prob + 
                    0.3 * social_influence
                )
                
                group_recommendations.append({
                    'group_id': group.id,
                    'item_title': group.item.title,
                    'current_size': len(group.members),
                    'target_size': group.target_size,
                    'current_price': float(group.current_price),
                    'target_price': float(group.target_price),
                    'time_remaining': (group.end_time - datetime.utcnow()).days,
                    'success_probability': success_prob,
                    'social_influence_score': social_influence,
                    'item_interest_score': item_score,
                    'composite_score': composite_score,
                    'recommendation_reason': self._generate_group_recommendation_reason(
                        item_score, success_prob, social_influence
                    )
                })
            
            # Sort by composite score
            group_recommendations.sort(key=lambda x: x['composite_score'], reverse=True)
            
            return group_recommendations[:k]
            
        except Exception as e:
            self.logger.error(f"Error getting group recommendations for user {user_id}: {e}")
            raise
    
    async def analyze_group_formation(
        self,
        initiator_id: str,
        item_id: str,
        potential_participants: List[str],
        target_size: int,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Analyze optimal group formation using GBGCN
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Get user and item details
            users_query = select(User).where(User.id.in_([initiator_id] + potential_participants))
            item_query = select(Item).where(Item.id == item_id)
            
            users_result = await db.execute(users_query)
            item_result = await db.execute(item_query)
            
            users = {user.id: user for user in users_result.scalars().all()}
            item = item_result.scalar_one_or_none()
            
            if not item:
                raise ValueError(f"Item {item_id} not found")
            
            # Use GBGCN to predict group formation success
            formation_prediction = await self.gbgcn_trainer.model.predict_group_formation(
                initiator_id=initiator_id,
                item_id=item_id,
                potential_participants=potential_participants
            )
            
            # Analyze participant compatibility
            participant_analysis = []
            for participant_id in potential_participants:
                if participant_id in users:
                    participant = users[participant_id]
                    
                    # Calculate compatibility metrics
                    social_connection = await self._get_social_connection_strength(
                        initiator_id, participant_id, db
                    )
                    
                    item_interest = await self._predict_user_item_interest(
                        participant_id, item_id, db
                    )
                    
                    participant_analysis.append({
                        'user_id': participant_id,
                        'username': participant.username,
                        'social_connection_strength': social_connection,
                        'item_interest_score': item_interest,
                        'predicted_participation_probability': formation_prediction.get(
                            'participant_scores', [0.5]
                        )[len(participant_analysis)] if len(participant_analysis) < len(
                            formation_prediction.get('participant_scores', [])
                        ) else 0.5
                    })
            
            # Generate optimization suggestions
            optimization_suggestions = await self._generate_optimization_suggestions(
                formation_prediction, participant_analysis, target_size
            )
            
            return {
                'group_success_probability': formation_prediction['group_success_probability'],
                'initiator_score': formation_prediction['initiator_score'],
                'overall_recommendation_score': formation_prediction['overall_recommendation_score'],
                'participant_analysis': participant_analysis,
                'optimization_suggestions': optimization_suggestions,
                'recommended_group_size': min(target_size, len([
                    p for p in participant_analysis 
                    if p['predicted_participation_probability'] > 0.6
                ]) + 1),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing group formation: {e}")
            raise
    
    async def get_social_influence_analysis(
        self,
        user_id: str,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Analyze social influence patterns for a user
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Get social connections
            connections_query = select(SocialConnection).options(
                selectinload(SocialConnection.friend)
            ).where(SocialConnection.user_id == user_id)
            
            result = await db.execute(connections_query)
            connections = result.scalars().all()
            
            # Analyze influence patterns
            influence_analysis = {
                'user_id': user_id,
                'total_connections': len(connections),
                'influence_received': [],
                'influence_given': [],
                'social_clusters': [],
                'recommendation_impact': 0.0
            }
            
            # Calculate influence received from friends
            for conn in connections:
                friend_influence = {
                    'friend_id': conn.friend_id,
                    'friend_username': conn.friend.username,
                    'connection_strength': float(conn.connection_strength),
                    'influence_type': conn.influence_type,
                    'shared_group_activities': await self._count_shared_group_activities(
                        user_id, conn.friend_id, db
                    )
                }
                influence_analysis['influence_received'].append(friend_influence)
            
            # Calculate overall recommendation impact
            if connections:
                avg_connection_strength = np.mean([
                    conn.connection_strength for conn in connections
                ])
                influence_analysis['recommendation_impact'] = float(avg_connection_strength * 0.3)
            
            return influence_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing social influence for user {user_id}: {e}")
            raise
    
    # Helper methods
    async def _calculate_group_buying_potential(
        self, 
        item_id: str, 
        user_id: str, 
        db: AsyncSession
    ) -> float:
        """Calculate the group buying potential for an item"""
        try:
            # Count recent group buying activities for this item
            recent_groups_query = select(func.count(Group.id)).where(
                and_(
                    Group.item_id == item_id,
                    Group.created_at > datetime.utcnow() - timedelta(days=30),
                    Group.status.in_(['active', 'completed'])
                )
            )
            
            result = await db.execute(recent_groups_query)
            recent_groups_count = result.scalar() or 0
            
            # Calculate potential score (0-1)
            potential_score = min(recent_groups_count / 10.0, 1.0)
            
            return potential_score
            
        except Exception:
            return 0.5
    
    async def _predict_user_item_interest(
        self, 
        user_id: str, 
        item_id: str, 
        db: AsyncSession
    ) -> float:
        """Predict user's interest in an item"""
        try:
            # Check past interactions
            interaction_query = select(UserItemInteraction).where(
                and_(
                    UserItemInteraction.user_id == user_id,
                    UserItemInteraction.item_id == item_id
                )
            )
            
            result = await db.execute(interaction_query)
            interaction = result.scalar_one_or_none()
            
            if interaction:
                return float(interaction.rating or 0.5)
            
            # Use GBGCN to predict interest
            recommendations = await self.gbgcn_trainer.predict_item_recommendations(
                user_id, k=100
            )
            
            for rec in recommendations:
                if rec['item_id'] == item_id:
                    return rec['score']
            
            return 0.3  # Default low interest
            
        except Exception:
            return 0.5
    
    async def _calculate_social_influence(
        self, 
        user_id: str, 
        group_id: str, 
        db: AsyncSession
    ) -> float:
        """Calculate social influence score for joining a group"""
        try:
            # Get group members
            members_query = select(GroupMember).options(
                selectinload(GroupMember.user)
            ).where(GroupMember.group_id == group_id)
            
            result = await db.execute(members_query)
            members = result.scalars().all()
            
            # Check social connections with members
            total_influence = 0.0
            connection_count = 0
            
            for member in members:
                connection_strength = await self._get_social_connection_strength(
                    user_id, member.user_id, db
                )
                if connection_strength > 0:
                    total_influence += connection_strength
                    connection_count += 1
            
            if connection_count > 0:
                return total_influence / connection_count
            
            return 0.0
            
        except Exception:
            return 0.0
    
    async def _get_social_connection_strength(
        self, 
        user_id: str, 
        friend_id: str, 
        db: AsyncSession
    ) -> float:
        """Get connection strength between two users"""
        try:
            connection_query = select(SocialConnection).where(
                and_(
                    SocialConnection.user_id == user_id,
                    SocialConnection.friend_id == friend_id
                )
            )
            
            result = await db.execute(connection_query)
            connection = result.scalar_one_or_none()
            
            if connection:
                return float(connection.connection_strength)
            
            return 0.0
            
        except Exception:
            return 0.0
    
    async def _count_shared_group_activities(
        self, 
        user_id: str, 
        friend_id: str, 
        db: AsyncSession
    ) -> int:
        """Count shared group buying activities between users"""
        try:
            # Find groups where both users are members
            shared_groups_query = select(func.count(Group.id)).select_from(
                Group
            ).join(
                GroupMember, Group.id == GroupMember.group_id
            ).where(
                and_(
                    GroupMember.user_id == user_id,
                    Group.id.in_(
                        select(GroupMember.group_id).where(
                            GroupMember.user_id == friend_id
                        )
                    )
                )
            )
            
            result = await db.execute(shared_groups_query)
            shared_count = result.scalar() or 0
            
            return shared_count
            
        except Exception:
            return 0
    
    def _generate_recommendation_reason(
        self, 
        gbgcn_rec: Dict[str, Any], 
        group_potential: float
    ) -> str:
        """Generate human-readable recommendation reason"""
        score = gbgcn_rec['score']
        
        if score > 0.8 and group_potential > 0.6:
            return "Highly recommended based on your preferences and strong group buying potential"
        elif score > 0.6:
            return "Recommended based on your past activity and similar users"
        elif group_potential > 0.7:
            return "Popular item for group buying with good discount potential"
        else:
            return "Suggested based on GBGCN analysis"
    
    def _generate_group_recommendation_reason(
        self, 
        item_score: float, 
        success_prob: float, 
        social_influence: float
    ) -> str:
        """Generate reason for group recommendation"""
        if social_influence > 0.5:
            return f"Your friends are in this group (social score: {social_influence:.2f})"
        elif success_prob > 0.7:
            return f"High success probability ({success_prob:.1%}) with good item match"
        elif item_score > 0.6:
            return f"Item matches your interests (score: {item_score:.2f})"
        else:
            return "Recommended by GBGCN algorithm"
    
    async def _generate_optimization_suggestions(
        self,
        formation_prediction: Dict[str, Any],
        participant_analysis: List[Dict[str, Any]],
        target_size: int
    ) -> List[str]:
        """Generate suggestions for optimizing group formation"""
        suggestions = []
        
        success_prob = formation_prediction['group_success_probability']
        
        if success_prob < 0.5:
            suggestions.append("Consider inviting users with higher social connections")
        
        high_interest_participants = [
            p for p in participant_analysis 
            if p['predicted_participation_probability'] > 0.7
        ]
        
        if len(high_interest_participants) < target_size * 0.6:
            suggestions.append("Consider reducing target group size for better success rate")
        
        low_social_participants = [
            p for p in participant_analysis 
            if p['social_connection_strength'] < 0.3
        ]
        
        if len(low_social_participants) > target_size * 0.5:
            suggestions.append("Add more participants with stronger social connections")
        
        if not suggestions:
            suggestions.append("Group formation looks optimal!")
        
        return suggestions 