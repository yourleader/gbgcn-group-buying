"""
GBGCN (Group-Buying Graph Convolutional Network) implementation
Based on the paper: "Group-Buying Recommendation for Social E-Commerce"

Implements:
1. Multi-view embedding propagation (Initiator & Participant views)
2. Cross-view propagation for social influence
3. Heterogeneous graph processing
4. Group buying success prediction
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, MessagePassing
from torch_geometric.data import HeteroData
from torch_geometric.utils import add_self_loops, degree
import numpy as np
from typing import Dict, List, Tuple, Optional
import math

class GBGCNLayer(MessagePassing):
    """
    Custom Graph Convolutional Layer for GBGCN
    Implements the multi-view propagation from the paper
    """
    
    def __init__(self, in_channels: int, out_channels: int, 
                 view_type: str = 'initiator', dropout: float = 0.1):
        super().__init__(aggr='mean')  # Mean aggregation as in paper
        
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.view_type = view_type
        self.dropout = dropout
        
        # Linear transformation matrices (Equation 4 in paper)
        self.linear_self = nn.Linear(in_channels, out_channels)
        self.linear_neigh = nn.Linear(in_channels, out_channels)
        self.bias = nn.Parameter(torch.zeros(out_channels))
        
        # Activation and normalization
        self.activation = nn.LeakyReLU(0.2)
        self.dropout_layer = nn.Dropout(dropout)
        
        self.reset_parameters()
    
    def reset_parameters(self):
        """Initialize parameters"""
        nn.init.xavier_uniform_(self.linear_self.weight)
        nn.init.xavier_uniform_(self.linear_neigh.weight)
        nn.init.zeros_(self.bias)
    
    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, 
                edge_weight: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass implementing Equation (1) from the paper
        
        Args:
            x: Node features [num_nodes, in_channels]
            edge_index: Edge connectivity [2, num_edges]
            edge_weight: Edge weights [num_edges]
        """
        # Add self-loops for self-connection
        edge_index, edge_weight = add_self_loops(
            edge_index, edge_weight, num_nodes=x.size(0)
        )
        
        # Self transformation
        out_self = self.linear_self(x)
        
        # Neighbor aggregation (Equation 1 in paper)
        out_neigh = self.propagate(edge_index, x=x, edge_weight=edge_weight)
        out_neigh = self.linear_neigh(out_neigh)
        
        # Combine self and neighbor information
        out = out_self + out_neigh + self.bias
        out = self.activation(out)
        out = self.dropout_layer(out)
        
        return out
    
    def message(self, x_j: torch.Tensor, edge_weight: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Message function for neighbor aggregation"""
        if edge_weight is not None:
            return edge_weight.view(-1, 1) * x_j
        return x_j

class CrossViewPropagation(nn.Module):
    """
    Cross-view propagation module from GBGCN paper
    Implements information exchange between initiator and participant views
    """
    
    def __init__(self, embedding_dim: int, dropout: float = 0.1):
        super().__init__()
        self.embedding_dim = embedding_dim
        
        # Cross-view attention mechanism
        self.attention_initiator = nn.Linear(embedding_dim, embedding_dim)
        self.attention_participant = nn.Linear(embedding_dim, embedding_dim)
        self.attention_combine = nn.Linear(embedding_dim * 2, 1)
        
        # Cross-view transformation
        self.cross_transform = nn.Linear(embedding_dim, embedding_dim)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, initiator_emb: torch.Tensor, 
                participant_emb: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Cross-view propagation as described in the paper
        
        Args:
            initiator_emb: Initiator view embeddings [num_users, embedding_dim]
            participant_emb: Participant view embeddings [num_users, embedding_dim]
        
        Returns:
            Updated embeddings for both views
        """
        # Attention weights for cross-view information
        attn_init = self.attention_initiator(initiator_emb)
        attn_part = self.attention_participant(participant_emb)
        
        # Combine for attention computation
        combined = torch.cat([attn_init, attn_part], dim=1)
        attention_weights = torch.sigmoid(self.attention_combine(combined))
        
        # Cross-view information exchange
        cross_info_to_init = attention_weights * self.cross_transform(participant_emb)
        cross_info_to_part = (1 - attention_weights) * self.cross_transform(initiator_emb)
        
        # Update embeddings
        updated_initiator = initiator_emb + self.dropout(cross_info_to_init)
        updated_participant = participant_emb + self.dropout(cross_info_to_part)
        
        return updated_initiator, updated_participant

class SocialInfluenceModule(nn.Module):
    """
    Social influence modeling from GBGCN paper
    Captures friend relationships and social network effects
    """
    
    def __init__(self, embedding_dim: int, num_layers: int = 2):
        super().__init__()
        self.embedding_dim = embedding_dim
        self.num_layers = num_layers
        
        # Social GCN layers
        self.social_gcn_layers = nn.ModuleList([
            GBGCNLayer(embedding_dim, embedding_dim, view_type='social')
            for _ in range(num_layers)
        ])
        
        # Social influence aggregation
        self.influence_aggregator = nn.Linear(embedding_dim, embedding_dim)
        
    def forward(self, user_embeddings: torch.Tensor, 
                social_edge_index: torch.Tensor,
                social_edge_weights: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Process social influence through friend network
        
        Args:
            user_embeddings: User embeddings [num_users, embedding_dim]
            social_edge_index: Social network edges [2, num_social_edges]
            social_edge_weights: Social connection strengths [num_social_edges]
        """
        social_emb = user_embeddings
        
        # Multi-layer social influence propagation
        for layer in self.social_gcn_layers:
            social_emb = layer(social_emb, social_edge_index, social_edge_weights)
        
        # Aggregate social influence
        social_influence = self.influence_aggregator(social_emb)
        
        return social_influence

class GBGCN(nn.Module):
    """
    Complete GBGCN model implementation based on the paper
    "Group-Buying Recommendation for Social E-Commerce"
    """
    
    def __init__(self, 
                 num_users: int,
                 num_items: int,
                 embedding_dim: int = 64,
                 num_layers: int = 3,
                 dropout: float = 0.1,
                 alpha: float = 0.6,  # Role coefficient from paper
                 beta: float = 0.4):   # Loss coefficient from paper
        super().__init__()
        
        self.num_users = num_users
        self.num_items = num_items
        self.embedding_dim = embedding_dim
        self.num_layers = num_layers
        self.alpha = alpha  # Controls initiator vs participant importance
        self.beta = beta    # Controls social influence vs preference
        
        # Raw embedding layers (Figure 2 in paper)
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.item_embedding = nn.Embedding(num_items, embedding_dim)
        
        # Multi-view GCN layers for initiator and participant views
        self.initiator_gcn_layers = nn.ModuleList([
            GBGCNLayer(embedding_dim, embedding_dim, view_type='initiator', dropout=dropout)
            for _ in range(num_layers)
        ])
        
        self.participant_gcn_layers = nn.ModuleList([
            GBGCNLayer(embedding_dim, embedding_dim, view_type='participant', dropout=dropout)
            for _ in range(num_layers)
        ])
        
        # Cross-view propagation
        self.cross_view_propagation = CrossViewPropagation(embedding_dim, dropout)
        
        # Social influence module
        self.social_influence = SocialInfluenceModule(embedding_dim, num_layers=2)
        
        # Prediction layers (Figure 2 in paper)
        self.prediction_layers = nn.Sequential(
            nn.Linear(embedding_dim * 4, embedding_dim * 2),  # Concat all views
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim * 2, embedding_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim, 1),
            nn.Sigmoid()
        )
        
        # Group success prediction (additional to paper)
        self.group_success_predictor = nn.Sequential(
            nn.Linear(embedding_dim * 2, embedding_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim, 1),
            nn.Sigmoid()
        )
        
        self.reset_parameters()
    
    def reset_parameters(self):
        """Initialize all parameters"""
        nn.init.normal_(self.user_embedding.weight, std=0.1)
        nn.init.normal_(self.item_embedding.weight, std=0.1)
    
    def forward(self, 
                user_ids: torch.Tensor,
                item_ids: torch.Tensor,
                initiator_edge_index: torch.Tensor,
                participant_edge_index: torch.Tensor,
                social_edge_index: torch.Tensor,
                social_edge_weights: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """
        Forward pass of GBGCN model
        
        Args:
            user_ids: User indices [batch_size]
            item_ids: Item indices [batch_size]
            initiator_edge_index: Edges for initiator view [2, num_edges]
            participant_edge_index: Edges for participant view [2, num_edges]
            social_edge_index: Social network edges [2, num_social_edges]
            social_edge_weights: Social connection strengths [num_social_edges]
        
        Returns:
            Dictionary with predictions and embeddings
        """
        # Raw embeddings
        all_user_emb = self.user_embedding.weight  # [num_users, embedding_dim]
        all_item_emb = self.item_embedding.weight  # [num_items, embedding_dim]
        
        # In-view propagation for initiator view
        initiator_user_emb = all_user_emb
        for layer in self.initiator_gcn_layers:
            initiator_user_emb = layer(initiator_user_emb, initiator_edge_index)
        
        # In-view propagation for participant view
        participant_user_emb = all_user_emb
        for layer in self.participant_gcn_layers:
            participant_user_emb = layer(participant_user_emb, participant_edge_index)
        
        # Cross-view propagation (Figure 2 in paper)
        initiator_user_emb, participant_user_emb = self.cross_view_propagation(
            initiator_user_emb, participant_user_emb
        )
        
        # Social influence modeling
        social_influence_emb = self.social_influence(
            all_user_emb, social_edge_index, social_edge_weights
        )
        
        # Get embeddings for specific users and items
        user_init_emb = initiator_user_emb[user_ids]      # [batch_size, embedding_dim]
        user_part_emb = participant_user_emb[user_ids]    # [batch_size, embedding_dim]
        user_social_emb = social_influence_emb[user_ids]  # [batch_size, embedding_dim]
        item_emb = all_item_emb[item_ids]                 # [batch_size, embedding_dim]
        
        # Combine multi-view user embeddings (Equation 9 in paper)
        combined_user_emb = (
            self.alpha * user_init_emb + 
            (1 - self.alpha) * user_part_emb + 
            self.beta * user_social_emb
        )
        
        # Concatenate for prediction
        combined_features = torch.cat([
            combined_user_emb, item_emb, user_init_emb, user_part_emb
        ], dim=1)  # [batch_size, embedding_dim * 4]
        
        # Group buying recommendation prediction
        recommendation_score = self.prediction_layers(combined_features).squeeze(-1)
        
        # Group success probability prediction
        group_features = torch.cat([combined_user_emb, item_emb], dim=1)
        success_probability = self.group_success_predictor(group_features).squeeze(-1)
        
        return {
            'recommendation_score': recommendation_score,
            'success_probability': success_probability,
            'user_initiator_emb': user_init_emb,
            'user_participant_emb': user_part_emb,
            'user_social_emb': user_social_emb,
            'item_emb': item_emb,
            'combined_user_emb': combined_user_emb
        }
    
    def predict_group_formation(self, 
                               initiator_id: int,
                               item_id: int,
                               potential_participants: List[int],
                               **kwargs) -> Dict[str, float]:
        """
        Predict the success probability of a group formation
        Based on GBGCN model predictions
        """
        self.eval()
        with torch.no_grad():
            # Get embeddings for all involved users
            all_users = [initiator_id] + potential_participants
            user_tensor = torch.tensor(all_users)
            item_tensor = torch.tensor([item_id] * len(all_users))
            
            # Forward pass
            outputs = self.forward(user_tensor, item_tensor, **kwargs)
            
            # Aggregate predictions
            recommendation_scores = outputs['recommendation_score']
            success_probabilities = outputs['success_probability']
            
            return {
                'group_success_probability': success_probabilities.mean().item(),
                'initiator_score': recommendation_scores[0].item(),
                'participant_scores': recommendation_scores[1:].tolist(),
                'overall_recommendation_score': recommendation_scores.mean().item()
            }

class GBGCNLoss(nn.Module):
    """
    Custom loss function for GBGCN training
    Implements the fine-grained loss from the paper (Equation 12)
    """
    
    def __init__(self, alpha: float = 0.6, beta: float = 0.4):
        super().__init__()
        self.alpha = alpha  # Role coefficient
        self.beta = beta    # Loss balance coefficient
        
    def forward(self, 
                predictions: Dict[str, torch.Tensor],
                targets: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        Compute GBGCN loss
        
        Args:
            predictions: Model predictions
            targets: Ground truth targets
        
        Returns:
            Dictionary with loss components
        """
        # Main recommendation loss (BPR-like from paper)
        pos_scores = predictions['recommendation_score'][targets['positive_mask']]
        neg_scores = predictions['recommendation_score'][targets['negative_mask']]
        
        # Bayesian Personalized Ranking loss
        bpr_loss = -torch.log(torch.sigmoid(pos_scores - neg_scores)).mean()
        
        # Group success prediction loss
        success_targets = targets.get('success_labels', None)
        if success_targets is not None:
            success_loss = F.binary_cross_entropy(
                predictions['success_probability'], 
                success_targets.float()
            )
        else:
            success_loss = torch.tensor(0.0)
        
        # Social influence regularization
        social_reg = torch.tensor(0.0)
        if 'user_social_emb' in predictions:
            social_reg = torch.norm(predictions['user_social_emb'], p=2, dim=1).mean()
        
        # Total loss (Equation 12 in paper)
        total_loss = (
            bpr_loss + 
            self.beta * success_loss + 
            0.001 * social_reg  # L2 regularization
        )
        
        return {
            'total_loss': total_loss,
            'bpr_loss': bpr_loss,
            'success_loss': success_loss,
            'social_regularization': social_reg
        }

def create_heterogeneous_graph(user_item_interactions: List[Tuple],
                              social_connections: List[Tuple],
                              num_users: int,
                              num_items: int) -> Dict[str, torch.Tensor]:
    """
    Create heterogeneous graph data for GBGCN training
    Following the graph construction in the paper
    
    Args:
        user_item_interactions: List of (user_id, item_id, interaction_type) tuples
        social_connections: List of (user_id, friend_id, strength) tuples
        num_users: Total number of users
        num_items: Total number of items
    
    Returns:
        Dictionary with edge indices for different views
    """
    # Separate initiator and participant interactions
    initiator_edges = []
    participant_edges = []
    
    for user_id, item_id, interaction_type in user_item_interactions:
        if interaction_type in ['create_group', 'initiate']:
            initiator_edges.append([user_id, item_id])
        else:  # join_group, participate, purchase, etc.
            participant_edges.append([user_id, item_id])
    
    # Create edge indices
    initiator_edge_index = torch.tensor(initiator_edges, dtype=torch.long).t()
    participant_edge_index = torch.tensor(participant_edges, dtype=torch.long).t()
    
    # Social network edges
    social_edges = [[u, f] for u, f, _ in social_connections]
    social_weights = [s for _, _, s in social_connections]
    social_edge_index = torch.tensor(social_edges, dtype=torch.long).t()
    social_edge_weights = torch.tensor(social_weights, dtype=torch.float)
    
    return {
        'initiator_edge_index': initiator_edge_index,
        'participant_edge_index': participant_edge_index,
        'social_edge_index': social_edge_index,
        'social_edge_weights': social_edge_weights
    } 