#!/bin/bash
#
# linux-api-headers.sh - Linux API Headers Installation
# LFS Chapter 5 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Prepares and installs Linux API headers for the LFS system

set -e

# Source our environment
source "$(dirname "$0")/../config/build-environment.conf"

# Color output setup
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Build configuration
LINUX_VERSION="6.13.4"
LINUX_FILE="linux-${LINUX_VERSION}.tar.xz"
LINUX_URL="https://www.kernel.org/pub/linux/kernel/v6.x/${LINUX_FILE}"
LINUX_MD5="13b9e6c29105a34db4647190a43d1810"

# Critical header files to verify
CRITICAL_HEADERS=(
    "asm/types.h"
    "linux/version.h"
    "linux/limits.h"
    "linux/posix_types.h"
    "linux/stddef.h"
)

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

verify_environment() {
    # Verify required variables
    local required_vars=(
        "LFS"
        "LFS_TGT"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required environment variable $var is not set"
            return 1
        fi
    done
    
    # Verify LFS directory exists
    if [ ! -d "$LFS" ]; then
        log_error "LFS directory $LFS does not exist"
        return 1
    }
    
    # Verify we're running as lfs user
    if [ "$(whoami)" != "lfs" ]; then
        log_error "This script must be run as the 'lfs' user"
        return 1
    }
    
    # Verify prerequisites
    if ! command -v make >/dev/null 2>&1; then
        log_error "make command not found"
        return 1
    }
    
    log_info "Environment verified successfully"
}

download_source() {
    local sources_dir="$LFS/sources"
    local file_path="$sources_dir/$LINUX_FILE"
    
    # Create sources directory if it doesn't exist
    mkdir -p "$sources_dir"
    
    # Download if not already present
    if [ ! -f "$file_path" ]; then
        log_info "Downloading Linux kernel..."
        wget "$LINUX_URL" -O "$file_path"
    fi
    
    # Verify MD5
    local md5_check=$(md5sum "$file_path" | awk '{print $1}')
    if [ "$md5_check" != "$LINUX_MD5" ]; then
        log_error "MD5 checksum verification failed"
        return 1
    fi
    
    log_info "Source package verified successfully"
}

prepare_source() {
    cd "$LFS/sources"
    
    # Clean previous build if exists
    rm -rf "linux-$LINUX_VERSION"
    
    # Extract source
    log_info "Extracting Linux kernel source..."
    tar xf "$LINUX_FILE"
    
    cd "linux-$LINUX_VERSION"
    
    # Clean the kernel tree
    log_info "Cleaning kernel tree..."
    make mrproper
    if [ $? -ne 0 ]; then
        log_error "Failed to clean kernel tree"
        return 1
    fi
    
    log_info "Source preparation completed"
}

generate_headers() {
    log_info "Generating API headers..."
    
    make headers
    if [ $? -ne 0 ]; then
        log_error "Header generation failed"
        return 1
    }
    
    log_info "Headers generated successfully"
}

install_headers() {
    log_info "Installing API headers..."
    
    # Create target directory
    mkdir -pv "$LFS/usr/include"
    
    # Find and copy only valid header files
    find usr/include -type f ! -name '*.h' -delete
    
    # Copy headers to target directory
    cp -rv usr/include/* "$LFS/usr/include"
    if [ $? -ne 0 ]; then
        log_error "Header installation failed"
        return 1
    fi
    
    log_info "Headers installed successfully"
}

verify_installation() {
    log_info "Verifying header installation..."
    local errors=0
    
    # Check for critical headers
    for header in "${CRITICAL_HEADERS[@]}"; do
        if [ ! -f "$LFS/usr/include/$header" ]; then
            log_error "Critical header missing: $header"
            ((errors++))
        fi
    done
    
    # Verify header integrity
    for header in "${CRITICAL_HEADERS[@]}"; do
        if [ -f "$LFS/usr/include/$header" ]; then
            if ! grep -q '^#' "$LFS/usr/include/$header" 2>/dev/null; then
                log_error "Header file appears corrupt: $header"
                ((errors++))
            fi
        fi
    done
    
    # Check total header count
    local header_count=$(find "$LFS/usr/include" -type f -name '*.h' | wc -l)
    if [ "$header_count" -lt 100 ]; then
        log_error "Suspiciously low number of headers installed: $header_count"
        ((errors++))
    fi
    
    if [ "$errors" -eq 0 ]; then
        log_info "Header verification completed successfully"
        return 0
    else
        log_error "Header verification failed with $errors errors"
        return 1
    fi
}

cleanup() {
    if [ "$1" != "keep" ]; then
        log_info "Cleaning up build directory..."
        cd "$LFS/sources"
        rm -rf "linux-$LINUX_VERSION"
    fi
}

main() {
    local start_time=$(date +%s)
    local keep_build=0
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --keep-build)
                keep_build=1
                shift
                ;;
            *)
                log_error "Unknown argument: $1"
                exit 1
                ;;
        esac
    done
    
    log_info "Starting Linux API Headers installation..."
    
    # Execute installation steps
    verify_environment || exit 1
    download_source || exit 1
    prepare_source || exit 1
    generate_headers || exit 1
    install_headers || exit 1
    verify_installation || exit 1
    
    # Cleanup unless --keep-build was specified
    if [ $keep_build -eq 0 ]; then
        cleanup
    else
        cleanup "keep"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "Linux API Headers installation completed successfully in ${duration} seconds"
    return 0
}

main "$@"

