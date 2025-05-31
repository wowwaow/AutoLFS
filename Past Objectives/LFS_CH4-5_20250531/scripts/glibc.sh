#!/bin/bash
#
# glibc.sh - Glibc Build Script
# LFS Chapter 5 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Builds and installs Glibc for the LFS cross-toolchain

set -e

# Source our environment
source "$(dirname "$0")/../config/build-environment.conf"

# Color output setup
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Build configuration
GLIBC_VERSION="2.41"
GLIBC_FILE="glibc-${GLIBC_VERSION}.tar.xz"
GLIBC_URL="https://ftp.gnu.org/gnu/glibc/${GLIBC_FILE}"
GLIBC_MD5="19862601af60f73ac69e067d3e9267d4"

# Required kernel version
MIN_KERNEL="5.4"

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
    
    # Verify prerequisites
    if ! command -v "$LFS_TGT-gcc" >/dev/null 2>&1; then
        log_error "GCC (Pass 1) must be installed first"
        return 1
    fi
    
    if ! command -v "$LFS_TGT-as" >/dev/null 2>&1; then
        log_error "Binutils (Pass 1) must be installed first"
        return 1
    fi
    
    # Verify Linux API Headers
    if [ ! -d "$LFS/usr/include" ]; then
        log_error "Linux API Headers must be installed first"
        return 1
    fi
    
    # Verify critical headers
    local required_headers=(
        "$LFS/usr/include/linux/version.h"
        "$LFS/usr/include/linux/limits.h"
    )
    
    for header in "${required_headers[@]}"; do
        if [ ! -f "$header" ]; then
            log_error "Required header missing: $header"
            return 1
        fi
    done
    
    log_info "Environment verified successfully"
}

download_source() {
    local sources_dir="$LFS/sources"
    local file_path="$sources_dir/$GLIBC_FILE"
    
    # Create sources directory if it doesn't exist
    mkdir -p "$sources_dir"
    
    # Download if not already present
    if [ ! -f "$file_path" ]; then
        log_info "Downloading Glibc..."
        wget "$GLIBC_URL" -O "$file_path"
    fi
    
    # Verify MD5
    local md5_check=$(md5sum "$file_path" | awk '{print $1}')
    if [ "$md5_check" != "$GLIBC_MD5" ]; then
        log_error "MD5 checksum verification failed"
        return 1
    fi
    
    log_info "Source package verified successfully"
}

prepare_build() {
    cd "$LFS/sources"
    
    # Clean previous build if exists
    rm -rf "glibc-$GLIBC_VERSION"
    
    # Extract source
    log_info "Extracting Glibc source..."
    tar xf "$GLIBC_FILE"
    
    # Create build directory
    cd "glibc-$GLIBC_VERSION"
    mkdir -v build
    cd build
    
    # Create configparms file
    echo "rootsbindir=/usr/sbin" > configparms
    
    log_info "Build directory prepared"
}

patch_source() {
    cd "$LFS/sources/glibc-$GLIBC_VERSION"
    
    # Apply any necessary patches here
    # For now, we don't have any patches to apply
    
    log_info "Source preparation completed"
}

configure_glibc() {
    log_info "Configuring Glibc..."
    
    # Basic sanity check
    echo "int main(){}" > dummy.c
    if ! $LFS_TGT-gcc dummy.c; then
        log_error "Cross-compiler check failed"
        rm -f dummy.c a.out
        return 1
    fi
    rm -f dummy.c a.out
    
    # Configure with options from toolchain-architecture.md
    ../configure \
        --prefix=/usr \
        --host=$LFS_TGT \
        --build=$(../scripts/config.guess) \
        --enable-kernel=$MIN_KERNEL \
        --with-headers=$LFS/usr/include \
        libc_cv_slibdir=/usr/lib
        
    if [ $? -ne 0 ]; then
        log_error "Configuration failed"
        return 1
    fi
    
    log_info "Configuration completed successfully"
}

build_glibc() {
    log_info "Building Glibc..."
    
    make -j$(nproc)
    
    if [ $? -ne 0 ]; then
        log_error "Build failed"
        return 1
    fi
    
    log_info "Build completed successfully"
}

install_glibc() {
    log_info "Installing Glibc..."
    
    make DESTDIR=$LFS install
    
    if [ $? -ne 0 ]; then
        log_error "Installation failed"
        return 1
    fi
    
    # Fix hardcoded path in ldd script
    sed '/RTLDLIST=/s@/usr@@g' -i $LFS/usr/bin/ldd
    
    log_info "Installation completed successfully"
}

verify_installation() {
    log_info "Verifying installation..."
    local errors=0
    
    # Check for critical files
    local check_files=(
        "$LFS/usr/lib/libc.so"
        "$LFS/usr/lib/ld-linux-x86-64.so.2"
        "$LFS/usr/lib/libm.so"
        "$LFS/usr/include/stdio.h"
    )
    
    for file in "${check_files[@]}"; do
        if [ ! -f "$file" ] && [ ! -L "$file" ]; then
            log_error "Critical file missing: $file"
            ((errors++))
        fi
    done
    
    # Basic functionality test
    cd "$LFS/sources/glibc-$GLIBC_VERSION/build"
    echo 'int main(){}' > dummy.c
    
    $LFS_TGT-gcc dummy.c
    if [ $? -ne 0 ]; then
        log_error "Basic compilation test failed"
        rm -f dummy.c a.out
        ((errors++))
    else
        # Check dynamic linker
        readelf -l a.out | grep -q '/lib64/ld-linux-x86-64.so.2'
        if [ $? -ne 0 ]; then
            log_error "Dynamic linker path verification failed"
            ((errors++))
        fi
        rm -f dummy.c a.out
    fi
    
    # Test basic C library functionality
    cat > test.c << "EOF"
#include <stdio.h>
int main() {
    printf("Hello, LFS!\n");
    return 0;
}
EOF
    
    $LFS_TGT-gcc test.c -o test
    if [ $? -ne 0 ]; then
        log_error "C library functionality test compilation failed"
        ((errors++))
    else
        # Test if the program runs
        if ! "$LFS/usr/lib/ld-linux-x86-64.so.2" --library-path "$LFS/usr/lib" ./test >/dev/null; then
            log_error "C library functionality test execution failed"
            ((errors++))
        fi
    fi
    rm -f test.c test
    
    if [ "$errors" -eq 0 ]; then
        log_info "Installation verification completed successfully"
        return 0
    else
        log_error "Installation verification failed with $errors errors"
        return 1
    fi
}

cleanup() {
    if [ "$1" != "keep" ]; then
        log_info "Cleaning up build directory..."
        cd "$LFS/sources"
        rm -rf "glibc-$GLIBC_VERSION"
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
    
    log_info "Starting Glibc build..."
    
    # Execute build steps
    verify_environment || exit 1
    download_source || exit 1
    prepare_build || exit 1
    patch_source || exit 1
    configure_glibc || exit 1
    build_glibc || exit 1
    install_glibc || exit 1
    verify_installation || exit 1
    
    # Cleanup unless --keep-build was specified
    if [ $keep_build -eq 0 ]; then
        cleanup
    else
        cleanup "keep"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "Glibc build completed successfully in ${duration} seconds"
    return 0
}

main "$@"

