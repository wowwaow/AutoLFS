#!/bin/bash
#
# LFS Script Integration Layer
# Provides standardized interface for LFS build scripts
#
# This wrapper manages the execution of LFS build scripts with:
# - Build sequence management
# - Checkpoint/resume functionality
# - Validation checks
# - Error handling and recovery
# - Logging and monitoring

set -euo pipefail
IFS=$'\n\t'

# Source core functionality
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
CHECKPOINT_DIR="${SCRIPT_DIR}/../../checkpoints"
LOG_DIR="${SCRIPT_DIR}/../../logs"
BUILD_SEQUENCE_FILE="${SCRIPT_DIR}/../../config/build_sequence.conf"
VALIDATION_SCRIPTS_DIR="${SCRIPT_DIR}/../../validation"

# Ensure required directories exist
mkdir -p "${CHECKPOINT_DIR}" "${LOG_DIR}"

# Validation Functions
validate_environment() {
    local chapter="$1"
    local package="$2"
    
    log_info "Validating environment for ${chapter}/${package}"
    
    # Check for required tools
    for tool in gcc make patch gawk; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_error "Required tool not found: ${tool}"
            return 1
        fi
    done
    
    # Validate build directory
    if [ ! -d "$LFS" ]; then
        log_error "LFS build directory not set or doesn't exist"
        return 1
    fi
    
    # Check disk space
    local required_space=10485760  # 10GB in KB
    local available_space
    available_space=$(df -k "$LFS" | awk 'NR==2 {print $4}')
    if [ "${available_space}" -lt "${required_space}" ]; then
        log_error "Insufficient disk space for build"
        return 1
    fi
    
    return 0
}

validate_build_result() {
    local chapter="$1"
    local package="$2"
    
    log_info "Validating build result for ${chapter}/${package}"
    
    # Check if expected binaries/libraries exist
    if [ -f "${VALIDATION_SCRIPTS_DIR}/${chapter}_${package}.validate" ]; then
        source "${VALIDATION_SCRIPTS_DIR}/${chapter}_${package}.validate"
        if ! run_validation_checks; then
            log_error "Build validation failed for ${package}"
            return 1
        fi
    fi
    
    return 0
}

# Checkpoint Management
create_checkpoint() {
    local chapter="$1"
    local package="$2"
    local checkpoint_file="${CHECKPOINT_DIR}/${chapter}_${package}.checkpoint"
    
    log_info "Creating checkpoint for ${chapter}/${package}"
    
    # Save environment state
    env > "${checkpoint_file}.env"
    
    # Save build directory state
    if [ -d "$LFS" ]; then
        tar -czf "${checkpoint_file}.tar.gz" -C "$LFS" .
    fi
    
    # Record package state
    {
        echo "CHAPTER=${chapter}"
        echo "PACKAGE=${package}"
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        echo "BUILD_STATUS=in_progress"
    } > "${checkpoint_file}.state"
    
    log_info "Checkpoint created: ${checkpoint_file}"
}

