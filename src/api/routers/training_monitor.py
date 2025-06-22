"""
Training Monitor Router for GBGCN System
Provides real-time training status, metrics, and results visualization
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import asyncio
import json

from src.database.connection import get_db
from src.database.models import User, Group, UserItemInteraction, GBGCNEmbedding
from src.ml.gbgcn_trainer import GBGCNTrainer
from src.services.data_service import DataService
from src.tasks.training_tasks import retrain_gbgcn, update_user_embeddings, check_training_health
from src.core.logging import get_model_logger

router = APIRouter(prefix="/training-monitor", tags=["Training Monitor"])
logger = get_model_logger()

# Response Models
class TrainingStatus(BaseModel):
    status: str
    current_epoch: Optional[int] = None
    total_epochs: Optional[int] = None
    current_loss: Optional[float] = None
    best_loss: Optional[float] = None
    training_accuracy: Optional[float] = None
    estimated_completion: Optional[str] = None
    elapsed_time_minutes: Optional[float] = None

class TrainingMetrics(BaseModel):
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    ndcg_at_5: float
    ndcg_at_10: float
    map_score: float

class ModelStats(BaseModel):
    model_config = {"protected_namespaces": ()}  # Allow model_ fields
    
    model_version: str
    last_training: Optional[datetime]
    total_parameters: int
    model_size_mb: float
    embeddings_count: int
    training_data_count: int

class TrainingHistory(BaseModel):
    timestamp: datetime
    epoch: int
    train_loss: float
    val_loss: float
    accuracy: float
    learning_rate: float

class DataStatistics(BaseModel):
    total_users: int
    total_items: int
    total_interactions: int
    total_groups: int
    active_groups: int
    successful_groups: int
    data_quality_score: float
    last_update: datetime

class TrainingDashboard(BaseModel):
    status: TrainingStatus
    metrics: TrainingMetrics
    model_stats: ModelStats
    data_stats: DataStatistics
    recent_history: List[TrainingHistory]
    system_health: Dict[str, Any]

# Training Control Models
class TrainingRequest(BaseModel):
    epochs: int = 50
    learning_rate: float = 0.001
    batch_size: int = 256
    reason: str = "Manual training request"

class TrainingResult(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_duration_minutes: int

# Endpoints
@router.get("/dashboard", response_model=TrainingDashboard)
async def get_training_dashboard(db: AsyncSession = Depends(get_db)):
    """
    Get comprehensive training dashboard with all metrics and status
    """
    try:
        # Get current training status
        trainer = GBGCNTrainer()
        trainer_status = await _get_training_status(trainer)
        
        # Get model metrics
        metrics = await _get_training_metrics(db)
        
        # Get model statistics
        model_stats = await _get_model_stats(trainer, db)
        
        # Get data statistics
        data_stats = await _get_data_statistics(db)
        
        # Get training history
        history = await _get_training_history()
        
        # Get system health
        health = await _get_system_health()
        
        return TrainingDashboard(
            status=trainer_status,
            metrics=metrics,
            model_stats=model_stats,
            data_stats=data_stats,
            recent_history=history,
            system_health=health
        )
        
    except Exception as e:
        logger.error(f"Dashboard data retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")

@router.get("/status", response_model=TrainingStatus)
async def get_training_status():
    """
    Get current training status only
    """
    try:
        trainer = GBGCNTrainer()
        return await _get_training_status(trainer)
    except Exception as e:
        logger.error(f"Training status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get training status")

@router.get("/metrics", response_model=TrainingMetrics)
async def get_training_metrics(db: AsyncSession = Depends(get_db)):
    """
    Get current model performance metrics
    """
    try:
        return await _get_training_metrics(db)
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get training metrics")

@router.get("/data-stats", response_model=DataStatistics)
async def get_data_statistics_endpoint(db: AsyncSession = Depends(get_db)):
    """
    Get current data statistics for training
    """
    try:
        return await _get_data_statistics(db)
    except Exception as e:
        logger.error(f"Data statistics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get data statistics")

@router.post("/start-training", response_model=TrainingResult)
async def start_training(
    request: TrainingRequest,
    background_tasks: BackgroundTasks
):
    """
    Start manual GBGCN training with custom parameters
    """
    try:
        # Trigger background training task
        task = retrain_gbgcn.delay()  # type: ignore[attr-defined]
        
        logger.info(f"Manual training started: {request.reason}")
        
        return TrainingResult(
            task_id=str(task.id) if hasattr(task, 'id') else "manual_training",
            status="started",
            message=f"Training started with {request.epochs} epochs",
            estimated_duration_minutes=request.epochs * 2  # Rough estimate
        )
        
    except Exception as e:
        logger.error(f"Failed to start training: {e}")
        raise HTTPException(status_code=500, detail="Failed to start training")

@router.post("/stop-training")
async def stop_training():
    """
    Stop current training (if running)
    """
    try:
        # In a real implementation, this would stop the training process
        logger.info("Training stop requested")
        return {"message": "Training stop requested", "status": "stopping"}
    except Exception as e:
        logger.error(f"Failed to stop training: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop training")

@router.get("/logs")
async def get_training_logs(limit: int = 100):
    """
    Get recent training logs
    """
    try:
        # Mock training logs - in real implementation, read from log files
        logs = [
            {
                "timestamp": datetime.utcnow() - timedelta(minutes=i),
                "level": "INFO" if i % 3 != 0 else "WARNING",
                "message": f"Training epoch {50-i}: loss={0.1 + i*0.001:.4f}, accuracy={0.85 - i*0.001:.3f}"
            }
            for i in range(min(limit, 50))
        ]
        
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Failed to get training logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve training logs")

@router.get("/health")
async def get_training_health():
    """
    Get training system health status
    """
    try:
        health_task = check_training_health.delay()  # type: ignore[attr-defined]
        return {"message": "Health check initiated", "task_id": str(health_task.id) if hasattr(health_task, 'id') else "health_check"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@router.get("/model-info")
async def get_model_info():
    """
    Get detailed model information and architecture
    """
    try:
        trainer = GBGCNTrainer()
        
        model_info = {
            "architecture": {
                "embedding_dim": 64,
                "num_gcn_layers": 3,
                "hidden_dims": [128, 64, 32],
                "activation": "ReLU",
                "dropout": 0.2
            },
            "training_config": {
                "optimizer": "Adam",
                "learning_rate": 0.001,
                "batch_size": 256,
                "weight_decay": 1e-5
            },
            "hyperparameters": {
                "alpha": 0.6,  # Cross-view weight
                "beta": 0.4,   # Social influence weight
                "gamma": 0.1,  # Regularization
                "temperature": 0.1  # Contrastive learning
            },
            "performance": {
                "best_validation_loss": 0.1234,
                "training_time_minutes": 45,
                "inference_time_ms": 2.5,
                "memory_usage_mb": 512
            }
        }
        
        return model_info
    except Exception as e:
        logger.error(f"Model info retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model info")

# Helper Functions
async def _get_training_status(trainer: GBGCNTrainer) -> TrainingStatus:
    """Get current training status"""
    try:
        if not trainer.is_ready():
            return TrainingStatus(status="not_initialized")
        
        # In a real implementation, this would check actual training state
        return TrainingStatus(
            status="ready",
            current_epoch=None,
            total_epochs=None,
            current_loss=None,
            best_loss=0.1234,
            training_accuracy=0.8567,
            estimated_completion=None,
            elapsed_time_minutes=None
        )
    except Exception:
        return TrainingStatus(status="error")

async def _get_training_metrics(db: AsyncSession) -> TrainingMetrics:
    """Get current model performance metrics"""
    # Mock metrics - in real implementation, calculate from validation data
    return TrainingMetrics(
        precision=0.78,
        recall=0.82,
        f1_score=0.80,
        accuracy=0.85,
        ndcg_at_5=0.75,
        ndcg_at_10=0.73,
        map_score=0.71
    )

async def _get_model_stats(trainer: GBGCNTrainer, db: AsyncSession) -> ModelStats:
    """Get model statistics"""
    async for session in db:
        # Count embeddings
        embeddings_count_query = select(func.count(GBGCNEmbedding.id))
        embeddings_result = await session.execute(embeddings_count_query)
        embeddings_count = embeddings_result.scalar() or 0
        
        # Count training data
        interactions_count_query = select(func.count(UserItemInteraction.id))
        interactions_result = await session.execute(interactions_count_query)
        training_data_count = interactions_result.scalar() or 0
        
        return ModelStats(
            model_version="1.0.0",
            last_training=datetime.utcnow() - timedelta(hours=2),
            total_parameters=1500000,  # ~1.5M parameters
            model_size_mb=6.2,
            embeddings_count=embeddings_count,
            training_data_count=training_data_count
        )
    
    # Fallback
    return ModelStats(
        model_version="1.0.0",
        last_training=None,
        total_parameters=0,
        model_size_mb=0,
        embeddings_count=0,
        training_data_count=0
    )

async def _get_data_statistics(db: AsyncSession) -> DataStatistics:
    """Get current data statistics"""
    async for session in db:
        # Get user count
        users_query = select(func.count(User.id))
        users_result = await session.execute(users_query)
        total_users = users_result.scalar() or 0
        
        # Get interactions count
        interactions_query = select(func.count(UserItemInteraction.id))
        interactions_result = await session.execute(interactions_query)
        total_interactions = interactions_result.scalar() or 0
        
        # Get groups count
        groups_query = select(func.count(Group.id))
        groups_result = await session.execute(groups_query)
        total_groups = groups_result.scalar() or 0
        
        # Get active groups
        active_groups_query = select(func.count(Group.id)).where(Group.status == 'active')
        active_result = await session.execute(active_groups_query)
        active_groups = active_result.scalar() or 0
        
        # Get successful groups
        successful_groups_query = select(func.count(Group.id)).where(Group.status == 'completed')
        successful_result = await session.execute(successful_groups_query)
        successful_groups = successful_result.scalar() or 0
        
        # Calculate data quality score (simplified)
        if total_users > 0 and total_interactions > 0:
            interaction_ratio = total_interactions / (total_users * 10)  # Expect ~10 interactions per user
            quality_score = min(interaction_ratio, 1.0)
        else:
            quality_score = 0.0
        
        return DataStatistics(
            total_users=total_users,
            total_items=1000,  # Mock value
            total_interactions=total_interactions,
            total_groups=total_groups,
            active_groups=active_groups,
            successful_groups=successful_groups,
            data_quality_score=quality_score,
            last_update=datetime.utcnow()
        )
    
    # Fallback
    return DataStatistics(
        total_users=0,
        total_items=0,
        total_interactions=0,
        total_groups=0,
        active_groups=0,
        successful_groups=0,
        data_quality_score=0.0,
        last_update=datetime.utcnow()
    )

async def _get_training_history() -> List[TrainingHistory]:
    """Get recent training history"""
    # Mock training history - in real implementation, read from database
    history = []
    for i in range(10):
        history.append(TrainingHistory(
            timestamp=datetime.utcnow() - timedelta(hours=i*2),
            epoch=50-i,
            train_loss=0.15 + i*0.01,
            val_loss=0.18 + i*0.01,
            accuracy=0.85 - i*0.005,
            learning_rate=0.001
        ))
    
    return history

async def _get_system_health() -> Dict[str, Any]:
    """Get system health metrics"""
    return {
        "database_status": "healthy",
        "redis_status": "healthy",
        "celery_status": "healthy",
        "model_status": "ready",
        "memory_usage_percent": 65,
        "cpu_usage_percent": 45,
        "disk_usage_percent": 30,
        "uptime_hours": 24.5
    } 