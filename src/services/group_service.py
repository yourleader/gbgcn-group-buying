"""
Group Service for Group Buying System
Handles group creation, joining, and management logic
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, update

from src.database.models import (
    User, Item, Group, GroupMember, UserItemInteraction, 
    SocialConnection, GroupRecommendation
)
from src.core.config import settings
from src.core.logging import get_model_logger
from src.database.connection import get_db

logger = get_model_logger()

class GroupService:
    """
    Service layer for group buying operations
    """
    
    def __init__(self, gbgcn_trainer=None):
        self.gbgcn_trainer = gbgcn_trainer
        self.logger = logger
    
    async def create_group(
        self,
        initiator_id: str,
        item_id: str,
        title: str,
        description: str,
        target_size: int,
        min_size: int,
        target_price: float,
        duration_days: int = 7,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Create a new group buying session
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Validate inputs
            if target_size < min_size:
                raise ValueError("Target size must be >= minimum size")
            
            if min_size < settings.MIN_GROUP_SIZE:
                raise ValueError(f"Minimum size must be >= {settings.MIN_GROUP_SIZE}")
            
            if target_size > settings.MAX_GROUP_SIZE:
                raise ValueError(f"Target size must be <= {settings.MAX_GROUP_SIZE}")
            
            # Check if user and item exist
            user = await db.get(User, initiator_id)
            item = await db.get(Item, item_id)
            
            if not user:
                raise ValueError(f"User {initiator_id} not found")
            if not item:
                raise ValueError(f"Item {item_id} not found")
            
            # Calculate pricing
            original_price = float(item.price)
            discount_percentage = await self._calculate_discount_percentage(
                target_size, item, db
            )
            
            current_price = original_price
            target_discounted_price = original_price * (1 - discount_percentage)
            
            # Create end time
            end_time = datetime.utcnow() + timedelta(days=duration_days)
            
            # Create group
            new_group = Group(
                initiator_id=initiator_id,
                item_id=item_id,
                title=title,
                description=description,
                target_size=target_size,
                min_size=min_size,
                current_size=1,  # Initiator is automatically a member
                original_price=Decimal(str(original_price)),
                current_price=Decimal(str(current_price)),
                target_price=Decimal(str(target_discounted_price)),
                status='active',
                end_time=end_time,
                created_at=datetime.utcnow()
            )
            
            db.add(new_group)
            await db.flush()  # Get the group ID
            
            # Add initiator as first member
            initiator_member = GroupMember(
                group_id=new_group.id,
                user_id=initiator_id,
                role='initiator',
                joined_at=datetime.utcnow(),
                status='active'
            )
            
            db.add(initiator_member)
            await db.commit()
            
            # Predict success probability using GBGCN
            success_probability = 0.5  # Default
            if self.gbgcn_trainer and self.gbgcn_trainer.is_ready():
                try:
                    success_probability = await self.gbgcn_trainer.predict_group_success(
                        new_group.id
                    )
                except Exception as e:
                    self.logger.warning(f"Could not predict group success: {e}")
            
            # Update group with GBGCN prediction
            new_group.gbgcn_success_prediction = success_probability
            await db.commit()
            
            return {
                'group_id': new_group.id,
                'status': 'created',
                'current_size': 1,
                'target_size': target_size,
                'success_probability': success_probability,
                'end_time': end_time.isoformat(),
                'current_price': float(current_price),
                'target_price': float(target_discounted_price),
                'discount_percentage': discount_percentage
            }
            
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Error creating group: {e}")
            raise
    
    async def join_group(
        self,
        user_id: str,
        group_id: str,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Join an existing group
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Get group with members
            group_query = select(Group).options(
                selectinload(Group.members),
                selectinload(Group.item)
            ).where(Group.id == group_id)
            
            result = await db.execute(group_query)
            group = result.scalar_one_or_none()
            
            if not group:
                raise ValueError(f"Group {group_id} not found")
            
            # Check if group is still active
            if group.status != 'active':
                raise ValueError(f"Group is {group.status} and cannot accept new members")
            
            if group.end_time <= datetime.utcnow():
                raise ValueError("Group has expired")
            
            # Check if user is already a member
            existing_member = next(
                (m for m in group.members if m.user_id == user_id), None
            )
            if existing_member:
                raise ValueError("User is already a member of this group")
            
            # Check if group is full
            if group.current_size >= group.target_size:
                raise ValueError("Group is already full")
            
            # Check user exists
            user = await db.get(User, user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Add user to group
            new_member = GroupMember(
                group_id=group_id,
                user_id=user_id,
                role='participant',
                joined_at=datetime.utcnow(),
                status='active'
            )
            
            db.add(new_member)
            
            # Update group size and pricing
            new_size = group.current_size + 1
            new_price = await self._calculate_current_price(
                group, new_size, db
            )
            
            # Update group
            group.current_size = new_size
            group.current_price = Decimal(str(new_price))
            
            # Update GBGCN prediction
            if self.gbgcn_trainer and self.gbgcn_trainer.is_ready():
                try:
                    new_success_prob = await self.gbgcn_trainer.predict_group_success(
                        group_id
                    )
                    group.gbgcn_success_prediction = new_success_prob
                except Exception as e:
                    self.logger.warning(f"Could not update group success prediction: {e}")
            
            await db.commit()
            
            # Check if group is complete
            completion_status = await self._check_group_completion(group, db)
            
            return {
                'status': 'joined',
                'group_id': group_id,
                'new_size': new_size,
                'target_size': group.target_size,
                'new_price': float(new_price),
                'target_price': float(group.target_price),
                'success_probability': group.gbgcn_success_prediction,
                'completion_status': completion_status
            }
            
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Error joining group {group_id}: {e}")
            raise
    
    async def leave_group(
        self,
        user_id: str,
        group_id: str,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Leave a group (if allowed)
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Get group and member
            group = await db.get(Group, group_id)
            if not group:
                raise ValueError(f"Group {group_id} not found")
            
            member_query = select(GroupMember).where(
                and_(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id
                )
            )
            result = await db.execute(member_query)
            member = result.scalar_one_or_none()
            
            if not member:
                raise ValueError("User is not a member of this group")
            
            # Check if leaving is allowed
            if group.status == 'completed':
                raise ValueError("Cannot leave completed group")
            
            if member.role == 'initiator' and group.current_size > 1:
                raise ValueError("Initiator cannot leave group with other members")
            
            # Remove member
            await db.delete(member)
            
            # Update group size and pricing
            new_size = group.current_size - 1
            
            if new_size == 0:
                # Delete empty group
                group.status = 'cancelled'
            else:
                new_price = await self._calculate_current_price(
                    group, new_size, db
                )
                group.current_size = new_size
                group.current_price = Decimal(str(new_price))
            
            await db.commit()
            
            return {
                'status': 'left',
                'group_id': group_id,
                'new_size': new_size,
                'group_status': group.status
            }
            
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Error leaving group {group_id}: {e}")
            raise
    
    async def get_group_details(
        self,
        group_id: str,
        requesting_user_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Get detailed information about a group
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Get group with all relations
            group_query = select(Group).options(
                selectinload(Group.members).selectinload(GroupMember.user),
                selectinload(Group.item),
                selectinload(Group.initiator)
            ).where(Group.id == group_id)
            
            result = await db.execute(group_query)
            group = result.scalar_one_or_none()
            
            if not group:
                raise ValueError(f"Group {group_id} not found")
            
            # Build member list
            members = []
            for member in group.members:
                member_info = {
                    'user_id': member.user_id,
                    'username': member.user.username,
                    'role': member.role,
                    'joined_at': member.joined_at.isoformat(),
                    'status': member.status
                }
                members.append(member_info)
            
            # Calculate time remaining
            time_remaining = (group.end_time - datetime.utcnow()).total_seconds()
            time_remaining_hours = max(0, time_remaining / 3600)
            
            # Check if requesting user is a member
            is_member = False
            user_role = None
            if requesting_user_id:
                user_member = next(
                    (m for m in group.members if m.user_id == requesting_user_id), None
                )
                if user_member:
                    is_member = True
                    user_role = user_member.role
            
            # Get join eligibility
            can_join = await self._check_join_eligibility(
                group, requesting_user_id, db
            )
            
            return {
                'group_id': group.id,
                'title': group.title,
                'description': group.description,
                'status': group.status,
                'item': {
                    'id': group.item.id,
                    'title': group.item.title,
                    'category': group.item.category,
                    'description': group.item.description,
                    'original_price': float(group.item.price)
                },
                'initiator': {
                    'id': group.initiator.id,
                    'username': group.initiator.username
                },
                'pricing': {
                    'original_price': float(group.original_price),
                    'current_price': float(group.current_price),
                    'target_price': float(group.target_price),
                    'discount_percentage': float(
                        (group.original_price - group.target_price) / group.original_price
                    )
                },
                'size': {
                    'current_size': group.current_size,
                    'target_size': group.target_size,
                    'min_size': group.min_size,
                    'slots_remaining': group.target_size - group.current_size
                },
                'timing': {
                    'created_at': group.created_at.isoformat(),
                    'end_time': group.end_time.isoformat(),
                    'time_remaining_hours': round(time_remaining_hours, 1)
                },
                'members': members,
                'user_context': {
                    'is_member': is_member,
                    'user_role': user_role,
                    'can_join': can_join
                },
                'gbgcn_prediction': {
                    'success_probability': group.gbgcn_success_prediction,
                    'last_updated': group.gbgcn_prediction_updated_at.isoformat() if group.gbgcn_prediction_updated_at else None
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting group details for {group_id}: {e}")
            raise
    
    async def get_user_groups(
        self,
        user_id: str,
        status_filter: Optional[str] = None,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        Get all groups for a user
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Get user's group memberships
            query = select(GroupMember).options(
                selectinload(GroupMember.group).selectinload(Group.item),
                selectinload(GroupMember.group).selectinload(Group.initiator)
            ).where(GroupMember.user_id == user_id)
            
            if status_filter:
                query = query.where(GroupMember.group.has(Group.status == status_filter))
            
            result = await db.execute(query)
            memberships = result.scalars().all()
            
            user_groups = []
            for membership in memberships:
                group = membership.group
                
                # Calculate progress percentage
                progress = (group.current_size / group.target_size) * 100
                
                # Time remaining
                time_remaining = (group.end_time - datetime.utcnow()).total_seconds()
                time_remaining_hours = max(0, time_remaining / 3600)
                
                group_info = {
                    'group_id': group.id,
                    'title': group.title,
                    'status': group.status,
                    'user_role': membership.role,
                    'item_title': group.item.title,
                    'current_size': group.current_size,
                    'target_size': group.target_size,
                    'progress_percentage': round(progress, 1),
                    'current_price': float(group.current_price),
                    'target_price': float(group.target_price),
                    'time_remaining_hours': round(time_remaining_hours, 1),
                    'joined_at': membership.joined_at.isoformat(),
                    'success_probability': group.gbgcn_success_prediction
                }
                
                user_groups.append(group_info)
            
            # Sort by most recent
            user_groups.sort(key=lambda x: x['joined_at'], reverse=True)
            
            return user_groups
            
        except Exception as e:
            self.logger.error(f"Error getting user groups for {user_id}: {e}")
            raise
    
    # Helper methods
    async def _calculate_discount_percentage(
        self, 
        target_size: int, 
        item: Item, 
        db: AsyncSession
    ) -> float:
        """Calculate discount percentage based on group size"""
        # Base discount from item settings
        base_discount = float(item.discount_percentage or 0.05)
        
        # Additional discount based on group size
        size_bonus = min(target_size * 0.01, 0.3)  # Max 30% additional
        
        total_discount = min(base_discount + size_bonus, settings.MAX_DISCOUNT_PERCENTAGE)
        
        return total_discount
    
    async def _calculate_current_price(
        self, 
        group: Group, 
        current_size: int, 
        db: AsyncSession
    ) -> float:
        """Calculate current price based on current group size"""
        original_price = float(group.original_price)
        target_price = float(group.target_price)
        
        # Progressive discount based on current size vs target size
        progress = current_size / group.target_size
        
        # Linear interpolation between original and target price
        current_price = original_price - (original_price - target_price) * progress
        
        return round(current_price, 2)
    
    async def _check_group_completion(
        self, 
        group: Group, 
        db: AsyncSession
    ) -> str:
        """Check if group should be completed"""
        if group.current_size >= group.target_size:
            group.status = 'completed'
            group.completion_time = datetime.utcnow()
            await db.commit()
            return 'completed'
        elif group.current_size >= group.min_size and group.end_time <= datetime.utcnow():
            group.status = 'completed'
            group.completion_time = datetime.utcnow()
            await db.commit()
            return 'completed'
        elif group.end_time <= datetime.utcnow():
            group.status = 'failed'
            await db.commit()
            return 'failed'
        
        return 'active'
    
    async def _check_join_eligibility(
        self, 
        group: Group, 
        user_id: Optional[str], 
        db: AsyncSession
    ) -> bool:
        """Check if a user can join the group"""
        if not user_id:
            return False
        
        if group.status != 'active':
            return False
        
        if group.end_time <= datetime.utcnow():
            return False
        
        if group.current_size >= group.target_size:
            return False
        
        # Check if already a member
        existing_member = next(
            (m for m in group.members if m.user_id == user_id), None
        )
        if existing_member:
            return False
        
        return True 