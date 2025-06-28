#!/bin/bash
set -e

echo "🚀 Starting USDA MCP Server (Development)"

# Check .env file
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Create from .env.example"
    exit 1
fi

# Load environment
export $(cat .env | grep -v '^#' | xargs)

if [ -z "$FDC_API_KEY" ]; then
    echo "❌ FDC_API_KEY not set in .env"
    exit 1
fi

echo "✅ Environment loaded"
echo "🌐 Starting on http://localhost:8080"
echo "📚 Docs at http://localhost:8080/docs"

python -m uvicorn src.mcp_http_server:app --host 0.0.0.0 --port 8080 --reload
EOF
