"""
Database models for Group-Buying system based on GBGCN paper.
Implements heterogeneous graphs for users, items, and social interactions.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, 
    String, Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

Base = declarative_base()

# Enums from paper context
class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    MODERATOR = "MODERATOR"

class GroupStatus(str, Enum):
    FORMING = "FORMING"     # Initial state - group is being formed
    OPEN = "OPEN"           # Group is accepting participants
    FULL = "FULL"           # Target quantity reached
    ACTIVE = "ACTIVE"       # Group buying is in progress
    COMPLETED = "COMPLETED" # Successfully completed
    CANCELLED = "CANCELLED" # Cancelled (failed)
    EXPIRED = "EXPIRED"     # Time expired

class MemberStatus(str, Enum):
    PENDING = "PENDING"     # Waiting for confirmation
    ACTIVE = "ACTIVE"       # Active member
    CONFIRMED = "CONFIRMED" # Confirmed participant
    CANCELLED = "CANCELLED" # User cancelled
    REJECTED = "REJECTED"   # Rejected by initiator

class InteractionType(str, Enum):
    VIEW = "VIEW"
    CLICK = "CLICK"
    SHARE = "SHARE"
    JOIN_GROUP = "JOIN_GROUP"
    PURCHASE = "PURCHASE"
    RATE = "RATE"

# Core Models for GBGCN

class User(Base):
    """
    User model representing nodes in the heterogeneous graph.
    Stores both initiators and participants from the paper.
    """
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    avatar_url = Column(String(500))
    
    # User status and role
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default=UserRole.USER)
    
    # Social influence metrics (from paper)
    reputation_score = Column(Float, default=0.0)  # Social influence score
    total_groups_created = Column(Integer, default=0)
    total_groups_joined = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # Group buying success rate
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active = Column(DateTime)
    
    # Relationships for heterogeneous graph
    created_groups = relationship("Group", back_populates="creator", foreign_keys="Group.creator_id")
    group_memberships = relationship("GroupMember", back_populates="user")
    social_connections = relationship("SocialConnection", 
                                    foreign_keys="SocialConnection.user_id",
                                    back_populates="user")
    user_item_interactions = relationship("UserItemInteraction", back_populates="user")
    
    # GBGCN Embeddings (stored for inference optimization)
    initiator_embedding = Column(ARRAY(Float))  # Initiator view embedding
    participant_embedding = Column(ARRAY(Float))  # Participant view embedding

class Item(Base):
    """
    Item model representing product nodes in the heterogeneous graph.
    Includes group buying specific attributes from the paper.
    """
    __tablename__ = "items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    
    # Pricing information for group buying
    base_price = Column(Float, nullable=False)
    images = Column(ARRAY(String))  # Array of image URLs
    specifications = Column(JSON)   # Product specifications
    
    # Group buying constraints
    min_group_size = Column(Integer, default=2)    # Minimum for group buying
    max_group_size = Column(Integer, default=100)  # Maximum group size
    
    # Category and metadata
    category_id = Column(String, ForeignKey("categories.id"))
    brand = Column(String(100))
    model = Column(String(100))
    
    # Status
    is_active = Column(Boolean, default=True)
    is_group_buyable = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("Category", back_populates="items")
    price_tiers = relationship("PriceTier", back_populates="item", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="item")
    user_interactions = relationship("UserItemInteraction", back_populates="item")
    
    # GBGCN Item embedding
    item_embedding = Column(ARRAY(Float))  # Item embedding from GBGCN

class Category(Base):
    """Category model for organizing items"""
    __tablename__ = "categories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    image_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = relationship("Item", back_populates="category")

class PriceTier(Base):
    """
    Price tiers for group buying discounts.
    Implements the volume-based pricing from the paper.
    """
    __tablename__ = "price_tiers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = Column(String, ForeignKey("items.id", ondelete="CASCADE"))
    
    min_quantity = Column(Integer, nullable=False)
    max_quantity = Column(Integer)  # Null means no upper limit
    discount_percentage = Column(Float, nullable=False)  # 0.0 to 1.0
    final_price = Column(Float, nullable=False)
    
    # Relationships
    item = relationship("Item", back_populates="price_tiers")

class Group(Base):
    """
    Group model representing group buying instances.
    Core entity for GBGCN group formation and recommendation.
    """
    __tablename__ = "groups"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Group buying parameters
    target_quantity = Column(Integer, nullable=False)
    current_quantity = Column(Integer, default=0)
    min_participants = Column(Integer, default=2)
    
    # Alternative naming for consistency with service layer
    target_size = Column(Integer, nullable=False)
    current_size = Column(Integer, default=0)
    min_size = Column(Integer, default=2)
    
    # Status and timing
    status = Column(String(20), default=GroupStatus.FORMING, index=True)
    end_date = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)  # Alternative naming
    
    # Delivery information
    delivery_address = Column(Text)
    estimated_delivery_date = Column(DateTime)
    
    # Financial information
    current_price_per_unit = Column(Float)
    total_amount = Column(Float, default=0.0)
    
    # Additional pricing fields for service layer compatibility
    original_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    
    # Completion tracking
    completion_time = Column(DateTime)
    gbgcn_success_prediction = Column(Float)
    gbgcn_prediction_updated_at = Column(DateTime)
    
    # Foreign keys
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)
    item_id = Column(String, ForeignKey("items.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # GBGCN specific fields
    success_probability = Column(Float)  # Predicted by GBGCN model
    social_influence_score = Column(Float)  # Social network influence
    
    # Relationships for heterogeneous graph
    creator = relationship("User", back_populates="created_groups", foreign_keys=[creator_id])
    item = relationship("Item", back_populates="groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_group_status_created', 'status', 'created_at'),
        Index('idx_group_item_status', 'item_id', 'status'),
    )

class GroupMember(Base):
    """
    Group membership model representing user-group interactions.
    Captures both initiator and participant relationships from GBGCN paper.
    """
    __tablename__ = "group_members"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    
    # Member details
    quantity = Column(Integer, default=1)
    status = Column(String(20), default=MemberStatus.PENDING)
    is_initiator = Column(Boolean, default=False)  # True for group creator
    
    # Social influence factors (from paper)
    social_influence_received = Column(Float, default=0.0)
    influence_from_friends = Column(Integer, default=0)  # Number of friends in group
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="group_memberships")
    group = relationship("Group", back_populates="members")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'group_id', name='unique_user_group'),
        Index('idx_group_member_status', 'group_id', 'status'),
    )

class SocialConnection(Base):
    """
    Social network connections between users.
    Implements the social influence modeling from GBGCN paper.
    """
    __tablename__ = "social_connections"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    friend_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Connection strength (for social influence calculation)
    connection_strength = Column(Float, default=1.0)  # 0.0 to 1.0
    interaction_frequency = Column(Float, default=0.0)
    
    # Connection metadata
    connection_type = Column(String(50), default="friend")  # friend, family, colleague
    is_mutual = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="social_connections")
    friend = relationship("User", foreign_keys=[friend_id])
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'friend_id', name='unique_user_friend'),
        Index('idx_social_user_friend', 'user_id', 'friend_id'),
    )

class UserItemInteraction(Base):
    """
    User-Item interactions for building the heterogeneous graph.
    Captures various interaction types from the GBGCN paper.
    """
    __tablename__ = "user_item_interactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    item_id = Column(String, ForeignKey("items.id"), nullable=False)
    
    # Interaction details
    interaction_type = Column(String(20), nullable=False)  # view, click, share, etc.
    interaction_value = Column(Float, default=1.0)  # Strength of interaction
    
    # Context information
    group_id = Column(String, ForeignKey("groups.id"))  # If interaction was in group context
    session_id = Column(String(100))
    device_type = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="user_item_interactions")
    item = relationship("Item", back_populates="user_interactions")
    group = relationship("Group")
    
    # Indexes for GBGCN graph construction
    __table_args__ = (
        Index('idx_user_item_interaction', 'user_id', 'item_id', 'interaction_type'),
        Index('idx_interaction_time', 'created_at'),
    )

class GBGCNEmbedding(Base):
    """
    Store GBGCN model embeddings for fast inference.
    Implements the multi-view embeddings from the paper.
    """
    __tablename__ = "gbgcn_embeddings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Entity identification
    entity_type = Column(String(20), nullable=False)  # 'user' or 'item'
    entity_id = Column(String, nullable=False)
    
    # Multi-view embeddings (from GBGCN paper)
    initiator_view_embedding = Column(ARRAY(Float))  # Initiator view
    participant_view_embedding = Column(ARRAY(Float))  # Participant view
    
    # Model versioning
    model_version = Column(String(50), nullable=False)
    embedding_dimension = Column(Integer, default=64)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', 'model_version', 
                        name='unique_entity_embedding'),
        Index('idx_embedding_entity', 'entity_type', 'entity_id'),
    )

class GroupRecommendation(Base):
    """
    Store group recommendations generated by GBGCN model.
    """
    __tablename__ = "group_recommendations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    item_id = Column(String, ForeignKey("items.id"), nullable=False)
    
    # GBGCN prediction scores
    recommendation_score = Column(Float, nullable=False)
    success_probability = Column(Float)  # Probability of successful group formation
    social_influence_score = Column(Float)  # Social influence component
    
    # Recommendation context
    recommendation_type = Column(String(50))  # 'initiate' or 'join'
    target_group_size = Column(Integer)
    predicted_price = Column(Float)
    
    # Model information
    model_version = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User")
    item = relationship("Item")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_recommendations', 'user_id', 'recommendation_score'),
        Index('idx_recommendation_time', 'created_at'),
    ) 