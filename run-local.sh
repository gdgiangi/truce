#!/bin/bash

# Local development setup script for Truce
# Use this if Docker is not available
# Usage: ./run-local.sh [demo]

DEMO_MODE=false
if [ "$1" = "demo" ]; then
    DEMO_MODE=true
    echo "🚀 Starting Truce demo with simulated votes..."
else
    echo "🚀 Starting Truce local development setup..."
fi

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

if [ "$DEMO_MODE" = true ]; then
    echo ""
    echo "🎬 Starting demo mode with automatic seeding..."
    
    # Start API server in background
    cd apps/adjudicator
    echo "🔧 Starting API server..."
    python3 -m truce_adjudicator.main &
    SERVER_PID=$!
    
    # Wait for server to start
    echo "⏳ Waiting for server to be ready..."
    sleep 3
    
    # Test if server is running
    if ! curl -s http://localhost:8000/ > /dev/null; then
        echo "❌ Server failed to start"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    
    echo "✅ Server is running"
    
    # Run seed script
    echo "🌱 Seeding demo data with simulated votes..."
    python3 truce_adjudicator/scripts/seed.py
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 Demo ready! You can now:"
        echo ""
        echo "📊 View consensus clusters:"
        echo "  curl -s 'http://localhost:8000/consensus/canada-crime/summary' | jq ."
        echo ""
        echo "🌐 API endpoints:"
        echo "  API Docs: http://localhost:8000/docs"
        echo "  Consensus: http://localhost:8000/consensus/canada-crime/summary"
        echo "  Claim: http://localhost:8000/claims/violent-crime-in-canada-is-rising"
        echo ""
        echo "💡 To start web frontend in another terminal:"
        echo "  cd apps/web && npm run dev"
        echo "  Then visit: http://localhost:3000"
        echo ""
        echo "Server PID: $SERVER_PID (kill $SERVER_PID to stop)"
        echo "Press Ctrl+C to stop the demo"
        
        # Keep script running
        wait $SERVER_PID
    else
        echo "❌ Demo seeding failed"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    
else
    echo ""
    echo "To start the services manually:"
    echo "  Terminal 1: cd apps/adjudicator && python3 -m truce_adjudicator.main"
    echo "  Terminal 2: cd apps/web && npm run dev"
    echo ""
    echo "Then run: cd apps/adjudicator && python3 truce_adjudicator/scripts/seed.py"
    echo ""
    echo "💡 For quick demo with clustering: ./run-local.sh demo"
fi

echo ""
echo "URLs:"
echo "  Web UI: http://localhost:3000"
echo "  API: http://localhost:8000"
echo "  Claim Card: http://localhost:3000/claim/violent-crime-in-canada-is-rising"
echo "  Consensus Board: http://localhost:3000/consensus/canada-crime"
