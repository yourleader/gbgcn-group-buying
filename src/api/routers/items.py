"""
Items router for Group Buying API - Product management for GBGCN
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
import uuid

from src.database.connection import get_db
from src.database.models import Item, User, UserItemInteraction, InteractionType, GroupMember, Group
from src.core.auth import get_current_user, admin_required, moderator_required
from src.core.config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class ItemCreate(BaseModel):
    """Create item request - Updated to match real DB schema"""
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    base_price: float = Field(..., gt=0)  # Changed from regular_price
    category_id: Optional[str] = Field(None, description="Category UUID")  # Changed from category
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    min_group_size: int = Field(default=2, ge=2)
    max_group_size: int = Field(default=100, ge=2)  # Changed from max_discount_percentage
    images: List[str] = Field(default=[])  # Changed to match DB
    specifications: Optional[dict] = None
    is_active: bool = Field(default=True)
    is_group_buyable: bool = Field(default=True)

class ItemUpdate(BaseModel):
    """Update item request - Updated to match real DB schema"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    base_price: Optional[float] = Field(None, gt=0)  # Changed from regular_price
    category_id: Optional[str] = Field(None, description="Category UUID")  # Changed from category
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    min_group_size: Optional[int] = Field(None, ge=2)
    max_group_size: Optional[int] = Field(None, ge=2)  # Changed from max_discount_percentage
    images: Optional[List[str]] = None
    specifications: Optional[dict] = None
    is_active: Optional[bool] = None
    is_group_buyable: Optional[bool] = None

class ItemResponse(BaseModel):
    """Item response model - Updated to match real DB schema"""
    id: str
    name: str
    description: Optional[str]
    base_price: float  # Changed from regular_price
    category_id: Optional[str]  # Changed from category
    brand: Optional[str]
    model: Optional[str]
    min_group_size: int
    max_group_size: int  # Changed from max_discount_percentage
    images: List[str]  # Changed from image_urls
    specifications: Optional[dict]
    is_active: bool
    is_group_buyable: bool
    created_at: datetime
    updated_at: datetime
    
    # Derived fields for compatibility
    category_name: Optional[str] = None  # Will be populated from join
    total_groups: int = 0  # Will be calculated
    success_rate: float = 0.0  # Will be calculated
    
    class Config:
        from_attributes = True

class ItemStats(BaseModel):
    """Item statistics for GBGCN analytics"""
    item_id: str
    total_views: int
    total_likes: int
    total_groups_formed: int
    successful_groups: int
    average_group_size: float
    average_completion_time_hours: float
    price_sensitivity: float
    seasonal_trend: str
    user_demographics: dict
    recommendation_score: float

class ItemInteraction(BaseModel):
    """Record item interaction"""
    interaction_type: str = Field(..., pattern="^(VIEW|LIKE|DISLIKE|SHARE|BOOKMARK)$")
    metadata: Optional[dict] = None

class ItemSummary(BaseModel):
    """Item summary model"""
    id: str
    name: str
    base_price: float
    brand: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True

class ItemCreateResponse(BaseModel):
    """Response for item creation"""
    item_id: str
    message: str
    success: bool

class ItemImageUploadResponse(BaseModel):
    """Response for image upload"""
    image_url: str
    message: str
    success: bool

# Utility functions
def calculate_item_stats(item: Item) -> dict:
    """Calculate item statistics (mock calculation for now)"""
    return {
        "total_groups": 0,
        "success_rate": 0.0,
        "category_name": None
    }

# =============================================================================
# API ENDPOINTS - ORDERED CORRECTLY TO AVOID ROUTE CONFLICTS
# =============================================================================

# 1. SPECIFIC ROUTES FIRST (before parameterized routes)

