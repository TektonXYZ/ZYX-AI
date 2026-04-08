"""
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from zyx_ai.core.config import settings
from zyx_ai.api.auth import router as auth_router
from zyx_ai.api.trading import router as trading_router
from zyx_ai.api.portfolio import router as portfolio_router
from zyx_ai.core.monitoring import PerformanceMonitor, CircuitBreaker
from zyx_ai.core.alerts import alert_manager, AlertSeverity


# Global monitoring instances
monitor = PerformanceMonitor()
circuit_breaker = CircuitBreaker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.app_env}")
    print(f"Paper Trading: {settings.enable_paper_trading}")
    
    # Send startup alert
    await alert_manager.send_alert(
        title="XYZ Bot Started",
        message=f"Version {settings.app_version} is now operational",
        severity=AlertSeverity.INFO
    )
    
    yield
    
    # Shutdown
    print(f"Shutting down {settings.app_name}")
    
    # Send shutdown alert
    await alert_manager.send_alert(
        title="XYZ Bot Shutting Down",
        message="Application is stopping",
        severity=AlertSeverity.WARNING
    )


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="High-frequency quantitative trading AI with leverage",
    lifespan=lifespan,
)

# CORS middleware with configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,  # 10 minutes
)

# Include routers
app.include_router(auth_router)
app.include_router(trading_router)
app.include_router(portfolio_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health = monitor.check_health()
    
    return {
        "status": "healthy" if health["healthy"] else "unhealthy",
        "version": settings.app_version,
        "issues": health["issues"],
        "metrics": health["metrics"],
        "circuit_breaker": circuit_breaker.state
    }


@app.get("/metrics")
async def get_metrics():
    """Get detailed performance metrics."""
    return monitor.get_metrics()


@app.get("/status")
async def get_status():
    """Get full system status."""
    return {
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
        },
        "health": monitor.check_health(),
        "circuit_breaker": {
            "state": circuit_breaker.state,
            "failure_count": circuit_breaker.failure_count,
        },
        "settings": {
            "paper_trading": settings.enable_paper_trading,
            "auto_trading": settings.enable_auto_trading,
            "max_leverage": settings.max_leverage,
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "zyx_ai.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
