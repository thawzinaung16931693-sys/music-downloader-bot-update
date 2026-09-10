"""Dashboard router for overview statistics."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import User, AdminUser, UsageLog, TrialCampaign
from app.models.schemas import DashboardStats, ActivityItem
from app.services.auth_service import get_current_admin

router = APIRouter(prefix="/api/admin/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get dashboard overview statistics.
    """
    # Total users
    total_users_result = await db.execute(select(func.count(User.user_id)))
    total_users = total_users_result.scalar() or 0
    
    # Active users (active in last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_users_result = await db.execute(
        select(func.count(User.user_id))
        .where(User.last_active >= seven_days_ago)
    )
    active_users = active_users_result.scalar() or 0
    
    # Premium users (all paid tiers)
    premium_users_result = await db.execute(
        select(func.count(User.user_id))
        .where(User.subscription_tier.in_(["basic", "premium", "enterprise"]))
        .where(User.subscription_status == "active")
    )
    premium_users = premium_users_result.scalar() or 0
    
    # Total downloads
    total_downloads_result = await db.execute(
        select(func.sum(User.downloads_count))
    )
    total_downloads = total_downloads_result.scalar() or 0
    
    # Revenue calculation (placeholder - implement with real payment data)
    from app.models.models import Subscription, SubscriptionPlan
    revenue_result = await db.execute(
        select(func.sum(Subscription.amount))
        .where(Subscription.status == "active")
    )
    revenue = revenue_result.scalar() or 0.0
    
    # Active trials
    active_trials_result = await db.execute(
        select(func.count(User.user_id))
        .where(User.trial_used == True)
        .where(User.trial_end >= datetime.utcnow())
    )
    active_trials = active_trials_result.scalar() or 0
    
    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        premium_users=premium_users,
        total_downloads=total_downloads,
        revenue=revenue,
        active_trials=active_trials
    )


@router.get("/activity")
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get recent activity feed.
    """
    activities = []
    
    # Get recent user registrations
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(5)
    )
    new_users = result.scalars().all()
    
    for user in new_users:
        activities.append({
            "type": "user_joined",
            "message": f"New user @{user.username or user.first_name} joined",
            "timestamp": user.created_at,
            "user_id": user.user_id
        })
    
    # Get recent subscription changes
    from app.models.models import Subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
        .limit(5)
    )
    new_subscriptions = result.scalars().all()
    
    for sub in new_subscriptions:
        # Get user info
        user_result = await db.execute(
            select(User).where(User.user_id == sub.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            activities.append({
                "type": "subscription",
                "message": f"@{user.username or user.first_name} upgraded to {user.subscription_tier}",
                "timestamp": sub.created_at,
                "user_id": user.user_id
            })
    
    # Get recent high-volume downloads
    result = await db.execute(
        select(UsageLog.user_id, func.count(UsageLog.id).label("count"))
        .where(UsageLog.action_type == "download")
        .where(UsageLog.timestamp >= datetime.utcnow() - timedelta(hours=1))
        .group_by(UsageLog.user_id)
        .having(func.count(UsageLog.id) > 10)
        .order_by(func.count(UsageLog.id).desc())
        .limit(3)
    )
    heavy_users = result.all()
    
    for user_id, count in heavy_users:
        activities.append({
            "type": "high_usage",
            "message": f"{count} downloads in the last hour",
            "timestamp": datetime.utcnow(),
            "user_id": user_id
        })
    
    # Sort by timestamp
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {"activities": activities[:limit]}


@router.get("/charts/user-growth")
async def get_user_growth_chart(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get user growth chart data.
    """
    from sqlalchemy import cast, Date
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(
            cast(User.created_at, Date).label("date"),
            func.count(User.user_id).label("count")
        )
        .where(User.created_at >= start_date)
        .group_by(cast(User.created_at, Date))
        .order_by(cast(User.created_at, Date))
    )
    data = result.all()
    
    return {
        "data": [
            {"date": str(date), "count": count}
            for date, count in data
        ]
    }


@router.get("/charts/downloads")
async def get_downloads_chart(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get downloads chart data.
    """
    from sqlalchemy import cast, Date
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(
            cast(UsageLog.timestamp, Date).label("date"),
            func.count(UsageLog.id).label("count")
        )
        .where(UsageLog.action_type == "download")
        .where(UsageLog.timestamp >= start_date)
        .group_by(cast(UsageLog.timestamp, Date))
        .order_by(cast(UsageLog.timestamp, Date))
    )
    data = result.all()
    
    return {
        "data": [
            {"date": str(date), "count": count}
            for date, count in data
        ]
    }
