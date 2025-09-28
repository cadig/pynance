#!/bin/bash

# Script to start the Pynance UI as a background service
# This script starts the UI server and keeps it running

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Default port
PORT=${1:-8080}

# PID file location
PID_FILE="/tmp/pynance_ui_${PORT}.pid"

# Function to check if service is running
is_service_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to start the service
start_service() {
    if is_service_running; then
        print_warning "UI service is already running on port $PORT"
        return 0
    fi
    
    print_status "Starting Pynance UI service on port $PORT..."
    
    # Start the server in background
    nohup python3 -m http.server $PORT --bind 0.0.0.0 --directory "$(dirname "$0")/../ui" > /tmp/pynance_ui_${PORT}.log 2>&1 &
    local pid=$!
    
    # Save PID
    echo "$pid" > "$PID_FILE"
    
    # Wait a moment to check if it started
    sleep 2
    
    if ps -p "$pid" > /dev/null 2>&1; then
        print_success "UI service started successfully (PID: $pid)"
        print_status "Log file: /tmp/pynance_ui_${PORT}.log"
        print_status "Access: http://localhost:$PORT"
        return 0
    else
        print_error "Failed to start UI service"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to stop the service
stop_service() {
    if ! is_service_running; then
        print_warning "UI service is not running"
        return 0
    fi
    
    local pid=$(cat "$PID_FILE")
    print_status "Stopping UI service (PID: $pid)..."
    
    kill "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
    
    print_success "UI service stopped"
}

# Function to restart the service
restart_service() {
    print_status "Restarting UI service..."
    stop_service
    sleep 1
    start_service
}

# Function to show service status
show_status() {
    if is_service_running; then
        local pid=$(cat "$PID_FILE")
        print_success "UI service is running (PID: $pid)"
        print_status "Port: $PORT"
        print_status "Access: http://localhost:$PORT"
        
        # Show log tail
        if [ -f "/tmp/pynance_ui_${PORT}.log" ]; then
            print_status "Recent log entries:"
            tail -5 "/tmp/pynance_ui_${PORT}.log" | sed 's/^/  /'
        fi
    else
        print_warning "UI service is not running"
    fi
}

# Function to show logs
show_logs() {
    if [ -f "/tmp/pynance_ui_${PORT}.log" ]; then
        print_status "UI service logs:"
        cat "/tmp/pynance_ui_${PORT}.log"
    else
        print_warning "No log file found"
    fi
}

# Main script logic
case "${1:-start}" in
    "start")
        start_service
        ;;
    "stop")
        stop_service
        ;;
    "restart")
        restart_service
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "help"|"-h"|"--help")
        echo "Pynance UI Service Manager"
        echo
        echo "Usage: $0 [command] [port]"
        echo
        echo "Commands:"
        echo "  start     Start the UI service (default)"
        echo "  stop      Stop the UI service"
        echo "  restart   Restart the UI service"
        echo "  status    Show service status"
        echo "  logs      Show service logs"
        echo "  help      Show this help message"
        echo
        echo "Examples:"
        echo "  $0 start 8080"
        echo "  $0 status"
        echo "  $0 logs"
        ;;
    *)
        print_error "Unknown command: $1"
        print_status "Use '$0 help' for usage information"
        exit 1
        ;;
esac
