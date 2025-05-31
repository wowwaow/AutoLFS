#!/bin/bash
#
# LFS GCC First Pass Build Script
# This script handles the first pass of GCC compilation in the LFS build process

# LFS environment setup
export LFS=/mnt/lfs
export LFS_TGT=$(uname -m)-lfs-linux-gnu
export PATH=/tools/bin:/bin:/usr/bin

# Script metadata
SCRIPT_VERSION="1.0"
SCRIPT_PHASE="toolchain"
SCRIPT_DEPENDENCIES="binutils-pass1"

# Error handling
set -e
trap 'echo "Error on line $LINENO"' ERR

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Verify environment
verify_environment() {
    if [ -z "$LFS" ]; then
        log "ERROR: LFS environment variable not set"
        exit 1
    fi
    if [ -z "$LFS_TGT" ]; then
        log "ERROR: LFS_TGT not set"
        exit 1
    fi
}

# Download and verify source
prepare_source() {
    log "Preparing GCC source"
    cd $LFS/sources
    test -f gcc-12.2.0.tar.xz || {
        log "ERROR: GCC source not found"
        exit 1
    }
}

# Configure GCC
configure_gcc() {
    log "Configuring GCC"
    mkdir -p build
    cd build
    ../configure                  \
        --target=$LFS_TGT        \
        --prefix=/tools          \
        --with-glibc-version=2.37 \
        --with-sysroot=$LFS      \
        --with-newlib            \
        --without-headers        \
        --enable-default-pie     \
        --enable-default-ssp     \
        --disable-nls            \
        --disable-shared         \
        --disable-multilib       \
        --disable-threads        \
        --disable-libatomic      \
        --disable-libgomp        \
        --disable-libquadmath    \
        --disable-libssp         \
        --disable-libvtv         \
        --disable-libstdcxx      \
        --enable-languages=c,c++
}

# Build GCC
build_gcc() {
    log "Building GCC"
    make -j$(nproc)
}

# Install GCC
install_gcc() {
    log "Installing GCC"
    make install
}

# Main function
main() {
    log "Starting GCC first pass build"
    verify_environment
    prepare_source
    configure_gcc
    build_gcc
    install_gcc
    log "GCC first pass build completed"
}

# Execute main function
main "$@"

