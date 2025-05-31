#!/bin/bash
#
# check-host-system.sh - Host System Requirements Verification
# LFS Chapter 4 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Verifies that the host system meets all requirements
# for building LFS 12.3 system.

set -e

# Configuration
MIN_DISK_SPACE=8  # GB
MIN_MEMORY=4      # GB
REQUIRED_PACKAGES=(
    bash
    binutils
    coreutils
    gcc
    glibc
    grep
    make
    sed
)

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_disk_space() {
    local available_space
    available_space=$(df -BG "$LFS" | awk 'NR==2 {print $4}' | tr -d 'G')
    
    if [ "$available_space" -lt "$MIN_DISK_SPACE" ]; then
        log_error "Insufficient disk space. Required: ${MIN_DISK_SPACE}GB, Available: ${available_space}GB"
        return 1
    fi
    log_info "Disk space check passed: ${available_space}GB available"
}

check_memory() {
    local available_memory
    available_memory=$(free -g | awk '/^Mem:/{print $2}')
    
    if [ "$available_memory" -lt "$MIN_MEMORY" ]; then
        log_warn "Low memory detected. Recommended: ${MIN_MEMORY}GB, Available: ${available_memory}GB"
    fi
    log_info "Memory check passed: ${available_memory}GB available"
}

check_required_packages() {
    local missing_packages=()
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! command -v "$package" >/dev/null 2>&1; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -ne 0 ]; then
        log_error "Missing required packages: ${missing_packages[*]}"
        return 1
    fi
    log_info "All required packages present"
}

check_compiler() {
    # Verify GCC and its version
    local gcc_version
    gcc_version=$(gcc --version | head -n1 | awk '{print $3}')
    log_info "GCC version: $gcc_version"
    
    # Simple compilation test
    echo 'int main(){}' > test.c
    if ! gcc -o test test.c; then
        log_error "GCC compilation test failed"
        rm -f test.c
        return 1
    fi
    rm -f test.c test
    log_info "GCC compilation test passed"
}

main() {
    log_info "Starting host system verification..."
    
    local errors=0
    
    check_disk_space || ((errors++))
    check_memory
    check_required_packages || ((errors++))
    check_compiler || ((errors++))
    
    if [ "$errors" -eq 0 ]; then
        log_info "Host system meets all requirements"
        return 0
    else
        log_error "Host system verification failed with $errors errors"
        return 1
    fi
}

main "$@"

