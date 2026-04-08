# XYZ Bot

> High-frequency quantitative trading AI with leverage

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
python -m zyx_ai.main
```

## Docker

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec app alembic upgrade head
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
pytest --cov=src --cov-report=html
```

## License

MIT
