"""
Simplified Celery application for GBGCN background training tasks
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime

# Simple task scheduler without Celery dependency for development
class SimpleCeleryApp:
    """Simple task scheduler that mimics Celery interface"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.tasks: Dict[str, Any] = {}
        
    def task(self, bind: bool = False, **kwargs):
        """Decorator to register tasks"""
        def decorator(func):
            self.tasks[func.__name__] = func
            
            # Add delay method for async execution
            def delay(*args, **kwargs):
                # In production, this would use Celery
                # For development, we'll just return a mock result
                return MockAsyncResult(f"task_{datetime.utcnow().timestamp()}")
            
            func.delay = delay
            return func
        return decorator
    
    class conf:
        """Configuration object"""
        @staticmethod
        def update(**kwargs):
            pass
        
        beat_schedule: Dict[str, Any] = {}
        task_default_queue = "default"
        task_default_exchange = "default"
        task_default_exchange_type = "direct" 
        task_default_routing_key = "default"

class MockAsyncResult:
    """Mock async result for development"""
    
    def __init__(self, task_id: str):
        self.id = task_id
        self.status = "PENDING"
        self.result = None
    
    def ready(self) -> bool:
        return False
    
    def get(self, timeout: Optional[int] = None):
        return {"status": "completed", "message": "Development mode"}

# Create app instance
celery_app = SimpleCeleryApp(
    "groupbuy_gbgcn"
)

# Mock crontab for development
def crontab(**kwargs):
    return f"crontab_{kwargs}"

# Simple configuration
celery_app.conf.beat_schedule = {
    # GBGCN model retraining - every 6 hours
    "retrain-gbgcn-model": {
        "task": "retrain_gbgcn",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"queue": "training", "priority": 9}
    },
    
    # Update user embeddings - every 2 hours  
    "update-user-embeddings": {
        "task": "update_user_embeddings", 
        "schedule": crontab(minute=0, hour="*/2"),
        "options": {"queue": "training", "priority": 7}
    },
    
    # Group success predictions update - every hour
    "update-group-predictions": {
        "task": "update_group_predictions",
        "schedule": crontab(minute=15, hour="*"),
        "options": {"queue": "training", "priority": 6}
    },
    
    # Data preprocessing - every 30 minutes
    "preprocess-new-data": {
        "task": "preprocess_new_interactions",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "data", "priority": 4}
    }
}

if __name__ == "__main__":
    print("GBGCN Task Scheduler - Development Mode")
    print("Available tasks:", list(celery_app.tasks.keys())) 