"""User management router."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from datetime import datetime

from app.database import get_db
from app.models.models import User, AdminUser, AdminLog
from app.models.schemas import (
    UserResponse,
    UserListResponse,
    UserUpdate,
    BanUserRequest,
    SendMessageRequest
)
from app.services.auth_service import get_current_admin
import httpx
from app.config import settings

router = APIRouter(prefix="/api/admin/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tier: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    List users with filtering and pagination.
    
    Filters:
    - tier: subscription tier (free, basic, premium, enterprise)
    - status: subscription status (active, expired, suspended, banned)
    - search: search by username or name
    """
    query = select(User)
    
    # Apply filters
    if tier:
        query = query.where(User.subscription_tier == tier)
    if status:
        query = query.where(User.subscription_status == status)
    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%")
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        total=total,
        users=users,
        page=(skip // limit) + 1,
        pages=((total + limit - 1) // limit) if total > 0 else 0
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get detailed information about a specific user."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Update user information."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    # Log admin action
    log = AdminLog(
        admin_id=admin.telegram_user_id,
        admin_username=admin.username,
        action="update_user",
        target_user_id=user_id,
        details=update_data
    )
    db.add(log)
    await db.commit()
    
    return user


@router.post("/{user_id}/ban")
async def ban_user(
    user_id: int,
    ban_data: BanUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Ban a user."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_banned = True
    user.ban_reason = ban_data.reason
    user.subscription_status = "banned"
    
    await db.commit()
    
    # Log admin action
    log = AdminLog(
        admin_id=admin.telegram_user_id,
        admin_username=admin.username,
        action="ban_user",
        target_user_id=user_id,
        details={"reason": ban_data.reason}
    )
    db.add(log)
    await db.commit()
    
    return {"success": True, "message": "User banned successfully"}


@router.post("/{user_id}/unban")
async def unban_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Unban a user."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_banned = False
    user.ban_reason = None
    user.subscription_status = "active"
    
    await db.commit()
    
    # Log admin action
    log = AdminLog(
        admin_id=admin.telegram_user_id,
        admin_username=admin.username,
        action="unban_user",
        target_user_id=user_id,
        details={}
    )
    db.add(log)
    await db.commit()
    
    return {"success": True, "message": "User unbanned successfully"}


@router.post("/{user_id}/message")
async def send_message_to_user(
    user_id: int,
    message_data: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Send a direct message to user via Telegram bot."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Send message via Telegram API
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={
                "chat_id": user_id,
                "text": f"📢 <b>Message from Admin</b>\n\n{message_data.message}",
                "parse_mode": "HTML"
            })
            data = response.json()
            
            if not data.get("ok"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to send message: {data.get('description')}"
                )
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    
    # Log admin action
    log = AdminLog(
        admin_id=admin.telegram_user_id,
        admin_username=admin.username,
        action="send_message",
        target_user_id=user_id,
        details={"message": message_data.message}
    )
    db.add(log)
    await db.commit()
    
    return {"success": True, "message": "Message sent successfully"}


@router.get("/{user_id}/history")
async def get_user_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get user activity history."""
    from app.models.models import UsageLog
    
    result = await db.execute(
        select(UsageLog)
        .where(UsageLog.user_id == user_id)
        .order_by(UsageLog.timestamp.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    
    return {
        "user_id": user_id,
        "history": [
            {
                "id": log.id,
                "action_type": log.action_type,
                "resource_id": log.resource_id,
                "metadata": log.metadata,
                "timestamp": log.timestamp
            }
            for log in logs
        ]
    }