restore_checkpoint() {
    local chapter="$1"
    local package="$2"
    local checkpoint_file="${CHECKPOINT_DIR}/${chapter}_${package}.checkpoint"
    
    log_info "Restoring checkpoint for ${chapter}/${package}"
    
    if [ ! -f "${checkpoint_file}.state" ]; then
        log_error "Checkpoint not found: ${checkpoint_file}"
        return 1
    fi
    
    # Restore environment
    if [ -f "${checkpoint_file}.env" ]; then
        while IFS='=' read -r key value; do
            export "${key}=${value}"
        done < "${checkpoint_file}.env"
    fi
    
    # Restore build directory state
    if [ -f "${checkpoint_file}.tar.gz" ]; then
        rm -rf "${LFS:?}"/*
        tar -xzf "${checkpoint_file}.tar.gz" -C "$LFS"
    fi
    
    log_info "Checkpoint restored: ${checkpoint_file}"
    return 0
}

# Build Sequence Management
get_build_sequence() {
    local chapter="$1"
    
    if [ ! -f "$BUILD_SEQUENCE_FILE" ]; then
        log_error "Build sequence file not found"
        return 1
    fi
    
    # Extract and return the build sequence for the chapter
    grep "^${chapter}:" "$BUILD_SEQUENCE_FILE" | cut -d: -f2
}

verify_dependencies() {
    local chapter="$1"
    local package="$2"
    
    log_info "Verifying dependencies for ${chapter}/${package}"
    
    # Read package dependencies
    local deps_file="${SCRIPT_DIR}/../../config/dependencies/${chapter}_${package}.deps"
    if [ -f "$deps_file" ]; then
        while IFS= read -r dep; do
            if ! check_package_installed "$dep"; then
                log_error "Required dependency not met: ${dep}"
                return 1
            fi
        done < "$deps_file"
    fi
    
    return 0
}

# Script Execution
execute_lfs_script() {
    local script_path="$1"
    local log_file="${LOG_DIR}/$(basename "$script_path").log"
    
    log_info "Executing script: ${script_path}"
    
    # Execute script with logging
    if ! bash "$script_path" > >(tee -a "$log_file") 2>&1; then
        log_error "Script execution failed: ${script_path}"
        return 1
    fi
    
    return 0
}

# Main Wrapper Function
wrap_lfs_script() {
    local script_path="$1"
    local chapter="$2"
    local package="$3"
    
    log_info "Starting LFS build: ${chapter}/${package}"
    
    # Pre-build validation
    if ! validate_environment "$chapter" "$package"; then
        log_error "Environment validation failed"
        return 1
    fi
    
    # Verify dependencies
    if ! verify_dependencies "$chapter" "$package"; then
        log_error "Dependency verification failed"
        return 1
    fi
    
    # Create checkpoint before build
    create_checkpoint "$chapter" "$package"
    
    # Execute the build script
    if ! execute_lfs_script "$script_path"; then
        log_error "Build failed: ${package}"
        restore_checkpoint "$chapter" "$package"
        return 1
    fi
    
    # Post-build validation
    if ! validate_build_result "$chapter" "$package"; then
        log_error "Build validation failed"
        restore_checkpoint "$chapter" "$package"
        return 1
    fi
    
    # Update build status
    local checkpoint_file="${CHECKPOINT_DIR}/${chapter}_${package}.checkpoint"
    sed -i 's/BUILD_STATUS=.*/BUILD_STATUS=completed/' "${checkpoint_file}.state"
    
    log_info "Completed LFS build: ${chapter}/${package}"
    return 0
}

# Progress Tracking
update_build_progress() {
    local chapter="$1"
    local package="$2"
    local status="$3"
    local progress_file="${LOG_DIR}/build_progress.log"
    
    # Record progress
    {
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        echo "CHAPTER=${chapter}"
        echo "PACKAGE=${package}"
        echo "STATUS=${status}"
    } >> "$progress_file"
}

# Main Build Coordinator
build_chapter() {
    local chapter="$1"
    local sequence
    
    sequence=$(get_build_sequence "$chapter") || return 1
    
    for package in $sequence; do
        local script_path="${SCRIPT_DIR}/../../scripts/${chapter}/${package}.sh"
        
        if [ ! -f "$script_path" ]; then
            log_error "Build script not found: ${script_path}"
            continue
        }
        
        update_build_progress "$chapter" "$package" "starting"
        
        if wrap_lfs_script "$script_path" "$chapter" "$package"; then
            update_build_progress "$chapter" "$package" "completed"
            log_info "Successfully built ${chapter}/${package}"
        else
            update_build_progress "$chapter" "$package" "failed"
            log_error "Failed to build ${chapter}/${package}"
            return 1
        fi
    done
    
    return 0
}

# Error Handling for the Main Script
trap 'log_error "Unexpected error occurred on line $LINENO"' ERR

# Main Script Logic
if [ "$#" -lt 1 ]; then
    log_error "Usage: $0 <chapter> [package]"
    exit 1
fi

CHAPTER="$1"
PACKAGE="${2:-}"

if [ -n "$PACKAGE" ]; then
    # Build single package
    script_path="${SCRIPT_DIR}/../../scripts/${CHAPTER}/${PACKAGE}.sh"
    if wrap_lfs_script "$script_path" "$CHAPTER" "$PACKAGE"; then
        log_info "Successfully built ${CHAPTER}/${PACKAGE}"
        exit 0
    else
        log_error "Failed to build ${CHAPTER}/${PACKAGE}"
        exit 1
    fi
else
    # Build entire chapter
    if build_chapter "$CHAPTER"; then
        log_info "Successfully completed chapter ${CHAPTER}"
        exit 0
    else
        log_error "Failed to complete chapter ${CHAPTER}"
        exit 1
    fi
fi

