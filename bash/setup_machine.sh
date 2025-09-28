#!/bin/bash

# Comprehensive machine setup script for Pynance trading system
# This script sets up the entire machine for running the trading system

set -e  # Exit on any error

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get the project root directory
PROJECT_ROOT="$(get_project_root_direct)"

print_header "PYNANCE MACHINE SETUP"
print_status "Setting up machine for Pynance trading system..."
print_status "Project root: $PROJECT_ROOT"

# Note: check_root() and check_system_requirements() are now in common.sh

# Function to setup conda environment
setup_conda_environment() {
    print_header "SETTING UP CONDA ENVIRONMENT"
    
    # Run the conda environment check script
    if [ -f "$PROJECT_ROOT/bash/setup/check_conda_environment.sh" ]; then
        print_status "Running conda environment setup..."
        bash "$PROJECT_ROOT/bash/setup/check_conda_environment.sh"
        print_success "Conda environment setup completed"
    else
        print_error "check_conda_environment.sh not found"
        exit 1
    fi
}

# Function to setup logging directories
setup_logging() {
    print_header "SETTING UP LOGGING DIRECTORIES"
    
    # Run the logging setup script
    if [ -f "$PROJECT_ROOT/bash/setup/setup_logging.sh" ]; then
        print_status "Setting up logging directories..."
        bash "$PROJECT_ROOT/bash/setup/setup_logging.sh"
        print_success "Logging setup completed"
    else
        print_error "setup_logging.sh not found"
        exit 1
    fi
}

# Function to setup cron jobs
setup_cron_jobs() {
    print_header "SETTING UP CRON JOBS"
    
    # Run the cron job setup script
    if [ -f "$PROJECT_ROOT/bash/setup_cron_jobs.sh" ]; then
        print_status "Setting up cron jobs..."
        bash "$PROJECT_ROOT/bash/setup_cron_jobs.sh"
        print_success "Cron job setup completed"
    else
        print_error "setup_cron_jobs.sh not found"
        exit 1
    fi
}

# Function to setup UI serving
setup_ui_serving() {
    print_header "SETTING UP UI SERVING"
    
    # Check if UI directory exists
    if [ ! -d "$PROJECT_ROOT/ui" ]; then
        print_error "UI directory not found: $PROJECT_ROOT/ui"
        return 1
    fi
    
    # Check if index.html exists
    if [ ! -f "$PROJECT_ROOT/ui/index.html" ]; then
        print_error "index.html not found in UI directory"
        return 1
    fi
    
    print_success "UI directory found"
    
    # Check if we're in WSL
    if grep -q Microsoft /proc/version 2>/dev/null; then
        print_status "WSL detected - configuring networking for Windows host access"
        
        # Run WSL networking configuration
        if [ -f "$PROJECT_ROOT/bash/network/configure_wsl_networking.sh" ]; then
            print_status "Configuring WSL networking..."
            bash "$PROJECT_ROOT/bash/network/configure_wsl_networking.sh" 8080
            print_success "WSL networking configuration completed"
        else
            print_warning "configure_wsl_networking.sh not found"
        fi
    else
        print_status "Not in WSL - standard networking configuration"
    fi
    
    # Make UI serving scripts executable
    if [ -f "$PROJECT_ROOT/bash/serve_ui.sh" ]; then
        chmod +x "$PROJECT_ROOT/bash/serve_ui.sh"
        print_success "UI serving script is executable"
    else
        print_error "serve_ui.sh not found"
        return 1
    fi
    
    if [ -f "$PROJECT_ROOT/bash/ui/start_ui_service.sh" ]; then
        chmod +x "$PROJECT_ROOT/bash/ui/start_ui_service.sh"
        print_success "UI service management script is executable"
    else
        print_error "start_ui_service.sh not found"
        return 1
    fi
    
    if [ -f "$PROJECT_ROOT/bash/ui/manage_ui_server.sh" ]; then
        chmod +x "$PROJECT_ROOT/bash/ui/manage_ui_server.sh"
        print_success "UI server management script is executable"
    else
        print_error "manage_ui_server.sh not found"
        return 1
    fi
    
    print_success "UI serving setup completed"
}

