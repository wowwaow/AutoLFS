#!/bin/bash
#
# gcc-pass1.sh - GCC Pass 1 Build Script
# LFS Chapter 5 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Builds the first pass of GCC for the LFS cross-toolchain

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

# Dependencies
GMP_VERSION="6.3.0"
GMP_FILE="gmp-${GMP_VERSION}.tar.xz"
GMP_URL="https://ftp.gnu.org/gnu/gmp/${GMP_FILE}"
GMP_MD5="956dc04e864001a9c22429f761f2c283"

MPFR_VERSION="4.2.1"
MPFR_FILE="mpfr-${MPFR_VERSION}.tar.xz"
MPFR_URL="https://ftp.gnu.org/gnu/mpfr/${MPFR_FILE}"
MPFR_MD5="523c50c6318dde6f9dc523bc0244690a"

MPC_VERSION="1.3.1"
MPC_FILE="mpc-${MPC_VERSION}.tar.gz"
MPC_URL="https://ftp.gnu.org/gnu/mpc/${MPC_FILE}"
MPC_MD5="5c9bc658c9fd0f940e8e3e0f09530c62"

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
    
    # Verify binutils is installed
    if ! command -v "${LFS_TGT}-as" >/dev/null 2>&1; then
        log_error "Binutils (Pass 1) must be installed first"
        return 1
    }
    
    log_info "Environment verified successfully"
}

download_source() {
    local sources_dir="$LFS/sources"
    mkdir -p "$sources_dir"
    
    # Download and verify each component
    local packages=(
        "$GCC_URL:$GCC_FILE:$GCC_MD5"
        "$GMP_URL:$GMP_FILE:$GMP_MD5"
        "$MPFR_URL:$MPFR_FILE:$MPFR_MD5"
        "$MPC_URL:$MPC_FILE:$MPC_MD5"
    )
    
    for package in "${packages[@]}"; do
        IFS=':' read -r url file md5 <<< "$package"
        local file_path="$sources_dir/$file"
        
        if [ ! -f "$file_path" ]; then
            log_info "Downloading $file..."
            wget "$url" -O "$file_path"
        fi
        
        local md5_check=$(md5sum "$file_path" | awk '{print $1}')
        if [ "$md5_check" != "$md5" ]; then
            log_error "MD5 checksum verification failed for $file"
            return 1
        fi
    done
    
    log_info "All source packages verified successfully"
}

prepare_build() {
    cd "$LFS/sources"
    
    # Clean previous build if exists
    rm -rf "gcc-$GCC_VERSION"
    
    # Extract GCC
    log_info "Extracting GCC source..."
    tar xf "$GCC_FILE"
    cd "gcc-$GCC_VERSION"
    
    # Extract dependencies into GCC directory
    log_info "Extracting GCC dependencies..."
    tar xf "../$MPFR_FILE"
    mv "mpfr-$MPFR_VERSION" mpfr
    tar xf "../$GMP_FILE"
    mv "gmp-$GMP_VERSION" gmp
    tar xf "../$MPC_FILE"
    mv "mpc-$MPC_VERSION" mpc
    
    # Create build directory
    mkdir -v build
    cd build
    
    log_info "Build directory prepared"
}

configure_gcc() {
    log_info "Configuring GCC..."
    
    # Configure with options from toolchain-architecture.md
    ../configure \
        --target=$LFS_TGT \
        --prefix=$LFS/tools \
        --with-glibc-version=2.41 \
        --with-sysroot=$LFS \
        --with-newlib \
        --without-headers \
        --enable-default-pie \
        --enable-default-ssp \
        --disable-nls \
        --disable-shared \
        --disable-threads \
        --disable-libatomic \
        --disable-libgomp \
        --disable-libquadmath \
        --disable-libssp \
        --disable-libvtv \
        --disable-libstdcxx \
        --enable-languages=c,c++
        
    if [ $? -ne 0 ]; then
        log_error "Configuration failed"
        return 1
    fi
    
    log_info "Configuration completed successfully"
}

build_gcc() {
    log_info "Building GCC..."
    
    make -j$(nproc)
    
    if [ $? -ne 0 ]; then
        log_error "Build failed"
        return 1
    fi
    
    log_info "Build completed successfully"
}

install_gcc() {
    log_info "Installing GCC..."
    
    make install
    
    if [ $? -ne 0 ]; then
        log_error "Installation failed"
        return 1
    fi
    
    log_info "Installation completed successfully"
    
    # Create full version of limits.h
    log_info "Creating limits.h..."
    cd ..
    cat gcc/limitx.h gcc/glimits.h gcc/limity.h > \
        `dirname $($LFS_TGT-gcc -print-libgcc-file-name)`/install-tools/include/limits.h
}

verify_build() {
    log_info "Verifying build..."
    
    # Check for critical files
    local check_files=(
        "$LFS/tools/bin/${LFS_TGT}-gcc"
        "$LFS/tools/bin/${LFS_TGT}-cpp"
        "$LFS/tools/lib/gcc/${LFS_TGT}/${GCC_VERSION}/include/limits.h"
    )
    
    for file in "${check_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Critical file missing: $file"
            return 1
        fi
    done
    
    # Test cross-compiler functionality
    log_info "Testing cross-compiler..."
    echo 'int main(){}' > dummy.c
    
    if ! $LFS_TGT-gcc dummy.c; then
        log_error "Basic compilation test failed"
        rm -f dummy.c a.out
        return 1
    fi
    
    # Verify the cross-compiler is producing correct output
    readelf -l a.out | grep -q ': /lib'
    if [ $? -eq 0 ]; then
        log_error "Cross-compiler is not producing correct output"
        rm -f dummy.c a.out
        return 1
    fi
    
    rm -f dummy.c a.out
    log_info "Build verification completed successfully"
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
    
    log_info "Starting GCC Pass 1 build..."
    
    # Execute build steps
    verify_environment || exit 1
    download_source || exit 1
    prepare_build || exit 1
    configure_gcc || exit 1
    build_gcc || exit 1
    install_gcc || exit 1
    verify_build || exit 1
    
    # Cleanup unless --keep-build was specified
    if [ $keep_build -eq 0 ]; then
        cleanup
    else
        cleanup "keep"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "GCC Pass 1 build completed successfully in ${duration} seconds"
    return 0
}

main "$@"

