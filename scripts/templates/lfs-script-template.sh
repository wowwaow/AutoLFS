#!/bin/bash
#===============================================================================
# LFS Build Script Template
# Type: LFS Component Build Script
#===============================================================================
# METADATA_BEGIN
NAME=""
VERSION=""
DESCRIPTION=""
CATEGORY="core"
DEPENDENCIES=""
SOURCE_URL=""
MD5SUM=""
# METADATA_END
#===============================================================================

set -euo pipefail
IFS=$'\n\t'

#===============================================================================
# Import Wrapper Configuration and Utilities
#===============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
# shellcheck source=config/core/config.sh
source "${WRAPPER_ROOT}/config/core/config.sh"

#===============================================================================
# Script Configuration
#===============================================================================
PACKAGE_NAME="${NAME}-${VERSION}"
BUILD_DIR="${LFS}/sources/${PACKAGE_NAME}"
LOG_FILE="${LOGS_DIR}/build/${PACKAGE_NAME}.log"

#===============================================================================
# Logging Functions
#===============================================================================
log_build() {
    local level=$1
    shift
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [${PACKAGE_NAME}] ${level}: $*" | tee -a "${LOG_FILE}"
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
}

prepare_source() {
    info "Preparing source directory"
    cd "${LFS}/sources"
    
    if [[ ! -f "${PACKAGE_NAME}.tar.xz" ]]; then
        error "Source archive not found: ${PACKAGE_NAME}.tar.xz"
        exit 1
    fi
    
    if [[ "${VERIFY_CHECKSUMS}" == "true" ]]; then
        echo "${MD5SUM}  ${PACKAGE_NAME}.tar.xz" | md5sum -c -
    fi
    
    rm -rf "${BUILD_DIR}"
    tar xf "${PACKAGE_NAME}.tar.xz"
    cd "${BUILD_DIR}"
}

configure_package() {
    info "Configuring package"
    ./configure \
        --prefix=/usr \
        --build="${LFS_TGT}" \
        "${DEFAULT_BUILD_OPTS[@]}"
}

build_package() {
    info "Building package"
    make "${DEFAULT_MAKEFLAGS}"
}

test_package() {
    if [[ "${LFS_TEST_SUITE}" -eq 1 ]]; then
        info "Running test suite"
        make check
    else
        info "Skipping test suite"
    fi
}

install_package() {
    info "Installing package"
    make DESTDIR="${LFS}" install
}

#===============================================================================
# Main Build Process
#===============================================================================
main() {
    info "Starting build for ${PACKAGE_NAME}"
    
    verify_environment
    prepare_source
    configure_package
    build_package
    test_package
    install_package
    
    info "Build process complete"
}

# Execute main function
main "$@"

