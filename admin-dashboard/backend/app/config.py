"""Configuration settings for admin dashboard."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Telegram
    telegram_bot_token: str
    admin_user_ids: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 43200  # 30 days
    jwt_refresh_token_expire_days: int = 60
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./admin_dashboard.db"
    
    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def admin_ids(self) -> List[int]:
        """Parse admin user IDs from comma-separated string."""
        return [int(uid.strip()) for uid in self.admin_user_ids.split(",") if uid.strip()]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
