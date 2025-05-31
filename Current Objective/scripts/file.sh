#!/bin/bash
#
# file.sh - File Build Script
# LFS Chapter 6 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Builds File utility as part of the temporary tools

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

# File-specific configuration
TOOL_NAME="file"
TOOL_VERSION=$(get_tool_version "$TOOL_NAME")
TOOL_URL=$(get_tool_url "$TOOL_NAME")
TOOL_MD5=$(get_tool_md5 "$TOOL_NAME")
BUILD_DIR="$LFS_SOURCES/${TOOL_NAME}-${TOOL_VERSION}"
TOOL_FILE="${TOOL_NAME}-${TOOL_VERSION}.tar.gz"

# Critical files to check
declare -a CRITICAL_FILES=(
    "usr/bin/file"                  # Main binary
    "usr/lib/libmagic.so"          # Shared library
    "usr/share/misc/magic.mgc"      # Compiled magic file
    "usr/share/man/man1/file.1"     # Man page
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
        --build=$(./config.guess)
        
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
    local test_dir="$LFS_SOURCES/file_test"
    mkdir -p "$test_dir"
    cd "$test_dir"
    
    # Test 1: Basic file type identification
    log_info "Testing basic file identification..."
    
    # Create test files
    echo '#!/bin/bash' > test.sh
    chmod +x test.sh
    
    echo "Hello, World!" > test.txt
    
    # Test shell script identification
    if ! $LFS/usr/bin/file test.sh | grep -q "shell script"; then
        log_error "Failed to identify shell script"
        ((errors++))
    fi
    
    # Test text file identification
    if ! $LFS/usr/bin/file test.txt | grep -q "ASCII text"; then
        log_error "Failed to identify text file"
        ((errors++))
    fi
    
    # Test 2: Binary file analysis
    log_info "Testing binary file analysis..."
    
    # Create ELF binary
    cat > test.c << "EOF"
int main() { return 0; }
EOF
    
    $LFS_TGT-gcc test.c -o test.bin
    
    if ! $LFS/usr/bin/file test.bin | grep -q "ELF.*executable"; then
        log_error "Failed to identify ELF binary"
        ((errors++))
    fi
    
    # Test 3: Text encoding detection
    log_info "Testing text encoding detection..."
    
    # Create UTF-8 file with BOM
    echo -e '\xEF\xBB\xBFUTF-8 text' > utf8.txt
    
    if ! $LFS/usr/bin/file utf8.txt | grep -q "UTF-8"; then
        log_error "Failed to detect UTF-8 encoding"
        ((errors++))
    fi
    
    # Test 4: Compressed file identification
    log_info "Testing compressed file identification..."
    
    # Create and compress a file
    echo "Test data for compression" > compress_me.txt
    gzip compress_me.txt
    
    if ! $LFS/usr/bin/file compress_me.txt.gz | grep -q "gzip compressed data"; then
        log_error "Failed to identify gzip compressed file"
        ((errors++))
    fi
    
    # Test 5: Magic file functionality
    log_info "Testing magic file functionality..."
    
    # Verify magic file is used correctly
    if ! $LFS/usr/bin/file --version | grep -q "magic file from"; then
        log_error "Magic file information not available"
        ((errors++))
    fi
    
    # Clean up test directory
    cd $LFS_SOURCES
    rm -rf "$test_dir"
    
    # Verify critical files
    for file in "${CRITICAL_FILES[@]}"; do
        if [ ! -e "$LFS/$file" ]; then
            log_error "Critical file missing: $file"
            ((errors++))
        fi
    done
    
    # Verify magic file is compiled and readable
    if [ ! -f "$LFS/usr/share/misc/magic.mgc" ]; then
        log_error "Compiled magic file missing"
        ((errors++))
    elif ! $LFS/usr/bin/file -m "$LFS/usr/share/misc/magic.mgc" test.txt >/dev/null 2>&1; then
        log_error "Compiled magic file not readable"
        ((errors++))
    fi
    
    # Verify library dependencies
    if ldd "$LFS/usr/bin/file" 2>/dev/null | grep -q "/usr/lib"; then
        log_error "Binary linked against host system libraries"
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

