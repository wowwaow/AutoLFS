#!/bin/bash
#
# libstdcxx.sh - Libstdc++ Build Script
# LFS Chapter 5 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Builds and installs Libstdc++ for the LFS cross-toolchain

set -e

# Source our environment
source "$(dirname "$0")/../config/build-environment.conf"

# Color output setup
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Build configuration
GCC_VERSION="14.2.0"
GCC_FILE="gcc-${GCC_VERSION}.tar.xz"
GCC_URL="https://ftp.gnu.org/gnu/gcc/gcc-${GCC_VERSION}/${GCC_FILE}"
GCC_MD5="2268420ba02dc01821960e274711bde0"

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
    
    # Verify Glibc installation
    if [ ! -f "$LFS/usr/lib/libc.so" ]; then
        log_error "Glibc must be installed first"
        return 1
    fi
    
    # Verify C++11 support
    echo 'int main(){return 0;}' > test.cpp
    if ! $LFS_TGT-g++ -std=c++11 test.cpp -o test >/dev/null 2>&1; then
        log_error "C++11 support check failed"
        rm -f test.cpp test
        return 1
    fi
    rm -f test.cpp test
    
    log_info "Environment verified successfully"
}

download_source() {
    local sources_dir="$LFS/sources"
    local file_path="$sources_dir/$GCC_FILE"
    
    # Create sources directory if it doesn't exist
    mkdir -p "$sources_dir"
    
    # Download if not already present
    if [ ! -f "$file_path" ]; then
        log_info "Downloading GCC source..."
        wget "$GCC_URL" -O "$file_path"
    fi
    
    # Verify MD5
    local md5_check=$(md5sum "$file_path" | awk '{print $1}')
    if [ "$md5_check" != "$GCC_MD5" ]; then
        log_error "MD5 checksum verification failed"
        return 1
    fi
    
    log_info "Source package verified successfully"
}

prepare_build() {
    cd "$LFS/sources"
    
    # Clean previous build if exists
    rm -rf "gcc-$GCC_VERSION"
    
    # Extract source
    log_info "Extracting GCC source..."
    tar xf "$GCC_FILE"
    
    # Create build directory
    cd "gcc-$GCC_VERSION"
    mkdir -v build
    cd build
    
    log_info "Build directory prepared"
}

configure_libstdcxx() {
    log_info "Configuring Libstdc++..."
    
    # Configure with options from toolchain-architecture.md
    ../libstdc++-v3/configure \
        --host=$LFS_TGT \
        --build=$(../config.guess) \
        --prefix=/usr \
        --disable-multilib \
        --disable-nls \
        --disable-libstdcxx-pch \
        --with-gxx-include-dir=/tools/$LFS_TGT/include/c++/$GCC_VERSION
        
    if [ $? -ne 0 ]; then
        log_error "Configuration failed"
        return 1
    fi
    
    log_info "Configuration completed successfully"
}

build_libstdcxx() {
    log_info "Building Libstdc++..."
    
    make -j$(nproc)
    
    if [ $? -ne 0 ]; then
        log_error "Build failed"
        return 1
    fi
    
    log_info "Build completed successfully"
}

install_libstdcxx() {
    log_info "Installing Libstdc++..."
    
    make DESTDIR=$LFS install
    
    if [ $? -ne 0 ]; then
        log_error "Installation failed"
        return 1
    fi
    
    log_info "Installation completed successfully"
}

verify_installation() {
    log_info "Verifying installation..."
    local errors=0
    
    # Check for critical files
    local check_files=(
        "$LFS/usr/lib/libstdc++.so"
        "$LFS/usr/lib/libstdc++.a"
        "$LFS/tools/$LFS_TGT/include/c++/$GCC_VERSION/iostream"
        "$LFS/tools/$LFS_TGT/include/c++/$GCC_VERSION/vector"
    )
    
    for file in "${check_files[@]}"; do
        if [ ! -f "$file" ] && [ ! -L "$file" ]; then
            log_error "Critical file missing: $file"
            ((errors++))
        fi
    done
    
    # Test C++ compilation and functionality
    cd "$LFS/sources/gcc-$GCC_VERSION/build"
    cat > test.cpp << "EOF"
#include <iostream>
#include <vector>
int main() {
    std::vector<int> v{1, 2, 3};
    return v.size() == 3 ? 0 : 1;
}
EOF
    
    if ! $LFS_TGT-g++ -std=c++11 test.cpp -o test; then
        log_error "C++ compilation test failed"
        ((errors++))
    else
        # Test execution
        if ! ./test; then
            log_error "C++ functionality test failed"
            ((errors++))
        fi
    fi
    rm -f test.cpp test
    
    # Verify library linkage
    echo 'int main(){}' > test.cpp
    if ! $LFS_TGT-g++ -v test.cpp -o test 2>&1 | grep -q "LIBRARY_PATH=$LFS/usr/lib"; then
        log_error "Library path verification failed"
        ((errors++))
    fi
    rm -f test.cpp test
    
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
        rm -rf "gcc-$GCC_VERSION"
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
    
    log_info "Starting Libstdc++ build..."
    
    # Execute build steps
    verify_environment || exit 1
    download_source || exit 1
    prepare_build || exit 1
    configure_libstdcxx || exit 1
    build_libstdcxx || exit 1
    install_libstdcxx || exit 1
    verify_installation || exit 1
    
    # Cleanup unless --keep-build was specified
    if [ $keep_build -eq 0 ]; then
        cleanup
    else
        cleanup "keep"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "Libstdc++ build completed successfully in ${duration} seconds"
    return 0
}

main "$@"

