"""Database models."""
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """Bot user model."""
    __tablename__ = "users"
    
    user_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="en")
    
    # Subscription
    subscription_tier = Column(String(50), default="free")  # free, basic, premium, enterprise
    subscription_status = Column(String(50), default="active")  # active, expired, suspended, banned
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    
    # Trial
    trial_used = Column(Boolean, default=False)
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    # Usage
    downloads_count = Column(Integer, default=0)
    ai_searches_count = Column(Integer, default=0)
    last_active = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Limits
    daily_download_limit = Column(Integer, default=10)
    monthly_download_limit = Column(Integer, default=100)
    
    # Moderation
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)


class AdminUser(Base):
    """Admin user model."""
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    role = Column(String(50), default="admin")  # super_admin, admin, moderator, support
    permissions = Column(JSON, nullable=True)
    
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SubscriptionPlan(Base):
    """Subscription plan model."""
    __tablename__ = "subscription_plans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    
    # Limits
    daily_downloads = Column(Integer, nullable=True)  # null = unlimited
    monthly_downloads = Column(Integer, nullable=True)
    max_quality = Column(Integer, default=320)  # kbps
    ai_search_enabled = Column(Boolean, default=False)
    priority_support = Column(Boolean, default=False)
    
    # Pricing
    price = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    billing_period = Column(String(50), default="monthly")  # monthly, yearly, lifetime
    
    trial_days = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Subscription(Base):
    """User subscription model."""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    
    status = Column(String(50), default="active")  # pending, active, expired, cancelled
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=True)
    
    payment_method = Column(String(50), nullable=True)
    payment_id = Column(String(255), nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TrialCampaign(Base):
    """Trial campaign model."""
    __tablename__ = "trial_campaigns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    trial_days = Column(Integer, nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    max_users = Column(Integer, nullable=True)  # null = unlimited
    users_claimed = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    promo_code = Column(String(50), unique=True, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())


class UsageLog(Base):
    """Usage log model."""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False, index=True)
    
    action_type = Column(String(50), nullable=False)  # download, search, ai_search, settings_change
    resource_id = Column(String(255), nullable=True)
    meta_data = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime, server_default=func.now(), index=True)


class AdminLog(Base):
    """Admin action log model."""
    __tablename__ = "admin_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(BigInteger, ForeignKey("admin_users.telegram_user_id"), nullable=False)
    admin_username = Column(String(255), nullable=True)
    
    action = Column(String(100), nullable=False)  # ban_user, change_subscription, etc.
    target_user_id = Column(BigInteger, nullable=True)
    details = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime, server_default=func.now(), index=True)
