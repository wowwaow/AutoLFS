#!/bin/bash
#
# binutils-pass1.sh - Binutils Pass 1 Build Script
# LFS Chapter 5 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Builds the first pass of Binutils for the LFS cross-toolchain

set -e

# Source our environment
source "$(dirname "$0")/../config/build-environment.conf"

# Color output setup
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Build configuration
BINUTILS_VERSION="2.41"
BINUTILS_FILE="binutils-${BINUTILS_VERSION}.tar.xz"
BINUTILS_URL="https://ftp.gnu.org/gnu/binutils/${BINUTILS_FILE}"
BINUTILS_MD5="49912ce774666a30806141f106124294"

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
        "PATH"
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
    
    log_info "Environment verified successfully"
}

download_source() {
    local sources_dir="$LFS/sources"
    local file_path="$sources_dir/$BINUTILS_FILE"
    
    # Create sources directory if it doesn't exist
    mkdir -p "$sources_dir"
    
    # Download if not already present
    if [ ! -f "$file_path" ]; then
        log_info "Downloading Binutils..."
        wget "$BINUTILS_URL" -O "$file_path"
    fi
    
    # Verify MD5
    local md5_check=$(md5sum "$file_path" | awk '{print $1}')
    if [ "$md5_check" != "$BINUTILS_MD5" ]; then
        log_error "MD5 checksum verification failed"
        return 1
    fi
    
    log_info "Source package verified successfully"
}

prepare_build() {
    cd "$LFS/sources"
    
    # Clean previous build if exists
    rm -rf "binutils-$BINUTILS_VERSION"
    
    # Extract source
    log_info "Extracting Binutils source..."
    tar xf "$BINUTILS_FILE"
    
    # Create and enter build directory
    cd "binutils-$BINUTILS_VERSION"
    mkdir -v build
    cd build
    
    log_info "Build directory prepared"
}

configure_binutils() {
    log_info "Configuring Binutils..."
    
    ../configure \
        --prefix=$LFS/tools \
        --with-sysroot=$LFS \
        --target=$LFS_TGT \
        --disable-nls \
        --enable-gprofng=no \
        --disable-werror \
        --enable-default-hash-style=gnu
        
    if [ $? -ne 0 ]; then
        log_error "Configuration failed"
        return 1
    fi
    
    log_info "Configuration completed successfully"
}

build_binutils() {
    log_info "Building Binutils..."
    
    make -j$(nproc)
    
    if [ $? -ne 0 ]; then
        log_error "Build failed"
        return 1
    fi
    
    log_info "Build completed successfully"
}

install_binutils() {
    log_info "Installing Binutils..."
    
    make install
    
    if [ $? -ne 0 ]; then
        log_error "Installation failed"
        return 1
    fi
    
    log_info "Installation completed successfully"
}

verify_build() {
    log_info "Verifying build..."
    
    # Check for critical files
    local check_files=(
        "$LFS/tools/bin/${LFS_TGT}-ld"
        "$LFS/tools/bin/${LFS_TGT}-as"
    )
    
    for file in "${check_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Critical file missing: $file"
            return 1
        fi
    done
    
    # Test basic functionality
    if ! "$LFS/tools/bin/${LFS_TGT}-ld" --version >/dev/null; then
        log_error "Linker functionality test failed"
        return 1
    fi
    
    log_info "Build verification completed successfully"
}

cleanup() {
    if [ "$1" != "keep" ]; then
        log_info "Cleaning up build directory..."
        cd "$LFS/sources"
        rm -rf "binutils-$BINUTILS_VERSION"
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
    
    log_info "Starting Binutils Pass 1 build..."
    
    # Execute build steps
    verify_environment || exit 1
    download_source || exit 1
    prepare_build || exit 1
    configure_binutils || exit 1
    build_binutils || exit 1
    install_binutils || exit 1
    verify_build || exit 1
    
    # Cleanup unless --keep-build was specified
    if [ $keep_build -eq 0 ]; then
        cleanup
    else
        cleanup "keep"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "Binutils Pass 1 build completed successfully in ${duration} seconds"
    return 0
}

main "$@"

