# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional required packages
RUN pip install --no-cache-dir \
    psycopg2-binary \
    PyJWT \
    python-multipart

# Copy application code
COPY app ./app
COPY data ./data
COPY .env.example .env

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the Docker-compatible application
CMD ["python", "-m", "uvicorn", "app.main_docker:app", "--host", "0.0.0.0", "--port", "8000"]
