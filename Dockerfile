FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and requirements first for better caching
COPY pyproject.toml .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Install the package in development mode
RUN pip install -e .

# Copy knowledge base and config
COPY knowledge_base/ ./knowledge_base/
COPY config/ ./config/

# Create necessary directories
RUN mkdir -p /app/logs /app/chroma_db

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the server
CMD ["uvicorn", "server.server.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
