#!/bin/bash
# UrbanHub - Launch All Services
# This script starts both FastAPI and Streamlit

echo "🏙️ UrbanHub - Starting all services..."

# Check if port 8000 is available
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use. Stop existing server or use different port."
    exit 1
fi

# Check if port 8501 is available
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8501 is already in use. Stop existing Streamlit or use different port."
    exit 1
fi

echo ""
echo "Starting FastAPI server on http://localhost:8000..."
uv run run_api_server.py &
API_PID=$!

# Wait for API to start
sleep 5

echo ""
echo "Starting Streamlit dashboard on http://localhost:8501..."
streamlit run src/visualization/dashboard_streaming.py --server.port 8501 &
STREAMLIT_PID=$!

echo ""
echo "✅ All services started!"
echo "📡 API:       http://localhost:8000"
echo "📚 API Docs:  http://localhost:8000/docs"
echo "📊 Dashboard: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $API_PID $STREAMLIT_PID 2>/dev/null; exit" INT TERM

wait
