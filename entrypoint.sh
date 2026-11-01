#!/bin/bash
set -e

# Port configuration (default to 10000 if not specified by cloud provider)
export PORT=${PORT:-10000}
echo "Starting RecruitFlow Single-Container Production Stack on Port $PORT..."

# Substitute $PORT into Nginx configuration
sed -i "s/listen 10000;/listen $PORT;/g" /etc/nginx/nginx.conf

# Initialize database schema if database credentials are provided
if [ -n "$DB_HOST" ]; then
    echo "Waiting for database and ensuring tables exist..."
    python create_tables.py || echo "Warning: Table initialization skipped or database already initialized."
fi

# Execute Supervisor to manage Uvicorn, Streamlit, and Nginx
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf

