#!/bin/bash
#
# LFS Script Integration Module
# Part of the LFS/BLFS Build Scripts Wrapper System
#
# This module handles the integration of LFS build scripts into the wrapper system,
# including script discovery, environment setup, and build coordination.
#
# Dependencies:
# - script-registry.sh
# - build-wrapper.sh
# - config-manager.sh
# - error-handler.sh
# - logging-system.sh
# - progress-tracker.sh

# Source required dependencies
source "$(dirname "${BASH_SOURCE[0]}")/error-handler.sh"
source "$(dirname "${BASH_SOURCE[0]}")/logging-system.sh"
source "$(dirname "${BASH_SOURCE[0]}")/config-manager.sh"
source "$(dirname "${BASH_SOURCE[0]}")/script-registry.sh"
source "$(dirname "${BASH_SOURCE[0]}")/build-wrapper.sh"
source "$(dirname "${BASH_SOURCE[0]}")/progress-tracker.sh"

# LFS-specific constants
LFS_SCRIPT_PATTERNS=("build-*.sh" "setup-*.sh" "configure-*.sh" "install-*.sh")
LFS_REQUIRED_ENV_VARS=("LFS" "LFS_TGT" "PATH")
LFS_BUILD_PHASES=("toolchain" "temp-system" "base-system" "configuration")

# Script discovery and validation
discover_lfs_scripts() {
    local search_dir="$1"
    local script_list=()
    log_info "Starting LFS script discovery in ${search_dir}"

    # Search for scripts matching LFS patterns
    for pattern in "${LFS_SCRIPT_PATTERNS[@]}"; do
        while IFS= read -r -d '' script; do
            if validate_lfs_script "$script"; then
                script_list+=("$script")
                log_debug "Discovered valid LFS script: ${script}"
            fi
        done < <(find "$search_dir" -type f -name "$pattern" -print0)
    done

    # Register discovered scripts
    for script in "${script_list[@]}"; do
        register_script "$script" "lfs" || {
            log_error "Failed to register script: ${script}"
            return 1
        }
    done

    log_info "Completed LFS script discovery. Found ${#script_list[@]} scripts"
    return 0
}

# Script validation
validate_lfs_script() {
    local script="$1"
    log_debug "Validating LFS script: ${script}"

    # Check for required shebang
    if ! grep -q '^#!/bin/bash' "$script"; then
        log_warning "Script ${script} missing proper shebang"
        return 1
    }

    # Check for basic LFS script structure
    if ! grep -q 'LFS=' "$script" && ! grep -q 'LFS_TGT=' "$script"; then
        log_warning "Script ${script} missing LFS environment variables"
        return 1
    }

    # Verify script permissions
    if [[ ! -x "$script" ]]; then
        log_warning "Script ${script} not executable"
        return 1
    }

    return 0
}

# Environment setup
setup_lfs_environment() {
    log_info "Setting up LFS build environment"

    # Verify required environment variables
    for var in "${LFS_REQUIRED_ENV_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Required environment variable ${var} not set"
            return 1
        fi
    done

    # Load LFS configuration
    local config_file
    config_file="$(get_config_path)/lfs.conf"
    if ! load_config "$config_file"; then
        log_error "Failed to load LFS configuration from ${config_file}"
        return 1
    }

    # Set up build directory structure
    local build_root
    build_root="$(get_config_value "LFS_BUILD_ROOT")"
    mkdir -p "${build_root}"/{sources,tools,build-logs} || {
        log_error "Failed to create LFS build directory structure"
        return 1
    }

    log_info "LFS environment setup completed"
    return 0
}

# Build coordination
coordinate_lfs_build() {
    local phase="$1"
    log_info "Starting LFS build coordination for phase: ${phase}"

    # Verify phase is valid
    if [[ ! " ${LFS_BUILD_PHASES[*]} " =~ ${phase} ]]; then
        log_error "Invalid build phase: ${phase}"
        return 1
    }

    # Get scripts for this phase
    local phase_scripts
    phase_scripts="$(get_phase_scripts "$phase")" || {
        log_error "Failed to get scripts for phase: ${phase}"
        return 1
    }

    # Execute scripts in order
    local status=0
    for script in $phase_scripts; do
        log_info "Executing script: ${script}"
        
        # Start progress tracking
        start_progress_tracking "$script"

        # Execute through build wrapper
        if ! execute_build_script "$script"; then
            log_error "Failed to execute script: ${script}"
            status=1
            break
        fi

        # Update progress
        update_build_progress "$script" "completed"
    done

    return $status
}

# Script execution wrapper
execute_lfs_script() {
    local script="$1"
    shift
    local args=("$@")

    log_info "Executing LFS script: ${script}"

    # Verify script exists and is registered
    if ! is_script_registered "$script"; then
        log_error "Script not registered: ${script}"
        return 1
    }

    # Set up script-specific environment
    local script_env
    script_env="$(get_script_environment "$script")" || {
        log_error "Failed to get environment for script: ${script}"
        return 1
    }

    # Execute with error handling
    if ! (
        eval "$script_env"
        execute_with_error_handling "$script" "${args[@]}"
    ); then
        log_error "Script execution failed: ${script}"
        return 1
    fi

    log_info "Successfully executed script: ${script}"
    return 0
}

# Dependency resolution
resolve_lfs_dependencies() {
    local script="$1"
    log_info "Resolving dependencies for script: ${script}"

    # Get script dependencies
    local deps
    deps="$(get_script_dependencies "$script")" || {
        log_error "Failed to get dependencies for script: ${script}"
        return 1
    }

    # Verify all dependencies are available
    local missing_deps=()
    for dep in $deps; do
        if ! is_script_registered "$dep"; then
            missing_deps+=("$dep")
        fi
    done

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies for ${script}: ${missing_deps[*]}"
        return 1
    fi

    return 0
}

# Progress tracking
track_lfs_progress() {
    local phase="$1"
    local script="$2"
    local status="$3"

    log_debug "Updating progress for ${script} in phase ${phase}: ${status}"

    # Update progress tracking
    update_progress "$phase" "$script" "$status" || {
        log_warning "Failed to update progress tracking"
        return 1
    }

    return 0
}

# Main integration function
integrate_lfs_scripts() {
    local scripts_dir="$1"
    log_info "Starting LFS script integration from: ${scripts_dir}"

    # Discover and register scripts
    if ! discover_lfs_scripts "$scripts_dir"; then
        log_error "Script discovery failed"
        return 1
    }

    # Set up environment
    if ! setup_lfs_environment; then
        log_error "Environment setup failed"
        return 1
    }

    # Initialize progress tracking
    if ! initialize_progress_tracking "lfs"; then
        log_error "Failed to initialize progress tracking"
        return 1
    }

    log_info "LFS script integration completed successfully"
    return 0
}

# Export functions
export -f discover_lfs_scripts
export -f validate_lfs_script
export -f setup_lfs_environment
export -f coordinate_lfs_build
export -f execute_lfs_script
export -f resolve_lfs_dependencies
export -f track_lfs_progress
export -f integrate_lfs_scripts

