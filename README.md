# Kalpi Tech API - Stock Technical Analysis API

A high-performance FastAPI application for calculating and serving technical indicators for stock data with tiered subscription access.

## 🚀 Features

- **Technical Indicators**: SMA, EMA, RSI, MACD, Bollinger Bands
- **Tiered Access**: Free, Pro, Premium subscription levels
- **Authentication**: JWT and API Key authentication
- **Rate Limiting**: Tier-based request limiting
- **Caching**: Redis-based caching for performance
- **High Performance**: Polars for efficient data processing
- **Containerized**: Docker and Docker Compose setup
- **Testing**: Comprehensive test suite
- **Documentation**: Auto-generated OpenAPI/Swagger docs

## 📊 Subscription Tiers

| Tier | Requests/Day | Indicators | Data Range |
|------|-------------|------------|------------|
| Free | 50 | SMA, EMA | Last 3 months |
| Pro | 500 | SMA, EMA, RSI, MACD | Last 1 year |
| Premium | Unlimited | All indicators | Full 3 years |

## 🛠️ Technology Stack

- **Framework**: FastAPI
- **Language**: Python 3.12+
- **Data Processing**: Polars (primary), Pandas (fallback)
- **Database**: PostgreSQL
- **Caching**: Redis
- **Authentication**: JWT + API Keys
- **Server**: Uvicorn
- **Testing**: pytest
- **Containerization**: Docker

## 🏗️ Architecture

```
kalpi-tech-api/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models/              # Pydantic models
│   ├── indicators/          # Technical indicator calculations
│   ├── services/            # Business logic (data, cache, rate limiting)
│   ├── routers/             # API endpoints
│   ├── database/            # Database models and connection
│   ├── core/                # Configuration and utilities
│   └── auth/                # Authentication logic
├── data/                    # Stock data storage
├── tests/                   # Test suite
├── docker-compose.yml       # Development environment
├── Dockerfile              # Container definition
└── README.md               # This file
```

## 🚦 Quick Start

### Prerequisites

- Python 3.12+
- UV (recommended) or pip
- Docker and Docker Compose (optional)
- PostgreSQL (if running locally)
- Redis (if running locally)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd kalpi-tech-api

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
```

### 2. Using UV (Recommended)

```bash
# Install dependencies
uv sync

# Run the application
uv run uvicorn app.main:app --reload
```

### 3. Using Docker Compose (Easiest)

```bash
# Start all services
docker-compose up --build

# Run in background
docker-compose up -d --build
```

### 4. Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis
# (Configure connection strings in .env)

# Run the application
uvicorn app.main:app --reload
```

## 📚 API Documentation

Once running, visit:
- **Interactive docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

## 🔐 Authentication

### JWT Authentication

1. Register a user:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

2. Login to get token:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

3. Use token in requests:
```bash
curl -X GET "http://localhost:8000/api/v1/indicators/sma?symbol=AAPL&window=20" \
  -H "Authorization: Bearer <your-token>"
```

### API Key Authentication

1. Create API key (requires JWT token):
```bash
curl -X POST "http://localhost:8000/api/v1/auth/api-key" \
  -H "Authorization: Bearer <your-token>"
```

2. Use API key in requests:
```bash
curl -X GET "http://localhost:8000/api/v1/indicators/sma?symbol=AAPL&window=20&api_key=<your-api-key>"
```

## 📈 Usage Examples

### Simple Moving Average (SMA)
```bash
curl -X GET "http://localhost:8000/api/v1/indicators/sma?symbol=AAPL&window=20&start_date=2023-01-01&end_date=2023-12-31" \
  -H "Authorization: Bearer <token>"
```

### Exponential Moving Average (EMA)
```bash
curl -X GET "http://localhost:8000/api/v1/indicators/ema?symbol=AAPL&window=20" \
  -H "Authorization: Bearer <token>"
```

### RSI (Pro tier required)
```bash
curl -X GET "http://localhost:8000/api/v1/indicators/rsi?symbol=AAPL&period=14" \
  -H "Authorization: Bearer <token>"
```

### MACD (Pro tier required)
```bash
curl -X GET "http://localhost:8000/api/v1/indicators/macd?symbol=AAPL&fast_period=12&slow_period=26&signal_period=9" \
  -H "Authorization: Bearer <token>"
```

### Bollinger Bands (Premium tier required)
```bash
curl -X GET "http://localhost:8000/api/v1/indicators/bollinger_bands?symbol=AAPL&period=20&std_dev=2.0" \
  -H "Authorization: Bearer <token>"
```

## 🧪 Testing

Run the test suite:

```bash
# Using UV
uv run pytest

# Using pip
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## 🔧 Configuration

Key environment variables:

```env
# Security
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql://user:password@localhost/kalpi_db

# Redis
REDIS_URL=redis://localhost:6379
CACHE_EXPIRE_MINUTES=30

# Data
DATA_FILE_PATH=data/stocks_ohlc_data.parquet

# Rate Limiting
RATE_LIMIT_FREE=50
RATE_LIMIT_PRO=500
RATE_LIMIT_PREMIUM=

# Data Access (days)
DATA_LIMIT_FREE=90
DATA_LIMIT_PRO=365
DATA_LIMIT_PREMIUM=

# Debug
DEBUG=false
```

## 📦 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.yml up -d

# Scale the API service
docker-compose up -d --scale api=3
```

### Production Considerations

1. **Security**:
   - Change `SECRET_KEY` in production
   - Use environment variables for secrets
   - Enable HTTPS
   - Configure CORS properly

2. **Database**:
   - Use managed PostgreSQL service
   - Configure connection pooling
   - Set up database backups

3. **Caching**:
   - Use managed Redis service
   - Configure Redis persistence
   - Set up Redis clustering for high availability

4. **Monitoring**:
   - Add health checks
   - Set up logging aggregation
   - Configure metrics collection

## 🚨 Troubleshooting

### Common Issues

1. **Database connection failed**:
   - Check PostgreSQL is running
   - Verify connection string in `.env`
   - Check database exists

2. **Redis connection failed**:
   - Check Redis is running
   - Verify Redis URL in `.env`
   - Check Redis is accepting connections

3. **Data file not found**:
   - Ensure `stocks_ohlc_data.parquet` exists in `data/` directory
   - Check file permissions
   - Verify file path in configuration

4. **Rate limiting not working**:
   - Check Redis connection
   - Verify user authentication
   - Check rate limit configuration

### Debug Mode

Enable debug mode for detailed logging:

```env
DEBUG=true
```

## 📄 API Reference

### Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/api-key` - Create API key
- `GET /api/v1/auth/api-keys` - List API keys

#### Technical Indicators
- `GET /api/v1/indicators/sma` - Simple Moving Average
- `GET /api/v1/indicators/ema` - Exponential Moving Average
- `GET /api/v1/indicators/rsi` - Relative Strength Index (Pro+)
- `GET /api/v1/indicators/macd` - MACD (Pro+)
- `GET /api/v1/indicators/bollinger_bands` - Bollinger Bands (Premium)

#### System
- `GET /health` - Health check
- `GET /data-info` - Data information
- `GET /` - API information

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## 📜 License

This project is licensed under the MIT License.