#!/bin/bash
#
# Build Environment Validation Framework
# Validates the build environment for LFS/BLFS builds
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
VALIDATION_DIR="/var/run/lfs-wrapper/validation"
VALIDATION_LOG="${VALIDATION_DIR}/validation.log"
mkdir -p "$VALIDATION_DIR"

# Required Tools Array
declare -A REQUIRED_TOOLS=(
    ["gcc"]="4.8.0"
    ["g++"]="4.8.0"
    ["make"]="4.0"
    ["ld"]="2.30"
    ["bison"]="3.0"
    ["gawk"]="4.0"
    ["patch"]="2.7"
    ["sed"]="4.2"
    ["tar"]="1.30"
)

# Required Libraries Array
declare -A REQUIRED_LIBS=(
    ["glibc"]="2.17"
    ["gcc-libs"]="4.8.0"
    ["zlib"]="1.2"
    ["openssl"]="1.0.2"
)

# System Requirements
declare -r MIN_RAM_GB=4
declare -r MIN_DISK_GB=20
declare -r MIN_CPU_CORES=2

# Environment Validation
validate_environment() {
    local build_dir="$1"
    local log_file="${VALIDATION_DIR}/env_check.log"
    local status=0
    
    log_info "Starting environment validation..."
    
    # Create fresh log
    > "$log_file"
    
    # Validate system resources
    validate_resources || status=1
    
    # Check required tools
    validate_tools || status=1
    
    # Check required libraries
    validate_libraries || status=1
    
    # Validate build directory
    validate_build_dir "$build_dir" || status=1
    
    # Check filesystem permissions
    validate_permissions "$build_dir" || status=1
    
    # Record validation results
    {
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        echo "STATUS=$([[ $status -eq 0 ]] && echo "PASSED" || echo "FAILED")"
        echo "BUILD_DIR=${build_dir}"
    } > "${VALIDATION_DIR}/env.status"
    
    return $status
}

# Resource Validation
validate_resources() {
    local status=0
    
    # Check RAM
    local total_ram_kb
    total_ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local total_ram_gb=$((total_ram_kb / 1024 / 1024))
    
    if [ "$total_ram_gb" -lt "$MIN_RAM_GB" ]; then
        log_error "Insufficient RAM: ${total_ram_gb}GB (minimum ${MIN_RAM_GB}GB required)"
        status=1
    fi
    
    # Check disk space
    local available_space_kb
    available_space_kb=$(df -k . | awk 'NR==2 {print $4}')
    local available_space_gb=$((available_space_kb / 1024 / 1024))
    
    if [ "$available_space_gb" -lt "$MIN_DISK_GB" ]; then
        log_error "Insufficient disk space: ${available_space_gb}GB (minimum ${MIN_DISK_GB}GB required)"
        status=1
    fi
    
    # Check CPU cores
    local cpu_cores
    cpu_cores=$(nproc)
    
    if [ "$cpu_cores" -lt "$MIN_CPU_CORES" ]; then
        log_error "Insufficient CPU cores: ${cpu_cores} (minimum ${MIN_CPU_CORES} required)"
        status=1
    fi
    
    return $status
}

# Tool Validation
validate_tools() {
    local status=0
    
    for tool in "${!REQUIRED_TOOLS[@]}"; do
        local required_version="${REQUIRED_TOOLS[$tool]}"
        
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_error "Required tool not found: ${tool}"
            status=1
            continue
        fi
        
        # Version check
        local current_version
        current_version=$("$tool" --version 2>/dev/null | head -n1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+|[0-9]+\.[0-9]+' || echo "0.0")
        
        if ! version_compare "$current_version" "$required_version"; then
            log_error "Tool version mismatch: ${tool} (found: ${current_version}, required: ${required_version})"
            status=1
        fi
    done
    
    return $status
}

# Library Validation
validate_libraries() {
    local status=0
    
    for lib in "${!REQUIRED_LIBS[@]}"; do
        local required_version="${REQUIRED_LIBS[$lib]}"
        
        # Check for library files
        if ! ldconfig -p | grep -q "lib${lib}\.so"; then
            log_error "Required library not found: ${lib}"
            status=1
            continue
        fi
        
        # Version check (implementation depends on the library)
        case "$lib" in
            glibc)
                local current_version
                current_version=$(ldd --version | head -n1 | grep -oE '[0-9]+\.[0-9]+')
                if ! version_compare "$current_version" "$required_version"; then
                    log_error "Library version mismatch: ${lib} (found: ${current_version}, required: ${required_version})"
                    status=1
                fi
                ;;
        esac
    done
    
    return $status
}

# Build Directory Validation
validate_build_dir() {
    local build_dir="$1"
    local status=0
    
    # Check if directory exists
    if [ ! -d "$build_dir" ]; then
        if ! mkdir -p "$build_dir"; then
            log_error "Failed to create build directory: ${build_dir}"
            return 1
        fi
    fi
    
    # Check write permissions
    if ! touch "${build_dir}/.write_test" 2>/dev/null; then
        log_error "No write permission in build directory: ${build_dir}"
        status=1
    else
        rm -f "${build_dir}/.write_test"
    fi
    
    # Check available inodes
    local inodes_available
    inodes_available=$(df -i "$build_dir" | awk 'NR==2 {print $4}')
    if [ "$inodes_available" -lt 1000000 ]; then
        log_error "Insufficient inodes available: ${inodes_available} (minimum 1000000 required)"
        status=1
    fi
    
    return $status
}

# Permission Validation
validate_permissions() {
    local build_dir="$1"
    local status=0
    
    # Check build directory permissions
    if [ ! -w "$build_dir" ]; then
        log_error "Build directory not writable: ${build_dir}"
        status=1
    fi
    
    # Check if we're root (required for some operations)
    if [ "$(id -u)" -ne 0 ]; then
        log_warn "Not running as root - some operations may fail"
    fi
    
    # Check sudo availability if not root
    if [ "$(id -u)" -ne 0 ] && ! command -v sudo >/dev/null 2>&1; then
        log_error "sudo not available - required for privileged operations"
        status=1
    fi
    
    return $status
}

# Security Validation
validate_security() {
    local status=0
    
    # Check SELinux/AppArmor status
    if command -v getenforce >/dev/null 2>&1; then
        local selinux_mode
        selinux_mode=$(getenforce)
        if [ "$selinux_mode" = "Enforcing" ]; then
            log_warn "SELinux is enforcing - may affect build process"
        fi
    fi
    
    if command -v aa-status >/dev/null 2>&1; then
        if aa-status --enabled 2>/dev/null; then
            log_warn "AppArmor is enabled - may affect build process"
        fi
    fi
    
    # Check for world-writable directories in PATH
    while IFS=: read -r path_dir; do
        if [ -d "$path_dir" ] && [ -w "$path_dir" ] && [ -x "$path_dir" ]; then
            if [ "$(stat -c '%a' "$path_dir")" = "777" ]; then
                log_error "World-writable directory in PATH: ${path_dir}"
                status=1
            fi
        fi
    done <<< "$PATH"
    
    return $status
}

# Main entry point
main() {
    if [ "$#" -lt 1 ]; then
        log_error "Usage: $0 <build_directory>"
        exit 1
    fi
    
    local build_dir="$1"
    
    # Run all validation checks
    if validate_environment "$build_dir"; then
        log_info "Environment validation passed"
        exit 0
    else
        log_error "Environment validation failed"
        exit 1
    fi
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

