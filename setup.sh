#!/bin/bash

# Grade Guardian Phase 1 Setup Script

set -e  # Exit on any error

echo "🚀 Setting up Grade Guardian Phase 1..."
echo "======================================"

# Check for required tools
echo "🔍 Checking dependencies..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.13"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Please install uv: pip install uv"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose"
    exit 1
fi

echo "✅ All dependencies found"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
uv sync

# Create required directories
echo "📁 Creating directories..."
mkdir -p data/config
mkdir -p data/scraped
mkdir -p sql

# Install Node.js dependencies for scraper
echo "📦 Installing Node.js dependencies..."
cd scraper
npm ci
cd ..

# Build Docker images
echo "🐳 Building Docker images..."
docker-compose build

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Configure your DPS and Database credentials:"
echo "   export DPS_USERNAME='your_username'"
echo "   export DPS_PASSWORD='your_password'"
echo "   export POSTGRES_PASSWORD='your_db_password'"
echo ""
echo "2. Start the services:"
echo "   docker-compose up -d postgres flask-api"
echo ""
echo "3. Test the system:"
echo "   uv run grade-guardian health"
echo "   uv run grade-guardian test-scrape --student-name 'Your Student'"
echo ""
echo "4. Check the Flask API:"
echo "   curl http://localhost:5000/health"
echo ""
echo "🎉 Grade Guardian Phase 1 is ready!"