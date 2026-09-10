"""Pydantic schemas for API requests and responses."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Auth schemas
class TelegramAuthData(BaseModel):
    """Telegram authentication data."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str


# User schemas
class UserBase(BaseModel):
    """Base user schema."""
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = "en"


class UserCreate(UserBase):
    """User creation schema."""
    user_id: int


class UserUpdate(BaseModel):
    """User update schema."""
    subscription_tier: Optional[str] = None
    subscription_status: Optional[str] = None
    daily_download_limit: Optional[int] = None
    monthly_download_limit: Optional[int] = None
    is_banned: Optional[bool] = None
    ban_reason: Optional[str] = None
    notes: Optional[str] = None


class UserResponse(UserBase):
    """User response schema."""
    user_id: int
    subscription_tier: str
    subscription_status: str
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    trial_used: bool
    downloads_count: int
    ai_searches_count: int
    last_active: Optional[datetime] = None
    created_at: datetime
    daily_download_limit: int
    monthly_download_limit: int
    is_banned: bool
    ban_reason: Optional[str] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response."""
    total: int
    users: List[UserResponse]
    page: int
    pages: int


# Subscription Plan schemas
class SubscriptionPlanBase(BaseModel):
    """Base subscription plan schema."""
    name: str
    slug: str
    daily_downloads: Optional[int] = None
    monthly_downloads: Optional[int] = None
    max_quality: int = 320
    ai_search_enabled: bool = False
    priority_support: bool = False
    price: float = 0.0
    currency: str = "USD"
    billing_period: str = "monthly"
    trial_days: int = 0
    is_active: bool = True


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Subscription plan creation schema."""
    pass


class SubscriptionPlanUpdate(BaseModel):
    """Subscription plan update schema."""
    name: Optional[str] = None
    daily_downloads: Optional[int] = None
    monthly_downloads: Optional[int] = None
    max_quality: Optional[int] = None
    ai_search_enabled: Optional[bool] = None
    priority_support: Optional[bool] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    billing_period: Optional[str] = None
    trial_days: Optional[int] = None
    is_active: Optional[bool] = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    """Subscription plan response schema."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Trial Campaign schemas
class TrialCampaignBase(BaseModel):
    """Base trial campaign schema."""
    name: str
    description: Optional[str] = None
    trial_days: int
    plan_id: int
    start_date: datetime
    end_date: datetime
    max_users: Optional[int] = None
    promo_code: Optional[str] = None
    is_active: bool = True


class TrialCampaignCreate(TrialCampaignBase):
    """Trial campaign creation schema."""
    pass


class TrialCampaignUpdate(BaseModel):
    """Trial campaign update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    trial_days: Optional[int] = None
    end_date: Optional[datetime] = None
    max_users: Optional[int] = None
    is_active: Optional[bool] = None


class TrialCampaignResponse(TrialCampaignBase):
    """Trial campaign response schema."""
    id: int
    users_claimed: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Dashboard schemas
class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_users: int
    active_users: int
    premium_users: int
    total_downloads: int
    revenue: float
    active_trials: int


class ActivityItem(BaseModel):
    """Activity feed item."""
    type: str
    message: str
    timestamp: datetime
    user_id: Optional[int] = None


# Analytics schemas
class AnalyticsOverview(BaseModel):
    """Analytics overview data."""
    period: str
    user_growth: List[Dict[str, Any]]
    download_stats: List[Dict[str, Any]]
    revenue_stats: List[Dict[str, Any]]


# Admin action schemas
class BanUserRequest(BaseModel):
    """Ban user request."""
    reason: str


class SendMessageRequest(BaseModel):
    """Send message to user request."""
    message: str


class BulkActionRequest(BaseModel):
    """Bulk action request."""
    user_ids: List[int]
    action: str  # ban, unban, change_tier
    parameters: Optional[Dict[str, Any]] = None
