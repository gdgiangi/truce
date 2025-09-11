#!/bin/bash

# Local development setup script for Truce
# Use this if Docker is not available

echo "🚀 Starting Truce local development setup..."

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 required but not installed"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js required but not installed"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm required but not installed"; exit 1; }

echo "✅ Prerequisites check passed"

# Setup backend
echo "📦 Setting up FastAPI backend..."
cd apps/adjudicator

# Upgrade pip first
echo "🔧 Upgrading pip..."
python3 -m pip install --upgrade pip

# Install build dependencies
python3 -m pip install build setuptools wheel

# Install the package
python3 -m pip install -e . || { 
    echo "⚠️  Editable install failed, trying requirements.txt..."
    python3 -m pip install -r requirements.txt || { echo "❌ Failed to install Python dependencies"; exit 1; }
}
cd ../..

# Setup frontend
echo "🌐 Setting up Next.js frontend..."
cd apps/web
npm install || { echo "❌ Failed to install Node dependencies"; exit 1; }
cd ../..

echo "✅ Installation complete!"
echo ""
echo "To start the services:"
echo "  Terminal 1: cd apps/adjudicator && uvicorn truce_adjudicator.main:app --reload --port 8000"
echo "  Terminal 2: cd apps/web && npm run dev"
echo ""
echo "Then run: cd apps/adjudicator && python -m truce_adjudicator.scripts.seed"
echo ""
echo "URLs:"
echo "  Web UI: http://localhost:3000"
echo "  API: http://localhost:8000"
echo "  Claim Card: http://localhost:3000/claim/violent-crime-canada"
echo "  Consensus Board: http://localhost:3000/consensus/canada-crime"
