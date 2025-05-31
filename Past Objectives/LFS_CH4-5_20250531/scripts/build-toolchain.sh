#!/bin/bash
#
# build-toolchain.sh - Master Cross-Toolchain Build Script
# LFS Chapter 5 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Coordinates the building of the complete LFS cross-toolchain

set -e

# Source our environment
source "$(dirname "$0")/../config/build-environment.conf"

# Script locations
SCRIPTS_DIR="$(dirname "$0")"
BUILD_LOG="$LFS/sources/build-toolchain.log"
STATE_FILE="$LFS/sources/build-state.json"

# Color output setup
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Build components in order
declare -A COMPONENTS=(
    ["binutils-pass1"]="Binutils Pass 1"
    ["gcc-pass1"]="GCC Pass 1"
    ["linux-api-headers"]="Linux API Headers"
    ["glibc"]="Glibc"
    ["libstdcxx"]="Libstdc++"
)

# Initialize or load build state
init_state() {
    if [ -f "$STATE_FILE" ]; then
        log_info "Resuming from previous build state"
    else
        echo '{
            "status": "initialized",
            "current_component": "",
            "completed": [],
            "start_time": "",
            "last_updated": ""
        }' > "$STATE_FILE"
    fi
}

save_state() {
    local status="$1"
    local component="$2"
    echo '{
        "status": "'"$status"'",
        "current_component": "'"$component"'",
        "completed": ["'"$(join_by '","' "${completed_components[@]}")"'"],
        "last_updated": "'"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'"
    }' > "$STATE_FILE"
}

join_by() {
    local IFS="$1"
    shift
    echo "$*"
}

log_info() {
    local msg="[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [INFO] $1"
    echo -e "${GREEN}$msg${NC}"
    echo "$msg" >> "$BUILD_LOG"
}

log_warn() {
    local msg="[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [WARN] $1"
    echo -e "${YELLOW}$msg${NC}"
    echo "$msg" >> "$BUILD_LOG"
}

log_error() {
    local msg="[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [ERROR] $1"
    echo -e "${RED}$msg${NC}"
    echo "$msg" >> "$BUILD_LOG"
}

log_progress() {
    local msg="[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [PROGRESS] $1"
    echo -e "${BLUE}$msg${NC}"
    echo "$msg" >> "$BUILD_LOG"
}

verify_environment() {
    log_info "Verifying build environment..."
    
    # Verify required variables
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
    
    # Verify LFS directory exists
    if [ ! -d "$LFS" ]; then
        log_error "LFS directory $LFS does not exist"
        return 1
    fi
    
    # Verify we're running as lfs user
    if [ "$(whoami)" != "lfs" ]; then
        log_error "This script must be run as the 'lfs' user"
        return 1
    fi
    
    # Verify all component scripts exist
    for component in "${!COMPONENTS[@]}"; do
        if [ ! -f "$SCRIPTS_DIR/${component}.sh" ]; then
            log_error "Component script missing: ${component}.sh"
            return 1
        fi
        if [ ! -x "$SCRIPTS_DIR/${component}.sh" ]; then
            log_error "Component script not executable: ${component}.sh"
            return 1
        fi
    done
    
    log_info "Environment verification completed"
    return 0
}

build_component() {
    local component="$1"
    local description="${COMPONENTS[$component]}"
    local script="$SCRIPTS_DIR/${component}.sh"
    
    log_progress "Building $description..."
    
    if [ -n "$RESUME" ] && [[ " ${completed_components[@]} " =~ " ${component} " ]]; then
        log_info "Skipping $description (already completed)"
        return 0
    fi
    
    save_state "building" "$component"
    
    if ! "$script"; then
        log_error "Failed to build $description"
        return 1
    fi
    
    completed_components+=("$component")
    save_state "completed" "$component"
    log_progress "$description completed successfully"
    return 0
}

verify_toolchain() {
    log_info "Verifying complete toolchain..."
    local errors=0
    
    # Verify all critical executables
    local check_executables=(
        "$LFS/tools/bin/$LFS_TGT-gcc"
        "$LFS/tools/bin/$LFS_TGT-ld"
        "$LFS/tools/bin/$LFS_TGT-as"
    )
    
    for exec in "${check_executables[@]}"; do
        if [ ! -x "$exec" ]; then
            log_error "Critical executable missing: $exec"
            ((errors++))
        fi
    done
    
    # Verify critical libraries
    local check_libraries=(
        "$LFS/usr/lib/libc.so"
        "$LFS/usr/lib/libstdc++.so"
    )
    
    for lib in "${check_libraries[@]}"; do
        if [ ! -f "$lib" ] && [ ! -L "$lib" ]; then
            log_error "Critical library missing: $lib"
            ((errors++))
        fi
    done
    
    # Test cross-compilation capability
    log_info "Testing cross-compilation capability..."
    
    cd "$LFS/sources"
    cat > test.c << "EOF"
#include <stdio.h>
int main() {
    printf("Hello from LFS!\n");
    return 0;
}
EOF
    
    if ! $LFS_TGT-gcc test.c -o test; then
        log_error "Cross-compilation test failed"
        ((errors++))
    else
        log_info "Cross-compilation test successful"
    fi
    rm -f test.c test
    
    if [ "$errors" -eq 0 ]; then
        log_info "Toolchain verification completed successfully"
        return 0
    else
        log_error "Toolchain verification failed with $errors errors"
        return 1
    fi
}

cleanup() {
    if [ "$1" != "keep" ]; then
        log_info "Cleaning up build artifacts..."
        # Add cleanup tasks here if needed
    fi
}

show_help() {
    echo "Usage: $0 [OPTIONS] [COMPONENT]"
    echo
    echo "Options:"
    echo "  --help              Show this help message"
    echo "  --resume           Resume from last successful build"
    echo "  --keep-build       Keep build directories after completion"
    echo "  --component NAME    Build only specified component"
    echo
    echo "Components:"
    for component in "${!COMPONENTS[@]}"; do
        echo "  $component - ${COMPONENTS[$component]}"
    done
}

main() {
    local start_time=$(date +%s)
    local keep_build=0
    local specific_component=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_help
                exit 0
                ;;
            --resume)
                RESUME=1
                shift
                ;;
            --keep-build)
                keep_build=1
                shift
                ;;
            --component)
                specific_component="$2"
                if [ -z "$specific_component" ] || [ ! -v "COMPONENTS[$specific_component]" ]; then
                    log_error "Invalid or missing component name"
                    show_help
                    exit 1
                fi
                shift 2
                ;;
            *)
                log_error "Unknown argument: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Initialize build state
    init_state
    declare -a completed_components=()
    
    log_info "Starting toolchain build..."
    
    # Verify environment
    verify_environment || exit 1
    
    if [ -n "$specific_component" ]; then
        # Build single component
        build_component "$specific_component" || exit 1
    else
        # Build all components in order
        for component in "${!COMPONENTS[@]}"; do
            build_component "$component" || exit 1
        done
        
        # Verify complete toolchain
        verify_toolchain || exit 1
    fi
    
    # Cleanup unless --keep-build was specified
    if [ $keep_build -eq 0 ]; then
        cleanup
    else
        cleanup "keep"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "Toolchain build completed successfully in ${duration} seconds"
    return 0
}

main "$@"

