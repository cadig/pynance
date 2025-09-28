#!/bin/bash

# Script to manage the UI server started by setup_machine.sh
# This script provides easy management of the background UI server

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(dirname "$SCRIPT_DIR")/common.sh"

# Get project root
PROJECT_ROOT="$(get_project_root_direct)"
LOGS_DIR="$(dirname "$PROJECT_ROOT")/logs"
UI_LOG_FILE="$LOGS_DIR/ui_server.log"
PID_FILE="/tmp/pynance_ui_server.pid"

# Function to check if UI server is running
is_server_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    
    # Fallback: check for any http.server process on port 8080
    if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Function to get server PID
get_server_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        lsof -Pi :8080 -sTCP:LISTEN -t 2>/dev/null | head -1
    fi
}

# Function to start the server
start_server() {
    if is_server_running; then
        print_warning "UI server is already running"
        return 0
    fi
    
    print_status "Starting UI server..."
    
    # Create logs directory if it doesn't exist
    if [ ! -d "$LOGS_DIR" ]; then
        mkdir -p "$LOGS_DIR"
    fi
    
    # Start server
    cd "$PROJECT_ROOT/ui"
    nohup python3 -m http.server 8080 --bind 0.0.0.0 > "$UI_LOG_FILE" 2>&1 &
    local server_pid=$!
    
    # Save PID
    echo "$server_pid" > "$PID_FILE"
    
    # Wait and check
    sleep 2
    if ps -p "$server_pid" > /dev/null 2>&1; then
        print_success "UI server started (PID: $server_pid)"
        print_status "Logs: $UI_LOG_FILE"
    else
        print_error "Failed to start UI server"
        return 1
    fi
}

# Function to stop the server
stop_server() {
    if ! is_server_running; then
        print_warning "UI server is not running"
        return 0
    fi
    
    local pid=$(get_server_pid)
    print_status "Stopping UI server (PID: $pid)..."
    
    kill "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
    
    # Wait for process to stop
    sleep 2
    
    if is_server_running; then
        print_warning "Server didn't stop gracefully, forcing..."
        pkill -f "http.server.*8080" 2>/dev/null || true
        sleep 1
    fi
    
    print_success "UI server stopped"
}

# Function to restart the server
restart_server() {
    print_status "Restarting UI server..."
    stop_server
    sleep 1
    start_server
}

# Function to show server status
show_status() {
    if is_server_running; then
        local pid=$(get_server_pid)
        print_success "UI server is running (PID: $pid)"
        
        # Show access URLs
        if grep -q Microsoft /proc/version 2>/dev/null; then
            local wsl_ip=$(hostname -I | awk '{print $1}')
            print_status "Access URLs:"
            print_status "  From WSL: http://localhost:8080"
            print_status "  From Windows: http://$wsl_ip:8080"
        else
            print_status "Access URL: http://localhost:8080"
        fi
        
        # Show recent logs
        if [ -f "$UI_LOG_FILE" ]; then
            print_status "Recent log entries:"
            tail -5 "$UI_LOG_FILE" | sed 's/^/  /'
        fi
    else
        print_warning "UI server is not running"
    fi
}

# Function to show logs
show_logs() {
    if [ -f "$UI_LOG_FILE" ]; then
        print_status "UI server logs:"
        cat "$UI_LOG_FILE"
    else
        print_warning "No log file found: $UI_LOG_FILE"
    fi
}

# Function to follow logs
follow_logs() {
    if [ -f "$UI_LOG_FILE" ]; then
        print_status "Following UI server logs (Ctrl+C to stop):"
        tail -f "$UI_LOG_FILE"
    else
        print_warning "No log file found: $UI_LOG_FILE"
    fi
}

# Function to test server
test_server() {
    print_status "Testing UI server..."
    
    if curl -s http://localhost:8080 > /dev/null 2>&1; then
        print_success "UI server is responding correctly"
    else
        print_error "UI server is not responding"
        print_status "Check logs: $UI_LOG_FILE"
    fi
}

# Main script logic
case "${1:-status}" in
    "start")
        start_server
        ;;
    "stop")
        stop_server
        ;;
    "restart")
        restart_server
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "follow"|"tail")
        follow_logs
        ;;
    "test")
        test_server
        ;;
    "help"|"-h"|"--help")
        echo "Pynance UI Server Manager"
        echo
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  start     Start the UI server"
        echo "  stop      Stop the UI server"
        echo "  restart   Restart the UI server"
        echo "  status    Show server status (default)"
        echo "  logs      Show server logs"
        echo "  follow    Follow server logs in real-time"
        echo "  test      Test server connectivity"
        echo "  help      Show this help message"
        echo
        echo "Examples:"
        echo "  $0 status"
        echo "  $0 logs"
        echo "  $0 follow"
        echo "  $0 test"
        ;;
    *)
        print_error "Unknown command: $1"
        print_status "Use '$0 help' for usage information"
        exit 1
        ;;
esac
