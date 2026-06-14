#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

export SOURCES_ENABLED=demo
export LLM_PROVIDER=none
export CHROMA_DB_PATH=./data/chroma_db
export SQL_DB_PATH=./data/content_hub.db

mkdir -p data data/chroma_db

ACTION="${1:-all}"
PYTHON="${PYTHON:-python3}"

run_pipeline() {
    echo "=== Running Pipeline ==="
    $PYTHON -m pipeline run
}

start_api() {
    echo "=== Starting API on port 8000 ==="
    export API_PORT=8000
    nohup $PYTHON -m pipeline api > data/api.log 2>&1 &
    echo "API PID: $!"
    sleep 2
}

start_dashboard() {
    echo "=== Starting Dashboard on port 8501 ==="
    nohup streamlit run pipeline/dashboard/app.py \
        --server.port=8501 \
        --server.headless=true \
        --server.address=0.0.0.0 \
        > data/dashboard.log 2>&1 &
    echo "Dashboard PID: $!"
    sleep 3
}

start_frontend() {
    echo "=== Starting React Frontend on port 3000 ==="
    cd frontend
    npm run dev > ../data/frontend.log 2>&1 &
    echo "Frontend PID: $!"
    cd ..
    sleep 2
}

show_status() {
    echo ""
    echo "========================================"
    echo "  AI Content Hub - Local Deployment"
    echo "========================================"
    echo "  API:        http://localhost:8000"
    echo "  Dashboard:  http://localhost:8501"
    echo "  Frontend:   http://localhost:3000"
    echo "  Health:     http://localhost:8000/health"
    echo "  Stats:      http://localhost:8000/stats"
    echo "========================================"
    echo ""
}

echo "========================================"
echo "  AI Content Hub - Local Deployment"
echo "========================================"

case "$ACTION" in
    pipeline)   run_pipeline ;;
    api)        start_api; show_status ;;
    dashboard)  start_dashboard; show_status ;;
    frontend)   start_frontend; show_status ;;
    all)
        run_pipeline
        start_api
        start_dashboard
        start_frontend
        show_status
        echo "Press Ctrl+C to stop all services"
        wait
        ;;
    *) echo "Usage: ./start.sh [pipeline|api|dashboard|frontend|all]" ;;
esac
