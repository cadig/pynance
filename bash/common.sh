#!/bin/bash

# Common functions and utilities for Pynance scripts
# This file contains shared functions used across multiple scripts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
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

print_header() {
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}================================${NC}"
}

# Get the project root directory
get_project_root() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
    echo "$(dirname "$script_dir")"
}

# Get the project root directory (alternative method for direct calls)
get_project_root_direct() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "$(dirname "$script_dir")"
}

# Source conda environment
source_conda() {
    # Try multiple conda installation locations
    local conda_paths=(
        "$HOME/miniconda3/etc/profile.d/conda.sh"
        "/opt/conda/etc/profile.d/conda.sh"
        "/usr/local/miniconda3/etc/profile.d/conda.sh"
        "/usr/local/anaconda3/etc/profile.d/conda.sh"
        "/opt/miniconda3/etc/profile.d/conda.sh"
        "/opt/anaconda3/etc/profile.d/conda.sh"
    )
    
    for conda_path in "${conda_paths[@]}"; do
        if [ -f "$conda_path" ]; then
            print_status "Sourcing conda from: $conda_path"
            source "$conda_path"
            return 0
        fi
    done
    
    # If conda.sh not found, try to find conda binary and add to PATH
    local conda_bin_paths=(
        "$HOME/miniconda3/bin"
        "/opt/conda/bin"
        "/usr/local/miniconda3/bin"
        "/usr/local/anaconda3/bin"
        "/opt/miniconda3/bin"
        "/opt/anaconda3/bin"
    )
    
    for conda_bin_path in "${conda_bin_paths[@]}"; do
        if [ -f "$conda_bin_path/conda" ]; then
            print_status "Adding conda to PATH: $conda_bin_path"
            export PATH="$conda_bin_path:$PATH"
            return 0
        fi
    done
    
    print_warning "Conda not found in standard locations"
    return 1
}

# Check if conda is available
check_conda() {
    # First try to source conda if it's not in PATH
    if ! command -v conda &> /dev/null; then
        print_status "Conda not found in PATH, attempting to source conda..."
        if source_conda; then
            print_status "Successfully sourced conda"
        else
            print_error "Conda is not installed. Please run check_conda_environment.sh first."
            return 1
        fi
    fi
    
    # Verify conda is now available
    if ! command -v conda &> /dev/null; then
        print_error "Conda is still not available after sourcing. Please check your conda installation."
        return 1
    fi
    
    return 0
}

# Check if pynance-v2.0 environment exists
check_pynance_env() {
    if ! conda env list | grep -q "pynance-v2.0"; then
        print_error "pynance-v2.0 environment not found. Please run setup_environment.sh first."
        return 1
    fi
    return 0
}

# Activate pynance environment
activate_pynance_env() {
    print_status "Activating pynance-v2.0 environment..."
    conda activate pynance-v2.0
}

# Setup logging directory structure
setup_logging_structure() {
    local logs_dir="$1"
    local system_id="$2"
    local script_id="$3"
    
    # Create system directory if it doesn't exist
    local system_dir="$logs_dir/$system_id"
    if [ ! -d "$system_dir" ]; then
        print_status "Creating system log directory: $system_dir" >&2
        mkdir -p "$system_dir"
    fi
    
    # Create script subdirectory if it doesn't exist
    local script_dir="$system_dir/$script_id"
    if [ ! -d "$script_dir" ]; then
        print_status "Creating script log directory: $script_dir" >&2
        mkdir -p "$script_dir"
    fi
    
    # Create year-month directory if it doesn't exist
    local current_year_month=$(date +%Y-%m)
    local year_month_dir="$script_dir/$current_year_month"
    if [ ! -d "$year_month_dir" ]; then
        print_status "Creating log directory: $year_month_dir" >&2
        mkdir -p "$year_month_dir"
    fi
    
    # Create log filename: YYYY-MM-DD-DayOfWeek.log
    local current_date=$(date +%Y-%m-%d)
    local current_day_of_week=$(date +%A)
    local log_filename="${current_date}-${current_day_of_week}.log"
    local log_file="$year_month_dir/$log_filename"
    
    # Create the log file if it doesn't exist
    if [ ! -f "$log_file" ]; then
        print_status "Creating log file: $log_file" >&2
        touch "$log_file"
    fi
    
    # Convert to absolute path
    local log_file_abs="$(realpath "$log_file")"
    
    print_status "Logging output to: $log_file_abs" >&2
    echo "$log_file_abs"
}

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root. This is not recommended for security reasons."
        print_warning "Consider running as a regular user and using sudo when needed."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Setup cancelled by user"
            exit 1
        fi
    fi
}

# Check system requirements
check_system_requirements() {
    print_header "CHECKING SYSTEM REQUIREMENTS"
    
    # Check if we're on a supported OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_success "Linux system detected"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        print_success "macOS system detected"
    else
        print_warning "Unsupported OS: $OSTYPE"
        print_warning "This script is designed for Linux and macOS"
    fi
    
    # Check available disk space
    local project_root=$(get_project_root_direct)
    local available_space=$(df -BG "$project_root" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt 5 ]; then
        print_warning "Low disk space detected: ${available_space}GB available"
        print_warning "Consider freeing up space before proceeding"
    else
        print_success "Sufficient disk space: ${available_space}GB available"
    fi
    
    # Check if git is available
    if command -v git &> /dev/null; then
        print_success "Git is available"
    else
        print_error "Git is not installed. Please install git first."
        exit 1
    fi
}

