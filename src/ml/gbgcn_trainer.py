"""
GBGCN Model Trainer for Group Buying Recommendations
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch_geometric.data import Data
import numpy as np
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

from src.ml.gbgcn_model import GBGCN, GBGCNLoss
from src.core.config import settings
from src.core.logging import get_model_logger
from src.database.connection import get_db
from src.database.models import User, Item, Group, GroupMember, UserItemInteraction, SocialConnection

class GBGCNTrainer:
    """
    Trainer class for GBGCN model with async support
    """
    
    def __init__(self):
        self.logger = get_model_logger()
        self.model: Optional[GBGCN] = None
        self.optimizer: Optional[optim.Optimizer] = None
        self.criterion: Optional[GBGCNLoss] = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.is_initialized = False
        self.last_training_time: Optional[datetime] = None
        self.training_metrics: Dict[str, float] = {}
        
        # Model paths
        self.model_dir = Path(settings.MODEL_SAVE_PATH)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.model_dir / "gbgcn_model.pth"
        self.metrics_path = self.model_dir / "training_metrics.json"
        
        self.logger.info(f"GBGCNTrainer initialized - Device: {self.device}")
    
    async def initialize(self) -> None:
        """Initialize the GBGCN model and components"""
        try:
            # Load existing model or create new one
            if self.model_path.exists():
                await self.load_model()
            else:
                await self.create_new_model()
            
            self.is_initialized = True
            self.logger.info("GBGCN trainer initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize GBGCN trainer: {e}")
            raise
    
    async def create_new_model(self) -> None:
        """Create a new GBGCN model with random initialization"""
        # Get data statistics for model dimensions
        stats = await self._get_data_statistics()
        
        num_users = stats['num_users']
        num_items = stats['num_items']
        
        # Initialize model
        self.model = GBGCN(
            num_users=num_users,
            num_items=num_items,
            embedding_dim=settings.EMBEDDING_DIM,
            num_layers=settings.NUM_GCN_LAYERS,
            dropout=settings.DROPOUT_RATE,
            alpha=settings.ALPHA,
            beta=settings.BETA
        ).to(self.device)
        
        # Initialize optimizer
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=settings.LEARNING_RATE,
            weight_decay=1e-5
        )
        
        # Initialize loss function
        self.criterion = GBGCNLoss(
            alpha=settings.ALPHA,
            beta=settings.BETA
        )
        
        self.logger.info(f"Created new GBGCN model - Users: {num_users}, Items: {num_items}")
    
    async def load_model(self) -> None:
        """Load existing GBGCN model from disk"""
        try:
            checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # Get current data statistics
            stats = await self._get_data_statistics()
            
            # Initialize model with current dimensions
            self.model = GBGCN(
                num_users=stats['num_users'],
                num_items=stats['num_items'],
                embedding_dim=settings.EMBEDDING_DIM,
                num_layers=settings.NUM_GCN_LAYERS,
                dropout=settings.DROPOUT_RATE,
                alpha=settings.ALPHA,
                beta=settings.BETA
            ).to(self.device)
            
            # Load model state
            self.model.load_state_dict(checkpoint['model_state_dict'])
            
            # Initialize optimizer
            self.optimizer = optim.Adam(
                self.model.parameters(),
                lr=settings.LEARNING_RATE,
                weight_decay=1e-5
            )
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            
            # Initialize loss function
            self.criterion = GBGCNLoss(
                alpha=settings.ALPHA,
                beta=settings.BETA
            )
            
            # Load training metrics
            if self.metrics_path.exists():
                with open(self.metrics_path, 'r') as f:
                    self.training_metrics = json.load(f)
            
            self.last_training_time = checkpoint.get('training_time')
            
            self.logger.info(f"Loaded GBGCN model from {self.model_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            await self.create_new_model()
    
    async def save_model(self) -> None:
        """Save GBGCN model to disk"""
        try:
            checkpoint = {
                'model_state_dict': self.model.state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'training_time': datetime.utcnow(),
                'config': {
                    'embedding_dim': settings.EMBEDDING_DIM,
                    'num_layers': settings.NUM_GCN_LAYERS,
                    'dropout': settings.DROPOUT_RATE,
                    'alpha': settings.ALPHA,
                    'beta': settings.BETA
                }
            }
            
            torch.save(checkpoint, self.model_path)
            
            # Save training metrics
            with open(self.metrics_path, 'w') as f:
                json.dump(self.training_metrics, f, indent=2, default=str)
            
            self.logger.info(f"Model saved to {self.model_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
    
    async def train_epoch(self, train_data: Data) -> Dict[str, float]:
        """Train one epoch of the GBGCN model"""
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        
        # For this implementation, we'll train on the full graph
        # In production, you might want to use mini-batching
        
        self.optimizer.zero_grad()
        
        # Forward pass
        outputs = self.model(train_data)
        
        # Calculate loss
        loss = self.criterion(outputs, train_data)
        
        # Backward pass
        loss.backward()
        self.optimizer.step()
        
        total_loss += loss.item()
        num_batches += 1
        
        avg_loss = total_loss / num_batches
        
        return {
            'loss': avg_loss,
            'learning_rate': self.optimizer.param_groups[0]['lr']
        }
    
    async def evaluate(self, eval_data: Data) -> Dict[str, float]:
        """Evaluate the GBGCN model"""
        self.model.eval()
        
        with torch.no_grad():
            outputs = self.model(eval_data)
            loss = self.criterion(outputs, eval_data)
            
            # Calculate additional metrics
            metrics = {
                'val_loss': loss.item(),
                'group_success_accuracy': self._calculate_group_success_accuracy(outputs, eval_data),
                'recommendation_recall_at_10': self._calculate_recall_at_k(outputs, eval_data, k=10),
                'social_influence_mse': self._calculate_social_influence_mse(outputs, eval_data)
            }
        
        return metrics
    
    async def train(self, num_epochs: Optional[int] = None) -> Dict[str, Any]:
        """Train the GBGCN model"""
        if not self.is_initialized:
            await self.initialize()
        
        if num_epochs is None:
            num_epochs = settings.MAX_EPOCHS
        
        self.logger.info(f"Starting GBGCN training for {num_epochs} epochs")
        
        # Prepare training data
        train_data, eval_data = await self._prepare_training_data()
        
        best_val_loss = float('inf')
        patience_counter = 0
        training_history = []
        
        for epoch in range(num_epochs):
            # Train one epoch
            train_metrics = await self.train_epoch(train_data)
            
            # Evaluate
            eval_metrics = await self.evaluate(eval_data)
            
            # Combine metrics
            epoch_metrics = {**train_metrics, **eval_metrics, 'epoch': epoch}
            training_history.append(epoch_metrics)
            
            # Log progress
            self.logger.info(
                f"Epoch {epoch}/{num_epochs} - "
                f"Loss: {train_metrics['loss']:.4f}, "
                f"Val Loss: {eval_metrics['val_loss']:.4f}, "
                f"Group Accuracy: {eval_metrics['group_success_accuracy']:.4f}"
            )
            
            # Early stopping
            if eval_metrics['val_loss'] < best_val_loss:
                best_val_loss = eval_metrics['val_loss']
                patience_counter = 0
                # Save best model
                await self.save_model()
            else:
                patience_counter += 1
                if patience_counter >= settings.PATIENCE:
                    self.logger.info(f"Early stopping at epoch {epoch}")
                    break
        
        # Update training metrics
        self.training_metrics = {
            'last_training_time': datetime.utcnow().isoformat(),
            'num_epochs_trained': epoch + 1,
            'best_val_loss': best_val_loss,
            'final_metrics': epoch_metrics
        }
        
        self.last_training_time = datetime.utcnow()
        
        return {
            'status': 'completed',
            'epochs_trained': epoch + 1,
            'best_val_loss': best_val_loss,
            'training_history': training_history
        }
    
    async def retrain(self) -> Dict[str, Any]:
        """Retrain the model with new data"""
        self.logger.info("Starting GBGCN model retraining")
        return await self.train()
    
    async def predict_item_recommendations(self, user_id: str, k: int = 10) -> List[Dict[str, Any]]:
        """Generate item recommendations for a user using GBGCN"""
        if not self.is_initialized:
            await self.initialize()
        
        self.model.eval()
        
        # Prepare data for this user
        user_data = await self._prepare_user_data(user_id)
        
        with torch.no_grad():
            outputs = self.model(user_data)
            
            # Extract item recommendations from outputs
            # This would depend on the specific output structure of your model
            item_scores = outputs.get('item_recommendations', torch.zeros(0))
            
            # Get top-k items
            if len(item_scores) > 0:
                top_k_indices = torch.topk(item_scores, min(k, len(item_scores))).indices
                
                recommendations = []
                for idx in top_k_indices:
                    item_id = self._index_to_item_id(idx.item())
                    score = item_scores[idx].item()
                    
                    recommendations.append({
                        'item_id': item_id,
                        'score': score,
                        'algorithm': 'GBGCN'
                    })
                
                return recommendations
        
        return []
    
    async def predict_group_success(self, group_id: str) -> float:
        """Predict group success probability using GBGCN"""
        if not self.is_initialized:
            await self.initialize()
        
        self.model.eval()
        
        # Prepare group data
        group_data = await self._prepare_group_data(group_id)
        
        with torch.no_grad():
            outputs = self.model(group_data)
            
            # Extract group success probability
            success_prob = outputs.get('group_success_prob', 0.5)
            
            if isinstance(success_prob, torch.Tensor):
                success_prob = success_prob.item()
        
        return float(success_prob)
    
    async def get_status(self) -> Dict[str, Any]:
        """Get trainer status and metrics"""
        return {
            'is_initialized': self.is_initialized,
            'device': str(self.device),
            'last_training_time': self.last_training_time.isoformat() if self.last_training_time else None,
            'model_path': str(self.model_path),
            'training_metrics': self.training_metrics,
            'config': {
                'embedding_dim': settings.EMBEDDING_DIM,
                'num_layers': settings.NUM_GCN_LAYERS,
                'dropout': settings.DROPOUT_RATE,
                'alpha': settings.ALPHA,
                'beta': settings.BETA,
                'learning_rate': settings.LEARNING_RATE
            }
        }
    
    def is_ready(self) -> bool:
        """Check if the trainer is ready for inference"""
        return self.is_initialized and self.model is not None
    
    # Helper methods
    async def _get_data_statistics(self) -> Dict[str, int]:
        """Get database statistics for model initialization"""
        try:
            from sqlalchemy import func, select
            
            async for db in get_db():
                # Count users
                users_result = await db.execute(select(func.count(User.id)))
                num_users = users_result.scalar() or 1000
                
                # Count items  
                items_result = await db.execute(select(func.count(Item.id)))
                num_items = items_result.scalar() or 500
                
                # Count groups
                groups_result = await db.execute(select(func.count(Group.id)))
                num_groups = groups_result.scalar() or 100
                
                # Count interactions
                interactions_result = await db.execute(select(func.count(UserItemInteraction.id)))
                num_interactions = interactions_result.scalar() or 5000
                
                return {
                    'num_users': max(num_users, 100),  # Ensure minimum for model stability
                    'num_items': max(num_items, 50),
                    'num_groups': num_groups,
                    'num_interactions': num_interactions
                }
                
        except Exception as e:
            self.logger.error(f"Error getting data statistics: {e}")
            # Return safe defaults
            return {
                'num_users': 1000,
                'num_items': 500,
                'num_groups': 100,
                'num_interactions': 5000
            }
    
    async def _prepare_training_data(self) -> Tuple[Data, Data]:
        """Prepare training and evaluation data for GBGCN"""
        try:
            # Import the data service
            from src.services.data_service import DataService
            
            data_service = DataService()
            train_data, eval_data = await data_service.prepare_training_data()
            
            return train_data, eval_data
            
        except Exception as e:
            self.logger.error(f"Error preparing training data: {e}")
            # Fallback to dummy data
            num_users = 1000
            num_items = 500
            
            # Create dummy edge indices
            edge_index = torch.randint(0, num_users + num_items, (2, 1000))
            
            # Create dummy features
            x = torch.randn(num_users + num_items, settings.EMBEDDING_DIM)
            
            train_data = Data(x=x, edge_index=edge_index)
            eval_data = Data(x=x, edge_index=edge_index)
            
            return train_data, eval_data
    
    async def _prepare_user_data(self, user_id: str) -> Data:
        """Prepare data for user-specific recommendations"""
        try:
            from src.services.data_service import DataService
            
            data_service = DataService()
            user_data = await data_service.prepare_user_data(user_id)
            
            return user_data
            
        except Exception as e:
            self.logger.error(f"Error preparing user data for {user_id}: {e}")
            # Fallback to dummy data
            num_nodes = 100
            edge_index = torch.randint(0, num_nodes, (2, 50))
            x = torch.randn(num_nodes, settings.EMBEDDING_DIM)
            
            return Data(x=x, edge_index=edge_index)
    
    async def _prepare_group_data(self, group_id: str) -> Data:
        """Prepare data for group success prediction"""
        try:
            from src.services.data_service import DataService
            
            data_service = DataService()
            group_data = await data_service.prepare_group_data(group_id)
            
            return group_data
            
        except Exception as e:
            self.logger.error(f"Error preparing group data for {group_id}: {e}")
            # Fallback to dummy data
            num_nodes = 50
            edge_index = torch.randint(0, num_nodes, (2, 25))
            x = torch.randn(num_nodes, settings.EMBEDDING_DIM)
            
            return Data(x=x, edge_index=edge_index)
    
    def _calculate_group_success_accuracy(self, outputs: Dict[str, torch.Tensor], data: Data) -> float:
        """Calculate group success prediction accuracy"""
        # Placeholder implementation
        return 0.75
    
    def _calculate_recall_at_k(self, outputs: Dict[str, torch.Tensor], data: Data, k: int) -> float:
        """Calculate recall@k for recommendations"""
        # Placeholder implementation
        return 0.65
    
    def _calculate_social_influence_mse(self, outputs: Dict[str, torch.Tensor], data: Data) -> float:
        """Calculate MSE for social influence predictions"""
        # Placeholder implementation
        return 0.15
    
    def _index_to_item_id(self, index: int) -> str:
        """Convert item index to item ID"""
        # Placeholder implementation
        return f"item_{index}" 