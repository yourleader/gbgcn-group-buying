"""
Create Test Data for GBGCN System
Generates realistic sample data for testing and development
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.database.connection import get_db
from src.database.models import (
    User, Item, Group, GroupMember, UserItemInteraction, 
    SocialConnection, GBGCNEmbedding, GroupRecommendation
)
from src.core.logging import get_logger

logger = get_logger(__name__)

# Test Data Configuration
TEST_DATA_CONFIG = {
    "users": 100,
    "items": 500,
    "groups": 50,
    "interactions_per_user": 15,
    "social_connections_per_user": 8,
    "group_members_avg": 6
}

# Sample Data
USER_NAMES = [
    "Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Emma Brown",
    "Frank Miller", "Grace Lee", "Henry Taylor", "Iris Chen", "Jack Williams",
    "Kate Anderson", "Liam Garcia", "Maya Patel", "Noah Rodriguez", "Olivia Martinez",
    "Paul Thompson", "Quinn Zhang", "Rachel Kumar", "Sam Ahmed", "Tina Lopez"
]

ITEM_CATEGORIES = [
    "Electronics", "Clothing", "Home & Garden", "Sports", "Books",
    "Beauty", "Toys", "Automotive", "Food", "Health"
]

ITEM_NAMES = {
    "Electronics": ["Smartphone", "Laptop", "Headphones", "Tablet", "Smart Watch"],
    "Clothing": ["T-Shirt", "Jeans", "Dress", "Jacket", "Shoes"],
    "Home & Garden": ["Coffee Maker", "Plant Pot", "Lamp", "Cushion", "Mirror"],
    "Sports": ["Running Shoes", "Yoga Mat", "Dumbbells", "Tennis Racket", "Bicycle"],
    "Books": ["Novel", "Cookbook", "Biography", "Self-Help", "Science Fiction"],
    "Beauty": ["Skincare Set", "Makeup Kit", "Perfume", "Hair Care", "Nail Polish"],
    "Toys": ["Board Game", "Puzzle", "Action Figure", "Doll", "Building Blocks"],
    "Automotive": ["Car Accessories", "Motor Oil", "Car Cover", "Phone Mount", "Dash Cam"],
    "Food": ["Organic Snacks", "Coffee Beans", "Spice Set", "Honey", "Tea Collection"],
    "Health": ["Vitamins", "Protein Powder", "First Aid Kit", "Thermometer", "Scale"]
}

GROUP_THEMES = [
    "Tech Enthusiasts", "Fashion Forward", "Home Decorators", "Fitness Fanatics",
    "Book Lovers", "Beauty Gurus", "Game Night", "Car Enthusiasts",
    "Foodies United", "Health & Wellness"
]

class TestDataGenerator:
    def __init__(self):
        self.users: List[User] = []
        self.items: List[Item] = []
        self.groups: List[Group] = []
        
    async def generate_all_data(self):
        """Generate all test data"""
        logger.info("🚀 Starting test data generation...")
        
        try:
            async for db in get_db():
                # Clear existing data
                await self._clear_existing_data(db)
                
                # Generate core entities
                await self._generate_users(db)
                await self._generate_items(db)
                await self._generate_groups(db)
                
                # Generate relationships
                await self._generate_social_connections(db)
                await self._generate_user_interactions(db)
                await self._generate_group_members(db)
                await self._generate_group_recommendations(db)
                
                # Generate GBGCN embeddings
                await self._generate_embeddings(db)
                
                await db.commit()
                logger.info("✅ Test data generation completed successfully!")
                
                # Print summary
                await self._print_data_summary(db)
                
        except Exception as e:
            logger.error(f"❌ Test data generation failed: {e}")
            raise
    
    async def _clear_existing_data(self, db):
        """Clear existing test data"""
        logger.info("🧹 Clearing existing data...")
        
        # Note: In production, be very careful with this!
        tables_to_clear = [
            GroupRecommendation, GBGCNEmbedding, GroupMember,
            UserItemInteraction, SocialConnection, Group, Item, User
        ]
        
        for table in tables_to_clear:
            await db.execute(f"DELETE FROM {table.__tablename__}")
    
    async def _generate_users(self, db):
        """Generate test users"""
        logger.info(f"👥 Generating {TEST_DATA_CONFIG['users']} users...")
        
        for i in range(TEST_DATA_CONFIG['users']):
            base_name = USER_NAMES[i % len(USER_NAMES)]
            username = f"{base_name.lower().replace(' ', '_')}_{i+1:03d}"
            email = f"{username}@testmail.com"
            
            user = User(
                id=f"user_{i+1:03d}",
                username=username,
                email=email,
                password_hash="$2b$12$test_hash_for_development",  # bcrypt hash for "password123"
                full_name=f"{base_name} {i+1}",
                phone=f"+1555{i+1:07d}",
                role="admin" if i == 0 else "user",  # First user is admin
                is_active=True,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
                last_login=datetime.utcnow() - timedelta(hours=random.randint(1, 168))
            )
            
            db.add(user)
            self.users.append(user)
    
    async def _generate_items(self, db):
        """Generate test items"""
        logger.info(f"📦 Generating {TEST_DATA_CONFIG['items']} items...")
        
        for i in range(TEST_DATA_CONFIG['items']):
            category = random.choice(ITEM_CATEGORIES)
            item_name = random.choice(ITEM_NAMES[category])
            
            item = Item(
                id=f"item_{i+1:03d}",
                name=f"{item_name} {random.choice(['Pro', 'Plus', 'Max', 'Elite', 'Standard'])}",
                description=f"High-quality {item_name.lower()} for {category.lower()} enthusiasts",
                category=category,
                price=round(random.uniform(10.0, 500.0), 2),
                min_group_size=random.randint(3, 8),
                max_group_size=random.randint(10, 25),
                group_discount_percent=random.randint(10, 30),
                is_active=True,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 180))
            )
            
            db.add(item)
            self.items.append(item)
    
    async def _generate_groups(self, db):
        """Generate test groups"""
        logger.info(f"👥 Generating {TEST_DATA_CONFIG['groups']} groups...")
        
        statuses = ['active', 'completed', 'failed', 'cancelled']
        status_weights = [0.4, 0.3, 0.2, 0.1]  # More active groups
        
        for i in range(TEST_DATA_CONFIG['groups']):
            item = random.choice(self.items)
            initiator = random.choice(self.users)
            status = random.choices(statuses, weights=status_weights)[0]
            
            # Group creation time
            created_at = datetime.utcnow() - timedelta(days=random.randint(1, 90))
            
            # Determine target and current members
            target_size = random.randint(item.min_group_size, item.max_group_size)
            if status == 'completed':
                current_members = target_size
            elif status == 'active':
                current_members = random.randint(1, target_size - 1)
            else:
                current_members = random.randint(1, target_size)
            
            group = Group(
                id=f"group_{i+1:03d}",
                name=f"{random.choice(GROUP_THEMES)} - {item.name}",
                description=f"Group buying {item.name} with {target_size} people for maximum discount!",
                item_id=item.id,
                initiator_id=initiator.id,
                target_size=target_size,
                current_members=current_members,
                status=status,
                end_date=created_at + timedelta(days=random.randint(7, 30)),
                created_at=created_at,
                updated_at=created_at + timedelta(days=random.randint(0, 7)),
                gbgcn_success_prediction=random.uniform(0.3, 0.9),
                gbgcn_prediction_updated_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24))
            )
            
            db.add(group)
            self.groups.append(group)
    
    async def _generate_social_connections(self, db):
        """Generate social connections between users"""
        logger.info("🤝 Generating social connections...")
        
        connection_count = 0
        for user in self.users:
            # Each user gets some random connections
            num_connections = random.randint(2, TEST_DATA_CONFIG['social_connections_per_user'])
            potential_friends = [u for u in self.users if u.id != user.id]
            friends = random.sample(potential_friends, min(num_connections, len(potential_friends)))
            
            for friend in friends:
                # Avoid duplicate connections
                existing = False
                # In real implementation, check if connection already exists
                
                if not existing:
                    connection = SocialConnection(
                        id=f"conn_{connection_count+1:06d}",
                        user_id=user.id,
                        connected_user_id=friend.id,
                        connection_type="friend",
                        connection_strength=random.uniform(0.3, 1.0),
                        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 365))
                    )
                    
                    db.add(connection)
                    connection_count += 1
    
    async def _generate_user_interactions(self, db):
        """Generate user-item interactions"""
        logger.info("📊 Generating user interactions...")
        
        interaction_types = ['view', 'like', 'add_to_cart', 'purchase', 'share']
        type_weights = [0.4, 0.2, 0.2, 0.1, 0.1]
        
        interaction_count = 0
        for user in self.users:
            # Each user interacts with multiple items
            num_interactions = random.randint(5, TEST_DATA_CONFIG['interactions_per_user'])
            interacted_items = random.sample(self.items, min(num_interactions, len(self.items)))
            
            for item in interacted_items:
                interaction_type = random.choices(interaction_types, weights=type_weights)[0]
                
                # Rating based on interaction type
                rating_map = {
                    'view': random.uniform(2.0, 3.5),
                    'like': random.uniform(3.5, 4.5),
                    'add_to_cart': random.uniform(4.0, 4.8),
                    'purchase': random.uniform(4.5, 5.0),
                    'share': random.uniform(4.0, 5.0)
                }
                
                interaction = UserItemInteraction(
                    id=f"interaction_{interaction_count+1:06d}",
                    user_id=user.id,
                    item_id=item.id,
                    interaction_type=interaction_type,
                    rating=round(rating_map[interaction_type], 1),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 180)),
                    gbgcn_processed=random.choice([True, False])  # Some processed, some not
                )
                
                db.add(interaction)
                interaction_count += 1
    
    async def _generate_group_members(self, db):
        """Generate group memberships"""
        logger.info("👥 Generating group memberships...")
        
        member_count = 0
        for group in self.groups:
            # Add the initiator first
            initiator_member = GroupMember(
                id=f"member_{member_count+1:06d}",
                group_id=group.id,
                user_id=group.initiator_id,
                role="initiator",
                joined_at=group.created_at,
                is_active=True
            )
            db.add(initiator_member)
            member_count += 1
            
            # Add other members
            members_needed = group.current_members - 1  # Minus initiator
            if members_needed > 0:
                potential_members = [u for u in self.users if u.id != group.initiator_id]
                selected_members = random.sample(potential_members, min(members_needed, len(potential_members)))
                
                for i, member_user in enumerate(selected_members):
                    member = GroupMember(
                        id=f"member_{member_count+1:06d}",
                        group_id=group.id,
                        user_id=member_user.id,
                        role="member",
                        joined_at=group.created_at + timedelta(hours=random.randint(1, 48)),
                        is_active=True
                    )
                    db.add(member)
                    member_count += 1
    
    async def _generate_group_recommendations(self, db):
        """Generate GBGCN group recommendations"""
        logger.info("🎯 Generating group recommendations...")
        
        rec_count = 0
        for group in self.groups:
            # Generate recommendations for this group
            num_recs = random.randint(1, 3)
            
            for i in range(num_recs):
                # Success based on group status
                if group.status == 'completed':
                    actual_success = True
                    confidence = random.uniform(0.7, 0.95)
                elif group.status == 'failed':
                    actual_success = False  
                    confidence = random.uniform(0.2, 0.6)
                else:
                    actual_success = None  # Unknown yet
                    confidence = random.uniform(0.4, 0.9)
                
                recommendation = GroupRecommendation(
                    id=f"rec_{rec_count+1:06d}",
                    group_id=group.id,
                    item_id=group.item_id,
                    recommended_for_user_id=random.choice(self.users).id,
                    confidence_score=confidence,
                    recommendation_reason=f"GBGCN predicted high group success probability based on social influence and item popularity",
                    actual_success=actual_success,
                    created_at=group.created_at + timedelta(hours=random.randint(1, 12))
                )
                
                db.add(recommendation)
                rec_count += 1
    
    async def _generate_embeddings(self, db):
        """Generate sample GBGCN embeddings"""
        logger.info("🧠 Generating GBGCN embeddings...")
        
        embedding_count = 0
        
        # User embeddings
        for user in self.users[:20]:  # Sample for first 20 users
            embedding = GBGCNEmbedding(
                id=f"emb_{embedding_count+1:06d}",
                entity_id=user.id,
                entity_type="user",
                embedding_data=json.dumps([random.uniform(-1, 1) for _ in range(64)]),  # 64-dim vector
                model_version="1.0.0",
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72))
            )
            db.add(embedding)
            embedding_count += 1
        
        # Item embeddings  
        for item in self.items[:50]:  # Sample for first 50 items
            embedding = GBGCNEmbedding(
                id=f"emb_{embedding_count+1:06d}",
                entity_id=item.id,
                entity_type="item",
                embedding_data=json.dumps([random.uniform(-1, 1) for _ in range(64)]),  # 64-dim vector
                model_version="1.0.0",
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72))
            )
            db.add(embedding)
            embedding_count += 1
    
    async def _print_data_summary(self, db):
        """Print summary of generated data"""
        from sqlalchemy import select, func
        
        # Count entities
        user_count = await db.execute(select(func.count(User.id)))
        item_count = await db.execute(select(func.count(Item.id)))
        group_count = await db.execute(select(func.count(Group.id)))
        interaction_count = await db.execute(select(func.count(UserItemInteraction.id)))
        connection_count = await db.execute(select(func.count(SocialConnection.id)))
        embedding_count = await db.execute(select(func.count(GBGCNEmbedding.id)))
        
        print("\n" + "="*50)
        print("📊 TEST DATA GENERATION SUMMARY")
        print("="*50)
        print(f"👥 Users: {user_count.scalar()}")
        print(f"📦 Items: {item_count.scalar()}")
        print(f"🎯 Groups: {group_count.scalar()}")
        print(f"📊 Interactions: {interaction_count.scalar()}")
        print(f"🤝 Social Connections: {connection_count.scalar()}")
        print(f"🧠 Embeddings: {embedding_count.scalar()}")
        print("="*50)
        print("✅ Ready for GBGCN testing!")
        print("🌐 API Docs: http://localhost:8000/docs")
        print("📱 Flutter can now connect to the API")
        print("="*50)

async def main():
    """Main function to run test data generation"""
    try:
        generator = TestDataGenerator()
        await generator.generate_all_data()
        print("\n🎉 Test data generation completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test data generation failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 