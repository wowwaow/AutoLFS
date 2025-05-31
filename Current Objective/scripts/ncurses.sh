#!/bin/bash
#
# ncurses.sh - Ncurses Build Script
# LFS Chapter 6 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Builds Ncurses as part of the temporary tools

set -e

# Source our environment
SCRIPT_DIR="$(dirname "$0")"
source "${SCRIPT_DIR}/../config/build-environment.conf"
source "${SCRIPT_DIR}/../config/tool-versions.conf"

# Color output setup
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ncurses-specific configuration
TOOL_NAME="ncurses"
TOOL_VERSION=$(get_tool_version "$TOOL_NAME")
TOOL_URL=$(get_tool_url "$TOOL_NAME")
TOOL_MD5=$(get_tool_md5 "$TOOL_NAME")
BUILD_DIR="$LFS_SOURCES/${TOOL_NAME}-${TOOL_VERSION}"
TOOL_FILE="${TOOL_NAME}-${TOOL_VERSION}.tar.gz"

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
    log_info "Verifying build environment..."
    
    # Check required variables
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
    
    # Verify cross-compilation tools
    if ! command -v "$LFS_TGT-gcc" >/dev/null 2>&1; then
        log_error "Cross-compiler not found: $LFS_TGT-gcc"
        return 1
    fi
    
    # Verify build location
    if [ ! -d "$LFS_SOURCES" ]; then
        log_error "Sources directory not found: $LFS_SOURCES"
        return 1
    fi
    
    # Verify we're running as lfs user
    if [ "$(whoami)" != "lfs" ]; then
        log_error "This script must be run as the 'lfs' user"
        return 1
    fi
    
    log_info "Environment verification completed"
}

download_source() {
    cd $LFS_SOURCES
    
    if [ ! -f "$TOOL_FILE" ]; then
        log_info "Downloading $TOOL_NAME..."
        wget "$TOOL_URL" -O "$TOOL_FILE"
    fi
    
    # Verify MD5
    local md5_check=$(md5sum "$TOOL_FILE" | awk '{print $1}')
    if [ "$md5_check" != "$TOOL_MD5" ]; then
        log_error "MD5 checksum verification failed"
        return 1
    fi
    
    log_info "Source package verified successfully"
}

prepare_build() {
    cd $LFS_SOURCES
    
    # Clean previous build if exists
    rm -rf "$BUILD_DIR"
    
    log_info "Extracting $TOOL_NAME..."
    tar xf "$TOOL_FILE"
    
    cd "$BUILD_DIR"
    
    # Ensure all wide-character functions will be built
    sed -i s/mawk// configure
    
    log_info "Build preparation completed"
}

configure_build() {
    log_info "Configuring $TOOL_NAME..."
    
    # Configure for cross-compilation with wide character support
    ./configure \
        --prefix=/usr \
        --host=$LFS_TGT \
        --build=$(./config.guess) \
        --without-debug \
        --without-ada \
        --with-manpage-format=normal \
        --with-shared \
        --without-normal \
        --enable-widec \
        --with-pkg-config-libdir=/usr/lib/pkgconfig
        
    if [ $? -ne 0 ]; then
        log_error "Configuration failed"
        return 1
    fi
    
    log_info "Configuration completed successfully"
}

compile() {
    log_info "Building $TOOL_NAME..."
    
    make $MAKEFLAGS
    
    if [ $? -ne 0 ]; then
        log_error "Build failed"
        return 1
    fi
    
    log_info "Build completed successfully"
}

install() {
    log_info "Installing $TOOL_NAME..."
    
    make DESTDIR=$LFS TIC_PATH=$(pwd)/build/progs/tic install
    
    if [ $? -ne 0 ]; then
        log_error "Installation failed"
        return 1
    fi
    
    # Create necessary symbolic links
    cd $LFS/usr/lib
    ln -sf libncursesw.so libncurses.so
    ln -sf libncursesw.so.6 libncurses.so.6
    
    # Create pkg-config symbolic links
    cd $LFS/usr/lib/pkgconfig
    ln -sf ncursesw.pc ncurses.pc
    ln -sf formw.pc form.pc
    ln -sf menuw.pc menu.pc
    ln -sf panelw.pc panel.pc
    
    log_info "Installation completed successfully"
}

verify_installation() {
    log_info "Verifying $TOOL_NAME installation..."
    local errors=0
    
    # Check for critical files
    local check_files=(
        "$LFS/usr/lib/libncursesw.so"
        "$LFS/usr/lib/libncurses.so"
        "$LFS/usr/include/ncurses.h"
        "$LFS/usr/include/ncursesw"
        "$LFS/usr/lib/pkgconfig/ncurses.pc"
    )
    
    for file in "${check_files[@]}"; do
        if [ ! -e "$file" ]; then
            log_error "Critical file/directory missing: $file"
            ((errors++))
        fi
    done
    
    # Verify wide character support
    cd "$LFS_SOURCES"
    cat > test.c << "EOF"
#include <ncursesw/curses.h>
int main() {
    initscr();
    printw("Hello, World!");
    refresh();
    endwin();
    return 0;
}
EOF
    
    if ! $LFS_TGT-gcc test.c -o test -lncursesw; then
        log_error "Wide character support test compilation failed"
        ((errors++))
    fi
    rm -f test.c test
    
    # Verify library linkage
    if ! readelf -d $LFS/usr/lib/libncursesw.so | grep -q "SONAME.*libncursesw.so.6"; then
        log_error "Library SONAME verification failed"
        ((errors++))
    fi
    
    # Verify pkg-config files
    local pc_files=(
        "ncurses.pc"
        "form.pc"
        "menu.pc"
        "panel.pc"
    )
    
    for pc in "${pc_files[@]}"; do
        if [ ! -L "$LFS/usr/lib/pkgconfig/$pc" ]; then
            log_error "pkg-config file missing: $pc"
            ((errors++))
        fi
    done
    
    # Test terminal database access
    if [ ! -f "$LFS/usr/share/terminfo/l/linux" ]; then
        log_error "Terminal database not properly installed"
        ((errors++))
    fi
    
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
        rm -rf "$BUILD_DIR"
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
    
    log_info "Starting $TOOL_NAME build..."
    
    verify_environment || exit 1
    download_source || exit 1
    prepare_build || exit 1
    configure_build || exit 1
    compile || exit 1
    install || exit 1
    verify_installation || exit 1
    
    # Cleanup unless --keep-build was specified
    if [ $keep_build -eq 0 ]; then
        cleanup
    else
        cleanup "keep"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "$TOOL_NAME build completed successfully in ${duration} seconds"
    return 0
}

main "$@"

