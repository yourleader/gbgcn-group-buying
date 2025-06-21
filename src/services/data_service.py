"""
Data Service for GBGCN Model
Handles data preprocessing and graph construction
"""

import torch
import numpy as np
from torch_geometric.data import Data, HeteroData
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_

from src.database.models import (
    User, Item, Group, GroupMember, UserItemInteraction, 
    SocialConnection, GBGCNEmbedding
)
from src.core.config import settings
from src.core.logging import get_model_logger
from src.database.connection import get_db

logger = get_model_logger()

class DataService:
    """
    Service for preparing data for GBGCN training and inference
    """
    
    def __init__(self):
        self.logger = logger
        self.user_id_to_index: Dict[str, int] = {}
        self.item_id_to_index: Dict[str, int] = {}
        self.index_to_user_id: Dict[int, str] = {}
        self.index_to_item_id: Dict[int, str] = {}
    
    async def get_data_statistics(self, db: AsyncSession = None) -> Dict[str, int]:
        """Get database statistics for model initialization"""
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Count users
            users_count_query = select(func.count(User.id))
            users_result = await db.execute(users_count_query)
            num_users = users_result.scalar() or 0
            
            # Count items
            items_count_query = select(func.count(Item.id))
            items_result = await db.execute(items_count_query)
            num_items = items_result.scalar() or 0
            
            # Count groups
            groups_count_query = select(func.count(Group.id))
            groups_result = await db.execute(groups_count_query)
            num_groups = groups_result.scalar() or 0
            
            # Count interactions
            interactions_count_query = select(func.count(UserItemInteraction.id))
            interactions_result = await db.execute(interactions_count_query)
            num_interactions = interactions_result.scalar() or 0
            
            # Count social connections
            social_count_query = select(func.count(SocialConnection.id))
            social_result = await db.execute(social_count_query)
            num_social = social_result.scalar() or 0
            
            return {
                'num_users': num_users,
                'num_items': num_items,
                'num_groups': num_groups,
                'num_interactions': num_interactions,
                'num_social_connections': num_social
            }
            
        except Exception as e:
            self.logger.error(f"Error getting data statistics: {e}")
            # Return default values for initialization
            return {
                'num_users': 1000,
                'num_items': 500,
                'num_groups': 100,
                'num_interactions': 5000,
                'num_social_connections': 2000
            }
    
    async def prepare_training_data(self, db: AsyncSession = None) -> Tuple[Data, Data]:
        """
        Prepare complete training and evaluation data for GBGCN
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Load all data
            users_data = await self._load_users_data(db)
            items_data = await self._load_items_data(db)
            interactions_data = await self._load_interactions_data(db)
            social_data = await self._load_social_data(db)
            groups_data = await self._load_groups_data(db)
            
            # Build mappings
            await self._build_id_mappings(users_data, items_data)
            
            # Construct heterogeneous graph
            hetero_data = await self._construct_heterogeneous_graph(
                users_data, items_data, interactions_data, social_data, groups_data
            )
            
            # Split into train/eval (80/20)
            train_data, eval_data = self._split_data(hetero_data, train_ratio=0.8)
            
            return train_data, eval_data
            
        except Exception as e:
            self.logger.error(f"Error preparing training data: {e}")
            # Return dummy data as fallback
            return self._create_dummy_data()
    
    async def prepare_user_data(self, user_id: str, db: AsyncSession = None) -> Data:
        """
        Prepare data for user-specific recommendations
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Get user's interaction history
            user_interactions = await self._get_user_interactions(user_id, db)
            
            # Get user's social connections
            user_social = await self._get_user_social_connections(user_id, db)
            
            # Get user's group history
            user_groups = await self._get_user_group_history(user_id, db)
            
            # Construct subgraph around this user
            subgraph_data = await self._construct_user_subgraph(
                user_id, user_interactions, user_social, user_groups, db
            )
            
            return subgraph_data
            
        except Exception as e:
            self.logger.error(f"Error preparing user data for {user_id}: {e}")
            return self._create_dummy_user_data()
    
    async def prepare_group_data(self, group_id: str, db: AsyncSession = None) -> Data:
        """
        Prepare data for group success prediction
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Get group details
            group_query = select(Group).options(
                selectinload(Group.members),
                selectinload(Group.item)
            ).where(Group.id == group_id)
            
            result = await db.execute(group_query)
            group = result.scalar_one_or_none()
            
            if not group:
                raise ValueError(f"Group {group_id} not found")
            
            # Get member interactions and social connections
            member_data = []
            for member in group.members:
                member_interactions = await self._get_user_interactions(member.user_id, db)
                member_social = await self._get_user_social_connections(member.user_id, db)
                member_data.append({
                    'user_id': member.user_id,
                    'interactions': member_interactions,
                    'social': member_social,
                    'join_time': member.joined_at,
                    'role': member.role
                })
            
            # Construct group-specific graph
            group_data = await self._construct_group_subgraph(
                group, member_data, db
            )
            
            return group_data
            
        except Exception as e:
            self.logger.error(f"Error preparing group data for {group_id}: {e}")
            return self._create_dummy_group_data()
    
    async def construct_hetero_graph_data(
        self, 
        user_ids: List[str], 
        item_ids: List[str], 
        db: AsyncSession = None
    ) -> HeteroData:
        """
        Construct heterogeneous graph data for specific users and items
        """
        if db is None:
            async for db in get_db():
                break
        
        try:
            # Load relevant data
            users_query = select(User).where(User.id.in_(user_ids))
            items_query = select(Item).where(Item.id.in_(item_ids))
            
            users_result = await db.execute(users_query)
            items_result = await db.execute(items_query)
            
            users = users_result.scalars().all()
            items = items_result.scalars().all()
            
            # Build mappings for this subset
            user_mapping = {user.id: idx for idx, user in enumerate(users)}
            item_mapping = {item.id: idx for idx, item in enumerate(items)}
            
            # Create heterogeneous data
            hetero_data = HeteroData()
            
            # User features
            user_features = torch.randn(len(users), settings.EMBEDDING_DIM)
            hetero_data['user'].x = user_features
            
            # Item features
            item_features = torch.randn(len(items), settings.EMBEDDING_DIM)
            hetero_data['item'].x = item_features
            
            # Get interactions between these users and items
            interactions_query = select(UserItemInteraction).where(
                and_(
                    UserItemInteraction.user_id.in_(user_ids),
                    UserItemInteraction.item_id.in_(item_ids)
                )
            )
            
            interactions_result = await db.execute(interactions_query)
            interactions = interactions_result.scalars().all()
            
            # Build interaction edges
            if interactions:
                user_indices = [user_mapping[inter.user_id] for inter in interactions]
                item_indices = [item_mapping[inter.item_id] for inter in interactions]
                
                hetero_data['user', 'interacts', 'item'].edge_index = torch.tensor([
                    user_indices, item_indices
                ], dtype=torch.long)
                
                # Edge attributes (ratings, timestamps, etc.)
                edge_attrs = []
                for inter in interactions:
                    attrs = [
                        inter.rating or 0.5,
                        inter.interaction_type == 'purchase' and 1.0 or 0.0,
                        (datetime.utcnow() - inter.created_at).days / 365.0  # Recency
                    ]
                    edge_attrs.append(attrs)
                
                hetero_data['user', 'interacts', 'item'].edge_attr = torch.tensor(
                    edge_attrs, dtype=torch.float
                )
            
            # Add social connections
            social_query = select(SocialConnection).where(
                and_(
                    SocialConnection.user_id.in_(user_ids),
                    SocialConnection.friend_id.in_(user_ids)
                )
            )
            
            social_result = await db.execute(social_query)
            social_connections = social_result.scalars().all()
            
            if social_connections:
                source_users = [user_mapping[conn.user_id] for conn in social_connections]
                target_users = [user_mapping[conn.friend_id] for conn in social_connections]
                
                hetero_data['user', 'friends', 'user'].edge_index = torch.tensor([
                    source_users, target_users
                ], dtype=torch.long)
                
                # Social edge attributes
                social_attrs = [[conn.connection_strength] for conn in social_connections]
                hetero_data['user', 'friends', 'user'].edge_attr = torch.tensor(
                    social_attrs, dtype=torch.float
                )
            
            return hetero_data
            
        except Exception as e:
            self.logger.error(f"Error constructing heterogeneous graph: {e}")
            return self._create_dummy_hetero_data()
    
    # Helper methods
    async def _load_users_data(self, db: AsyncSession) -> List[User]:
        """Load all users data"""
        query = select(User).options(selectinload(User.social_connections))
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _load_items_data(self, db: AsyncSession) -> List[Item]:
        """Load all items data"""
        query = select(Item)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _load_interactions_data(self, db: AsyncSession) -> List[UserItemInteraction]:
        """Load all user-item interactions"""
        query = select(UserItemInteraction)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _load_social_data(self, db: AsyncSession) -> List[SocialConnection]:
        """Load all social connections"""
        query = select(SocialConnection)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _load_groups_data(self, db: AsyncSession) -> List[Group]:
        """Load all groups data"""
        query = select(Group).options(selectinload(Group.members))
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _build_id_mappings(self, users: List[User], items: List[Item]):
        """Build ID to index mappings"""
        # User mappings
        self.user_id_to_index = {user.id: idx for idx, user in enumerate(users)}
        self.index_to_user_id = {idx: user.id for idx, user in enumerate(users)}
        
        # Item mappings
        self.item_id_to_index = {item.id: idx for idx, item in enumerate(items)}
        self.index_to_item_id = {idx: item.id for idx, item in enumerate(items)}
    
    async def _construct_heterogeneous_graph(
        self,
        users: List[User],
        items: List[Item],
        interactions: List[UserItemInteraction],
        social: List[SocialConnection],
        groups: List[Group]
    ) -> HeteroData:
        """Construct the complete heterogeneous graph"""
        
        hetero_data = HeteroData()
        
        # Node features
        num_users = len(users)
        num_items = len(items)
        
        # Initialize with random features (will be replaced by learned embeddings)
        hetero_data['user'].x = torch.randn(num_users, settings.EMBEDDING_DIM)
        hetero_data['item'].x = torch.randn(num_items, settings.EMBEDDING_DIM)
        
        # User-Item interaction edges
        if interactions:
            user_indices = []
            item_indices = []
            edge_attrs = []
            
            for inter in interactions:
                if (inter.user_id in self.user_id_to_index and 
                    inter.item_id in self.item_id_to_index):
                    
                    user_idx = self.user_id_to_index[inter.user_id]
                    item_idx = self.item_id_to_index[inter.item_id]
                    
                    user_indices.append(user_idx)
                    item_indices.append(item_idx)
                    
                    # Edge features: [rating, interaction_type, recency]
                    rating = inter.rating or 0.5
                    is_purchase = 1.0 if inter.interaction_type == 'purchase' else 0.0
                    recency = (datetime.utcnow() - inter.created_at).days / 365.0
                    
                    edge_attrs.append([rating, is_purchase, min(recency, 1.0)])
            
            if user_indices:
                hetero_data['user', 'interacts', 'item'].edge_index = torch.tensor([
                    user_indices, item_indices
                ], dtype=torch.long)
                
                hetero_data['user', 'interacts', 'item'].edge_attr = torch.tensor(
                    edge_attrs, dtype=torch.float
                )
        
        # Social connections
        if social:
            source_users = []
            target_users = []
            social_attrs = []
            
            for conn in social:
                if (conn.user_id in self.user_id_to_index and 
                    conn.friend_id in self.user_id_to_index):
                    
                    source_idx = self.user_id_to_index[conn.user_id]
                    target_idx = self.user_id_to_index[conn.friend_id]
                    
                    source_users.append(source_idx)
                    target_users.append(target_idx)
                    social_attrs.append([conn.connection_strength])
            
            if source_users:
                hetero_data['user', 'friends', 'user'].edge_index = torch.tensor([
                    source_users, target_users
                ], dtype=torch.long)
                
                hetero_data['user', 'friends', 'user'].edge_attr = torch.tensor(
                    social_attrs, dtype=torch.float
                )
        
        return hetero_data
    
    def _split_data(self, data: HeteroData, train_ratio: float = 0.8) -> Tuple[Data, Data]:
        """Split heterogeneous data into train/eval"""
        # For simplicity, we'll return the same data for both
        # In production, you'd implement proper train/test splitting
        return data, data
    
    def _create_dummy_data(self) -> Tuple[Data, Data]:
        """Create dummy data for fallback"""
        num_nodes = 1000
        num_edges = 2000
        
        x = torch.randn(num_nodes, settings.EMBEDDING_DIM)
        edge_index = torch.randint(0, num_nodes, (2, num_edges))
        
        train_data = Data(x=x, edge_index=edge_index)
        eval_data = Data(x=x, edge_index=edge_index)
        
        return train_data, eval_data
    
    def _create_dummy_user_data(self) -> Data:
        """Create dummy user data"""
        num_nodes = 100
        num_edges = 200
        
        x = torch.randn(num_nodes, settings.EMBEDDING_DIM)
        edge_index = torch.randint(0, num_nodes, (2, num_edges))
        
        return Data(x=x, edge_index=edge_index)
    
    def _create_dummy_group_data(self) -> Data:
        """Create dummy group data"""
        num_nodes = 50
        num_edges = 100
        
        x = torch.randn(num_nodes, settings.EMBEDDING_DIM)
        edge_index = torch.randint(0, num_nodes, (2, num_edges))
        
        return Data(x=x, edge_index=edge_index)
    
    def _create_dummy_hetero_data(self) -> HeteroData:
        """Create dummy heterogeneous data"""
        hetero_data = HeteroData()
        
        hetero_data['user'].x = torch.randn(100, settings.EMBEDDING_DIM)
        hetero_data['item'].x = torch.randn(50, settings.EMBEDDING_DIM)
        
        hetero_data['user', 'interacts', 'item'].edge_index = torch.randint(0, 50, (2, 200))
        hetero_data['user', 'friends', 'user'].edge_index = torch.randint(0, 100, (2, 150))
        
        return hetero_data
    
    async def _get_user_interactions(self, user_id: str, db: AsyncSession) -> List[UserItemInteraction]:
        """Get user's interaction history"""
        query = select(UserItemInteraction).where(UserItemInteraction.user_id == user_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _get_user_social_connections(self, user_id: str, db: AsyncSession) -> List[SocialConnection]:
        """Get user's social connections"""
        query = select(SocialConnection).where(SocialConnection.user_id == user_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _get_user_group_history(self, user_id: str, db: AsyncSession) -> List[GroupMember]:
        """Get user's group participation history"""
        query = select(GroupMember).options(
            selectinload(GroupMember.group)
        ).where(GroupMember.user_id == user_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _construct_user_subgraph(
        self,
        user_id: str,
        interactions: List[UserItemInteraction],
        social: List[SocialConnection],
        groups: List[GroupMember],
        db: AsyncSession
    ) -> Data:
        """Construct subgraph around a specific user"""
        # This is a simplified implementation
        # In production, you'd build a proper subgraph with k-hop neighbors
        
        num_nodes = len(interactions) + len(social) + 10  # Add some padding
        x = torch.randn(num_nodes, settings.EMBEDDING_DIM)
        
        # Create edges based on interactions and social connections
        edges = []
        for i, interaction in enumerate(interactions[:50]):  # Limit for efficiency
            edges.append([0, i + 1])  # User to item edges
        
        for i, conn in enumerate(social[:20]):  # Limit social connections
            edges.append([0, len(interactions) + i + 1])  # User to friend edges
        
        if edges:
            edge_index = torch.tensor(edges, dtype=torch.long).t()
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long)
        
        return Data(x=x, edge_index=edge_index)
    
    async def _construct_group_subgraph(
        self,
        group: Group,
        member_data: List[Dict[str, Any]],
        db: AsyncSession
    ) -> Data:
        """Construct subgraph for a specific group"""
        # Simplified group subgraph
        num_members = len(member_data)
        x = torch.randn(num_members + 1, settings.EMBEDDING_DIM)  # +1 for the item
        
        # Create edges between members and item
        edges = []
        for i in range(num_members):
            edges.append([i, num_members])  # Member to item edge
        
        # Add member-to-member edges based on social connections
        for i, member1 in enumerate(member_data):
            for j, member2 in enumerate(member_data):
                if i != j:
                    # Check if they're socially connected (simplified)
                    edges.append([i, j])
        
        if edges:
            edge_index = torch.tensor(edges, dtype=torch.long).t()
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long)
        
        return Data(x=x, edge_index=edge_index) 