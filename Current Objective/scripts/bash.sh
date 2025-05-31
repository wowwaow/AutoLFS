#!/bin/bash
#
# bash.sh - Bash Shell Build Script
# LFS Chapter 6 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Builds Bash as part of the temporary tools

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

# Bash-specific configuration
TOOL_NAME="bash"
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
    
    log_info "Build preparation completed"
}

configure_build() {
    log_info "Configuring $TOOL_NAME..."
    
    # Configure for cross-compilation
    ./configure \
        --prefix=/usr \
        --host=$LFS_TGT \
        --build=$(build-aux/config.guess) \
        --without-bash-malloc \
        --with-installed-readline
        
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
    
    # Create sh symlink
    ln -sfv bash $LFS/bin/sh
    
    log_info "Installation completed successfully"
}

verify_installation() {
    log_info "Verifying $TOOL_NAME installation..."
    local errors=0
    
    # Check for critical files
    local check_files=(
        "$LFS/usr/bin/bash"
        "$LFS/bin/sh"
    )
    
    for file in "${check_files[@]}"; do
        if [ ! -e "$file" ]; then
            log_error "Critical file missing: $file"
            ((errors++))
        fi
    done
    
    # Check symlink
    if [ ! -L "$LFS/bin/sh" ] || [ ! "$(readlink $LFS/bin/sh)" = "bash" ]; then
        log_error "/bin/sh symlink incorrect"
        ((errors++))
    fi
    
    # Check permissions
    if [ ! -x "$LFS/usr/bin/bash" ]; then
        log_error "Bash binary not executable"
        ((errors++))
    fi
    
    # Test basic shell functionality
    cd "$LFS_SOURCES"
    
    # Test 1: Basic variable assignment and echo
    cat > test.sh << "EOF"
#!/bin/bash
TEST_VAR="Hello from Bash"
echo $TEST_VAR
EOF
    chmod +x test.sh
    
    if ! $LFS/usr/bin/bash test.sh | grep -q "Hello from Bash"; then
        log_error "Basic shell script test failed"
        ((errors++))
    fi
    
    # Test 2: Built-in commands
    cat > test2.sh << "EOF"
#!/bin/bash
pwd
cd /
pwd
type ls
EOF
    chmod +x test2.sh
    
    if ! $LFS/usr/bin/bash test2.sh > /dev/null 2>&1; then
        log_error "Built-in commands test failed"
        ((errors++))
    fi
    
    # Test 3: Environment handling
    cat > test3.sh << "EOF"
#!/bin/bash
export TEST_ENV="test_value"
echo $TEST_ENV
env | grep TEST_ENV
EOF
    chmod +x test3.sh
    
    if ! $LFS/usr/bin/bash test3.sh | grep -q "test_value"; then
        log_error "Environment handling test failed"
        ((errors++))
    fi
    
    # Test 4: Script execution with /bin/sh symlink
    cat > test4.sh << "EOF"
#!/bin/sh
echo "Testing sh symlink"
EOF
    chmod +x test4.sh
    
    if ! $LFS/bin/sh test4.sh | grep -q "Testing sh symlink"; then
        log_error "/bin/sh symlink functionality test failed"
        ((errors++))
    fi
    
    # Clean up test files
    rm -f test.sh test2.sh test3.sh test4.sh
    
    # Verify library dependencies
    if ldd "$LFS/usr/bin/bash" | grep -q "/usr/lib"; then
        log_error "Bash binary linked against host system libraries"
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

