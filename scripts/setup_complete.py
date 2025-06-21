#!/usr/bin/env python3
"""
Complete Setup Script for GBGCN Group Buying System
Initializes database, generates sample data, and trains the model
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.database.connection import init_db, get_db
from src.database.models import (
    User, Item, Group, GroupMember, UserItemInteraction, 
    SocialConnection, GBGCNEmbedding
)
from src.core.config import settings
from src.core.logging import setup_logging
from src.ml.gbgcn_trainer import GBGCNTrainer
from scripts.simple_data_generator import SimpleDataGenerator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompleteSetup:
    """
    Complete setup for GBGCN Group Buying System
    """
    
    def __init__(self):
        self.logger = logger
        self.data_generator = SimpleDataGenerator()
        self.gbgcn_trainer = None
    
    async def run_complete_setup(self):
        """Run the complete setup process"""
        try:
            self.logger.info("🚀 Starting GBGCN Group Buying System Setup")
            
            # Step 1: Initialize Database
            await self.setup_database()
            
            # Step 2: Generate Sample Data
            await self.generate_sample_data()
            
            # Step 3: Initialize and Train GBGCN Model
            await self.setup_gbgcn_model()
            
            # Step 4: Verify Setup
            await self.verify_setup()
            
            self.logger.info("✅ GBGCN System Setup Complete!")
            self.print_summary()
            
        except Exception as e:
            self.logger.error(f"❌ Setup failed: {e}")
            raise
    
    async def setup_database(self):
        """Initialize the database"""
        self.logger.info("📊 Setting up database...")
        
        try:
            await init_db()
            self.logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Database setup failed: {e}")
            raise
    
    async def generate_sample_data(self):
        """Generate sample data for testing"""
        self.logger.info("🏭 Generating sample data...")
        
        try:
            # Generate comprehensive sample data
            await self.data_generator.generate_all_data(
                num_users=1000,
                num_items=300,
                num_groups=50,
                num_interactions=5000,
                num_social_connections=2000
            )
            
            self.logger.info("✅ Sample data generated successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Sample data generation failed: {e}")
            raise
    
    async def setup_gbgcn_model(self):
        """Initialize and train the GBGCN model"""
        self.logger.info("🧠 Setting up GBGCN model...")
        
        try:
            # Initialize trainer
            self.gbgcn_trainer = GBGCNTrainer()
            await self.gbgcn_trainer.initialize()
            
            self.logger.info("✅ GBGCN model initialized")
            
            # Train the model
            self.logger.info("🏋️ Training GBGCN model...")
            training_result = await self.gbgcn_trainer.train(num_epochs=50)
            
            self.logger.info(f"✅ GBGCN training completed: {training_result['status']}")
            self.logger.info(f"📈 Best validation loss: {training_result['best_val_loss']:.4f}")
            
        except Exception as e:
            self.logger.error(f"❌ GBGCN setup failed: {e}")
            # Continue without GBGCN for basic functionality
            self.logger.warning("⚠️ Continuing without GBGCN model")
    
    async def verify_setup(self):
        """Verify that the setup is working correctly"""
        self.logger.info("🔍 Verifying setup...")
        
        try:
            async for db in get_db():
                # Check data counts
                from sqlalchemy import select, func
                
                # Count users
                users_result = await db.execute(select(func.count(User.id)))
                user_count = users_result.scalar()
                
                # Count items
                items_result = await db.execute(select(func.count(Item.id)))
                item_count = items_result.scalar()
                
                # Count groups
                groups_result = await db.execute(select(func.count(Group.id)))
                group_count = groups_result.scalar()
                
                # Count interactions
                interactions_result = await db.execute(select(func.count(UserItemInteraction.id)))
                interaction_count = interactions_result.scalar()
                
                # Count social connections
                social_result = await db.execute(select(func.count(SocialConnection.id)))
                social_count = social_result.scalar()
                
                self.logger.info(f"📊 Data verification:")
                self.logger.info(f"   Users: {user_count}")
                self.logger.info(f"   Items: {item_count}")
                self.logger.info(f"   Groups: {group_count}")
                self.logger.info(f"   Interactions: {interaction_count}")
                self.logger.info(f"   Social connections: {social_count}")
                
                # Test GBGCN if available
                if self.gbgcn_trainer and self.gbgcn_trainer.is_ready():
                    # Get a sample user for testing
                    user_result = await db.execute(select(User).limit(1))
                    sample_user = user_result.scalar_one_or_none()
                    
                    if sample_user:
                        # Test item recommendations
                        recommendations = await self.gbgcn_trainer.predict_item_recommendations(
                            sample_user.id, k=5
                        )
                        self.logger.info(f"🎯 GBGCN recommendations test: {len(recommendations)} items")
                
                break
                
            self.logger.info("✅ Setup verification completed")
            
        except Exception as e:
            self.logger.error(f"❌ Setup verification failed: {e}")
            raise
    
    def print_summary(self):
        """Print setup summary"""
        print("\n" + "="*60)
        print("🎉 GBGCN GROUP BUYING SYSTEM READY!")
        print("="*60)
        print()
        print("📋 SETUP SUMMARY:")
        print(f"   ✅ Database: PostgreSQL initialized")
        print(f"   ✅ Sample Data: Generated successfully")
        if self.gbgcn_trainer and self.gbgcn_trainer.is_ready():
            print(f"   ✅ GBGCN Model: Trained and ready")
        else:
            print(f"   ⚠️ GBGCN Model: Not available (basic functionality only)")
        print()
        print("🚀 NEXT STEPS:")
        print("   1. Start the API server:")
        print("      docker-compose up -d")
        print()
        print("   2. Access the API at:")
        print(f"      http://localhost:{settings.API_PORT}")
        print()
        print("   3. Check the API documentation:")
        print(f"      http://localhost:{settings.API_PORT}/docs")
        print()
        print("   4. Test the system:")
        print("      python test_api.py")
        print()
        print("📚 DOCUMENTATION:")
        print("   - README.md: Complete setup guide")
        print("   - API_DOCUMENTATION.md: API reference")
        print("   - IMPLEMENTATION_SUMMARY.md: Technical details")
        print()
        print("🔧 CONFIGURATION:")
        print(f"   - Database: {settings.DATABASE_URL}")
        print(f"   - Redis: {settings.REDIS_URL}")
        print(f"   - Model Path: {settings.MODEL_SAVE_PATH}")
        print()
        print("="*60)

async def main():
    """Main setup function"""
    setup = CompleteSetup()
    await setup.run_complete_setup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1) 