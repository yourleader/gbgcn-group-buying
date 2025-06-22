"""
Business Rules for Group Buying System (GBGCN)
Centralizes all business logic constraints and validation rules
"""

from typing import Dict, Any, List
from enum import Enum
from src.core.config import settings


class BusinessRuleViolation(Exception):
    """Custom exception for business rule violations"""
    pass


class GroupBusinessRules:
    """Business rules for group management"""
    
    # Group Size Rules
    MIN_GROUP_SIZE = settings.MIN_GROUP_SIZE  # 2
    MAX_GROUP_SIZE = settings.MAX_GROUP_SIZE  # 100
    DEFAULT_GROUP_SIZE = 10
    
    # Duration Rules
    MIN_DURATION_DAYS = 1
    MAX_DURATION_DAYS = 30
    DEFAULT_DURATION_DAYS = settings.DEFAULT_GROUP_DURATION_DAYS  # 7
    
    # User Limits
    MAX_ACTIVE_GROUPS_PER_USER = 5
    MAX_GROUPS_JOINED_PER_DAY = 10
    MAX_GROUPS_CREATED_PER_DAY = 3
    
    # Pricing Rules
    MIN_DISCOUNT_PERCENTAGE = settings.MIN_DISCOUNT_PERCENTAGE  # 0.05 (5%)
    MAX_DISCOUNT_PERCENTAGE = settings.MAX_DISCOUNT_PERCENTAGE  # 0.50 (50%)
    MIN_ITEM_PRICE = 1.00  # Minimum item price in currency
    
    @staticmethod
    def validate_group_creation(
        user_active_groups: int,
        target_size: int,
        min_size: int,
        duration_days: int,
        target_price: float,
        item_base_price: float
    ) -> Dict[str, Any]:
        """
        Validate group creation parameters
        Returns: {"valid": bool, "errors": List[str]}
        """
        errors = []
        
        # User limits
        if user_active_groups >= GroupBusinessRules.MAX_ACTIVE_GROUPS_PER_USER:
            errors.append(f"Maximum {GroupBusinessRules.MAX_ACTIVE_GROUPS_PER_USER} active groups allowed per user")
        
        # Group size validation
        if min_size < GroupBusinessRules.MIN_GROUP_SIZE:
            errors.append(f"Minimum group size must be at least {GroupBusinessRules.MIN_GROUP_SIZE}")
        
        if target_size > GroupBusinessRules.MAX_GROUP_SIZE:
            errors.append(f"Maximum group size is {GroupBusinessRules.MAX_GROUP_SIZE}")
        
        if min_size > target_size:
            errors.append("Minimum size cannot be greater than target size")
        
        # Duration validation
        if duration_days < GroupBusinessRules.MIN_DURATION_DAYS:
            errors.append(f"Minimum duration is {GroupBusinessRules.MIN_DURATION_DAYS} day")
        
        if duration_days > GroupBusinessRules.MAX_DURATION_DAYS:
            errors.append(f"Maximum duration is {GroupBusinessRules.MAX_DURATION_DAYS} days")
        
        # Pricing validation
        if target_price >= item_base_price:
            errors.append("Target price must be lower than base price to provide discount")
        
        discount_percentage = (item_base_price - target_price) / item_base_price
        if discount_percentage < GroupBusinessRules.MIN_DISCOUNT_PERCENTAGE:
            errors.append(f"Minimum discount is {GroupBusinessRules.MIN_DISCOUNT_PERCENTAGE*100}%")
        
        if discount_percentage > GroupBusinessRules.MAX_DISCOUNT_PERCENTAGE:
            errors.append(f"Maximum discount is {GroupBusinessRules.MAX_DISCOUNT_PERCENTAGE*100}%")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "calculated_discount": discount_percentage
        }
    
    @staticmethod
    def can_join_group(
        group_status: str,
        current_members: int,
        target_size: int,
        user_groups_today: int
    ) -> Dict[str, Any]:
        """
        Check if user can join a specific group
        """
        errors = []
        
        # Status validation
        if group_status not in ["FORMING", "OPEN"]:
            errors.append("Group is not accepting new members")
        
        # Capacity validation
        if current_members >= target_size:
            errors.append("Group is already full")
        
        # User daily limit
        if user_groups_today >= GroupBusinessRules.MAX_GROUPS_JOINED_PER_DAY:
            errors.append(f"Maximum {GroupBusinessRules.MAX_GROUPS_JOINED_PER_DAY} groups can be joined per day")
        
        return {
            "can_join": len(errors) == 0,
            "errors": errors
        }


