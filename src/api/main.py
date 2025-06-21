"""
Main FastAPI application for Group Buying system
Based on GBGCN paper implementation
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import asyncio
from typing import List, Optional

from src.database.connection import get_db, init_db
from src.api.routers import (
    users, items, groups, recommendations, 
    social, auth, analytics, background_tasks
)
from src.ml.gbgcn_trainer import GBGCNTrainer
from src.core.config import settings
from src.core.logging import setup_logging

# Setup logging
logger = setup_logging()

# Initialize GBGCN trainer as global variable
gbgcn_trainer: Optional[GBGCNTrainer] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Group Buying API based on GBGCN...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize GBGCN model
    global gbgcn_trainer
    try:
        gbgcn_trainer = GBGCNTrainer()
        await gbgcn_trainer.initialize()
        logger.info("GBGCN model initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize GBGCN model: {e}")
    
    # Start background tasks
    asyncio.create_task(periodic_model_training())
    
    yield
    
    # Shutdown
    logger.info("Shutting down Group Buying API...")
    if gbgcn_trainer:
        await gbgcn_trainer.save_model()

# Create FastAPI app
app = FastAPI(
    title="Group Buying API (GBGCN)",
    description="""
    Group Buying Recommendation System based on GBGCN paper
    
    Features:
    - Multi-view Graph Convolutional Networks
    - Social influence modeling
    - Group formation optimization
    - Real-time recommendations
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(items.router, prefix="/api/v1/items", tags=["Items"])
app.include_router(groups.router, prefix="/api/v1/groups", tags=["Groups"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["GBGCN Recommendations"])
app.include_router(social.router, prefix="/api/v1/social", tags=["Social Network"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(background_tasks.router, tags=["Background Training Tasks"])

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Group Buying API based on GBGCN paper",
        "paper": "Group-Buying Recommendation for Social E-Commerce",
        "features": [
            "Multi-view embedding propagation",
            "Cross-view social influence",
            "Heterogeneous graph neural networks",
            "Group formation optimization"
        ],
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    model_status = "healthy" if gbgcn_trainer and gbgcn_trainer.is_ready() else "not_ready"
    
    return {
        "status": "healthy",
        "model_status": model_status,
        "database": "connected"
    }

@app.get("/model/status")
async def model_status():
    """Get GBGCN model status and metrics"""
    if not gbgcn_trainer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GBGCN model not initialized"
        )
    
    return await gbgcn_trainer.get_status()

async def periodic_model_training():
    """Background task for periodic model retraining"""
    while True:
        try:
            await asyncio.sleep(settings.MODEL_RETRAIN_INTERVAL)
            
            if gbgcn_trainer:
                logger.info("Starting periodic GBGCN model retraining...")
                await gbgcn_trainer.retrain()
                logger.info("GBGCN model retrained successfully")
                
        except Exception as e:
            logger.error(f"Error in periodic model training: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 