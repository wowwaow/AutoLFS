#!/bin/bash

# Configuration Manager
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Handle configuration loading and management

# Configuration defaults
declare -A CONFIG=(
    [parallel_jobs]="4"
    [log_level]="info"
    [work_dir]="/mnt/lfs"
    [test_suite]="enabled"
    [verification]="enabled"
    [keep_work]="false"
    [build_root]="/mnt/lfs"
    [tools_dir]="/tools"
    [sources_dir]="/sources"
    [check_space]="true"
    [verify_checksums]="true"
    [run_tests]="true"
)

# Load YAML configuration
load_config() {
    local config_file=$1
    
    if [ ! -f "$config_file" ]; then
        warn "Configuration file not found: $config_file"
        warn "Using default configuration"
        return 0
    fi
    
    info "Loading configuration from: $config_file"
    
    # Parse YAML file
    while IFS=':' read -r key value; do
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if [ -n "$key" ] && [ -n "$value" ]; then
            CONFIG[$key]="$value"
        fi
    done < "$config_file"
}

# Get configuration value
get_config() {
    local key=$1
    local default=$2
    
    if [ -n "${CONFIG[$key]}" ]; then
        echo "${CONFIG[$key]}"
    else
        echo "$default"
    fi
}

# Set configuration value
set_config() {
    local key=$1
    local value=$2
    
    CONFIG[$key]="$value"
}

# Save configuration
save_config() {
    local config_file=$1
    
    {
        echo "# Build Wrapper Configuration"
        echo "# Generated: $(date -u --iso-8601=seconds)"
        echo
        for key in "${!CONFIG[@]}"; do
            echo "$key: ${CONFIG[$key]}"
        done
    } > "$config_file"
}

# Validate configuration
validate_config() {
    local errors=0
    
    # Check required directories
    for dir in build_root tools_dir sources_dir; do
        if [ ! -d "$(get_config $dir)" ]; then
            error "Required directory not found: $(get_config $dir)"
            ((errors++))
        fi
    done
    
    # Validate numeric values
    if ! [[ "$(get_config parallel_jobs)" =~ ^[0-9]+$ ]]; then
        error "Invalid parallel_jobs value: $(get_config parallel_jobs)"
        ((errors++))
    fi
    
    # Validate boolean values
    for key in test_suite verification keep_work check_space verify_checksums run_tests; do
        value=$(get_config $key)
        if [[ "$value" != "true" && "$value" != "false" ]]; then
            error "Invalid boolean value for $key: $value"
            ((errors++))
        fi
    done
    
    return $errors
}

# Export configuration to environment
export_config() {
    export LFS="$(get_config build_root)"
    export LFS_TGT="$(uname -m)-lfs-linux-gnu"
    export PATH="$(get_config tools_dir)/bin:/bin:/usr/bin"
    export BUILD_WRAPPER_CONFIG="$CONFIG_FILE"
    export BUILD_WRAPPER_JOBS="$(get_config parallel_jobs)"
    export BUILD_WRAPPER_VERBOSE="$VERBOSE"
    export BUILD_WRAPPER_DEBUG="$DEBUG"
    export BUILD_WRAPPER_LOG_LEVEL="$(get_config log_level)"
    export BUILD_WRAPPER_LOG_FILE="build.log"
}

# Import configuration from environment
import_config() {
    if [ -n "$LFS" ]; then
        set_config build_root "$LFS"
    fi
    
    if [ -n "$BUILD_WRAPPER_JOBS" ]; then
        set_config parallel_jobs "$BUILD_WRAPPER_JOBS"
    fi
    
    if [ -n "$BUILD_WRAPPER_LOG_LEVEL" ]; then
        set_config log_level "$BUILD_WRAPPER_LOG_LEVEL"
    fi
}

# Reset configuration to defaults
reset_config() {
    declare -A CONFIG=(
        [parallel_jobs]="4"
        [log_level]="info"
        [work_dir]="/mnt/lfs"
        [test_suite]="enabled"
        [verification]="enabled"
        [keep_work]="false"
        [build_root]="/mnt/lfs"
        [tools_dir]="/tools"
        [sources_dir]="/sources"
        [check_space]="true"
        [verify_checksums]="true"
        [run_tests]="true"
    )
}

