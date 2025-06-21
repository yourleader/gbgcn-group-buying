"""
Data processing tasks for GBGCN system
Handles data preprocessing, cleanup, and graph construction
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
import numpy as np

from src.tasks.celery_app import celery_app
from src.services.data_service import DataService
from src.database.connection import get_db
from src.database.models import (
    User, Item, Group, UserItemInteraction, 
    SocialConnection, GBGCNEmbedding
)
from src.core.logging import get_model_logger

logger = get_model_logger()

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 2, "countdown": 60})  # type: ignore[misc]
def preprocess_new_interactions(self):
    """
    Preprocess new user interactions for GBGCN training
    Critical for maintaining fresh training data
    """
    try:
        logger.info("🔄 Preprocessing new user interactions...")
        
        result = asyncio.run(_async_preprocess_interactions())
        
        logger.info(f"✅ Preprocessing completed: {result['interactions_processed']} interactions")
        return {
            "status": "success",
            "interactions_processed": result["interactions_processed"],
            "new_users": result.get("new_users", 0),
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"❌ Interaction preprocessing failed: {e}")
        raise


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 1, "countdown": 300})  # type: ignore[misc]
def cleanup_old_embeddings(self):
    """
    Cleanup old GBGCN embeddings to manage storage
    """
    try:
        logger.info("🧹 Cleaning up old GBGCN embeddings...")
        
        result = asyncio.run(_async_cleanup_embeddings())
        
        logger.info(f"✅ Cleanup completed: {result['embeddings_removed']} old embeddings removed")
        return {
            "status": "success",
            "embeddings_removed": result["embeddings_removed"],
            "storage_freed_mb": result.get("storage_freed_mb", 0),
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"❌ Embedding cleanup failed: {e}")
        raise


@celery_app.task(bind=True)  # type: ignore[misc]
def build_training_graph(self):
    """
    Build heterogeneous graph data for GBGCN training
    """
    try:
        logger.info("📊 Building training graph for GBGCN...")
        
        result = asyncio.run(_async_build_training_graph())
        
        logger.info(f"✅ Training graph built: {result['nodes']} nodes, {result['edges']} edges")
        return {
            "status": "success",
            "nodes": result["nodes"],
            "edges": result["edges"],
            "graph_density": result.get("graph_density", 0),
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"❌ Training graph building failed: {e}")
        raise


@celery_app.task(bind=True)  # type: ignore[misc]
def validate_data_quality(self):
    """
    Validate data quality for GBGCN training
    """
    try:
        logger.info("🔍 Validating data quality for GBGCN...")
        
        result = asyncio.run(_async_validate_data_quality())
        
        issues_found = len(result.get("issues", []))
        logger.info(f"✅ Data validation completed: {issues_found} issues found")
        
        return {
            "status": "success",
            "issues_found": issues_found,
            "data_quality_score": result.get("quality_score", 0),
            "issues": result.get("issues", []),
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"❌ Data validation failed: {e}")
        raise


# Async helper functions
async def _async_preprocess_interactions() -> Dict[str, Any]:
    """Preprocess new interactions for training"""
    try:
        async for db in get_db():
            from sqlalchemy import select, func
            
            # Find interactions from last 30 minutes
            recent_cutoff = datetime.utcnow() - timedelta(minutes=30)
            
            query = select(UserItemInteraction).where(
                UserItemInteraction.created_at > recent_cutoff
            )
            
            result = await db.execute(query)
            new_interactions = result.scalars().all()
            
            if not new_interactions:
                return {"interactions_processed": 0, "new_users": 0}
            
            # Process interactions
            processed_count = 0
            new_users = set()
            
            for interaction in new_interactions:
                try:
                    # Validate interaction data
                    if interaction.rating is None:
                        # Infer rating based on interaction type
                        if interaction.interaction_type == 'purchase':
                            interaction.rating = 5.0
                        elif interaction.interaction_type == 'add_to_cart':
                            interaction.rating = 4.0
                        elif interaction.interaction_type == 'view':
                            interaction.rating = 3.0
                        else:
                            interaction.rating = 2.5
                    
                    # Normalize rating to 0-1 range for GBGCN
                    interaction.rating = min(max(interaction.rating / 5.0, 0.0), 1.0)
                    
                    new_users.add(interaction.user_id)
                    processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process interaction {interaction.id}: {e}")
                    continue
            
            await db.commit()
            
            return {
                "interactions_processed": processed_count,
                "new_users": len(new_users)
            }
            
    except Exception as e:
        logger.error(f"❌ Async interaction preprocessing failed: {e}")
        raise
    
    # Fallback return to satisfy linter
    return {"interactions_processed": 0, "new_users": 0}


async def _async_cleanup_embeddings() -> Dict[str, Any]:
    """Cleanup old embeddings to manage storage"""
    try:
        async for db in get_db():
            from sqlalchemy import select, delete, func
            
            # Remove embeddings older than 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Count embeddings to be removed
            count_query = select(func.count(GBGCNEmbedding.id)).where(
                GBGCNEmbedding.created_at < cutoff_date
            )
            count_result = await db.execute(count_query)
            embeddings_to_remove = count_result.scalar() or 0
            
            if embeddings_to_remove == 0:
                return {"embeddings_removed": 0, "storage_freed_mb": 0}
            
            # Delete old embeddings
            delete_query = delete(GBGCNEmbedding).where(
                GBGCNEmbedding.created_at < cutoff_date
            )
            await db.execute(delete_query)
            await db.commit()
            
            # Estimate storage freed (rough calculation)
            estimated_size_per_embedding = 256  # bytes (64-dim float32 vector)
            storage_freed_mb = (embeddings_to_remove * estimated_size_per_embedding) / (1024 * 1024)
            
            return {
                "embeddings_removed": embeddings_to_remove,
                "storage_freed_mb": round(storage_freed_mb, 2)
            }
            
    except Exception as e:
        logger.error(f"❌ Async embedding cleanup failed: {e}")
        raise
    
    # Fallback return to satisfy linter
    return {"embeddings_removed": 0, "storage_freed_mb": 0}


async def _async_build_training_graph() -> Dict[str, Any]:
    """Build heterogeneous graph for GBGCN training"""
    try:
        data_service = DataService()
        
        # Get data statistics
        stats = await data_service.get_data_statistics()
        
        # Build graph data
        train_data, eval_data = await data_service.prepare_training_data()
        
        # Calculate graph metrics
        total_nodes = stats['num_users'] + stats['num_items']
        total_edges = stats['num_interactions'] + stats['num_social_connections']
        
        # Calculate graph density
        max_possible_edges = (total_nodes * (total_nodes - 1)) / 2
        graph_density = total_edges / max_possible_edges if max_possible_edges > 0 else 0
        
        return {
            "nodes": total_nodes,
            "edges": total_edges,
            "graph_density": round(graph_density, 4),
            "user_nodes": stats['num_users'],
            "item_nodes": stats['num_items'],
            "interaction_edges": stats['num_interactions'],
            "social_edges": stats['num_social_connections']
        }
        
    except Exception as e:
        logger.error(f"❌ Async graph building failed: {e}")
        raise


async def _async_validate_data_quality() -> Dict[str, Any]:
    """Validate data quality for GBGCN"""
    try:
        async for db in get_db():
            from sqlalchemy import select, func
            
            issues = []
            quality_metrics = {}
            
            # Check for users without interactions
            users_without_interactions = await db.execute(
                select(func.count(User.id))
                .outerjoin(UserItemInteraction)
                .where(UserItemInteraction.user_id.is_(None))
            )
            isolated_users = users_without_interactions.scalar() or 0
            
            if isolated_users > 0:
                issues.append(f"{isolated_users} users have no interactions")
            
            quality_metrics['isolated_users'] = isolated_users
            
            # Check for items without interactions
            items_without_interactions = await db.execute(
                select(func.count(Item.id))
                .outerjoin(UserItemInteraction)
                .where(UserItemInteraction.item_id.is_(None))
            )
            isolated_items = items_without_interactions.scalar() or 0
            
            if isolated_items > 0:
                issues.append(f"{isolated_items} items have no interactions")
            
            quality_metrics['isolated_items'] = isolated_items
            
            # Check for users without social connections
            users_without_friends = await db.execute(
                select(func.count(User.id))
                .outerjoin(SocialConnection)
                .where(SocialConnection.user_id.is_(None))
            )
            isolated_social_users = users_without_friends.scalar() or 0
            
            if isolated_social_users > 0:
                issues.append(f"{isolated_social_users} users have no social connections")
            
            quality_metrics['isolated_social_users'] = isolated_social_users
            
            # Calculate overall quality score (0-1)
            total_users = await db.execute(select(func.count(User.id)))
            user_count = total_users.scalar() or 1
            
            total_items = await db.execute(select(func.count(Item.id)))
            item_count = total_items.scalar() or 1
            
            # Quality score based on connectivity
            user_connectivity = 1 - (isolated_users / user_count)
            item_connectivity = 1 - (isolated_items / item_count)
            social_connectivity = 1 - (isolated_social_users / user_count)
            
            quality_score = (user_connectivity + item_connectivity + social_connectivity) / 3
            
            return {
                "issues": issues,
                "quality_score": round(quality_score, 3),
                "metrics": quality_metrics
            }
            
    except Exception as e:
        logger.error(f"❌ Async data validation failed: {e}")
        raise
    
    # Fallback return to satisfy linter
    return {
        "issues": ["No database connection"],
        "quality_score": 0.0,
        "metrics": {}
    } 