@router.get("/stats/categories")
async def get_item_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all available item categories
    
    Returns list of categories for filtering and navigation
    """
    try:
        result = await db.execute(
            select(Item.category_id, func.count(Item.id).label('count'))
            .where(Item.is_active == True)
            .group_by(Item.category_id)
            .order_by(func.count(Item.id).desc())
        )
        
        categories = result.all()
        
        return [
            {"category_id": category_id, "item_count": count}
            for category_id, count in categories
        ]
        
    except Exception as e:
        logger.error(f"Error getting item categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting categories: {str(e)}"
        )

# 2. ROOT ROUTES (/, POST /, GET /)

@router.post("/", response_model=ItemCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(get_current_user),  # Changed from moderator_required
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new item for group buying
    
    Adds a new product that can be used for group buying sessions
    """
    try:
        new_item = Item(
            name=item_data.name,
            description=item_data.description,
            base_price=item_data.base_price,
            category_id=item_data.category_id,
            brand=item_data.brand,
            model=item_data.model,
            min_group_size=item_data.min_group_size,
            max_group_size=item_data.max_group_size,
            images=item_data.images or [],
            specifications=item_data.specifications or {},
            is_active=item_data.is_active,
            is_group_buyable=item_data.is_group_buyable
            # Note: created_at and updated_at are auto-set by SQLAlchemy defaults
        )
        
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        
        logger.info(f"Item created successfully with ID: {new_item.id}")
        
        return ItemCreateResponse(
            item_id=str(new_item.id),
            message="Item created successfully",
            success=True
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating item: {str(e)}"
        )

@router.get("/", response_model=List[ItemResponse])
async def get_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    is_active: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Get filtered items with simplified, robust serialization"""
    try:
        # Build query with filters
        filters = [Item.is_active == is_active]
        
        if category:
            filters.append(Item.category_id.ilike(f"%{category}%"))
        
        if brand:
            filters.append(Item.brand.ilike(f"%{brand}%"))
        
        if min_price is not None:
            filters.append(Item.base_price >= min_price)
        
        if max_price is not None:
            filters.append(Item.base_price <= max_price)
        
        if search:
            search_filter = or_(
                Item.name.ilike(f"%{search}%"),
                Item.description.ilike(f"%{search}%"),
                Item.brand.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        # Execute query
        result = await db.execute(
            select(Item)
            .where(and_(*filters))
            .offset(skip)
            .limit(limit)
            .order_by(Item.created_at.desc())
        )
        items = result.scalars().all()
        
        # ✅ SAFE SERIALIZATION - Extract values and handle nulls
        response_items = []
        for item in items:
            try:
                # Safe extraction of values with null handling
                item_data = {
                    "id": str(item.id) if item.id else "",
                    "name": item.name or "",
                    "description": item.description,
                    "base_price": float(item.base_price) if item.base_price is not None else 0.0,
                    "category_id": item.category_id,
                    "brand": item.brand,
                    "model": item.model,
                    "min_group_size": int(item.min_group_size) if item.min_group_size is not None else 2,
                    "max_group_size": int(item.max_group_size) if item.max_group_size is not None else 100,
                    "images": list(item.images) if item.images else [],
                    "specifications": dict(item.specifications) if item.specifications else {},
                    "is_active": bool(item.is_active) if item.is_active is not None else True,
                    "is_group_buyable": bool(item.is_group_buyable) if item.is_group_buyable is not None else True,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                    # Calculated fields
                    "category_name": None,
                    "total_groups": 0,
                    "success_rate": 0.0
                }
                
                # Use model_validate for Pydantic v2 compatibility
                response_item = ItemResponse.model_validate(item_data)
                response_items.append(response_item)
                
            except Exception as item_error:
                logger.error(f"Error serializing item {getattr(item, 'id', 'unknown')}: {str(item_error)}")
                # Continue with other items, don't fail the entire request
                continue
        
        logger.info(f"Retrieved {len(response_items)} items successfully") 
        return response_items
        
    except Exception as e:
        logger.error(f"Error retrieving items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving items: {str(e)}"
        )

# 3. PARAMETERIZED ROUTES LAST (after specific routes)

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get item details by ID
    
    Returns detailed item information including analytics
    """
    try:
        result = await db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        if not bool(item.is_active):
            # Only moderators and admins can view inactive items
            if str(current_user.role) not in ["ADMIN", "MODERATOR"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Item not found"
                )
        
        # Record view interaction
        view_interaction = UserItemInteraction(
            user_id=str(current_user.id),
            item_id=item_id,
            interaction_type=InteractionType.VIEW
        )
        db.add(view_interaction)
        await db.commit()
        
        stats = calculate_item_stats(item)
        
        item_dict = {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "base_price": float(item.base_price),
            "category_id": item.category_id,
            "brand": item.brand,
            "model": item.model,
            "min_group_size": item.min_group_size,
            "max_group_size": item.max_group_size,
            "images": item.images or [],
            "specifications": item.specifications or {},
            "is_active": bool(item.is_active),
            "is_group_buyable": bool(item.is_group_buyable),
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "category_name": stats["category_name"],
            "total_groups": stats["total_groups"],
            "success_rate": stats["success_rate"]
        }
        
        return ItemResponse(**item_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving item: {str(e)}"
        )

