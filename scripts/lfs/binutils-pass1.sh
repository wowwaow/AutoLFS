#!/bin/bash
#===============================================================================
# LFS Build Script Template
# Type: LFS Component Build Script
#===============================================================================
# METADATA_BEGIN
NAME="binutils"
VERSION="2.41"
DESCRIPTION="Binutils Pass 1 - Contains a linker, an assembler, and other tools for handling object files"
CATEGORY="toolchain"
DEPENDENCIES=""
SOURCE_URL="https://ftp.gnu.org/gnu/binutils/binutils-2.41.tar.xz"
MD5SUM="256d7e0ad998e423030c84483a7c1e30"
# METADATA_END
#===============================================================================

set -euo pipefail
IFS=$'\n\t'

#===============================================================================
# Import Wrapper Configuration and Utilities
#===============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Verify and load core configuration
CONFIG_FILE="${WRAPPER_ROOT}/config/core/config.sh"
if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "ERROR: Core configuration file not found: ${CONFIG_FILE}"
    exit 1
fi

# Source configuration file
# shellcheck source=config/core/config.sh
source "${CONFIG_FILE}"

# Verify required environment variables
REQUIRED_VARS=(
    "LOGS_DIR"
    "ARTIFACTS_DIR"
    "TEMP_DIR"
    "DEFAULT_BUILD_OPTS"
    "DEFAULT_MAKEFLAGS"
    "VERIFY_CHECKSUMS"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo "ERROR: Required environment variable not set: ${var}"
        exit 1
    fi
done

#===============================================================================
# Script Configuration
#===============================================================================
# Package configuration
PACKAGE_NAME="${NAME}-${VERSION}"
BUILD_DIR="${LFS}/sources/${PACKAGE_NAME}"
LOG_FILE="${LOGS_DIR}/build/${PACKAGE_NAME}-pass1.log"

# Ensure log directory exists
LOG_DIR="$(dirname "${LOG_FILE}")"
mkdir -p "${LOG_DIR}"

# Binutils Pass 1 specific settings
BUILD_SUBDIR="${BUILD_DIR}/build"
EXTRA_CONFIG_OPTS=(
    --target="${LFS_TGT}"
    --prefix="${LFS}/tools"
    --with-sysroot="${LFS}"
    --disable-nls
    --enable-gprofng=no
    --disable-werror
    --disable-shared
    --disable-multilib
)

#===============================================================================
# Logging Functions
#===============================================================================
log_build() {
    local level=$1
    shift
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [${PACKAGE_NAME}-pass1] ${level}: $*" | tee -a "${LOG_FILE}"
}

info() { log_build "INFO" "$*"; }
warn() { log_build "WARN" "$*"; }
error() { log_build "ERROR" "$*"; }

#===============================================================================
# Error Handling
#===============================================================================
cleanup() {
    local exit_code=$?
    if [[ ${exit_code} -ne 0 ]]; then
        error "Build failed with exit code: ${exit_code}"
    else
        info "Build completed successfully"
    fi
    exit ${exit_code}
}

trap cleanup EXIT
trap 'error "Caught interrupt signal"; exit 1' INT TERM

#===============================================================================
# Build Functions
#===============================================================================
verify_environment() {
    info "Verifying build environment"
    [[ -z "${LFS:-}" ]] && error "LFS environment variable not set" && exit 1
    [[ -z "${LFS_TGT:-}" ]] && error "LFS_TGT not set" && exit 1
    [[ ! -d "${LFS}/sources" ]] && error "LFS sources directory not found" && exit 1
    [[ ! -d "${LFS}/tools" ]] && error "LFS tools directory not found" && exit 1
    
    # Check for existing installation
    if [[ -x "${LFS}/tools/bin/${LFS_TGT}-ld" ]]; then
        info "Found existing binutils installation, cleaning up for reinstallation"
        rm -rf "${LFS}/tools/bin/${LFS_TGT}-"*
        rm -rf "${LFS}/tools/lib/bfd-plugins"
        info "Cleaned up previous binutils installation"
    fi
}

prepare_source() {
    info "Preparing source directory"
    cd "${LFS}/sources"
    
    if [[ ! -f "${PACKAGE_NAME}.tar.xz" ]]; then
        error "Source archive not found: ${PACKAGE_NAME}.tar.xz"
        exit 1
    fi
    
    if [[ "${VERIFY_CHECKSUMS}" == "true" ]]; then
        info "Verifying source package checksum"
        echo "${MD5SUM}  ${PACKAGE_NAME}.tar.xz" | md5sum -c -
    fi
    
    info "Extracting source package"
    rm -rf "${BUILD_DIR}"
    tar xf "${PACKAGE_NAME}.tar.xz"
    
    info "Creating build directory"
    mkdir -p "${BUILD_SUBDIR}"
    cd "${BUILD_SUBDIR}"
}

configure_package() {
    info "Configuring package"
    # Ensure adequate PTY support
    mkdir -pv "${LFS}/tools/etc"
    touch "${LFS}/tools/etc/ld.so.conf"
    
    # Configure with specific options for pass 1
    ../configure \
        "${EXTRA_CONFIG_OPTS[@]}"
}

build_package() {
    info "Building package"
    make "${DEFAULT_MAKEFLAGS}"
}

test_package() {
    if [[ "${LFS_TEST_SUITE}" -eq 1 ]]; then
        info "Running test suite"
        # Note: Testing binutils in pass 1 is not typically done in LFS
        warn "Test suite for binutils pass 1 is not recommended at this stage"
    else
        info "Skipping test suite as per configuration"
    fi
}

install_package() {
    info "Installing package"
    make install
    
    info "Verifying installation"
    if [[ ! -x "${LFS}/tools/bin/${LFS_TGT}-ld" ]]; then
        error "Installation verification failed: ${LFS_TGT}-ld not found"
        exit 1
    fi
}

post_install_checks() {
    info "Running post-installation checks"
    
    # Verify critical files exist
    local check_files=(
        "${LFS}/tools/bin/${LFS_TGT}-ld"
        "${LFS}/tools/bin/${LFS_TGT}-as"
        "${LFS}/tools/bin/${LFS_TGT}-ar"
    )
    
    for file in "${check_files[@]}"; do
        if [[ ! -x "${file}" ]]; then
            error "Critical file missing: ${file}"
            exit 1
        fi
    done
    
    info "All critical files present"
}

#===============================================================================
# Main Build Process
#===============================================================================
main() {
    info "Starting build for ${PACKAGE_NAME} Pass 1"
    info "Target: ${LFS_TGT}"
    info "Prefix: ${LFS}/tools"
    
    verify_environment
    prepare_source
    configure_package
    build_package
    test_package
    install_package
    post_install_checks
    
    info "Binutils Pass 1 build complete"
}

# Execute main function
main "$@"

