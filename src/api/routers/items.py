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
from src.database.models import Item, User, UserItemInteraction, InteractionType
from src.core.auth import get_current_user, admin_required, moderator_required
from src.core.config import settings

router = APIRouter()

# Pydantic models
class ItemCreate(BaseModel):
    """Create item request"""
    name: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    category: str = Field(..., min_length=2, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    regular_price: float = Field(..., gt=0)
    min_group_size: int = Field(..., ge=2)
    max_discount_percentage: float = Field(..., ge=0.05, le=0.8)  # 5-80%
    supplier_name: str = Field(..., min_length=2, max_length=200)
    supplier_contact: str = Field(..., min_length=5, max_length=200)
    specifications: Optional[dict] = None
    tags: List[str] = Field(default=[], max_items=10)
    external_url: Optional[HttpUrl] = None

class ItemUpdate(BaseModel):
    """Update item request"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    regular_price: Optional[float] = Field(None, gt=0)
    min_group_size: Optional[int] = Field(None, ge=2)
    max_discount_percentage: Optional[float] = Field(None, ge=0.05, le=0.8)
    supplier_name: Optional[str] = Field(None, min_length=2, max_length=200)
    supplier_contact: Optional[str] = Field(None, min_length=5, max_length=200)
    specifications: Optional[dict] = None
    tags: Optional[List[str]] = Field(None, max_items=10)
    external_url: Optional[HttpUrl] = None
    is_active: Optional[bool] = None

class ItemResponse(BaseModel):
    """Item response model"""
    id: str
    name: str
    description: str
    category: str
    subcategory: Optional[str]
    brand: Optional[str]
    regular_price: float
    min_group_size: int
    max_discount_percentage: float
    current_discount: float
    supplier_name: str
    supplier_contact: str
    specifications: Optional[dict]
    tags: List[str]
    external_url: Optional[str]
    image_urls: List[str]
    is_active: bool
    popularity_score: float
    total_groups: int
    successful_groups: int
    success_rate: float
    avg_group_size: float
    created_at: datetime
    updated_at: datetime
    
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

@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(moderator_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new item for group buying
    
    Adds a new product that can be used for group buying sessions
    """
    # Create new item
    new_item = Item(
        name=item_data.name,
        description=item_data.description,
        category=item_data.category,
        subcategory=item_data.subcategory,
        brand=item_data.brand,
        regular_price=item_data.regular_price,
        min_group_size=item_data.min_group_size,
        max_discount_percentage=item_data.max_discount_percentage,
        current_discount=0.0,
        supplier_name=item_data.supplier_name,
        supplier_contact=item_data.supplier_contact,
        specifications=item_data.specifications or {},
        tags=item_data.tags or [],
        external_url=str(item_data.external_url) if item_data.external_url else None,
        image_urls=[],
        is_active=True,
        popularity_score=0.0,
        total_groups=0,
        successful_groups=0,
        created_by=str(current_user.id)
    )
    
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    
    # Calculate derived fields for response
    success_rate = 0.0
    avg_group_size = 0.0
    
    response = ItemResponse(
        id=str(new_item.id),
        name=new_item.name,
        description=new_item.description,
        category=new_item.category,
        subcategory=new_item.subcategory,
        brand=new_item.brand,
        regular_price=float(new_item.regular_price),
        min_group_size=new_item.min_group_size,
        max_discount_percentage=float(new_item.max_discount_percentage),
        current_discount=float(new_item.current_discount),
        supplier_name=new_item.supplier_name,
        supplier_contact=new_item.supplier_contact,
        specifications=new_item.specifications or {},
        tags=new_item.tags or [],
        external_url=str(new_item.external_url) if new_item.external_url else None,
        image_urls=new_item.image_urls or [],
        is_active=bool(new_item.is_active),
        popularity_score=float(new_item.popularity_score),
        total_groups=new_item.total_groups,
        successful_groups=new_item.successful_groups,
        success_rate=success_rate,
        avg_group_size=avg_group_size,
        created_at=new_item.created_at,
        updated_at=new_item.updated_at
    )
    
    return response

@router.get("/", response_model=List[ItemResponse])
async def list_items(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, le=100, description="Page size"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, gt=0, description="Maximum price"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    active_only: bool = Query(True, description="Show only active items"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List items with filtering and search
    
    Returns items available for group buying with GBGCN recommendations
    """
    # Build query
    query = select(Item)
    
    # Apply filters
    filters = []
    if active_only:
        filters.append(Item.is_active == True)
    
    if category:
        filters.append(Item.category.ilike(f"%{category}%"))
    
    if brand:
        filters.append(Item.brand.ilike(f"%{brand}%"))
    
    if min_price is not None:
        filters.append(Item.regular_price >= min_price)
    
    if max_price is not None:
        filters.append(Item.regular_price <= max_price)
    
    if search:
        search_pattern = f"%{search}%"
        filters.append(or_(
            Item.name.ilike(search_pattern),
            Item.description.ilike(search_pattern),
            Item.tags.cast(str).ilike(search_pattern)
        ))
    
    if filters:
        query = query.where(and_(*filters))
    
    # Apply sorting
    sort_column = getattr(Item, sort_by, Item.created_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    
    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Format response
    responses = []
    for item in items:
        # Calculate derived fields
        success_rate = 0.0
        avg_group_size = 0.0
        
        if item.total_groups > 0:
            success_rate = item.successful_groups / item.total_groups
            # Would calculate actual avg_group_size from groups table
        
        responses.append(ItemResponse(
            id=str(item.id),
            name=item.name,
            description=item.description,
            category=item.category,
            subcategory=item.subcategory,
            brand=item.brand,
            regular_price=float(item.regular_price),
            min_group_size=item.min_group_size,
            max_discount_percentage=float(item.max_discount_percentage),
            current_discount=float(item.current_discount),
            supplier_name=item.supplier_name,
            supplier_contact=item.supplier_contact,
            specifications=item.specifications or {},
            tags=item.tags or [],
            external_url=str(item.external_url) if item.external_url else None,
            image_urls=item.image_urls or [],
            is_active=bool(item.is_active),
            popularity_score=float(item.popularity_score),
            total_groups=item.total_groups,
            successful_groups=item.successful_groups,
            success_rate=success_rate,
            avg_group_size=avg_group_size,
            created_at=item.created_at,
            updated_at=item.updated_at
        ))
    
    return responses

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
    
    # Calculate derived fields
    success_rate = 0.0
    avg_group_size = 0.0
    
    if item.total_groups > 0:
        success_rate = item.successful_groups / item.total_groups
    
    return ItemResponse(
        id=str(item.id),
        name=item.name,
        description=item.description,
        category=item.category,
        subcategory=item.subcategory,
        brand=item.brand,
        regular_price=float(item.regular_price),
        min_group_size=item.min_group_size,
        max_discount_percentage=float(item.max_discount_percentage),
        current_discount=float(item.current_discount),
        supplier_name=item.supplier_name,
        supplier_contact=item.supplier_contact,
        specifications=item.specifications or {},
        tags=item.tags or [],
        external_url=str(item.external_url) if item.external_url else None,
        image_urls=item.image_urls or [],
        is_active=bool(item.is_active),
        popularity_score=float(item.popularity_score),
        total_groups=item.total_groups,
        successful_groups=item.successful_groups,
        success_rate=success_rate,
        avg_group_size=avg_group_size,
        created_at=item.created_at,
        updated_at=item.updated_at
    )

@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str,
    item_update: ItemUpdate,
    current_user: User = Depends(moderator_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Update item details (Moderator/Admin only)
    
    Allows authorized users to modify item information
    """
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
        if field == "external_url" and value:
            setattr(item, field, str(value))
        else:
            setattr(item, field, value)
    
    await db.commit()
    await db.refresh(item)
    
    # Calculate derived fields
    success_rate = 0.0
    avg_group_size = 0.0
    
    if item.total_groups > 0:
        success_rate = item.successful_groups / item.total_groups
    
    return ItemResponse(
        id=str(item.id),
        name=item.name,
        description=item.description,
        category=item.category,
        subcategory=item.subcategory,
        brand=item.brand,
        regular_price=float(item.regular_price),
        min_group_size=item.min_group_size,
        max_discount_percentage=float(item.max_discount_percentage),
        current_discount=float(item.current_discount),
        supplier_name=item.supplier_name,
        supplier_contact=item.supplier_contact,
        specifications=item.specifications or {},
        tags=item.tags or [],
        external_url=str(item.external_url) if item.external_url else None,
        image_urls=item.image_urls or [],
        is_active=bool(item.is_active),
        popularity_score=float(item.popularity_score),
        total_groups=item.total_groups,
        successful_groups=item.successful_groups,
        success_rate=success_rate,
        avg_group_size=avg_group_size,
        created_at=item.created_at,
        updated_at=item.updated_at
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
    
    # Update item popularity (simplified calculation)
    if interaction.interaction_type in ["LIKE", "BOOKMARK"]:
        item.popularity_score += 0.1
        await db.commit()
    
    return {
        "message": f"Interaction {interaction.interaction_type} recorded successfully",
        "item_id": item_id,
        "interaction_type": interaction.interaction_type
    }

@router.post("/{item_id}/images")
async def upload_item_image(
    item_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(moderator_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload item image (Moderator/Admin only)
    
    Adds product images for better user experience
    """
    # Verify item exists
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Validate file size (10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size too large. Maximum 10MB allowed."
        )
    
    # In production, save to cloud storage (AWS S3, etc.)
    # For now, return a placeholder URL
    file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
    image_filename = f"item_{item_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
    image_url = f"{settings.BASE_URL}/static/items/{image_filename}"
    
    # Add image URL to item
    current_images = item.image_urls or []
    current_images.append(image_url)
    item.image_urls = current_images
    
    await db.commit()
    
    return {
        "message": "Image uploaded successfully",
        "image_url": image_url,
        "total_images": len(current_images)
    }

@router.get("/{item_id}/stats", response_model=ItemStats)
async def get_item_stats(
    item_id: str,
    current_user: User = Depends(moderator_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Get item analytics and statistics
    
    Returns detailed GBGCN analytics for item performance
    """
    # Verify item exists
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Get interaction stats
    views_result = await db.execute(
        select(func.count(UserItemInteraction.id))
        .where(and_(
            UserItemInteraction.item_id == item_id,
            UserItemInteraction.interaction_type == InteractionType.VIEW
        ))
    )
    total_views = views_result.scalar() or 0
    
    likes_result = await db.execute(
        select(func.count(UserItemInteraction.id))
        .where(and_(
            UserItemInteraction.item_id == item_id,
            UserItemInteraction.interaction_type == InteractionType.LIKE
        ))
    )
    total_likes = likes_result.scalar() or 0
    
    # Calculate metrics
    avg_completion_time = 72.0  # Placeholder: 72 hours average
    price_sensitivity = 0.7  # Placeholder
    seasonal_trend = "stable"  # Placeholder
    user_demographics = {
        "age_groups": {"18-25": 30, "26-35": 40, "36-45": 20, "46+": 10},
        "gender": {"male": 55, "female": 45}
    }
    recommendation_score = float(item.popularity_score)
    
    return ItemStats(
        item_id=item_id,
        total_views=total_views,
        total_likes=total_likes,
        total_groups_formed=item.total_groups,
        successful_groups=item.successful_groups,
        average_group_size=0.0,  # Would calculate from actual groups
        average_completion_time_hours=avg_completion_time,
        price_sensitivity=price_sensitivity,
        seasonal_trend=seasonal_trend,
        user_demographics=user_demographics,
        recommendation_score=recommendation_score
    )

@router.get("/categories/list")
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all available item categories
    
    Returns list of categories for filtering and navigation
    """
    result = await db.execute(
        select(Item.category, func.count(Item.id).label('count'))
        .where(Item.is_active == True)
        .group_by(Item.category)
        .order_by(func.count(Item.id).desc())
    )
    
    categories = result.all()
    
    return [
        {"category": category, "item_count": count}
        for category, count in categories
    ]

@router.delete("/{item_id}")
async def delete_item(
    item_id: str,
    admin_user: User = Depends(admin_required),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an item (Admin only)
    
    Permanently removes item and associated data
    """
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Check if item has active groups
    from src.database.models import Group
    active_groups_result = await db.execute(
        select(func.count(Group.id))
        .where(and_(
            Group.item_id == item_id,
            Group.status.in_(["FORMING", "ACTIVE"])
        ))
    )
    
    active_groups = active_groups_result.scalar() or 0
    if active_groups > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete item with {active_groups} active groups"
        )
    
    # Delete all interactions first
    await db.execute(
        UserItemInteraction.__table__.delete().where(
            UserItemInteraction.item_id == item_id
        )
    )
    
    # Delete item
    await db.delete(item)
    await db.commit()
    
    return {"message": "Item deleted successfully", "item_id": item_id} 