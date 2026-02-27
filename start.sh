#!/bin/bash
# Quick start script for OWID Dataset Cleaner

echo "🚀 OWID Dataset Cleaner - Quick Start"
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from example..."
    cp .env.example .env
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Starting Flask application..."
echo "   Access the app at: http://localhost:5000"
echo ""
echo "   Press Ctrl+C to stop the server"
echo ""

# Run the application
python app.py
