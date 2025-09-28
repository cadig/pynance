# WSL Networking Guide for Pynance UI

## Overview
This guide explains how to access the Pynance UI from your Windows host machine when running in WSL Ubuntu.

## WSL Networking Basics

### How WSL Networking Works
- **WSL2**: Uses a virtual network adapter with its own IP address
- **WSL1**: Shares the Windows host network adapter
- **Port Forwarding**: Required to access WSL services from Windows

### Network Architecture
```
Windows Host (192.168.1.100)
    ↓
WSL Ubuntu (172.20.240.2)
    ↓
Pynance UI (localhost:8080)
```

## Setup Process

### 1. **Automatic Setup**
The setup_machine.sh script automatically detects WSL and configures networking:

```bash
./bash/setup_machine.sh
```

### 2. **Manual Setup**
If you need to configure networking manually:

```bash
# Configure WSL networking
./bash/network/configure_wsl_networking.sh 8080

# Start UI server
./bash/serve_ui.sh 8080
```

## Access Methods

### From WSL (Local)
```bash
# Start the server
./bash/serve_ui.sh

# Access locally
curl http://localhost:8080
# Or open browser: http://localhost:8080
```

### From Windows Host
```bash
# Get WSL IP address
hostname -I

# Access from Windows browser
http://[WSL_IP]:8080
# Example: http://172.20.240.2:8080
```

## Windows Firewall Configuration

### Method 1: Batch Script (Recommended)
The setup script creates a Windows batch file:

```cmd
# Run in Windows Command Prompt as Administrator
cmd.exe /c /tmp/configure_windows_firewall.bat
```

### Method 2: PowerShell Script
```powershell
# Run in Windows PowerShell as Administrator
powershell.exe -ExecutionPolicy Bypass -File /tmp/configure_windows_firewall.ps1
```

### Method 3: Manual Configuration
```cmd
# Add firewall rule for the port
netsh advfirewall firewall add rule name="WSL Port 8080" dir=in action=allow protocol=TCP localport=8080

# Add firewall rule for WSL subnet
netsh advfirewall firewall add rule name="WSL Subnet" dir=in action=allow protocol=TCP localport=8080 remoteip=172.20.240.2
```

## Troubleshooting

### Common Issues

#### 1. **Connection Refused**
```bash
# Check if port is in use
lsof -i :8080

# Check if server is running
ps aux | grep "http.server"

# Restart server
./bash/serve_ui.sh
```

#### 2. **Windows Can't Access WSL**
```bash
# Check WSL IP
hostname -I

# Check Windows host IP
ip route | grep default

# Test connectivity
ping [WSL_IP]
```

#### 3. **Firewall Blocking**
```cmd
# Check Windows Firewall status
netsh advfirewall show allprofiles

# Temporarily disable for testing
netsh advfirewall set allprofiles state off
```

### Debug Commands

#### Check Network Configuration
```bash
# WSL IP address
hostname -I

# Windows host IP
ip route | grep default

# Test port accessibility
netstat -tlnp | grep :8080
```

#### Test Connectivity
```bash
# From WSL
curl http://localhost:8080

# From Windows (in Command Prompt)
curl http://[WSL_IP]:8080
```

## Port Configuration

### Default Ports
- **UI Server**: 8080
- **Alternative**: 8081, 8082, etc.

### Change Port
```bash
# Use different port
./bash/serve_ui.sh 8081

# Configure networking for new port
./bash/network/configure_wsl_networking.sh 8081
```

## Security Considerations

### Firewall Rules
- **Inbound**: Allow TCP port 8080 from WSL IP
- **Outbound**: Allow TCP port 8080 to WSL IP
- **Scope**: Limit to WSL subnet only

### Network Isolation
- **WSL Subnet**: 172.20.240.0/20 (typical)
- **Windows Host**: 192.168.1.0/24 (typical)
- **Internet**: Blocked by default

## Advanced Configuration

### Custom Port Forwarding
```bash
# Forward Windows port to WSL port
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=172.20.240.2
```

### Persistent Configuration
```bash
# Add to WSL startup script
echo "netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=172.20.240.2" >> ~/.bashrc
```

## Monitoring and Maintenance

### Check Server Status
```bash
# Check if server is running
ps aux | grep "http.server"

# Check port status
netstat -tlnp | grep :8080

# Check logs
tail -f /var/log/syslog | grep "http.server"
```

### Restart Server
```bash
# Stop server
pkill -f "http.server"

# Start server
./bash/serve_ui.sh
```

## Best Practices

### 1. **Use Specific Ports**
- Avoid port conflicts
- Use 8080-8090 range
- Document port usage

### 2. **Secure Configuration**
- Limit firewall rules to WSL subnet
- Use HTTPS in production
- Implement authentication

### 3. **Monitor Performance**
- Check server logs
- Monitor resource usage
- Test connectivity regularly

### 4. **Backup Configuration**
- Save firewall rules
- Document network settings
- Test after system updates

## Example Workflow

### Complete Setup
```bash
# 1. Run setup script
./bash/setup_machine.sh

# 2. Configure WSL networking
./bash/network/configure_wsl_networking.sh 8080

# 3. Start UI server
./bash/serve_ui.sh 8080

# 4. Test from WSL
curl http://localhost:8080

# 5. Test from Windows
# Open browser: http://[WSL_IP]:8080
```

### Daily Usage
```bash
# Start UI server
./bash/serve_ui.sh

# Access from Windows browser
# http://[WSL_IP]:8080
```

## Summary

The Pynance UI can be easily accessed from Windows when running in WSL by:

1. **Configuring WSL networking** for port forwarding
2. **Setting up Windows Firewall** rules
3. **Starting the UI server** with proper binding
4. **Accessing via Windows browser** using WSL IP address

The setup scripts handle most of this automatically, but manual configuration is available for advanced users!
