# ZYX AI - High-Frequency Quantitative Trading System

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-80%25+-brightgreen.svg)](tests/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **Production-ready algorithmic trading engine with real exchange integration**

## 🚨 IMPORTANT DISCLAIMER

**This is a quantitative trading framework for educational and research purposes.**

- ⚠️ **Live trading is disabled by default** - uses paper trading mode
- ⚠️ **No guaranteed returns** - all trading involves substantial risk
- ⚠️ **Not financial advice** - consult a professional before trading
- ⚠️ **Test thoroughly** in paper mode before using real capital

## 🎯 Features

### Core Trading Engine
- ✅ **Multiple Trading Strategies**: RSI, MACD, Bollinger Bands, Mean Reversion, Momentum
- ✅ **Real Exchange Integration**: Binance, Bybit (with paper trading mode)
- ✅ **Leverage Management**: Up to 10x with configurable risk limits
- ✅ **Position Sizing**: Kelly Criterion with drawdown protection
- ✅ **Risk Management**: Stop-loss, take-profit, trailing stops, max exposure limits

### Data & Analytics
- ✅ **Live Price Feeds**: WebSocket connections to exchanges
- ✅ **Historical Backtesting**: Test strategies on historical data
- ✅ **Performance Metrics**: Sharpe ratio, Sortino, max drawdown, win rate
- ✅ **Portfolio Analytics**: Real-time P&L, exposure analysis, correlation matrix

### Infrastructure
- ✅ **PostgreSQL Database**: Persistent trade and signal storage
- ✅ **Redis Cache**: High-speed data caching and rate limiting
- ✅ **JWT Authentication**: Secure API access with role-based permissions
- ✅ **WebSocket API**: Real-time updates for frontend dashboard
- ✅ **Docker Deployment**: One-command setup with docker-compose

### Quality & Testing
- ✅ **Comprehensive Test Suite**: 80%+ coverage with pytest
- ✅ **CI/CD Pipeline**: GitHub Actions for automated testing and deployment
- ✅ **Type Safety**: Full mypy type checking
- ✅ **Code Quality**: Black formatting, isort imports, flake8 linting
- ✅ **Monitoring**: Prometheus metrics and structured logging

## 🏗️ Architecture

```
zyx-ai/
├── src/
│   ├── zyx_ai/           # Main package
│   │   ├── api/          # FastAPI routes
│   │   ├── core/         # Configuration, auth, logging
│   │   ├── database/     # SQLAlchemy models & migrations
│   │   ├── exchanges/    # Exchange integrations (Binance, Bybit)
│   │   ├── strategies/   # Trading strategies
│   │   ├── risk/         # Risk management
│   │   └── ws/           # WebSocket handlers
│   └── main.py           # Application entry point
├── tests/                # Comprehensive test suite
├── docker/               # Docker configurations
├── docs/                 # Documentation
└── scripts/              # Utility scripts
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 14+ (or use Docker)
- Redis 7+ (optional, for caching)

### Installation

```bash
# Clone repository
git clone https://github.com/TektonXYZ/ZYX-AI.git
cd ZYX-AI

# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
python -m zyx_ai.main
```

### Docker Setup

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec app alembic upgrade head

# View logs
docker-compose logs -f app
```

## 📊 Trading Strategies

### Implemented Strategies

1. **RSI Mean Reversion**
   - Buys when RSI < 30 (oversold)
   - Sells when RSI > 70 (overbought)
   - Configurable lookback period

2. **MACD Trend Following**
   - Entry on MACD line crossover
   - Exit on signal line crossover
   - Volume confirmation filter

3. **Bollinger Band Breakout**
   - Entry on band squeeze breakout
   - Volatility-based position sizing
   - Mean reversion exit

4. **Custom Strategy**
   - Template for your own algorithm
   - Plug-and-play architecture

### Adding a Custom Strategy

```python
from zyx_ai.strategies.base import BaseStrategy

class MyStrategy(BaseStrategy):
    def generate_signal(self, data: pd.DataFrame) -> Signal:
        # Your algorithm here
        return Signal(
            symbol=data.symbol,
            direction="long",
            strength=0.85,
            metadata={"indicator": value}
        )
```

## 🔌 API Endpoints

### Authentication
```bash
POST /auth/register    # Create new account
POST /auth/login       # Get JWT token
POST /auth/refresh     # Refresh token
```

### Trading
```bash
GET  /signals          # Get active signals
POST /signals/generate # Generate new signal
GET  /trades           # List trades
POST /trades/execute   # Execute trade
POST /trades/{id}/close # Close position
```

### Portfolio
```bash
GET /portfolio         # Current portfolio state
GET /performance       # Performance metrics
GET /history           # Trade history
```

### WebSocket
```bash
ws://localhost:8000/ws/v1
# Real-time updates: trades, signals, portfolio changes
```

## ⚙️ Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/zyx_ai

# Exchange (Paper Trading Mode)
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret
BINANCE_TESTNET=true

# Security
JWT_SECRET_KEY=your-256-bit-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Trading
MAX_LEVERAGE=10
DEFAULT_LEVERAGE=3
MAX_POSITION_PCT=0.5
RISK_PER_TRADE=0.02

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

### Risk Management Settings

```python
# config/risk.yaml
risk_management:
  max_leverage: 10
  max_position_size: 0.5  # 50% of portfolio
  max_drawdown: 0.2       # 20% max drawdown
  risk_per_trade: 0.02    # 2% risk per trade
  stop_loss_pct: 0.02     # 2% stop loss
  take_profit_pct: 0.04   # 4% take profit (2:1 RR)
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_strategies.py -v

# Run integration tests
pytest tests/integration/ -m integration
```

## 📈 Performance

Benchmarks on standard hardware (4 vCPU, 8GB RAM):

- **Signal Generation**: <10ms per symbol
- **Trade Execution**: <50ms round-trip
- **WebSocket Latency**: <20ms
- **Database Queries**: <5ms average
- **Backtesting**: 1000 candles/second

## 🔒 Security

- All API endpoints require JWT authentication
- API keys stored in environment variables, never in code
- CORS restricted to configured origins
- Rate limiting prevents abuse
- Input validation on all endpoints
- SQL injection protection via SQLAlchemy
- XSS protection via proper encoding

## 🐳 Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/zyx_ai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: zyx_ai
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
```

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [Strategy Development](docs/strategies.md)
- [API Reference](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Risk Management](docs/risk.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit with clear messages
6. Push and create a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## ⚠️ Risk Warning

Trading cryptocurrencies and other financial instruments carries a high level of risk and may not be suitable for all investors. Past performance is not indicative of future results. The high degree of leverage can work against you as well as for you. Before deciding to trade, you should carefully consider your investment objectives, level of experience, and risk appetite.

---

**Built with ❤️ by the ZYX AI Team**

For questions or support, open an issue on GitHub.
