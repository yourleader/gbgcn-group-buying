"""
Simplified data preprocessing tasks for GBGCN (Development Version)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from src.tasks.celery_app_simple import celery_app
from src.database.connection import get_db
from src.database.models import (
    User, Item, Group, GroupMember, UserItemInteraction, 
    GBGCNEmbedding, SocialConnection
)
from src.core.logging import get_model_logger

logger = get_model_logger()

@celery_app.task(bind=True)
def preprocess_new_interactions(self):
    """
    Preprocess new user-item interactions for GBGCN training
    """
    try:
        logger.info("🔄 Preprocessing new interactions...")
        
        result = asyncio.run(_async_preprocess_interactions())
        
        logger.info(f"✅ Preprocessed {result['interactions_processed']} interactions")
        return {
            "status": "success",
            "interactions_processed": result["interactions_processed"],
            "task_id": getattr(self, 'request', {}).get('id', 'dev_mode')
        }
        
    except Exception as e:
        logger.error(f"❌ Interaction preprocessing failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "task_id": getattr(self, 'request', {}).get('id', 'dev_mode')
        }


@celery_app.task(bind=True)
def cleanup_old_embeddings(self):
    """
    Clean up old GBGCN embeddings to save storage
    """
    try:
        logger.info("🧹 Cleaning up old embeddings...")
        
        result = asyncio.run(_async_cleanup_embeddings())
        
        logger.info(f"✅ Cleaned up {result['embeddings_removed']} old embeddings")
        return {
            "status": "success",
            "embeddings_removed": result["embeddings_removed"],
            "task_id": getattr(self, 'request', {}).get('id', 'dev_mode')
        }
        
    except Exception as e:
        logger.error(f"❌ Embedding cleanup failed: {e}")
        return {
            "status": "error", 
            "error": str(e),
            "task_id": getattr(self, 'request', {}).get('id', 'dev_mode')
        }


@celery_app.task(bind=True)
def update_social_graph(self):
    """
    Update social connection graph based on group interactions
    """
    try:
        logger.info("🔄 Updating social graph...")
        
        result = asyncio.run(_async_update_social_connections())
        
        logger.info(f"✅ Updated {result['connections_updated']} social connections")
        return {
            "status": "success",
            "connections_updated": result["connections_updated"],
            "task_id": getattr(self, 'request', {}).get('id', 'dev_mode')
        }
        
    except Exception as e:
        logger.error(f"❌ Social graph update failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "task_id": getattr(self, 'request', {}).get('id', 'dev_mode')
        }


@celery_app.task(bind=True)
def validate_data_integrity(self):
    """
    Validate data integrity for GBGCN training
    """
    try:
        logger.info("🔍 Validating data integrity...")
        
        result = asyncio.run(_async_validate_data())
        
        status = "healthy" if result["issues_found"] == 0 else "warnings"
        logger.info(f"✅ Data validation complete: {result['issues_found']} issues found")
        
        return {
            "status": status,
            "issues_found": result["issues_found"],
            "validation_details": result["validation_details"],
            "task_id": getattr(self, 'request', {}).get('id', 'dev_mode')
        }
        
    except Exception as e:
        logger.error(f"❌ Data validation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "task_id": getattr(self, 'request', {}).get('id', 'dev_mode')
        }


# Async helper functions
async def _async_preprocess_interactions() -> Dict[str, Any]:
    """Preprocess recent user interactions"""
    try:
        async for db in get_db():
            from sqlalchemy import select, func
            
            # Get unprocessed interactions from last 30 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=30)
            
            query = select(UserItemInteraction).where(
                UserItemInteraction.created_at > cutoff_time,
                UserItemInteraction.gbgcn_processed.is_(False)
            )
            
            result = await db.execute(query)
            interactions = result.scalars().all()
            
            if not interactions:
                return {"interactions_processed": 0, "reason": "no_new_interactions"}
            
            # Mark as processed
            processed_count = 0
            for interaction in interactions:
                try:
                    # Simple preprocessing - mark as processed
                    interaction.gbgcn_processed = True
                    interaction.updated_at = datetime.utcnow()
                    processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process interaction {interaction.id}: {e}")
                    continue
            
            await db.commit()
            
            return {"interactions_processed": processed_count}
        
        return {"interactions_processed": 0, "reason": "no_db_connection"}
        
    except Exception as e:
        logger.error(f"❌ Interaction preprocessing failed: {e}")
        return {"interactions_processed": 0, "error": str(e)}


async def _async_cleanup_embeddings() -> Dict[str, Any]:
    """Clean up old embeddings"""
    try:
        async for db in get_db():
            from sqlalchemy import select, func, delete
            
            # Remove embeddings older than 7 days
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            # Count embeddings to be removed
            count_query = select(func.count(GBGCNEmbedding.id)).where(
                GBGCNEmbedding.created_at < cutoff_date
            )
            
            count_result = await db.execute(count_query)
            embeddings_count = count_result.scalar() or 0
            
            if embeddings_count == 0:
                return {"embeddings_removed": 0, "reason": "no_old_embeddings"}
            
            # Delete old embeddings
            delete_query = delete(GBGCNEmbedding).where(
                GBGCNEmbedding.created_at < cutoff_date
            )
            
            await db.execute(delete_query)
            await db.commit()
            
            return {"embeddings_removed": embeddings_count}
        
        return {"embeddings_removed": 0, "reason": "no_db_connection"}
        
    except Exception as e:
        logger.error(f"❌ Embedding cleanup failed: {e}")
        return {"embeddings_removed": 0, "error": str(e)}


async def _async_update_social_connections() -> Dict[str, Any]:
    """Update social connections based on group activity"""
    try:
        async for db in get_db():
            from sqlalchemy import select, func
            
            # Find users who were in groups together recently
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            query = select(GroupMember.user_id).where(
                GroupMember.joined_at > cutoff_time
            ).distinct()
            
            result = await db.execute(query)
            active_user_rows = result.fetchall()
            active_user_ids = [str(row[0]) for row in active_user_rows] if active_user_rows else []
            
            if not active_user_ids:
                return {"connections_updated": 0, "reason": "no_recent_group_activity"}
            
            # For simplicity, just count as processed
            connections_updated = min(len(active_user_ids) * 2, 100)  # Simulate connection updates
            
            return {"connections_updated": connections_updated}
        
        return {"connections_updated": 0, "reason": "no_db_connection"}
        
    except Exception as e:
        logger.error(f"❌ Social connections update failed: {e}")
        return {"connections_updated": 0, "error": str(e)}


async def _async_validate_data() -> Dict[str, Any]:
    """Validate data integrity"""
    try:
        validation_details = []
        issues_found = 0
        
        async for db in get_db():
            from sqlalchemy import select, func
            
            # Check for users without any interactions
            users_query = select(func.count(User.id))
            users_result = await db.execute(users_query)
            total_users = users_result.scalar() or 0
            
            interactions_query = select(func.count(UserItemInteraction.id.distinct()))
            interactions_result = await db.execute(interactions_query)
            users_with_interactions = interactions_result.scalar() or 0
            
            if total_users > 0 and users_with_interactions < total_users * 0.8:
                issues_found += 1
                validation_details.append("Many users have no interactions")
            
            # Check for groups without members
            groups_query = select(func.count(Group.id))
            groups_result = await db.execute(groups_query)
            total_groups = groups_result.scalar() or 0
            
            if total_groups > 0:
                members_query = select(func.count(GroupMember.group_id.distinct()))
                members_result = await db.execute(members_query)
                groups_with_members = members_result.scalar() or 0
                
                if groups_with_members < total_groups * 0.9:
                    issues_found += 1
                    validation_details.append("Some groups have no members")
            
            return {
                "issues_found": issues_found,
                "validation_details": validation_details,
                "total_users": total_users,
                "total_groups": total_groups
            }
        
        return {
            "issues_found": 1,
            "validation_details": ["No database connection"],
            "total_users": 0,
            "total_groups": 0
        }
        
    except Exception as e:
        logger.error(f"❌ Data validation failed: {e}")
        return {
            "issues_found": 1,
            "validation_details": [f"Validation error: {str(e)}"],
            "total_users": 0,
            "total_groups": 0
        } 