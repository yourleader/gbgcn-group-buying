"""
Secure Authentication Router for GBGCN API
Includes JWT authentication, registration, login, and security policies
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import bcrypt
import secrets
import re
from email_validator import validate_email

from src.database.connection import get_db
from src.database.models import User
from src.core.config import settings
from src.core.logging import get_logger

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])
logger = get_logger()

# Security schemes
security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Pydantic Models
class UserRegistration(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Username must be between 3 and 50 characters')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, hyphens and underscores')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    role: str
    created_at: datetime
    last_login: Optional[datetime]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class SecurityPolicy(BaseModel):
    password_policy: Dict[str, Any]
    session_policy: Dict[str, Any]
    api_limits: Dict[str, Any]

# Security Configuration
SECURITY_CONFIG = {
    "password_policy": {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special_chars": False,
        "max_age_days": 90,
        "history_count": 5
    },
    "session_policy": {
        "access_token_expire_minutes": 30,
        "refresh_token_expire_days": 7,
        "max_concurrent_sessions": 3,
        "idle_timeout_minutes": 60
    },
    "api_limits": {
        "max_requests_per_minute": 100,
        "max_requests_per_hour": 1000,
        "max_failed_login_attempts": 5,
        "lockout_duration_minutes": 15
    }
}

# Utility Functions
def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=SECURITY_CONFIG["session_policy"]["access_token_expire_minutes"])
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(32)  # JWT ID for token revocation
    })
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(user_id: str) -> str:
    """Create refresh token"""
    data = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=SECURITY_CONFIG["session_policy"]["refresh_token_expire_days"])
    }
    return jwt.encode(data, settings.SECRET_KEY, algorithm="HS256")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    async for session in get_db():
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# Authentication Endpoints
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegistration,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with security validation
    """
    try:
        async for session in get_db():
            # Check if username or email already exists
            query = select(User).where(
                (User.username == user_data.username) | (User.email == user_data.email)
            )
            result = await session.execute(query)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                if existing_user.username == user_data.username:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Username already registered"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Email already registered"
                    )
            
            # Create new user
            hashed_password = hash_password(user_data.password)
            
            new_user = User(
                id=secrets.token_urlsafe(16),
                username=user_data.username,
                email=user_data.email,
                password_hash=hashed_password,
                full_name=user_data.full_name,
                phone=user_data.phone,
                role="user",  # Default role
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            logger.info(f"New user registered: {user_data.username}")
            
            return UserResponse(
                id=new_user.id,
                username=new_user.username,
                email=new_user.email,
                full_name=new_user.full_name,
                is_active=new_user.is_active,
                role=new_user.role,
                created_at=new_user.created_at,
                last_login=new_user.last_login
            )
            
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=TokenResponse)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens
    """
    try:
        async for session in get_db():
            # Find user by username
            query = select(User).where(User.username == form_data.username)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user or not verify_password(form_data.password, user.password_hash):
                logger.warning(f"Failed login attempt for username: {form_data.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is disabled"
                )
            
            # Update last login
            user.last_login = datetime.utcnow()
            await session.commit()
            
            # Create tokens
            access_token_expires = timedelta(minutes=SECURITY_CONFIG["session_policy"]["access_token_expire_minutes"])
            access_token = create_access_token(
                data={"sub": user.id, "username": user.username, "role": user.role},
                expires_delta=access_token_expires
            )
            refresh_token = create_refresh_token(user.id)
            
            logger.info(f"Successful login: {user.username}")
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=SECURITY_CONFIG["session_policy"]["access_token_expire_minutes"] * 60,
                user=UserResponse(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    full_name=user.full_name,
                    is_active=user.is_active,
                    role=user.role,
                    created_at=user.created_at,
                    last_login=user.last_login
                )
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=Dict[str, str])
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        async for session in get_db():
            query = select(User).where(User.id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            # Create new access token
            access_token_expires = timedelta(minutes=SECURITY_CONFIG["session_policy"]["access_token_expire_minutes"])
            access_token = create_access_token(
                data={"sub": user.id, "username": user.username, "role": user.role},
                expires_delta=access_token_expires
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": str(SECURITY_CONFIG["session_policy"]["access_token_expire_minutes"] * 60)
            }
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        role=current_user.role,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@router.post("/logout")
async def logout_user(current_user: User = Depends(get_current_user)):
    """
    Logout user (client should delete tokens)
    """
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Successfully logged out"}

@router.get("/security-policy", response_model=SecurityPolicy)
async def get_security_policy():
    """
    Get current security policies for client validation
    """
    return SecurityPolicy(
        password_policy=SECURITY_CONFIG["password_policy"],
        session_policy=SECURITY_CONFIG["session_policy"],
        api_limits=SECURITY_CONFIG["api_limits"]
    )

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password
    """
    # Verify current password
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    user_data = UserRegistration(
        username="temp",
        email="temp@temp.com",
        password=new_password
    )  # Will validate password
    
    # Update password
    async for session in get_db():
        query = select(User).where(User.id == current_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            user.password_hash = hash_password(new_password)
            user.updated_at = datetime.utcnow()
            await session.commit()
            
            logger.info(f"Password changed for user: {current_user.username}")
            return {"message": "Password changed successfully"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    ) 