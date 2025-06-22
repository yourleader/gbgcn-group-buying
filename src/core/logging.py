"""
Logging configuration for Group Buying API
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.core.config import settings

def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """
    Setup logging configuration for the application
    
    Args:
        log_file: Optional log file path. If None, uses default path.
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Default log file with timestamp
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"groupbuy_{timestamp}.log"
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Set logging level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    
    # Create application logger
    logger = logging.getLogger("groupbuy")
    logger.setLevel(log_level)
    
    # Configure specific loggers
    
    # SQLAlchemy logger (reduce verbosity in production)
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    if settings.DEBUG:
        sqlalchemy_logger.setLevel(logging.INFO)
    else:
        sqlalchemy_logger.setLevel(logging.WARNING)
    
    # Uvicorn logger
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)
    
    # FastAPI logger
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.setLevel(logging.INFO)
    
    # GBGCN model logger
    gbgcn_logger = logging.getLogger("gbgcn")
    gbgcn_logger.setLevel(log_level)
    
    # PyTorch logger (reduce verbosity)
    torch_logger = logging.getLogger("torch")
    torch_logger.setLevel(logging.WARNING)
    
    logger.info(f"Logging initialized - Level: {settings.LOG_LEVEL}")
    logger.info(f"Log file: {log_file}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f"groupbuy.{name}")

# Specific loggers for different components
def get_api_logger() -> logging.Logger:
    """Get logger for API components"""
    return get_logger("api")

def get_model_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get logger for GBGCN model components
    
    Args:
        name: Optional specific module name. If None, uses "model"
    """
    if name:
        return get_logger(f"model.{name}")
    return get_logger("model")

def get_database_logger() -> logging.Logger:
    """Get logger for database components"""
    return get_logger("database")

def get_auth_logger() -> logging.Logger:
    """Get logger for authentication components"""
    return get_logger("auth")

class StructuredLogger:
    """
    Structured logger for consistent log formatting
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_api_request(self, method: str, path: str, user_id: Optional[str] = None, 
                       duration_ms: Optional[float] = None):
        """Log API request with structured data"""
        extra_data = {
            "method": method,
            "path": path,
            "user_id": user_id,
            "duration_ms": duration_ms
        }
        
        message = f"{method} {path}"
        if user_id:
            message += f" - User: {user_id}"
        if duration_ms:
            message += f" - Duration: {duration_ms:.2f}ms"
        
        self.logger.info(message, extra=extra_data)
    
    def log_model_training(self, epoch: int, loss: float, metrics: dict):
        """Log model training progress"""
        extra_data = {
            "epoch": epoch,
            "loss": loss,
            **metrics
        }
        
        message = f"Training - Epoch: {epoch}, Loss: {loss:.4f}"
        for metric, value in metrics.items():
            message += f", {metric}: {value:.4f}"
        
        self.logger.info(message, extra=extra_data)
    
    def log_recommendation(self, user_id: str, item_ids: list, 
                          algorithm: str, execution_time_ms: float):
        """Log recommendation generation"""
        extra_data = {
            "user_id": user_id,
            "item_count": len(item_ids),
            "algorithm": algorithm,
            "execution_time_ms": execution_time_ms
        }
        
        message = f"Recommendation - User: {user_id}, Items: {len(item_ids)}, "
        message += f"Algorithm: {algorithm}, Time: {execution_time_ms:.2f}ms"
        
        self.logger.info(message, extra=extra_data)
    
    def log_group_formation(self, group_id: str, initiator_id: str, 
                           target_size: int, success_probability: float):
        """Log group formation event"""
        extra_data = {
            "group_id": group_id,
            "initiator_id": initiator_id,
            "target_size": target_size,
            "success_probability": success_probability
        }
        
        message = f"Group Formation - ID: {group_id}, Initiator: {initiator_id}, "
        message += f"Target Size: {target_size}, Success Prob: {success_probability:.3f}"
        
        self.logger.info(message, extra=extra_data)
    
    def log_error(self, error: Exception, context: dict = None):
        """Log error with context"""
        extra_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            **(context or {})
        }
        
        message = f"Error - {type(error).__name__}: {str(error)}"
        if context:
            message += f" - Context: {context}"
        
        self.logger.error(message, extra=extra_data, exc_info=True)

# Create default structured logger
def get_structured_logger(name: str) -> StructuredLogger:
    """Get structured logger instance"""
    logger = get_logger(name)
    return StructuredLogger(logger) 