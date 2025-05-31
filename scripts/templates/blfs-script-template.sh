#!/bin/bash
#===============================================================================
# BLFS Build Script Template
# Type: BLFS Package Build Script
#===============================================================================
# METADATA_BEGIN
NAME=""
VERSION=""
DESCRIPTION=""
CATEGORY=""
DEPENDENCIES=""
SOURCE_URL=""
MD5SUM=""
REQUIRES_X11="false"
REQUIRES_SYSTEMD="false"
REQUIRES_PAM="false"
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
BUILD_DIR="/tmp/blfs-build/${PACKAGE_NAME}"
INSTALL_DIR="/usr"
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
        # Preserve build directory for investigation if build failed
        warn "Build directory preserved at: ${BUILD_DIR}"
    else
        info "Build completed successfully"
        # Clean up build directory on success
        rm -rf "${BUILD_DIR}"
    fi
    exit ${exit_code}
}

trap cleanup EXIT
trap 'error "Caught interrupt signal"; exit 1' INT TERM

#===============================================================================
# Dependency Functions
#===============================================================================
check_dependencies() {
    info "Checking dependencies"
    local missing_deps=()
    
    # Split dependencies string into array
    IFS=',' read -ra DEPS <<< "${DEPENDENCIES}"
    
    for dep in "${DEPS[@]}"; do
        if ! command -v "${dep}" >/dev/null 2>&1; then
            missing_deps+=("${dep}")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

verify_system_requirements() {
    info "Verifying system requirements"
    
    # Check X11 if required
    if [[ "${REQUIRES_X11}" == "true" ]]; then
        [[ ! -d "/usr/include/X11" ]] && error "X11 development files not found" && exit 1
    fi
    
    # Check systemd if required
    if [[ "${REQUIRES_SYSTEMD}" == "true" ]]; then
        [[ ! -d "/usr/lib/systemd" ]] && error "systemd not found" && exit 1
    fi
    
    # Check PAM if required
    if [[ "${REQUIRES_PAM}" == "true" ]]; then
        [[ ! -d "/etc/pam.d" ]] && error "PAM not found" && exit 1
    fi
}

#===============================================================================
# Build Functions
#===============================================================================
prepare_source() {
    info "Preparing source directory"
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"
    
    if [[ ! -f "/sources/${PACKAGE_NAME}.tar.xz" ]]; then
        wget -c "${SOURCE_URL}"
        if [[ "${VERIFY_CHECKSUMS}" == "true" ]]; then
            echo "${MD5SUM}  ${PACKAGE_NAME}.tar.xz" | md5sum -c -
        fi
    else
        cp "/sources/${PACKAGE_NAME}.tar.xz" .
    fi
    
    tar xf "${PACKAGE_NAME}.tar.xz"
    cd "${PACKAGE_NAME}"
}

configure_package() {
    info "Configuring package"
    ./configure \
        --prefix="${INSTALL_DIR}" \
        --sysconfdir=/etc \
        --localstatedir=/var \
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
    make install
    
    # Run ldconfig if installing libraries
    if [[ -d "${INSTALL_DIR}/lib" || -d "${INSTALL_DIR}/lib64" ]]; then
        ldconfig
    fi
}

post_install() {
    info "Running post-installation tasks"
    
    # Update desktop database if installing desktop files
    if [[ -d "${INSTALL_DIR}/share/applications" ]]; then
        update-desktop-database
    fi
    
    # Update icon cache if installing icons
    if [[ -d "${INSTALL_DIR}/share/icons" ]]; then
        gtk-update-icon-cache -f -t "${INSTALL_DIR}/share/icons/hicolor"
    fi
    
    # Install systemd service if provided
    if [[ -f "systemd/${NAME}.service" ]]; then
        cp "systemd/${NAME}.service" "/usr/lib/systemd/system/"
        systemctl daemon-reload
    fi
}

#===============================================================================
# Main Build Process
#===============================================================================
main() {
    info "Starting build for ${PACKAGE_NAME}"
    
    check_dependencies
    verify_system_requirements
    prepare_source
    configure_package
    build_package
    test_package
    install_package
    post_install
    
    info "Build process complete"
}

# Execute main function
main "$@"

