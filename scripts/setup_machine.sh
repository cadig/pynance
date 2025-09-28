#!/bin/bash

# Comprehensive machine setup script for Pynance trading system
# This script sets up the entire machine for running the trading system

set -e  # Exit on any error

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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_header "PYNANCE MACHINE SETUP"
print_status "Setting up machine for Pynance trading system..."
print_status "Project root: $PROJECT_ROOT"

# Function to check if running as root
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

# Function to check system requirements
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
    local available_space=$(df -BG "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
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

# Function to setup conda environment
setup_conda_environment() {
    print_header "SETTING UP CONDA ENVIRONMENT"
    
    # Run the conda environment check script
    if [ -f "$PROJECT_ROOT/scripts/check_conda_environment.sh" ]; then
        print_status "Running conda environment setup..."
        bash "$PROJECT_ROOT/scripts/check_conda_environment.sh"
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
    if [ -f "$PROJECT_ROOT/scripts/setup_logging.sh" ]; then
        print_status "Setting up logging directories..."
        bash "$PROJECT_ROOT/scripts/setup_logging.sh"
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
    if [ -f "$PROJECT_ROOT/scripts/setup_cron_jobs.sh" ]; then
        print_status "Setting up cron jobs..."
        bash "$PROJECT_ROOT/scripts/setup_cron_jobs.sh"
        print_success "Cron job setup completed"
    else
        print_error "setup_cron_jobs.sh not found"
        exit 1
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
    local scripts=("run_alpaca_trend.sh" "run_risk_manager.sh" "setup_logging.sh" "setup_cron_jobs.sh")
    for script in "${scripts[@]}"; do
        if [ -x "$PROJECT_ROOT/scripts/$script" ]; then
            print_success "$script is executable"
        else
            print_warning "$script is not executable. Fixing..."
            chmod +x "$PROJECT_ROOT/scripts/$script"
            print_success "$script is now executable"
        fi
    done
}

# Function to test the setup
test_setup() {
    print_header "TESTING SETUP"
    
    print_status "Testing script execution (dry run)..."
    
    # Test if we can run the scripts (they might fail due to missing config, but that's expected)
    if bash -n "$PROJECT_ROOT/scripts/run_alpaca_trend.sh" 2>/dev/null; then
        print_success "trendTrader script syntax is valid"
    else
        print_warning "trendTrader script has syntax issues"
    fi
    
    if bash -n "$PROJECT_ROOT/scripts/run_risk_manager.sh" 2>/dev/null; then
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

# Function to show next steps
show_next_steps() {
    print_header "NEXT STEPS"
    
    echo "Your Pynance trading system is now set up! Here's what to do next:"
    echo
    echo "1. Configure your API credentials:"
    echo "   Edit: $(dirname "$PROJECT_ROOT")/config/alpaca-config.ini"
    echo "   Add your Alpaca API key and secret"
    echo "   Edit: $(dirname "$PROJECT_ROOT")/config/finnhub-config.ini"
    echo "   Add your Finnhub API key"
    echo
    echo "2. Test the system manually:"
    echo "   cd $PROJECT_ROOT"
    echo "   ./scripts/run_alpaca_trend.sh"
    echo "   ./scripts/run_risk_manager.sh"
    echo
    echo "3. Monitor the logs:"
    echo "   ./scripts/view_logs.sh"
    echo "   ./scripts/view_risk_manager_logs.sh"
    echo "   ./scripts/view_all_logs.sh"
    echo
    echo "4. Check cron jobs:"
    echo "   crontab -l"
    echo
    echo "5. The system will automatically run:"
    echo "   - trendTrader: Daily at 8:55 AM EST (before market opens)"
    echo "   - RiskManager: Every hour from 9 AM to 4 PM EST (during market hours)"
    echo
    echo "6. For troubleshooting:"
    echo "   - Check logs in: $(dirname "$PROJECT_ROOT")/logs/"
    echo "   - View cron job logs: grep CRON /var/log/syslog (Linux) or /var/log/system.log (macOS)"
    echo
}

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
    
    # Verify configuration
    verify_configuration
    
    # Test setup
    test_setup
    
    # Show next steps
    show_next_steps
    
    print_success "Machine setup completed successfully!"
    print_status "Your Pynance trading system is ready to use!"
}

# Run main function
main "$@"
