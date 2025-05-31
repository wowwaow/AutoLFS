#!/bin/bash
#
# coreutils.sh - Coreutils Build Script
# LFS Chapter 6 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Builds Coreutils as part of the temporary tools

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

# Coreutils-specific configuration
TOOL_NAME="coreutils"
TOOL_VERSION=$(get_tool_version "$TOOL_NAME")
TOOL_URL=$(get_tool_url "$TOOL_NAME")
TOOL_MD5=$(get_tool_md5 "$TOOL_NAME")
BUILD_DIR="$LFS_SOURCES/${TOOL_NAME}-${TOOL_VERSION}"
TOOL_FILE="${TOOL_NAME}-${TOOL_VERSION}.tar.xz"

# Essential utilities to test
declare -a ESSENTIAL_UTILS=(
    "ls" "cp" "mv" "rm"        # File operations
    "cat" "sort" "uniq"        # Text processing
    "mkdir" "rmdir"            # Directory operations
    "chmod" "chown" "touch"    # File attributes
    "ln" "pwd" "basename"      # Path handling
    "uname" "hostname"         # System information
    "echo" "printf" "test"     # Shell utilities
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
    
    # Configure for cross compilation
    autoreconf -fiv
    
    log_info "Build preparation completed"
}

configure_build() {
    log_info "Configuring $TOOL_NAME..."
    
    # Configure for cross-compilation
    ./configure \
        --prefix=/usr \
        --host=$LFS_TGT \
        --build=$(build-aux/config.guess) \
        --enable-install-program=hostname \
        --enable-no-install-program=kill,uptime \
        --without-perl
        
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
    
    make DESTDIR=$LFS install
    
    if [ $? -ne 0 ]; then
        log_error "Installation failed"
        return 1
    fi
    
    # Create essential directories
    mkdir -pv $LFS/usr/bin
    mkdir -pv $LFS/usr/sbin
    mkdir -pv $LFS/usr/share/man/man1
    mkdir -pv $LFS/usr/share/man/man8
    
    log_info "Installation completed successfully"
}

verify_installation() {
    log_info "Verifying $TOOL_NAME installation..."
    local errors=0
    
    # Create test directory
    local test_dir="$LFS_SOURCES/coreutils_test"
    mkdir -p "$test_dir"
    cd "$test_dir"
    
    # Test 1: Basic file operations
    log_info "Testing basic file operations..."
    
    # Create and list files
    touch test_file{1..3}
    if ! $LFS/usr/bin/ls test_file* > /dev/null 2>&1; then
        log_error "ls command failed"
        ((errors++))
    fi
    
    # Copy and move files
    if ! $LFS/usr/bin/cp test_file1 test_file1_copy > /dev/null 2>&1; then
        log_error "cp command failed"
        ((errors++))
    fi
    
    if ! $LFS/usr/bin/mv test_file1_copy test_file1_moved > /dev/null 2>&1; then
        log_error "mv command failed"
        ((errors++))
    fi
    
    # Test 2: Text processing
    log_info "Testing text processing..."
    
    # Create test file
    cat > test_data.txt << "EOF"
apple
banana
apple
cherry
banana
EOF
    
    # Test sort and uniq
    if ! $LFS/usr/bin/sort test_data.txt | $LFS/usr/bin/uniq > sorted_unique.txt; then
        log_error "sort/uniq test failed"
        ((errors++))
    fi
    
    # Verify correct number of unique lines
    if [ "$($LFS/usr/bin/wc -l < sorted_unique.txt)" != "3" ]; then
        log_error "Text processing produced incorrect results"
        ((errors++))
    fi
    
    # Test 3: Directory operations
    log_info "Testing directory operations..."
    
    if ! $LFS/usr/bin/mkdir test_dir && $LFS/usr/bin/rmdir test_dir; then
        log_error "Directory operations failed"
        ((errors++))
    fi
    
    # Test 4: Permission handling
    log_info "Testing permission handling..."
    
    touch test_perms
    if ! $LFS/usr/bin/chmod 644 test_perms; then
        log_error "chmod test failed"
        ((errors++))
    fi
    
    # Test 5: System information
    log_info "Testing system information commands..."
    
    if ! $LFS/usr/bin/uname -a > /dev/null 2>&1; then
        log_error "uname test failed"
        ((errors++))
    fi
    
    if ! $LFS/usr/bin/hostname > /dev/null 2>&1; then
        log_error "hostname test failed"
        ((errors++))
    fi
    
    # Clean up test directory
    cd $LFS_SOURCES
    rm -rf "$test_dir"
    
    # Verify all essential utilities are present and executable
    for util in "${ESSENTIAL_UTILS[@]}"; do
        if [ ! -x "$LFS/usr/bin/$util" ]; then
            log_error "Essential utility missing or not executable: $util"
            ((errors++))
        fi
    done
    
    # Verify library dependencies
    for util in "${ESSENTIAL_UTILS[@]}"; do
        if [ -x "$LFS/usr/bin/$util" ]; then
            if ldd "$LFS/usr/bin/$util" 2>/dev/null | grep -q "/usr/lib"; then
                log_error "Utility $util linked against host system libraries"
                ((errors++))
            fi
        fi
    done
    
    # Verify man pages
    for util in "${ESSENTIAL_UTILS[@]}"; do
        if [ ! -f "$LFS/usr/share/man/man1/$util.1" ]; then
            log_warn "Man page missing for: $util"
        fi
    done
    
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