@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str,
    item_update: ItemUpdate,
    current_user: User = Depends(get_current_user),  # Changed from moderator_required
    db: AsyncSession = Depends(get_db)
):
    """
    Update item details
    
    Allows users to modify item information
    """
    try:
        result = await db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        # Update fields
        update_data = item_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "images":
                setattr(item, field, value or [])
            else:
                setattr(item, field, value)
        
        await db.commit()
        await db.refresh(item)
        
        stats = calculate_item_stats(item)
        
        item_dict = {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "base_price": float(item.base_price),
            "category_id": item.category_id,
            "brand": item.brand,
            "model": item.model,
            "min_group_size": item.min_group_size,
            "max_group_size": item.max_group_size,
            "images": item.images or [],
            "specifications": item.specifications or {},
            "is_active": bool(item.is_active),
            "is_group_buyable": bool(item.is_group_buyable),
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "category_name": stats["category_name"],
            "total_groups": stats["total_groups"],
            "success_rate": stats["success_rate"]
        }
        
        return ItemResponse(**item_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating item: {str(e)}"
        )

@router.delete("/{item_id}")
async def delete_item(
    item_id: str,
    current_user: User = Depends(get_current_user),  # Changed from admin_required
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an item (Soft delete by setting is_active=False)
    
    Marks item as inactive instead of permanently deleting
    """
    try:
        result = await db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        # Soft delete
        item.is_active = False
        await db.commit()
        
        return {"message": "Item deleted successfully", "item_id": item_id}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting item: {str(e)}"
        )

@router.post("/{item_id}/interact")
async def record_interaction(
    item_id: str,
    interaction: ItemInteraction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Record user interaction with item
    
    Tracks user behavior for GBGCN recommendation algorithm
    """
    try:
        # Verify item exists
        result = await db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        # Create interaction record
        user_interaction = UserItemInteraction(
            user_id=str(current_user.id),
            item_id=item_id,
            interaction_type=InteractionType[interaction.interaction_type],
            metadata=interaction.metadata or {}
        )
        
        db.add(user_interaction)
        await db.commit()
        
        return {
            "message": f"Interaction {interaction.interaction_type} recorded successfully",
            "item_id": item_id,
            "interaction_type": interaction.interaction_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording interaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording interaction: {str(e)}"
        )

@router.post("/{item_id}/upload-image", response_model=ItemImageUploadResponse)
async def upload_item_image(
    item_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),  # Changed from moderator_required
    db: AsyncSession = Depends(get_db)
):
    """
    Upload item image
    
    Adds product images for better user experience
    """
    try:
        # Check if item exists
        result = await db.execute(
            select(Item).where(Item.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        # For now, return a mock URL
        image_url = f"https://example.com/images/{item_id}/{file.filename}"
        
        # Add image URL to item
        current_images = item.images or []
        current_images.append(image_url)
        item.images = current_images
        
        await db.commit()
        
        return ItemImageUploadResponse(
            image_url=image_url,
            message="Image uploaded successfully",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error uploading image for item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        ) 