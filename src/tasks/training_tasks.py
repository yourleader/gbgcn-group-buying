"""
Background training tasks for GBGCN model
These tasks ensure the model stays updated with new data
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from src.tasks.celery_app import celery_app
from src.ml.gbgcn_trainer import GBGCNTrainer
from src.services.data_service import DataService
from src.database.connection import get_db
from src.database.models import User, Item, Group, GroupMember, UserItemInteraction, GBGCNEmbedding
from src.core.config import settings
from src.core.logging import get_model_logger

logger = get_model_logger()

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 300})  # type: ignore[misc]
def retrain_gbgcn(self):
    """
    CRITICAL TASK: Retrain the GBGCN model with latest data
    This ensures recommendations stay accurate as new users/groups join
    """
    try:
        logger.info("🔄 Starting GBGCN model retraining...")
        
        # Run async training in sync context
        result = asyncio.run(_async_retrain_gbgcn())
        
        logger.info(f"✅ GBGCN retraining completed: {result['status']}")
        return {
            "status": "success", 
            "epochs_trained": result.get("epochs_trained", 0),
            "final_loss": result.get("best_val_loss", 0),
            "training_time": datetime.utcnow().isoformat(),
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"❌ GBGCN retraining failed: {e}")
        raise


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 2, "countdown": 120})  # type: ignore[misc]
def update_user_embeddings(self):
    """
    Update user embeddings for new users or changed behavior
    Critical for personalized recommendations
    """
    try:
        logger.info("🔄 Updating user embeddings...")
        
        result = asyncio.run(_async_update_user_embeddings())
        
        logger.info(f"✅ User embeddings updated: {result['users_updated']} users")
        return {
            "status": "success",
            "users_updated": result["users_updated"],
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"❌ User embeddings update failed: {e}")
        raise


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 2, "countdown": 60})  # type: ignore[misc]
def update_group_predictions(self):
    """
    Update success probability predictions for active groups
    Ensures group recommendations are current
    """
    try:
        logger.info("🔄 Updating group success predictions...")
        
        result = asyncio.run(_async_update_group_predictions())
        
        logger.info(f"✅ Group predictions updated: {result['groups_updated']} groups")
        return {
            "status": "success",
            "groups_updated": result["groups_updated"],
            "avg_success_prob": result.get("avg_success_prob", 0),
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"❌ Group predictions update failed: {e}")
        raise


@celery_app.task(bind=True)  # type: ignore[misc]
def trigger_manual_retrain(self, reason: str = "manual"):
    """
    Manually trigger GBGCN retraining (e.g., when new data is imported)
    """
    try:
        logger.info(f"🔄 Manual GBGCN retraining triggered: {reason}")
        
        # Call the main retraining task
        result = retrain_gbgcn.apply_async(queue="training", priority=10)  # type: ignore[attr-defined]
        
        return {
            "status": "triggered",
            "reason": reason,
            "retrain_task_id": result.id,
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"❌ Manual retrain trigger failed: {e}")
        raise


# Async helper functions
async def _async_retrain_gbgcn() -> Dict[str, Any]:
    """Async wrapper for GBGCN retraining"""
    try:
        # Initialize trainer
        trainer = GBGCNTrainer()
        await trainer.initialize()
        
        # Check if retraining is needed
        if trainer.last_training_time:
            time_since_training = datetime.utcnow() - trainer.last_training_time
            if time_since_training < timedelta(hours=4):
                logger.info("⏭️ Skipping retraining - too recent")
                return {"status": "skipped", "reason": "too_recent"}
        
        # Get data statistics to see if we have enough new data
        data_service = DataService()
        stats = await data_service.get_data_statistics()
        
        min_interactions = 100  # Minimum new interactions to justify retraining
        if stats['num_interactions'] < min_interactions:
            logger.info("⏭️ Skipping retraining - insufficient new data")
            return {"status": "skipped", "reason": "insufficient_data"}
        
        # Perform training
        logger.info(f"🏋️ Starting GBGCN training with {stats['num_interactions']} interactions...")
        
        training_result = await trainer.train(num_epochs=30)  # Shorter for background training
        
        # Save model
        await trainer.save_model()
        
        return training_result
        
    except Exception as e:
        logger.error(f"❌ Async GBGCN retraining failed: {e}")
        raise


async def _async_update_user_embeddings() -> Dict[str, Any]:
    """Update embeddings for users with new activity"""
    try:
        # Get users with recent activity (last 24 hours)
        async for db in get_db():
            from sqlalchemy import select, func
            
            # Find users with recent interactions
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            
            query = select(User.id).join(UserItemInteraction).where(
                UserItemInteraction.created_at > recent_cutoff
            ).distinct()
            
            result = await db.execute(query)
            user_ids = [row[0] for row in result.fetchall()]
            
            if not user_ids:
                return {"users_updated": 0, "reason": "no_recent_activity"}
            
            # Initialize trainer for inference
            trainer = GBGCNTrainer()
            if not trainer.is_ready():
                await trainer.initialize()
            
            # Update embeddings for these users
            updated_count = 0
            for user_id in user_ids[:50]:  # Limit to avoid overwhelming
                try:
                    # Generate new embeddings
                    recommendations = await trainer.predict_item_recommendations(user_id, k=1)
                    if recommendations:
                        updated_count += 1
                except Exception as e:
                    logger.warning(f"Failed to update embeddings for user {user_id}: {e}")
                    continue
            
            return {"users_updated": updated_count}
            
    except Exception as e:
        logger.error(f"❌ User embeddings update failed: {e}")
        raise
    
    # This should never be reached, but ensures return path
    return {"users_updated": 0, "reason": "no_db_connection"}


async def _async_update_group_predictions() -> Dict[str, Any]:
    """Update success predictions for active groups"""
    try:
        async for db in get_db():
            from sqlalchemy import select
            
            # Get active groups
            query = select(Group).where(Group.status == 'active')
            result = await db.execute(query)
            active_groups = result.scalars().all()
            
            if not active_groups:
                return {"groups_updated": 0, "reason": "no_active_groups"}
            
            # Initialize trainer
            trainer = GBGCNTrainer()
            if not trainer.is_ready():
                await trainer.initialize()
            
            # Update predictions
            updated_count = 0
            total_success_prob = 0
            
            for group in active_groups[:20]:  # Limit to avoid overwhelming
                try:
                    # Get new success prediction
                    success_prob = await trainer.predict_group_success(str(group.id))
                    
                    # Update group record
                    group.gbgcn_success_prediction = success_prob
                    group.gbgcn_prediction_updated_at = datetime.utcnow()
                    
                    updated_count += 1
                    total_success_prob += success_prob
                    
                except Exception as e:
                    logger.warning(f"Failed to update prediction for group {group.id}: {e}")
                    continue
            
            await db.commit()
            
            avg_success_prob = total_success_prob / updated_count if updated_count > 0 else 0
            
            return {
                "groups_updated": updated_count,
                "avg_success_prob": avg_success_prob
            }
            
    except Exception as e:
        logger.error(f"❌ Group predictions update failed: {e}")
        raise
    
    # This should never be reached, but ensures return path
    return {"groups_updated": 0, "avg_success_prob": 0.0}


# Monitoring task
@celery_app.task(bind=True)  # type: ignore[misc]
def check_training_health(self):
    """
    Check if GBGCN training system is healthy
    """
    try:
        trainer = GBGCNTrainer()
        
        health_status = {
            "trainer_initialized": False,
            "model_ready": False,
            "last_training": None,
            "model_path_exists": False,
            "status": "unhealthy"
        }
        
        # Check trainer status
        result = asyncio.run(_async_check_trainer_health(trainer))
        health_status.update(result)
        
        # Determine overall health
        if health_status["trainer_initialized"] and health_status["model_ready"]:
            health_status["status"] = "healthy"
        
        logger.info(f"📊 Training health check: {health_status['status']}")
        return health_status
        
    except Exception as e:
        logger.error(f"❌ Training health check failed: {e}")
        return {"status": "error", "error": str(e)}


async def _async_check_trainer_health(trainer: GBGCNTrainer) -> Dict[str, Any]:
    """Async health check for trainer"""
    try:
        await trainer.initialize()
        
        status = await trainer.get_status()
        
        return {
            "trainer_initialized": status["is_initialized"],
            "model_ready": trainer.is_ready(),
            "last_training": status.get("last_training_time"),
            "model_path_exists": status.get("model_path", "").endswith(".pth")
        }
        
    except Exception as e:
        return {"error": str(e)} 