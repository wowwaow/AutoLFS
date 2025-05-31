#!/bin/bash
#
# findutils.sh - Findutils Build Script
# LFS Chapter 6 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Builds Findutils as part of the temporary tools

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

# Findutils-specific configuration
TOOL_NAME="findutils"
TOOL_VERSION=$(get_tool_version "$TOOL_NAME")
TOOL_URL=$(get_tool_url "$TOOL_NAME")
TOOL_MD5=$(get_tool_md5 "$TOOL_NAME")
BUILD_DIR="$LFS_SOURCES/${TOOL_NAME}-${TOOL_VERSION}"
TOOL_FILE="${TOOL_NAME}-${TOOL_VERSION}.tar.xz"

# Essential utilities to test
declare -a FIND_UTILS=(
    "find"       # File searching
    "xargs"      # Command building
    "locate"     # Database searching
    "updatedb"   # Database updating
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
    
    log_info "Build preparation completed"
}

configure_build() {
    log_info "Configuring $TOOL_NAME..."
    
    # Configure for cross-compilation
    ./configure \
        --prefix=/usr \
        --localstatedir=/var/lib/locate \
        --host=$LFS_TGT \
        --build=$(build-aux/config.guess)
        
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
    
    # Create locate database directory
    mkdir -pv $LFS/var/lib/locate
    
    log_info "Installation completed successfully"
}

verify_installation() {
    log_info "Verifying $TOOL_NAME installation..."
    local errors=0
    
    # Create test directory
    local test_dir="$LFS_SOURCES/findutils_test"
    mkdir -p "$test_dir"
    cd "$test_dir"
    
    # Test 1: Basic find functionality
    log_info "Testing find..."
    
    # Create test files and directories
    mkdir -p test_dir/subdir
    touch test_dir/file1.txt
    touch test_dir/file2.txt
    touch test_dir/subdir/file3.txt
    chmod 644 test_dir/file1.txt
    
    # Test name-based search
    if ! $LFS/usr/bin/find test_dir -name "file1.txt" | grep -q "file1.txt"; then
        log_error "find name-based search failed"
        ((errors++))
    fi
    
    # Test type-based search
    if ! $LFS/usr/bin/find test_dir -type f | grep -q "file2.txt"; then
        log_error "find type-based search failed"
        ((errors++))
    fi
    
    # Test permission-based search
    if ! $LFS/usr/bin/find test_dir -perm 644 | grep -q "file1.txt"; then
        log_error "find permission-based search failed"
        ((errors++))
    fi
    
    # Test 2: xargs functionality
    log_info "Testing xargs..."
    
    # Create test file list
    echo "file1.txt" > files.txt
    echo "file2.txt" >> files.txt
    
    # Test xargs with echo
    if ! cat files.txt | $LFS/usr/bin/xargs -I{} echo "Found {}" | grep -q "Found file1.txt"; then
        log_error "xargs basic functionality failed"
        ((errors++))
    fi
    
    # Test 3: locate and updatedb
    log_info "Testing locate database functionality..."
    
    # Create and update database
    if ! $LFS/usr/bin/updatedb \
         --output=$LFS/var/lib/locate/locatedb \
         --database-root=$test_dir \
         --prunefs=""; then
        log_error "updatedb failed to create database"
        ((errors++))
    fi
    
    # Test locate
    if [ -f "$LFS/var/lib/locate/locatedb" ]; then
        if ! $LFS/usr/bin/locate -d $LFS/var/lib/locate/locatedb "file1.txt" | grep -q "file1.txt"; then
            log_error "locate search failed"
            ((errors++))
        fi
    else
        log_error "locate database not created"
        ((errors++))
    fi
    
    # Test 4: Complex find operations
    log_info "Testing complex find operations..."
    
    # Test find with -exec
    if ! $LFS/usr/bin/find test_dir -type f -exec echo "Found: {}" \; | grep -q "Found: "; then
        log_error "find with -exec failed"
        ((errors++))
    fi
    
    # Test find with multiple conditions
    touch test_dir/subdir/test.txt
    chmod 755 test_dir/subdir/test.txt
    
    if ! $LFS/usr/bin/find test_dir -type f -perm 755 -name "test.txt" | grep -q "test.txt"; then
        log_error "find with multiple conditions failed"
        ((errors++))
    fi
    
    # Clean up test directory
    cd $LFS_SOURCES
    rm -rf "$test_dir"
    
    # Verify all utilities are present and executable
    for util in "${FIND_UTILS[@]}"; do
        if [ ! -x "$LFS/usr/bin/$util" ]; then
            log_error "Utility missing or not executable: $util"
            ((errors++))
        fi
    done
    
    # Verify database directory
    if [ ! -d "$LFS/var/lib/locate" ]; then
        log_error "Locate database directory missing"
        ((errors++))
    fi
    
    # Verify library dependencies
    for util in "${FIND_UTILS[@]}"; do
        if [ -x "$LFS/usr/bin/$util" ]; then
            if ldd "$LFS/usr/bin/$util" 2>/dev/null | grep -q "/usr/lib"; then
                log_error "Utility $util linked against host system libraries"
                ((errors++))
            fi
        fi
    done
    
    # Verify man pages
    for util in "${FIND_UTILS[@]}"; do
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

