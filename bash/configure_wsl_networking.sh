#!/bin/bash

# Script to configure WSL networking for Windows host access
# This script helps set up port forwarding and firewall rules for WSL

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

# Default port
PORT=${1:-8080}

print_header "WSL NETWORKING CONFIGURATION"

# Check if we're in WSL
if ! grep -q Microsoft /proc/version 2>/dev/null; then
    print_error "This script is designed for WSL (Windows Subsystem for Linux)"
    print_status "If you're not using WSL, you can skip this configuration"
    exit 1
fi

print_success "WSL detected - configuring networking for Windows host access"

# Get WSL IP address
WSL_IP=$(hostname -I | awk '{print $1}')
print_status "WSL IP address: $WSL_IP"

# Get Windows host IP
WINDOWS_HOST_IP=$(ip route | grep default | awk '{print $3}')
print_status "Windows host IP: $WINDOWS_HOST_IP"

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Port $PORT is already in use"
    print_status "You may need to stop the current service or use a different port"
fi

print_status "Configuring networking for port $PORT..."

# Create Windows batch script for firewall configuration
WINDOWS_SCRIPT="/tmp/configure_windows_firewall.bat"
cat > "$WINDOWS_SCRIPT" << EOF
@echo off
echo Configuring Windows Firewall for WSL port $PORT...

REM Add firewall rule for the port
netsh advfirewall firewall add rule name="WSL Port $PORT" dir=in action=allow protocol=TCP localport=$PORT

REM Add firewall rule for WSL subnet
netsh advfirewall firewall add rule name="WSL Subnet" dir=in action=allow protocol=TCP localport=$PORT remoteip=$WSL_IP

echo Firewall rules added for port $PORT
echo You can now access the UI from Windows at: http://$WSL_IP:$PORT
echo.
echo To remove these rules later, run:
echo netsh advfirewall firewall delete rule name="WSL Port $PORT"
echo netsh advfirewall firewall delete rule name="WSL Subnet"
pause
EOF

print_success "Windows batch script created: $WINDOWS_SCRIPT"
print_status "To configure Windows Firewall, run this script in Windows Command Prompt:"
print_status "  cmd.exe /c $WINDOWS_SCRIPT"

# Alternative: PowerShell script
POWERSHELL_SCRIPT="/tmp/configure_windows_firewall.ps1"
cat > "$POWERSHELL_SCRIPT" << EOF
# PowerShell script to configure Windows Firewall for WSL
Write-Host "Configuring Windows Firewall for WSL port $PORT..." -ForegroundColor Green

# Add firewall rule for the port
New-NetFirewallRule -DisplayName "WSL Port $PORT" -Direction Inbound -Protocol TCP -LocalPort $PORT -Action Allow

# Add firewall rule for WSL subnet
New-NetFirewallRule -DisplayName "WSL Subnet" -Direction Inbound -Protocol TCP -LocalPort $PORT -RemoteAddress $WSL_IP -Action Allow

Write-Host "Firewall rules added for port $PORT" -ForegroundColor Green
Write-Host "You can now access the UI from Windows at: http://$WSL_IP:$PORT" -ForegroundColor Yellow
Write-Host ""
Write-Host "To remove these rules later, run:" -ForegroundColor Cyan
Write-Host "Remove-NetFirewallRule -DisplayName 'WSL Port $PORT'"
Write-Host "Remove-NetFirewallRule -DisplayName 'WSL Subnet'"
EOF

print_success "PowerShell script created: $POWERSHELL_SCRIPT"
print_status "To configure Windows Firewall with PowerShell, run:"
print_status "  powershell.exe -ExecutionPolicy Bypass -File $POWERSHELL_SCRIPT"

# Create a simple test script
TEST_SCRIPT="/tmp/test_wsl_networking.sh"
cat > "$TEST_SCRIPT" << EOF
#!/bin/bash
echo "Testing WSL networking configuration..."
echo "WSL IP: $WSL_IP"
echo "Windows Host IP: $WINDOWS_HOST_IP"
echo "Port: $PORT"
echo ""
echo "To test from Windows:"
echo "1. Open Windows Command Prompt"
echo "2. Run: curl http://$WSL_IP:$PORT"
echo "3. Or open browser: http://$WSL_IP:$PORT"
echo ""
echo "To test from WSL:"
echo "1. Run: curl http://localhost:$PORT"
echo "2. Or open browser: http://localhost:$PORT"
EOF

chmod +x "$TEST_SCRIPT"
print_success "Test script created: $TEST_SCRIPT"

# Show configuration summary
print_header "CONFIGURATION SUMMARY"

print_status "WSL Configuration:"
print_status "  WSL IP: $WSL_IP"
print_status "  Windows Host IP: $WINDOWS_HOST_IP"
print_status "  Port: $PORT"

print_status "Access URLs:"
print_status "  From WSL: http://localhost:$PORT"
print_status "  From Windows: http://$WSL_IP:$PORT"

print_status "Next Steps:"
print_status "1. Run the Windows batch script to configure firewall"
print_status "2. Start the UI server: ./bash/serve_ui.sh $PORT"
print_status "3. Test access from Windows browser"

print_warning "Important Notes:"
print_status "- You may need to run the Windows script as Administrator"
print_status "- Windows Defender may prompt for permission"
print_status "- Some corporate networks may block this configuration"

print_success "WSL networking configuration completed!"
