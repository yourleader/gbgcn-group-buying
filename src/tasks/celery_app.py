"""
Celery application for GBGCN background training tasks
"""

import os
from typing import Any, Dict

# Suppress linter warnings for Celery imports in development
try:
    from celery import Celery  # type: ignore[import-untyped]
    from celery.schedules import crontab  # type: ignore[import-untyped]
    CELERY_AVAILABLE = True
except ImportError:
    # Mock Celery for development - properly handle arguments
    CELERY_AVAILABLE = False
    
    class MockCelery:
        def __init__(self, *args, **kwargs):
            # Accept any arguments but don't do anything with them
            self.name = args[0] if args else "mock"
            
        @property
        def conf(self):
            return MockConfig()
        
        def task(self, *args, **kwargs):
            def decorator(func):
                # Add delay method for compatibility
                def delay(*task_args, **task_kwargs):
                    return MockAsyncResult("mock_task_id")
                func.delay = delay
                return func
            return decorator
    
    class MockConfig:
        def __init__(self):
            self.beat_schedule = {}
            self.task_default_queue = "default"
            self.task_default_exchange = "default"
            self.task_default_exchange_type = "direct"
            self.task_default_routing_key = "default"
        
        def update(self, **kwargs):
            # Accept configuration updates but don't process them
            pass
    
    class MockAsyncResult:
        def __init__(self, task_id):
            self.id = task_id
            self.status = "PENDING"
    
    Celery = MockCelery  # type: ignore
    crontab = lambda **kwargs: f"crontab_{kwargs}"  # type: ignore

from src.core.config import settings

# Create Celery instance
celery_app = Celery(
    "groupbuy_gbgcn",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "src.tasks.training_tasks",
        "src.tasks.data_tasks",
        "src.tasks.analytics_tasks"
    ]
)

# Only configure if real Celery is available
if CELERY_AVAILABLE:
    # Celery configuration
    celery_app.conf.update(  # type: ignore[attr-defined]
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        
        # Worker settings
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_max_tasks_per_child=1000,
        
        # Task routing
        task_routes={
            "src.tasks.training_tasks.*": {"queue": "training"},
            "src.tasks.data_tasks.*": {"queue": "data"},
            "src.tasks.analytics_tasks.*": {"queue": "analytics"},
        },
        
        # Result backend settings
        result_expires=3600,  # 1 hour
        result_backend_transport_options={
            "master_name": "mymaster",
            "retry_on_timeout": True,
        },
    )

    # Periodic task schedule (CRITICAL for GBGCN)
    celery_app.conf.beat_schedule = {  # type: ignore[attr-defined]
        # GBGCN model retraining - every 6 hours
        "retrain-gbgcn-model": {
            "task": "src.tasks.training_tasks.retrain_gbgcn",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
            "options": {"queue": "training", "priority": 9}
        },
        
        # Update user embeddings - every 2 hours  
        "update-user-embeddings": {
            "task": "src.tasks.training_tasks.update_user_embeddings",
            "schedule": crontab(minute=0, hour="*/2"),  # Every 2 hours
            "options": {"queue": "training", "priority": 7}
        },
        
        # Social influence analysis - every 4 hours
        "analyze-social-influence": {
            "task": "src.tasks.analytics_tasks.analyze_social_influence",
            "schedule": crontab(minute=30, hour="*/4"),  # Every 4 hours
            "options": {"queue": "analytics", "priority": 5}
        },
        
        # Group success predictions update - every hour
        "update-group-predictions": {
            "task": "src.tasks.training_tasks.update_group_predictions", 
            "schedule": crontab(minute=15, hour="*"),  # Every hour
            "options": {"queue": "training", "priority": 6}
        },
        
        # Data preprocessing - every 30 minutes
        "preprocess-new-data": {
            "task": "src.tasks.data_tasks.preprocess_new_interactions",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
            "options": {"queue": "data", "priority": 4}
        },
        
        # Model performance monitoring - daily
        "monitor-model-performance": {
            "task": "src.tasks.analytics_tasks.monitor_model_performance",
            "schedule": crontab(minute=0, hour=2),  # Daily at 2 AM
            "options": {"queue": "analytics", "priority": 3}
        },
        
        # Clean old data - weekly
        "cleanup-old-data": {
            "task": "src.tasks.data_tasks.cleanup_old_embeddings",
            "schedule": crontab(minute=0, hour=3, day_of_week=0),  # Weekly Sunday 3 AM
            "options": {"queue": "data", "priority": 1}
        }
    }

    # Task defaults
    celery_app.conf.task_default_queue = "default"  # type: ignore[attr-defined]
    celery_app.conf.task_default_exchange = "default"  # type: ignore[attr-defined]
    celery_app.conf.task_default_exchange_type = "direct"  # type: ignore[attr-defined]
    celery_app.conf.task_default_routing_key = "default"  # type: ignore[attr-defined]

if __name__ == "__main__":
    if CELERY_AVAILABLE:
        celery_app.start()  # type: ignore[attr-defined]
    else:
        print("Celery not available - running in mock mode") 