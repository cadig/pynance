#!/bin/bash

# Script to serve the Pynance UI locally
# This script starts a local web server for the trading dashboard

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get the project root directory
PROJECT_ROOT="$(get_project_root_direct)"
UI_DIR="$PROJECT_ROOT/ui"

# Default port
PORT=${1:-8080}

print_header "PYNANCE UI SERVER"

# Check if UI directory exists
if [ ! -d "$UI_DIR" ]; then
    print_error "UI directory not found: $UI_DIR"
    exit 1
fi

# Check if index.html exists
if [ ! -f "$UI_DIR/index.html" ]; then
    print_error "index.html not found in UI directory"
    exit 1
fi

print_status "Starting Pynance UI server..."
print_status "UI directory: $UI_DIR"
print_status "Port: $PORT"

# Check if port is already in use
if ! check_port_available "$PORT"; then
    print_warning "Port $PORT is already in use"
    print_status "Trying to find an available port..."
    
    # Find an available port
    local available_port=$(find_available_port 8080 8090)
    if [ -n "$available_port" ]; then
        PORT=$available_port
        print_success "Found available port: $PORT"
    else
        print_error "No available ports found in range 8080-8090"
        exit 1
    fi
fi

# Get the local IP address for WSL
LOCAL_IP=$(get_wsl_ip)

print_status "UI will be available at:"
print_status "  Local: http://localhost:$PORT"
print_status "  Network: http://$LOCAL_IP:$PORT"
print_status "  Windows Host: http://$LOCAL_IP:$PORT"

# Check if we're in WSL
if is_wsl; then
    print_status "WSL detected - configuring for Windows host access"
    
    # Check if Windows host IP is available
    WINDOWS_HOST_IP=$(get_windows_host_ip)
    if [ -n "$WINDOWS_HOST_IP" ]; then
        print_status "Windows host IP: $WINDOWS_HOST_IP"
        print_status "Windows host access: http://$WINDOWS_HOST_IP:$PORT"
    fi
    
    # Check if Windows firewall might block the port
    print_warning "If you can't access from Windows, you may need to:"
    print_status "1. Allow the port in Windows Firewall"
    print_status "2. Run: netsh advfirewall firewall add rule name=\"WSL Port $PORT\" dir=in action=allow protocol=TCP localport=$PORT"
    print_status "3. Or disable Windows Firewall temporarily for testing"
fi

# Start the server
print_status "Starting HTTP server..."
print_status "Press Ctrl+C to stop the server"
echo

# Change to UI directory and start server
cd "$UI_DIR"

# Start the server with proper binding for WSL
python3 -m http.server $PORT --bind 0.0.0.0

# If python3 -m http.server fails, try python
if [ $? -ne 0 ]; then
    print_warning "python3 -m http.server failed, trying python..."
    python -m http.server $PORT --bind 0.0.0.0
fi
