#!/bin/bash

# Security Validation Framework
# Purpose: System security assessment and validation tool
# Author: WARP System
# Date: 2025-05-31

# Exit on error, undefined vars, and propagate pipe failures
set -euo pipefail

# Constants
readonly SECURITY_DIR="/mnt/host/WARP_CURRENT/Current Objective/implementation/qa/security"
readonly LOG_DIR="/mnt/host/WARP_CURRENT/System Logs"
readonly SECURITY_LOG="${LOG_DIR}/security_validation.log"
readonly TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
readonly ALERT_THRESHOLD="HIGH"

# Ensure proper permissions before starting
function ensure_permissions() {
    local dir_path="$1"
    sudo chown ubuntu:ubuntu "$dir_path"
    sudo chmod 755 "$dir_path"
}

# Logging functions
function log_info() {
    echo "[INFO] $(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$SECURITY_LOG"
}

function log_error() {
    echo "[ERROR] $(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$SECURITY_LOG"
}

function log_alert() {
    echo "[ALERT] $(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$SECURITY_LOG"
    
    # Send alert to security team (implement your preferred notification method)
    # Example: Email, Slack, etc.
}

# Initialize security environment
function init_security_env() {
    # Create necessary directories with proper permissions
    for dir in "$SECURITY_DIR" "$LOG_DIR"; do
        if [[ ! -d "$dir" ]]; then
            sudo mkdir -p "$dir"
            ensure_permissions "$dir"
        fi
    done
    
    log_info "Security validation environment initialized"
}

# File permission validation
function validate_file_permissions() {
    local target_path="$1"
    local report_file="${SECURITY_DIR}/permission_audit_${TIMESTAMP}.csv"
    
    log_info "Starting permission validation for: $target_path"
    
    echo "path,owner,group,permissions,issues" > "$report_file"
    
    find "$target_path" -type f -o -type d | while read -r item; do
        local owner=$(stat -c '%U' "$item")
        local group=$(stat -c '%G' "$item")
        local perms=$(stat -c '%a' "$item")
        local issues=""
        
        # Check for insecure permissions
        if [[ -d "$item" && "$perms" != "755" ]]; then
            issues+="directory_permission_error;"
        elif [[ -f "$item" && "$perms" != "644" ]]; then
            issues+="file_permission_error;"
        fi
        
        # Check ownership
        if [[ "$owner" != "ubuntu" ]]; then
            issues+="wrong_owner;"
        fi
        if [[ "$group" != "ubuntu" ]]; then
            issues+="wrong_group;"
        fi
        
        echo "$item,$owner,$group,$perms,$issues" >> "$report_file"
        
        if [[ -n "$issues" ]]; then
            log_alert "Permission issue found: $item ($issues)"
        fi
    done
    
    log_info "Permission validation completed. Report: $report_file"
}

# Security scanning function
function run_security_scan() {
    local target_path="$1"
    local scan_report="${SECURITY_DIR}/security_scan_${TIMESTAMP}.log"
    
    log_info "Starting security scan for: $target_path"
    
    # Check for common security tools
    local security_tools=("clamscan" "chkrootkit" "rkhunter")
    local missing_tools=()
    
    for tool in "${security_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    # Install missing security tools
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_info "Installing missing security tools: ${missing_tools[*]}"
        sudo apt-get update
        for tool in "${missing_tools[@]}"; do
            case "$tool" in
                "clamscan")
                    sudo apt-get install -y clamav
                    sudo freshclam
                    ;;
                "chkrootkit")
                    sudo apt-get install -y chkrootkit
                    ;;
                "rkhunter")
                    sudo apt-get install -y rkhunter
                    sudo rkhunter --update
                    ;;
            esac
        done
    fi
    
    # Run security scans
    {
        echo "=== Security Scan Report ==="
        echo "Scan Time: $(date)"
        echo "Target: $target_path"
        echo
        
        # Virus scan
        echo "=== Virus Scan ==="
        sudo clamscan -r "$target_path"
        
        # Rootkit check
        echo "=== Rootkit Check ==="
        sudo chkrootkit -p "$target_path"
        
        # Additional rootkit hunter
        echo "=== RKHunter Scan ==="
        sudo rkhunter --check --skip-keypress --path "$target_path"
        
    } > "$scan_report"
    
    log_info "Security scan completed. Report: $scan_report"
}

# Vulnerability testing
function test_vulnerabilities() {
    local target_system="$1"
    local report_file="${SECURITY_DIR}/vulnerability_test_${TIMESTAMP}.log"
    
    log_info "Starting vulnerability testing for: $target_system"
    
    {
        echo "=== Vulnerability Test Report ==="
        echo "Test Time: $(date)"
        echo "Target System: $target_system"
        echo
        
        # System update check
        echo "=== System Updates ==="
        sudo apt-get update &> /dev/null
        apt list --upgradable
        
        # Open ports check
        echo "=== Open Ports ==="
        sudo netstat -tuln
        
        # Service version check
        echo "=== Service Versions ==="
        dpkg -l | grep -E "ssh|apache2|nginx|mysql|postgresql"
        
        # SSL/TLS check
        if command -v openssl &> /dev/null; then
            echo "=== SSL/TLS Configuration ==="
            openssl version
            # Add specific SSL checks here
        fi
        
    } > "$report_file"
    
    log_info "Vulnerability testing completed. Report: $report_file"
}

