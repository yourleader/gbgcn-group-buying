"""
Background Tasks API Router
Endpoints for monitoring and controlling GBGCN background training
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.tasks.celery_app import celery_app
from src.tasks.training_tasks import (
    retrain_gbgcn, update_user_embeddings, 
    update_group_predictions, trigger_manual_retrain,
    check_training_health
)
from src.tasks.data_tasks import (
    preprocess_new_interactions, cleanup_old_embeddings,
    build_training_graph, validate_data_quality
)
from src.core.auth import get_current_user
from src.database.models import User

router = APIRouter(prefix="/api/v1/background", tags=["background-tasks"])

@router.get("/health")
async def background_tasks_health():
    """Get health status of background training system"""
    try:
        # Check Celery worker status
        inspector = celery_app.control.inspect()
        
        # Get active workers
        active_workers = inspector.active()
        registered_tasks = inspector.registered()
        
        # Get scheduled tasks
        scheduled_tasks = inspector.scheduled()
        
        # Check training health
        health_task = check_training_health.delay()
        training_health = health_task.get(timeout=10)
        
        return {
            "status": "healthy",
            "celery_workers": len(active_workers) if active_workers else 0,
            "active_workers": list(active_workers.keys()) if active_workers else [],
            "training_health": training_health,
            "scheduled_tasks_count": sum(len(tasks) for tasks in scheduled_tasks.values()) if scheduled_tasks else 0,
            "last_check": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.utcnow().isoformat()
        }


@router.get("/tasks/active")
async def get_active_tasks(current_user: User = Depends(get_current_user)):
    """Get currently running background tasks"""
    try:
        inspector = celery_app.control.inspect()
        active_tasks = inspector.active()
        
        if not active_tasks:
            return {"active_tasks": [], "total_active": 0}
        
        # Format active tasks
        formatted_tasks = []
        for worker, tasks in active_tasks.items():
            for task in tasks:
                formatted_tasks.append({
                    "task_id": task.get("id"),
                    "task_name": task.get("name"),
                    "worker": worker,
                    "args": task.get("args", []),
                    "kwargs": task.get("kwargs", {}),
                    "time_start": task.get("time_start")
                })
        
        return {
            "active_tasks": formatted_tasks,
            "total_active": len(formatted_tasks)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active tasks: {e}"
        )


@router.get("/tasks/scheduled")
async def get_scheduled_tasks(current_user: User = Depends(get_current_user)):
    """Get scheduled background tasks"""
    try:
        inspector = celery_app.control.inspect()
        scheduled_tasks = inspector.scheduled()
        
        if not scheduled_tasks:
            return {"scheduled_tasks": [], "total_scheduled": 0}
        
        # Format scheduled tasks
        formatted_tasks = []
        for worker, tasks in scheduled_tasks.items():
            for task in tasks:
                formatted_tasks.append({
                    "task_id": task.get("request", {}).get("id"),
                    "task_name": task.get("request", {}).get("task"),
                    "worker": worker,
                    "eta": task.get("eta"),
                    "priority": task.get("priority")
                })
        
        return {
            "scheduled_tasks": formatted_tasks,
            "total_scheduled": len(formatted_tasks)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduled tasks: {e}"
        )


@router.post("/training/trigger-retrain")
async def trigger_gbgcn_retrain(
    reason: str = "manual_api_trigger",
    current_user: User = Depends(get_current_user)
):
    """Manually trigger GBGCN model retraining"""
    try:
        # Only admins can trigger manual retraining
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can trigger manual retraining"
            )
        
        # Trigger the retraining task
        task = trigger_manual_retrain.delay(reason=reason)
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "reason": reason,
            "triggered_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger retraining: {e}"
        )


@router.post("/training/update-embeddings")
async def trigger_embeddings_update(current_user: User = Depends(get_current_user)):
    """Manually trigger user embeddings update"""
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can trigger embeddings update"
            )
        
        task = update_user_embeddings.delay()
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "triggered_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger embeddings update: {e}"
        )


@router.post("/training/update-group-predictions")
async def trigger_group_predictions_update(current_user: User = Depends(get_current_user)):
    """Manually trigger group predictions update"""
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can trigger group predictions update"
            )
        
        task = update_group_predictions.delay()
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "triggered_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger group predictions update: {e}"
        )


@router.post("/data/preprocess")
async def trigger_data_preprocessing(current_user: User = Depends(get_current_user)):
    """Manually trigger data preprocessing"""
    try:
        task = preprocess_new_interactions.delay()
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "triggered_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger data preprocessing: {e}"
        )


@router.post("/data/validate-quality")
async def trigger_data_validation(current_user: User = Depends(get_current_user)):
    """Manually trigger data quality validation"""
    try:
        task = validate_data_quality.delay()
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "triggered_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger data validation: {e}"
        )


@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str, current_user: User = Depends(get_current_user)):
    """Get result of a specific background task"""
    try:
        # Get task result
        result = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task result: {e}"
        )


@router.get("/stats")
async def get_background_stats(current_user: User = Depends(get_current_user)):
    """Get comprehensive background tasks statistics"""
    try:
        inspector = celery_app.control.inspect()
        
        # Get various stats
        stats = inspector.stats()
        active_tasks = inspector.active()
        scheduled_tasks = inspector.scheduled()
        
        # Count tasks by type
        task_counts = {
            "training_tasks": 0,
            "data_tasks": 0,
            "analytics_tasks": 0,
            "other_tasks": 0
        }
        
        # Count active tasks by category
        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    task_name = task.get("name", "")
                    if "training_tasks" in task_name:
                        task_counts["training_tasks"] += 1
                    elif "data_tasks" in task_name:
                        task_counts["data_tasks"] += 1
                    elif "analytics_tasks" in task_name:
                        task_counts["analytics_tasks"] += 1
                    else:
                        task_counts["other_tasks"] += 1
        
        return {
            "worker_stats": stats,
            "active_tasks_count": sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0,
            "scheduled_tasks_count": sum(len(tasks) for tasks in scheduled_tasks.values()) if scheduled_tasks else 0,
            "task_counts_by_category": task_counts,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get background stats: {e}"
        ) 