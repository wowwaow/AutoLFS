#!/bin/bash
#
# LFS Toolchain Configuration Script
# Configures the toolchain environment and verifies tool versions

# LFS environment setup
export LFS=/mnt/lfs
export LFS_TGT=$(uname -m)-lfs-linux-gnu
export PATH=/tools/bin:/bin:/usr/bin

# Script metadata
SCRIPT_VERSION="1.0"
SCRIPT_PHASE="toolchain"
SCRIPT_DEPENDENCIES="setup-lfs-env"

# Error handling
set -e
trap 'echo "Error on line $LINENO"' ERR

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Version check function
check_version() {
    local program="$1"
    local required="$2"
    local version

    version=$($program --version 2>&1 | head -n1 | awk '{print $NF}')
    if [ -z "$version" ]; then
        log "ERROR: Could not determine $program version"
        return 1
    fi

    if [[ "$version" < "$required" ]]; then
        log "ERROR: $program version $version is less than required version $required"
        return 1
    }

    log "INFO: $program version $version meets minimum requirement $required"
    return 0
}

# Check required tools
verify_tools() {
    log "Verifying required tools"
    
    # Required tool versions
    local REQUIRED_VERSIONS=(
        "bash:5.0"
        "binutils:2.38"
        "bison:3.7"
        "bzip2:1.0.8"
        "gcc:12.2.0"
        "gawk:5.1"
        "grep:3.7"
        "gzip:1.10"
        "make:4.3"
        "patch:2.7"
        "python:3.9"
        "sed:4.8"
        "tar:1.34"
        "texinfo:6.8"
        "xz:5.2"
    )

    for tool in "${REQUIRED_VERSIONS[@]}"; do
        local name="${tool%%:*}"
        local version="${tool#*:}"
        
        if ! check_version "$name" "$version"; then
            return 1
        fi
    done
}

# Configure build flags
configure_build_flags() {
    log "Configuring build flags"
    
    # Set up compiler flags
    export CFLAGS="-O2 -pipe"
    export CXXFLAGS="$CFLAGS"
    
    # Set up linker flags
    export LDFLAGS="-Wl,-rpath,/tools/lib"
    
    # Write flags to config
    cat > $LFS/tools/build-config << EOF
# Build configuration
CFLAGS="$CFLAGS"
CXXFLAGS="$CXXFLAGS"
LDFLAGS="$LDFLAGS"
BUILD_JOBS=$(nproc)
EOF
}

# Set up symbolic links
setup_symlinks() {
    log "Setting up toolchain symlinks"
    
    ln -sf /tools/bin/bash /bin/bash || true
    ln -sf /tools/bin/cat /bin/cat || true
    ln -sf /tools/bin/echo /bin/echo || true
    ln -sf /tools/bin/pwd /bin/pwd || true
    ln -sf /tools/bin/rm /bin/rm || true
    ln -sf /tools/bin/stty /bin/stty || true
}

# Verify configuration
verify_configuration() {
    log "Verifying toolchain configuration"
    
    if [ ! -f "$LFS/tools/build-config" ]; then
        log "ERROR: Build configuration not created"
        return 1
    }
    
    if [ ! -L "/bin/bash" ]; then
        log "ERROR: Essential symlinks not created"
        return 1
    }
}

# Main function
main() {
    log "Starting toolchain configuration"
    verify_tools
    configure_build_flags
    setup_symlinks
    verify_configuration
    log "Toolchain configuration completed"
}

# Execute main function
main "$@"