# Check if we're in the right directory
check_project_directory() {
    local required_file="$1"
    if [ ! -f "$required_file" ]; then
        print_error "$required_file not found. Please run this script from the project root directory."
        exit 1
    fi
}

# Setup config files if they don't exist
setup_config_files() {
    local config_dir="../config"
    local alpaca_config_file="$config_dir/alpaca-config.ini"
    local finnhub_config_file="$config_dir/finnhub-config.ini"
    
    if [ ! -f "$alpaca_config_file" ]; then
        print_warning "alpaca-config.ini not found. Creating template in sibling config directory..."
        mkdir -p "$config_dir"
        cat > "$alpaca_config_file" << EOF
[paper]
API_KEY = your_api_key_here
API_SECRET = your_api_secret_here

[live]
API_KEY = your_live_api_key_here
API_SECRET = your_live_api_secret_here
EOF
        print_warning "Please edit $alpaca_config_file with your actual API credentials."
    fi
    
    if [ ! -f "$finnhub_config_file" ]; then
        print_warning "finnhub-config.ini not found. Creating template in sibling config directory..."
        mkdir -p "$config_dir"
        cat > "$finnhub_config_file" << EOF
[finnhub]
API_KEY = your_finnhub_api_key_here
EOF
        print_warning "Please edit $finnhub_config_file with your actual Finnhub API key."
    fi
    
    if [ ! -f "$alpaca_config_file" ] || [ ! -f "$finnhub_config_file" ]; then
        print_warning "The config directory is located outside the repository for security."
        print_warning "The script will continue but may fail without proper credentials."
    fi
}

# Check if port is available
check_port_available() {
    local port="$1"
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # Port is in use
    else
        return 0  # Port is available
    fi
}

# Find available port
find_available_port() {
    local start_port="$1"
    local end_port="$2"
    
    for ((i=start_port; i<=end_port; i++)); do
        if check_port_available "$i"; then
            echo "$i"
            return 0
        fi
    done
    return 1
}

# Check if we're in WSL
is_wsl() {
    grep -q Microsoft /proc/version 2>/dev/null
}

# Get WSL IP address
get_wsl_ip() {
    hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost"
}

# Get Windows host IP from WSL
get_windows_host_ip() {
    ip route | grep default | awk '{print $3}' 2>/dev/null || echo ""
}

# Test if a URL is accessible
test_url() {
    local url="$1"
    if command -v curl >/dev/null 2>&1; then
        if curl -s "$url" > /dev/null 2>&1; then
            return 0
        else
            return 1
        fi
    else
        print_warning "curl not available - cannot test URL automatically"
        return 2
    fi
}

# Make scripts executable
make_scripts_executable() {
    local project_root="$1"
    local scripts=("run_alpaca_trend.sh" "run_risk_manager.sh" "setup_cron_jobs.sh" "serve_ui.sh")
    
    for script in "${scripts[@]}"; do
        if [ -f "$project_root/bash/$script" ]; then
            chmod +x "$project_root/bash/$script"
            print_success "$script is now executable"
        fi
    done
}

# Validate script syntax
validate_script_syntax() {
    local script_path="$1"
    local script_name="$2"
    
    if bash -n "$script_path" 2>/dev/null; then
        print_success "$script_name script syntax is valid"
        return 0
    else
        print_warning "$script_name script has syntax issues"
        return 1
    fi
}

# Show next steps for setup
show_setup_next_steps() {
    local project_root="$1"
    
    print_header "NEXT STEPS"
    
    echo "Your Pynance trading system is now set up! Here's what to do next:"
    echo
    echo "1. Configure your API credentials:"
    echo "   Edit: $(dirname "$project_root")/config/alpaca-config.ini"
    echo "   Add your Alpaca API key and secret"
    echo "   Edit: $(dirname "$project_root")/config/finnhub-config.ini"
    echo "   Add your Finnhub API key"
    echo
    echo "2. Test the system manually:"
    echo "   cd $project_root"
    echo "   ./bash/run_alpaca_trend.sh"
    echo "   ./bash/run_risk_manager.sh"
    echo
    echo "3. Monitor the logs:"
    echo "   ./bash/view_logs.sh"
    echo "   ./bash/logs/view_risk_manager_logs.sh"
    echo "   ./bash/logs/view_all_logs.sh"
    echo
    echo "4. Check cron jobs:"
    echo "   crontab -l"
    echo
    echo "5. The system will automatically run:"
    echo "   - trendTrader: Daily at adjusted local time (equivalent to 8:55 AM EST)"
    echo "   - RiskManager: Every hour during adjusted local time (equivalent to 9 AM - 4 PM EST)"
    echo "   - Times are automatically adjusted for your system timezone"
    echo
    echo "6. UI server is already running:"
    echo "   - Access from WSL: http://localhost:8080"
    echo "   - Access from Windows: http://[WSL_IP]:8080"
    echo "   - Manage server: ./bash/ui/manage_ui_server.sh [start|stop|restart|status|logs|test]"
    echo "   - View logs: ./bash/ui/manage_ui_server.sh logs"
    echo "   - Follow logs: ./bash/ui/manage_ui_server.sh follow"
    echo
    echo "7. For DST transitions:"
    echo "   - Check DST status: ./bash/check_dst_status.sh"
    echo "   - Re-run setup after DST transitions: ./bash/setup_cron_jobs.sh"
    echo
    echo "8. For troubleshooting:"
    echo "   - Check logs in: $(dirname "$project_root")/logs/"
    echo "   - View cron job logs: grep CRON /var/log/syslog (Linux) or /var/log/system.log (macOS)"
    echo "   - Test UI access: curl http://localhost:8080"
    echo
}