# Function to start UI server as background process
start_ui_server() {
    print_header "STARTING UI SERVER"
    
    # Check if UI server is already running
    if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "UI server is already running on port 8080"
        print_status "Stopping existing server..."
        pkill -f "http.server.*8080" 2>/dev/null || true
        sleep 2
    fi
    
    # Create logs directory if it doesn't exist
    local logs_dir="$(dirname "$PROJECT_ROOT")/logs"
    if [ ! -d "$logs_dir" ]; then
        print_status "Creating logs directory: $logs_dir"
        mkdir -p "$logs_dir"
    fi
    
    # Create UI log file
    local ui_log_file="$logs_dir/ui_server.log"
    print_status "UI server logs will be written to: $ui_log_file"
    
    # Start the UI server in background
    print_status "Starting UI server on port 8080..."
    cd "$PROJECT_ROOT/ui"
    
    # Start server with proper logging
    nohup python3 -m http.server 8080 --bind 0.0.0.0 > "$ui_log_file" 2>&1 &
    local server_pid=$!
    
    # Save PID to file for later management
    echo "$server_pid" > "/tmp/pynance_ui_server.pid"
    
    # Wait a moment to check if server started successfully
    sleep 3
    
    # Check if server is running
    if ps -p "$server_pid" > /dev/null 2>&1; then
        print_success "UI server started successfully (PID: $server_pid)"
        print_status "Server logs: $ui_log_file"
        
        # Get WSL IP for Windows access
        if grep -q Microsoft /proc/version 2>/dev/null; then
            local wsl_ip=$(hostname -I | awk '{print $1}')
            print_status "Access URLs:"
            print_status "  From WSL: http://localhost:8080"
            print_status "  From Windows: http://$wsl_ip:8080"
        else
            print_status "Access URL: http://localhost:8080"
        fi
        
        # Test the server
        print_status "Testing UI server..."
        if command -v curl >/dev/null 2>&1; then
            if curl -s http://localhost:8080 > /dev/null 2>&1; then
                print_success "UI server is responding correctly"
            else
                print_warning "UI server may not be responding - check logs: $ui_log_file"
            fi
        else
            print_warning "curl not available - cannot test server automatically"
            print_status "Test manually: http://localhost:8080"
        fi
        
    else
        print_error "Failed to start UI server"
        print_status "Check logs for errors: $ui_log_file"
        return 1
    fi
}

# Function to verify configuration
verify_configuration() {
    print_header "VERIFYING CONFIGURATION"
    
    # Check if config directory exists
    local config_dir="$(dirname "$PROJECT_ROOT")/config"
    if [ -d "$config_dir" ]; then
        print_success "Config directory exists: $config_dir"
        
    # Check for alpaca config
    if [ -f "$config_dir/alpaca-config.ini" ]; then
        print_success "Alpaca config file found"
    else
        print_warning "Alpaca config file not found. You'll need to create it manually."
        print_status "Template location: $config_dir/alpaca-config.ini"
    fi
    
    # Check for finnhub config
    if [ -f "$config_dir/finnhub-config.ini" ]; then
        print_success "Finnhub config file found"
    else
        print_warning "Finnhub config file not found. You'll need to create it manually."
        print_status "Template location: $config_dir/finnhub-config.ini"
    fi
    else
        print_warning "Config directory not found. Creating template..."
        mkdir -p "$config_dir"
        cat > "$config_dir/alpaca-config.ini" << EOF
[paper]
API_KEY = your_api_key_here
API_SECRET = your_api_secret_here

[live]
API_KEY = your_live_api_key_here
API_SECRET = your_live_api_secret_here
EOF
        
        cat > "$config_dir/finnhub-config.ini" << EOF
[finnhub]
API_KEY = your_finnhub_api_key_here
EOF
        print_success "Config directory and templates created"
    fi
    
    # Check if scripts are executable
    local scripts=("run_alpaca_trend.sh" "run_risk_manager.sh" "setup_cron_jobs.sh")
    for script in "${scripts[@]}"; do
        if [ -x "$PROJECT_ROOT/bash/$script" ]; then
            print_success "$script is executable"
        else
            print_warning "$script is not executable. Fixing..."
            chmod +x "$PROJECT_ROOT/bash/$script"
            print_success "$script is now executable"
        fi
    done
}

# Function to test the setup
test_setup() {
    print_header "TESTING SETUP"
    
    print_status "Testing script execution (dry run)..."
    
    # Test if we can run the scripts (they might fail due to missing config, but that's expected)
    if bash -n "$PROJECT_ROOT/bash/run_alpaca_trend.sh" 2>/dev/null; then
        print_success "trendTrader script syntax is valid"
    else
        print_warning "trendTrader script has syntax issues"
    fi
    
    if bash -n "$PROJECT_ROOT/bash/run_risk_manager.sh" 2>/dev/null; then
        print_success "RiskManager script syntax is valid"
    else
        print_warning "RiskManager script has syntax issues"
    fi
    
    # Check if log directories exist
    local logs_dir="$(dirname "$PROJECT_ROOT")/logs"
    if [ -d "$logs_dir" ]; then
        print_success "Logs directory exists: $logs_dir"
        
        # Check for expected subdirectories
        if [ -d "$logs_dir/01_alpaca/trendTrader" ]; then
            print_success "trendTrader log directory exists"
        else
            print_warning "trendTrader log directory missing"
        fi
        
        if [ -d "$logs_dir/01_alpaca/RiskManager" ]; then
            print_success "RiskManager log directory exists"
        else
            print_warning "RiskManager log directory missing"
        fi
    else
        print_warning "Logs directory not found"
    fi
}

# Note: show_next_steps() is now in common.sh as show_setup_next_steps()

# Main execution
main() {
    print_header "PYNANCE MACHINE SETUP STARTING"
    
    # Check if running as root
    check_root
    
    # Check system requirements
    check_system_requirements
    
    # Setup conda environment
    setup_conda_environment
    
    # Setup logging
    setup_logging
    
    # Setup cron jobs
    setup_cron_jobs
    
    # Setup UI serving
    setup_ui_serving
    
    # Start UI server
    start_ui_server
    
    # Verify configuration
    verify_configuration
    
    # Test setup
    test_setup
    
    # Show next steps
    show_setup_next_steps "$PROJECT_ROOT"
    
    print_success "Machine setup completed successfully!"
    print_status "Your Pynance trading system is ready to use!"
}

# Run main function
main "$@"
