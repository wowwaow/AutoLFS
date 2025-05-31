#!/bin/bash
#
# diffutils.sh - Diffutils Build Script
# LFS Chapter 6 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Builds Diffutils as part of the temporary tools

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

# Diffutils-specific configuration
TOOL_NAME="diffutils"
TOOL_VERSION=$(get_tool_version "$TOOL_NAME")
TOOL_URL=$(get_tool_url "$TOOL_NAME")
TOOL_MD5=$(get_tool_md5 "$TOOL_NAME")
BUILD_DIR="$LFS_SOURCES/${TOOL_NAME}-${TOOL_VERSION}"
TOOL_FILE="${TOOL_NAME}-${TOOL_VERSION}.tar.xz"

# Essential utilities to test
declare -a DIFF_UTILS=(
    "diff"    # Basic file comparison
    "cmp"     # Binary file comparison
    "diff3"   # Three-way file comparison
    "sdiff"   # Side-by-side comparison
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
        --host=$LFS_TGT \
        --build=$(./build-aux/config.guess)
        
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
    
    log_info "Installation completed successfully"
}

verify_installation() {
    log_info "Verifying $TOOL_NAME installation..."
    local errors=0
    
    # Create test directory
    local test_dir="$LFS_SOURCES/diffutils_test"
    mkdir -p "$test_dir"
    cd "$test_dir"
    
    # Test 1: Basic diff functionality
    log_info "Testing diff..."
    
    # Create test files
    cat > file1.txt << "EOF"
line 1
line 2
line 3
EOF

    cat > file2.txt << "EOF"
line 1
modified line
line 3
EOF

    # Test diff command
    if ! $LFS/usr/bin/diff file1.txt file2.txt > diff_output 2>/dev/null; then
        # diff should return non-zero for different files
        if [ ! -s diff_output ]; then
            log_error "diff command failed to detect differences"
            ((errors++))
        fi
    fi
    
    # Test 2: Binary comparison with cmp
    log_info "Testing cmp..."
    
    # Create binary test files
    dd if=/dev/urandom of=bin1 bs=1024 count=1 2>/dev/null
    cp bin1 bin2
    echo "modified" >> bin2
    
    if ! $LFS/usr/bin/cmp bin1 bin2 >/dev/null 2>&1; then
        # cmp should return non-zero for different files
        if [ $? -eq 0 ]; then
            log_error "cmp command failed to detect differences"
            ((errors++))
        fi
    fi
    
    # Test 3: Three-way diff
    log_info "Testing diff3..."
    
    # Create three variants of a file
    cat > orig.txt << "EOF"
This is the original line.
Common line 1.
Common line 2.
EOF

    cat > mod1.txt << "EOF"
This is the modified line 1.
Common line 1.
Common line 2.
EOF

    cat > mod2.txt << "EOF"
This is the modified line 2.
Common line 1.
Common line 2.
EOF

    if ! $LFS/usr/bin/diff3 mod1.txt orig.txt mod2.txt > diff3_output 2>/dev/null; then
        if [ ! -s diff3_output ]; then
            log_error "diff3 command failed to detect differences"
            ((errors++))
        fi
    fi
    
    # Test 4: Side-by-side comparison
    log_info "Testing sdiff..."
    
    if ! $LFS/usr/bin/sdiff file1.txt file2.txt > sdiff_output 2>/dev/null; then
        if [ ! -s sdiff_output ]; then
            log_error "sdiff command failed to generate output"
            ((errors++))
        fi
    fi
    
    # Clean up test directory
    cd $LFS_SOURCES
    rm -rf "$test_dir"
    
    # Verify all utilities are present and executable
    for util in "${DIFF_UTILS[@]}"; do
        if [ ! -x "$LFS/usr/bin/$util" ]; then
            log_error "Utility missing or not executable: $util"
            ((errors++))
        fi
    done
    
    # Verify library dependencies
    for util in "${DIFF_UTILS[@]}"; do
        if [ -x "$LFS/usr/bin/$util" ]; then
            if ldd "$LFS/usr/bin/$util" 2>/dev/null | grep -q "/usr/lib"; then
                log_error "Utility $util linked against host system libraries"
                ((errors++))
            fi
        fi
    done
    
    # Verify man pages
    for util in "${DIFF_UTILS[@]}"; do
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

