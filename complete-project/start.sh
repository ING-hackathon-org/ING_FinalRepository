#!/bin/bash

# =============================================================================
# ING ESG Platform - Start/Stop Script
# =============================================================================
# This script starts both the backend (FastAPI) and frontend (Vite) servers.
# Press Ctrl+C to gracefully terminate both servers.
# =============================================================================

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# PID storage
BACKEND_PID=""
FRONTEND_PID=""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_header() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          ING ESG Risk Assessment Platform                     ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# CLEANUP FUNCTION (Called on exit)
# =============================================================================

cleanup() {
    echo ""
    print_warning "Shutting down services..."

    # Kill backend server
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        print_status "Stopping backend server (PID: $BACKEND_PID)..."
        kill -TERM "$BACKEND_PID" 2>/dev/null
        wait "$BACKEND_PID" 2>/dev/null
        print_success "Backend server stopped."
    fi

    # Kill frontend server
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        print_status "Stopping frontend server (PID: $FRONTEND_PID)..."
        kill -TERM "$FRONTEND_PID" 2>/dev/null
        wait "$FRONTEND_PID" 2>/dev/null
        print_success "Frontend server stopped."
    fi

    # Kill any remaining npm/node processes for this project
    pkill -f "vite.*$FRONTEND_DIR" 2>/dev/null
    pkill -f "uvicorn.*server:app" 2>/dev/null

    echo ""
    print_success "All services have been gracefully terminated."
    echo ""
    exit 0
}

# Register cleanup function for various signals
trap cleanup SIGINT SIGTERM EXIT

# =============================================================================
# VALIDATION
# =============================================================================

validate_environment() {
    print_status "Validating environment..."

    # Check if backend directory exists
    if [ ! -d "$BACKEND_DIR" ]; then
        print_error "Backend directory not found: $BACKEND_DIR"
        exit 1
    fi

    # Check if frontend directory exists
    if [ ! -d "$FRONTEND_DIR" ]; then
        print_error "Frontend directory not found: $FRONTEND_DIR"
        exit 1
    fi

    # Check if server.py exists
    if [ ! -f "$BACKEND_DIR/server.py" ]; then
        print_error "Backend server.py not found: $BACKEND_DIR/server.py"
        exit 1
    fi

    # Check if package.json exists
    if [ ! -f "$FRONTEND_DIR/package.json" ]; then
        print_error "Frontend package.json not found: $FRONTEND_DIR/package.json"
        exit 1
    fi

    # Check for Python
    if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        print_error "Python is not installed or not in PATH"
        exit 1
    fi

    # Check for npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed or not in PATH"
        exit 1
    fi

    # Load .env file if it exists
    if [ -f "$BACKEND_DIR/.env" ]; then
        print_status "Loading environment variables from .env..."
        export $(grep -v '^#' "$BACKEND_DIR/.env" | xargs)
    fi

    # Warn if OPENAI_API_KEY is not set
    if [ -z "$OPENAI_API_KEY" ]; then
        print_warning "OPENAI_API_KEY is not set. PDF processing will not work."
    fi

    print_success "Environment validation complete."
}

# =============================================================================
# START SERVICES
# =============================================================================

start_backend() {
    print_status "Starting backend server..."
    
    cd "$BACKEND_DIR" || exit 1
    
    # Use python3 if available, otherwise python
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi
    
    # Start the FastAPI server in the background
    $PYTHON_CMD server.py &
    BACKEND_PID=$!
    
    # Wait a bit for the server to start
    sleep 2
    
    # Check if backend is running
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        print_success "Backend server started (PID: $BACKEND_PID)"
        print_status "Backend API: http://localhost:8000"
        print_status "API Docs: http://localhost:8000/docs"
    else
        print_error "Failed to start backend server"
        exit 1
    fi
    
    cd - > /dev/null || exit 1
}

start_frontend() {
    print_status "Starting frontend server..."
    
    cd "$FRONTEND_DIR" || exit 1
    
    # Clear all caches to ensure fresh start
    print_status "Clearing frontend caches..."
    rm -rf node_modules/.vite 2>/dev/null
    rm -rf node_modules/.cache 2>/dev/null
    rm -rf dist 2>/dev/null
    rm -rf .vite 2>/dev/null
    
    # Check if node_modules exists, if not run npm install
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        npm install
    fi
    
    # Start Vite dev server in the background with force flag
    npm run dev -- --force &
    FRONTEND_PID=$!
    
    # Wait a bit for the server to start
    sleep 3
    
    # Check if frontend is running
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        print_success "Frontend server started (PID: $FRONTEND_PID)"
        print_status "Frontend: http://localhost:3000"
    else
        print_error "Failed to start frontend server"
        cleanup
        exit 1
    fi
    
    cd - > /dev/null || exit 1
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    print_header
    
    validate_environment
    
    echo ""
    print_status "Starting ING ESG Platform..."
    echo ""
    
    start_backend
    echo ""
    start_frontend
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  🚀 Platform is running!                                      ║${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}║  Frontend:  http://localhost:3000                             ║${NC}"
    echo -e "${GREEN}║  Backend:   http://localhost:8000                             ║${NC}"
    echo -e "${GREEN}║  API Docs:  http://localhost:8000/docs                        ║${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}║  Press Ctrl+C to stop all services                            ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Keep the script running and wait for both processes
    # This allows the cleanup function to be triggered on Ctrl+C
    while true; do
        # Check if processes are still running
        if [ -n "$BACKEND_PID" ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
            print_error "Backend server stopped unexpectedly!"
        fi
        
        if [ -n "$FRONTEND_PID" ] && ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
            print_error "Frontend server stopped unexpectedly!"
        fi
        
        sleep 5
    done
}

# Run main function
main "$@"
