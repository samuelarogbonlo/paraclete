#!/bin/bash
# Development startup script

echo "🚀 Starting Paraclete Backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
fi

# Check if virtual environment exists
if [ ! -d venv ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if PostgreSQL is running (Docker)
if ! docker ps | grep -q paraclete-postgres; then
    echo "🐘 Starting PostgreSQL with Docker..."
    docker-compose up -d postgres redis
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 5
fi

# Run migrations
echo "🗃️  Running database migrations..."
alembic upgrade head

# Start the server
echo "✨ Starting FastAPI server..."
echo "📚 API docs: http://localhost:8000/docs"
echo "❤️  Health check: http://localhost:8000/health"
echo ""
uvicorn app.main:app --reload --port 8000