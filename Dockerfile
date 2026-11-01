# =============================================================================
# RecruitFlow – Enterprise Single-Container Production Dockerfile
# Bundles Nginx (Port 10000), Streamlit (Port 8501), and FastAPI (Port 8000)
# managed under Supervisor for seamless single-URL cloud deployment.
# =============================================================================

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    PORT=10000

WORKDIR /app

# Install system dependencies, Nginx reverse proxy, and Supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/supervisor

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Nginx and Supervisor configurations
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy application source code
COPY . .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Single externally exposed port (default 10000, Render injects $PORT)
EXPOSE 10000

# Health check against unified proxy health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:10000/health || exit 1

# Start container via entrypoint
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