# Security metrics collection
function collect_security_metrics() {
    local metrics_file="${SECURITY_DIR}/security_metrics_${TIMESTAMP}.json"
    
    log_info "Collecting security metrics"
    
    # Collect various security metrics
    {
        echo "{"
        echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
        echo "  \"metrics\": {"
        echo "    \"failed_login_attempts\": $(grep -c "Failed password" /var/log/auth.log),"
        echo "    \"sudo_usage\": $(grep -c "sudo:" /var/log/auth.log),"
        echo "    \"file_permission_issues\": $(grep -c "permission_error" "${SECURITY_DIR}/permission_audit_${TIMESTAMP}.csv"),"
        echo "    \"open_ports\": $(netstat -tuln | grep -c LISTEN),"
        echo "    \"active_users\": $(who | wc -l)"
        echo "  }"
        echo "}"
    } > "$metrics_file"
    
    log_info "Security metrics collected. File: $metrics_file"
}

# Generate security report
function generate_security_report() {
    local report_file="${SECURITY_DIR}/security_report_${TIMESTAMP}.html"
    
    log_info "Generating security report"
    
    # Create HTML report
    {
        echo "<html><head><title>Security Validation Report</title>"
        echo "<style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .alert { color: red; font-weight: bold; }
            .warning { color: orange; }
            .success { color: green; }
        </style>"
        echo "</head><body>"
        echo "<h1>Security Validation Report</h1>"
        echo "<p>Generated: $(date)</p>"
        
        # Include permission validation results
        echo "<h2>Permission Validation</h2>"
        if [[ -f "${SECURITY_DIR}/permission_audit_${TIMESTAMP}.csv" ]]; then
            echo "<pre>"
            cat "${SECURITY_DIR}/permission_audit_${TIMESTAMP}.csv"
            echo "</pre>"
        fi
        
        # Include security scan results
        echo "<h2>Security Scan Results</h2>"
        if [[ -f "${SECURITY_DIR}/security_scan_${TIMESTAMP}.log" ]]; then
            echo "<pre>"
            cat "${SECURITY_DIR}/security_scan_${TIMESTAMP}.log"
            echo "</pre>"
        fi
        
        # Include vulnerability test results
        echo "<h2>Vulnerability Test Results</h2>"
        if [[ -f "${SECURITY_DIR}/vulnerability_test_${TIMESTAMP}.log" ]]; then
            echo "<pre>"
            cat "${SECURITY_DIR}/vulnerability_test_${TIMESTAMP}.log"
            echo "</pre>"
        fi
        
        # Include security metrics
        echo "<h2>Security Metrics</h2>"
        if [[ -f "${SECURITY_DIR}/security_metrics_${TIMESTAMP}.json" ]]; then
            echo "<pre>"
            cat "${SECURITY_DIR}/security_metrics_${TIMESTAMP}.json"
            echo "</pre>"
        fi
        
        echo "</body></html>"
    } > "$report_file"
    
    log_info "Security report generated: $report_file"
}

# Main security validation execution
function run_security_validation() {
    local target_path="${1:-/mnt/host/WARP_CURRENT}"
    
    # Initialize environment
    init_security_env
    
    # Run all security checks
    validate_file_permissions "$target_path"
    run_security_scan "$target_path"
    test_vulnerabilities "$target_path"
    collect_security_metrics
    
    # Generate final report
    generate_security_report
}

# Script usage
function show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -h, --help                 Show this help message
    -p, --permissions PATH     Validate permissions for specified path
    -s, --scan PATH           Run security scan on specified path
    -v, --vulnerabilities     Test system vulnerabilities
    -m, --metrics            Collect security metrics
    -r, --report             Generate security report only

Example:
    $0 --permissions /path/to/check   # Check permissions
    $0 --scan /path/to/scan          # Run security scan
    $0 --vulnerabilities            # Run vulnerability tests
EOF
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_usage
        exit 0
        ;;
    -p|--permissions)
        validate_file_permissions "${2:-/mnt/host/WARP_CURRENT}"
        ;;
    -s|--scan)
        run_security_scan "${2:-/mnt/host/WARP_CURRENT}"
        ;;
    -v|--vulnerabilities)
        test_vulnerabilities "${2:-/mnt/host/WARP_CURRENT}"
        ;;
    -m|--metrics)
        collect_security_metrics
        ;;
    -r|--report)
        generate_security_report
        ;;
    *)
        run_security_validation
        ;;
esac

