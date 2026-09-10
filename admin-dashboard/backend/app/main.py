"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import auth, users, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events."""
    # Startup
    await init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Shutting down")


# Create FastAPI app
app = FastAPI(
    title="Bar Lar Lar Admin Dashboard API",
    description="Admin dashboard API for Telegram music bot",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(dashboard.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Bar Lar Lar Admin Dashboard API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
