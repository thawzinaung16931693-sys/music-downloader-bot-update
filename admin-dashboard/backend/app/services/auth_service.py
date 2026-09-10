"""Authentication and authorization services."""
import hashlib
import hmac
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.models import AdminUser

security = HTTPBearer()


def verify_telegram_auth(auth_data: Dict[str, Any]) -> bool:
    """Verify Telegram authentication data hash."""
    check_hash = auth_data.pop("hash", None)
    if not check_hash:
        return False
    
    # Create data-check-string
    data_check_arr = [f"{k}={v}" for k, v in sorted(auth_data.items())]
    data_check_string = "\n".join(data_check_arr)
    
    # Calculate secret key
    secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    
    # Calculate hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return calculated_hash == check_hash


async def get_telegram_user_info(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user info from Telegram API."""
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getChat"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={"chat_id": user_id})
            data = response.json()
            if data.get("ok"):
                return data.get("result")
        except Exception:
            pass
    return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    """Get current authenticated admin user."""
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    telegram_user_id: int = payload.get("sub")
    if telegram_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    # Get admin user from database
    result = await db.execute(
        select(AdminUser).where(AdminUser.telegram_user_id == telegram_user_id)
    )
    admin = result.scalar_one_or_none()
    
    if admin is None or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin user not found or inactive"
        )
    
    return admin


def check_permission(admin: AdminUser, permission: str) -> bool:
    """Check if admin has specific permission."""
    if admin.role == "super_admin":
        return True
    
    # Parse permission (e.g., "users.ban")
    parts = permission.split(".")
    if len(parts) != 2:
        return False
    
    resource, action = parts
    
    if not admin.permissions:
        return False
    
    resource_perms = admin.permissions.get(resource, {})
    return resource_perms.get(action, False)


async def require_permission(permission: str):
    """Dependency to require specific permission."""
    async def permission_checker(admin: AdminUser = Depends(get_current_admin)):
        if not check_permission(admin, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission} required"
            )
        return admin
    return permission_checker
