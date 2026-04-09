"""
Application configuration using Pydantic Settings.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = Field(default="XYZ AI", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/zyx_ai",
        env="DATABASE_URL"
    )
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    
    # Redis
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # Security
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")
    
    # CORS
    cors_origins: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    # Exchange API (Binance)
    binance_api_key: Optional[str] = Field(default=None, env="BINANCE_API_KEY")
    binance_secret: Optional[str] = Field(default=None, env="BINANCE_SECRET")
    binance_testnet: bool = Field(default=True, env="BINANCE_TESTNET")
    
    # Exchange API (Bybit)
    bybit_api_key: Optional[str] = Field(default=None, env="BYBIT_API_KEY")
    bybit_secret: Optional[str] = Field(default=None, env="BYBIT_SECRET")
    bybit_testnet: bool = Field(default=True, env="BYBIT_TESTNET")
    
    # Trading
    max_leverage: int = Field(default=10, env="MAX_LEVERAGE")
    default_leverage: int = Field(default=3, env="DEFAULT_LEVERAGE")
    max_position_pct: float = Field(default=0.5, env="MAX_POSITION_PCT")
    risk_per_trade: float = Field(default=0.02, env="RISK_PER_TRADE")
    max_drawdown_pct: float = Field(default=0.20, env="MAX_DRAWDOWN_PCT")
    default_stop_loss_pct: float = Field(default=0.02, env="DEFAULT_STOP_LOSS_PCT")
    default_take_profit_pct: float = Field(default=0.04, env="DEFAULT_TAKE_PROFIT_PCT")
    trading_symbols: List[str] = Field(
        default=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        env="TRADING_SYMBOLS"
    )
    
    @validator("trading_symbols", pre=True)
    def parse_trading_symbols(cls, v):
        """Parse comma-separated trading symbols."""
        if isinstance(v, str):
            return [symbol.strip() for symbol in v.split(",")]
        return v
    
    # Feature Flags
    enable_auto_trading: bool = Field(default=False, env="ENABLE_AUTO_TRADING")
    enable_websocket: bool = Field(default=True, env="ENABLE_WEBSOCKET")
    enable_cache: bool = Field(default=True, env="ENABLE_CACHE")
    enable_paper_trading: bool = Field(default=True, env="ENABLE_PAPER_TRADING")
    
    # Monitoring
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
