#!/bin/bash
#===============================================================================
# LFS/BLFS Build Environment Initialization Script
# Description: Sets up the build environment for LFS/BLFS builds
# Version: 0.1.0
#===============================================================================

set -euo pipefail
IFS=$'\n\t'

#===============================================================================
# Script Setup
#===============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Load core configuration
CONFIG_FILE="${WRAPPER_ROOT}/config/core/config.sh"
if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "ERROR: Core configuration file not found: ${CONFIG_FILE}"
    exit 1
fi

source "${CONFIG_FILE}"

#===============================================================================
# Utility Functions
#===============================================================================
info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
error() { echo "[ERROR] $*"; exit 1; }

create_directory() {
    local dir=$1
    local mode=${2:-${DEFAULT_DIR_MODE}}
    
    if [[ ! -d "${dir}" ]]; then
        mkdir -p "${dir}"
        chmod "${mode}" "${dir}"
        info "Created directory: ${dir}"
    else
        chmod "${mode}" "${dir}"
        info "Directory exists: ${dir}"
    fi
}

#===============================================================================
# Environment Setup
#===============================================================================
setup_system_directories() {
    info "Setting up system directories..."
    
    # Create system directories with proper permissions
    local system_dirs=(
        "${LOGS_DIR}"
        "${ARTIFACTS_DIR}"
        "${TEMP_DIR}"
        "${CONFIG_DIR}"
        "${SCRIPTS_DIR}"
        "${LOGS_DIR}/system"
        "${LOGS_DIR}/build"
        "${LOGS_DIR}/error"
        "${ARTIFACTS_DIR}/state"
        "${ARTIFACTS_DIR}/failed"
    )
    
    for dir in "${system_dirs[@]}"; do
        create_directory "${dir}"
    done
}

setup_lfs_directories() {
    info "Setting up LFS directories..."
    
    # Create LFS directories
    create_directory "${LFS}"
    create_directory "${LFS}/sources"
    create_directory "${LFS}/tools"
    create_directory "${LFS}/tools/bin"
    create_directory "${LFS}/tools/lib"
    create_directory "${LFS}/tools/include"
    
    # Set permissions
    chmod -R u+rwx,g+rx-w,o+rx-w "${LFS}/tools"
    info "Set permissions for LFS tools directory"
}

setup_build_environment() {
    info "Setting up build environment..."
    
    # Export critical environment variables
    export LFS="${LFS:-/mnt/lfs}"
    export LFS_TGT="${LFS_TGT:-$(uname -m)-lfs-linux-gnu}"
    export PATH="${LFS}/tools/bin:/bin:/usr/bin"
    export CONFIG_SITE="${LFS}/usr/share/config.site"
    export LC_ALL=POSIX
    
    # Set up build flags
    export MAKEFLAGS="${DEFAULT_MAKEFLAGS}"
    export CFLAGS="${DEFAULT_CFLAGS}"
    export CXXFLAGS="${DEFAULT_CXXFLAGS}"
    
    info "Environment variables set:"
    echo "  LFS=${LFS}"
    echo "  LFS_TGT=${LFS_TGT}"
    echo "  PATH=${PATH}"
    echo "  MAKEFLAGS=${MAKEFLAGS}"
}

verify_environment() {
    info "Verifying environment setup..."
    
    # Check required commands
    local required_commands=(gcc make ld as ar)
    for cmd in "${required_commands[@]}"; do
        if ! command -v "${cmd}" >/dev/null 2>&1; then
            error "Required command not found: ${cmd}"
        fi
    done
    
    # Check critical directories
    [[ ! -d "${LFS}" ]] && error "LFS directory not found: ${LFS}"
    [[ ! -w "${LFS}" ]] && error "LFS directory not writable: ${LFS}"
    [[ ! -d "${LFS}/tools" ]] && error "LFS tools directory not found: ${LFS}/tools"
    
    # Check environment variables
    [[ -z "${LFS_TGT:-}" ]] && error "LFS_TGT not set"
    [[ -z "${MAKEFLAGS:-}" ]] && error "MAKEFLAGS not set"
    
    info "Environment verification complete"
}

create_build_user() {
    info "Checking build user setup..."
    
    if ! id -u "${BUILD_USER}" >/dev/null 2>&1; then
        if [[ ${EUID} -eq 0 ]]; then
            groupadd "${BUILD_GROUP}"
            useradd -s /bin/bash -g "${BUILD_GROUP}" -m -k /dev/null "${BUILD_USER}"
            info "Created build user: ${BUILD_USER}"
        else
            warn "Not running as root, skipping build user creation"
            warn "Some operations may fail without proper user setup"
        fi
    else
        info "Build user already exists: ${BUILD_USER}"
    fi
}

#===============================================================================
# Main Execution
#===============================================================================
main() {
    info "Initializing build environment..."
    
    # Create directory structure
    setup_system_directories
    
    # Set up LFS environment
    setup_lfs_directories
    
    # Initialize build environment
    setup_build_environment
    
    # Create build user if needed
    create_build_user
    
    # Verify setup
    verify_environment
    
    info "Build environment initialization complete"
    info "You can now proceed with building LFS packages"
}

# Execute main function
main "$@"