class ItemBusinessRules:
    """Business rules for item management"""
    
    # Item validation rules
    MIN_ITEM_PRICE = 1.00
    MAX_ITEM_PRICE = 100000.00
    MIN_GROUP_SIZE_FOR_ITEM = 2
    MAX_GROUP_SIZE_FOR_ITEM = 1000
    
    # Item status rules
    REQUIRED_FIELDS = ["name", "base_price", "category_id"]
    MAX_IMAGES_PER_ITEM = 10
    MAX_SPECIFICATIONS_SIZE = 50  # KB
    
    @staticmethod
    def validate_item_for_group_buying(item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if item is suitable for group buying
        """
        errors = []
        
        # Required fields
        for field in ItemBusinessRules.REQUIRED_FIELDS:
            if not item_data.get(field):
                errors.append(f"Field '{field}' is required")
        
        # Price validation
        base_price = item_data.get("base_price", 0)
        if base_price < ItemBusinessRules.MIN_ITEM_PRICE:
            errors.append(f"Minimum item price is ${ItemBusinessRules.MIN_ITEM_PRICE}")
        
        if base_price > ItemBusinessRules.MAX_ITEM_PRICE:
            errors.append(f"Maximum item price is ${ItemBusinessRules.MAX_ITEM_PRICE}")
        
        # Group size validation for item
        min_group_size = item_data.get("min_group_size", 2)
        max_group_size = item_data.get("max_group_size", 100)
        
        if min_group_size < ItemBusinessRules.MIN_GROUP_SIZE_FOR_ITEM:
            errors.append(f"Minimum group size for items must be at least {ItemBusinessRules.MIN_GROUP_SIZE_FOR_ITEM}")
        
        if max_group_size > ItemBusinessRules.MAX_GROUP_SIZE_FOR_ITEM:
            errors.append(f"Maximum group size for items cannot exceed {ItemBusinessRules.MAX_GROUP_SIZE_FOR_ITEM}")
        
        # Images validation
        images = item_data.get("images", [])
        if len(images) > ItemBusinessRules.MAX_IMAGES_PER_ITEM:
            errors.append(f"Maximum {ItemBusinessRules.MAX_IMAGES_PER_ITEM} images allowed per item")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


class UserBusinessRules:
    """Business rules for user management"""
    
    # User limits
    MAX_SOCIAL_CONNECTIONS = settings.MAX_SOCIAL_CONNECTIONS_PER_USER  # 500
    MIN_REPUTATION_SCORE = 0.0
    MAX_REPUTATION_SCORE = 10.0
    
    # Activity limits
    MAX_DAILY_INTERACTIONS = 1000
    MAX_RECOMMENDATIONS_PER_REQUEST = settings.MAX_RECOMMENDATION_LIMIT  # 50
    
    @staticmethod
    def can_create_social_connection(
        current_connections: int,
        target_user_reputation: float
    ) -> Dict[str, Any]:
        """
        Check if user can create new social connection
        """
        errors = []
        
        if current_connections >= UserBusinessRules.MAX_SOCIAL_CONNECTIONS:
            errors.append(f"Maximum {UserBusinessRules.MAX_SOCIAL_CONNECTIONS} connections allowed")
        
        if target_user_reputation < UserBusinessRules.MIN_REPUTATION_SCORE:
            errors.append("Cannot connect to users with negative reputation")
        
        return {
            "can_connect": len(errors) == 0,
            "errors": errors
        }


class GBGCNBusinessRules:
    """Business rules specific to GBGCN model operations"""
    
    # Model parameters
    MIN_INTERACTIONS_FOR_TRAINING = settings.MIN_INTERACTIONS_PER_USER  # 5
    MIN_ITEMS_FOR_TRAINING = settings.MIN_INTERACTIONS_PER_ITEM  # 3
    MIN_SUCCESS_PROBABILITY = settings.MIN_SUCCESS_PROBABILITY  # 0.1
    
    # Recommendation rules
    MAX_RECOMMENDATION_AGE_HOURS = 24
    MIN_SOCIAL_INFLUENCE_THRESHOLD = settings.SOCIAL_INFLUENCE_THRESHOLD  # 0.1
    
    @staticmethod
    def validate_recommendation_request(
        user_interaction_count: int,
        limit: int,
        include_social: bool
    ) -> Dict[str, Any]:
        """
        Validate GBGCN recommendation request
        """
        errors = []
        
        if user_interaction_count < GBGCNBusinessRules.MIN_INTERACTIONS_FOR_TRAINING:
            errors.append(f"User needs at least {GBGCNBusinessRules.MIN_INTERACTIONS_FOR_TRAINING} interactions for personalized recommendations")
        
        if limit > UserBusinessRules.MAX_RECOMMENDATIONS_PER_REQUEST:
            errors.append(f"Maximum {UserBusinessRules.MAX_RECOMMENDATIONS_PER_REQUEST} recommendations per request")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "use_fallback": user_interaction_count < GBGCNBusinessRules.MIN_INTERACTIONS_FOR_TRAINING
        }


class SystemBusinessRules:
    """System-wide business rules and constraints"""
    
    # Performance limits
    MAX_CONCURRENT_GROUPS_PER_ITEM = 10
    MAX_GRAPH_NODES_FOR_TRAINING = settings.MAX_GRAPH_NODES  # 100000
    
    # Data retention rules
    INACTIVE_USER_DAYS = 365
    COMPLETED_GROUP_RETENTION_DAYS = 90
    FAILED_GROUP_RETENTION_DAYS = 30
    
    @staticmethod
    def validate_system_load(
        active_groups: int,
        concurrent_users: int,
        training_in_progress: bool
    ) -> Dict[str, Any]:
        """
        Validate system load and capacity
        """
        warnings = []
        errors = []
        
        if active_groups > 10000:
            warnings.append("High number of active groups - consider optimization")
        
        if concurrent_users > 1000:
            warnings.append("High concurrent user load")
        
        if training_in_progress and concurrent_users > 500:
            errors.append("Cannot handle high load during model training")
        
        return {
            "system_healthy": len(errors) == 0,
            "warnings": warnings,
            "errors": errors
        }


# Validation helper functions
def validate_business_rules(operation: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Central validation function for all business operations
    """
    if operation == "create_group":
        return GroupBusinessRules.validate_group_creation(**data)
    elif operation == "join_group":
        return GroupBusinessRules.can_join_group(**data)
    elif operation == "create_item":
        return ItemBusinessRules.validate_item_for_group_buying(data)
    elif operation == "recommend":
        return GBGCNBusinessRules.validate_recommendation_request(**data)
    else:
        return {"valid": False, "errors": [f"Unknown operation: {operation}"]}


# Constants for easy import
BUSINESS_RULES = {
    "group": GroupBusinessRules,
    "item": ItemBusinessRules,
    "user": UserBusinessRules,
    "gbgcn": GBGCNBusinessRules,
    "system": SystemBusinessRules
} 