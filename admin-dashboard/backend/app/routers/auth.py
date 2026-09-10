"""Authentication router."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.config import settings
from app.models.schemas import TelegramAuthData, Token, TokenRefresh
from app.models.models import AdminUser
from app.services.auth_service import (
    verify_telegram_auth,
    get_telegram_user_info,
    create_access_token,
    create_refresh_token,
    decode_token
)

router = APIRouter(prefix="/api/admin/auth", tags=["auth"])


@router.post("/telegram", response_model=Token)
async def telegram_login(
    auth_data: TelegramAuthData,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate admin using Telegram OAuth.
    
    Verifies Telegram authentication data and creates JWT tokens.
    """
    # Verify telegram auth data
    auth_dict = auth_data.model_dump()
    if not verify_telegram_auth(auth_dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication data"
        )
    
    # Check if user is in admin list
    if auth_data.id not in settings.admin_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not authorized as admin"
        )
    
    # Get or create admin user
    result = await db.execute(
        select(AdminUser).where(AdminUser.telegram_user_id == auth_data.id)
    )
    admin = result.scalar_one_or_none()
    
    if admin is None:
        # Create new admin user
        # First admin becomes super_admin
        result = await db.execute(select(AdminUser))
        existing_admins = result.scalars().all()
        
        role = "super_admin" if len(existing_admins) == 0 else "admin"
        
        admin = AdminUser(
            telegram_user_id=auth_data.id,
            username=auth_data.username,
            first_name=auth_data.first_name,
            last_name=auth_data.last_name,
            role=role,
            permissions={
                "users": {"view": True, "edit": True, "ban": True},
                "subscriptions": {"view": True, "create": True, "modify": True},
                "analytics": {"view": True, "export": True},
                "trials": {"view": True, "create": True, "modify": True}
            } if role == "admin" else None  # super_admin gets all permissions
        )
        db.add(admin)
        await db.flush()
    
    # Update last login
    admin.last_login = datetime.utcnow()
    await db.commit()
    
    # Create tokens
    access_token = create_access_token({"sub": auth_data.id})
    refresh_token = create_refresh_token({"sub": auth_data.id})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    try:
        payload = decode_token(token_data.refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        telegram_user_id: int = payload.get("sub")
        if telegram_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Verify admin still exists and is active
        result = await db.execute(
            select(AdminUser).where(AdminUser.telegram_user_id == telegram_user_id)
        )
        admin = result.scalar_one_or_none()
        
        if admin is None or not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin user not found or inactive"
            )
        
        # Create new tokens
        access_token = create_access_token({"sub": telegram_user_id})
        new_refresh_token = create_refresh_token({"sub": telegram_user_id})
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )
    
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


@router.get("/me")
async def get_current_user_info(
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get current authenticated admin user information.
    """
    return {
        "telegram_user_id": admin.telegram_user_id,
        "username": admin.username,
        "first_name": admin.first_name,
        "last_name": admin.last_name,
        "role": admin.role,
        "permissions": admin.permissions,
        "last_login": admin.last_login,
        "created_at": admin.created_at
    }


from app.services.auth_service import get_current_admin
