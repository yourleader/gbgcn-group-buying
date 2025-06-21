"""
Background tasks module for GBGCN system
"""

# Suppress import warnings for development
try:
    from . import training_tasks  # type: ignore[attr-defined]
    from . import data_tasks  # type: ignore[attr-defined] 
    from . import analytics_tasks  # type: ignore[attr-defined]
except ImportError:
    # Tasks may not be available in development without Celery
    pass

__all__ = ["training_tasks", "data_tasks", "analytics_tasks"] 