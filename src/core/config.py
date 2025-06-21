"""
Configuration settings for Group Buying system based on GBGCN
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Group Buying API (GBGCN)"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    BASE_URL: str = "http://localhost:8000"
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/groupbuy_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # GBGCN Model Configuration (from paper parameters)
    EMBEDDING_DIM: int = 64  # Default embedding dimension from paper
    NUM_GCN_LAYERS: int = 3  # Number of GCN layers
    DROPOUT_RATE: float = 0.1
    LEARNING_RATE: float = 0.001
    ALPHA: float = 0.6  # Role coefficient (initiator vs participant)
    BETA: float = 0.4   # Loss coefficient (social influence vs preference)
    
    # Model Training
    BATCH_SIZE: int = 512
    MAX_EPOCHS: int = 500
    PATIENCE: int = 20  # Early stopping patience
    MODEL_SAVE_PATH: str = "models/gbgcn"
    MODEL_RETRAIN_INTERVAL: int = 86400  # 24 hours in seconds
    
    # Graph Construction
    MIN_INTERACTIONS_PER_USER: int = 5
    MIN_INTERACTIONS_PER_ITEM: int = 3
    SOCIAL_INFLUENCE_THRESHOLD: float = 0.1
    
    # Recommendation Parameters
    DEFAULT_RECOMMENDATION_LIMIT: int = 10
    MAX_RECOMMENDATION_LIMIT: int = 50
    MIN_SUCCESS_PROBABILITY: float = 0.1
    
    # Group Buying Business Rules
    MIN_GROUP_SIZE: int = 2
    MAX_GROUP_SIZE: int = 100
    DEFAULT_GROUP_DURATION_DAYS: int = 7
    MIN_DISCOUNT_PERCENTAGE: float = 0.05  # 5%
    MAX_DISCOUNT_PERCENTAGE: float = 0.5   # 50%
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_EXPIRE_SECONDS: int = 3600  # 1 hour
    
    # Social Network Parameters (from GBGCN paper)
    MAX_SOCIAL_CONNECTIONS_PER_USER: int = 500
    SOCIAL_INFLUENCE_DECAY_FACTOR: float = 0.8
    FRIEND_RECOMMENDATION_WEIGHT: float = 1.5
    
    # Performance and Monitoring
    LOG_LEVEL: str = "INFO"
    MAX_REQUEST_SIZE: int = 16 * 1024 * 1024  # 16MB
    REQUEST_TIMEOUT: int = 300  # 5 minutes
    
    # Machine Learning Pipeline
    FEATURE_STORE_PATH: str = "data/features"
    MODEL_METRICS_PATH: str = "metrics/gbgcn"
    ENABLE_MODEL_MONITORING: bool = True
    
    # Data Processing
    MAX_GRAPH_NODES: int = 100000
    GRAPH_SAMPLING_RATIO: float = 0.8
    NEGATIVE_SAMPLING_RATIO: int = 4  # 4 negative samples per positive
    
    # Notification Settings
    ENABLE_NOTIFICATIONS: bool = True
    NOTIFICATION_BATCH_SIZE: int = 100
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]
    UPLOAD_PATH: str = "uploads"
    
    # External Services
    STRIPE_PUBLIC_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    
    # Social Media Integration
    FACEBOOK_APP_ID: Optional[str] = None
    FACEBOOK_APP_SECRET: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # GBGCN Specific Hyperparameters (from paper)
    GRAPH_ATTENTION_HEADS: int = 4
    CROSS_VIEW_ATTENTION_DIM: int = 32
    SOCIAL_GCN_LAYERS: int = 2
    PREDICTION_HIDDEN_DIM: int = 128
    
    # Experimental Features
    ENABLE_ADVANCED_ANALYTICS: bool = False
    ENABLE_A_B_TESTING: bool = False
    ENABLE_REAL_TIME_UPDATES: bool = True
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

# Create global settings instance
settings = Settings()

# Validate critical configurations
def validate_config():
    """Validate critical configuration settings"""
    errors = []
    
    if not settings.SECRET_KEY or settings.SECRET_KEY == "your-secret-key-change-in-production":
        if settings.ENVIRONMENT == "production":
            errors.append("SECRET_KEY must be set in production")
    
    if settings.EMBEDDING_DIM <= 0:
        errors.append("EMBEDDING_DIM must be positive")
    
    if settings.NUM_GCN_LAYERS <= 0:
        errors.append("NUM_GCN_LAYERS must be positive")
    
    if not (0 <= settings.ALPHA <= 1):
        errors.append("ALPHA must be between 0 and 1")
    
    if not (0 <= settings.BETA <= 1):
        errors.append("BETA must be between 0 and 1")
    
    if settings.MIN_GROUP_SIZE < 2:
        errors.append("MIN_GROUP_SIZE must be at least 2")
    
    if settings.MAX_GROUP_SIZE <= settings.MIN_GROUP_SIZE:
        errors.append("MAX_GROUP_SIZE must be greater than MIN_GROUP_SIZE")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

# Validate on import
validate_config() 