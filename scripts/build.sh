#!/bin/bash
# Build script for PII Anonymizer
# Builds frontend and prepares for deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Building PII Anonymizer..."

# Build frontend
echo "Building frontend..."
cd "$PROJECT_ROOT/frontend"
npm install
npm run build

echo "Frontend built to $PROJECT_ROOT/static"

# Verify build output
if [ -f "$PROJECT_ROOT/static/index.html" ]; then
    echo "Build successful!"
    echo "Files in static directory:"
    ls -la "$PROJECT_ROOT/static"
else
    echo "ERROR: Build failed - index.html not found"
    exit 1
fi

echo ""
echo "To run the application:"
echo "  cd $PROJECT_ROOT"
echo "  source .venv/bin/activate"
echo "  uvicorn backend.src.api.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "Then open http://localhost:8000 in your browser"
