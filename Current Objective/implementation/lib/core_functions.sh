#!/bin/bash
# Core Functions Library for LFS Build Wrapper System
# Version: 1.0.0
# Created: 2025-05-31
# Description: Provides core functionality for configuration, logging, and error handling

# Ensure we're running with bash
if [ -z "$BASH_VERSION" ]; then
    echo "Error: This script requires bash" >&2
    exit 1
fi

# Script initialization
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Global configuration
declare -A CONFIG
declare -A ENV_VARS
declare -A STATE

# Log levels
declare -r LOG_DEBUG=0
declare -r LOG_INFO=1
declare -r LOG_WARN=2
declare -r LOG_ERROR=3
declare -r LOG_FATAL=4

# Current log level (default: INFO)
CURRENT_LOG_LEVEL=$LOG_INFO

#######################################
# Configuration Management Functions
#######################################

function load_config() {
    # Purpose: Loads configuration following the hierarchy defined in system design
    # Arguments: None
    # Returns: 0 on success, 1 on failure
    local -r system_config="${WRAPPER_ROOT}/config/system.conf"
    local -r user_config="${WRAPPER_ROOT}/config/user.conf"
    local -r build_config="${WRAPPER_ROOT}/config/build.conf"

    # Load system defaults
    if [[ -f "${system_config}" ]]; then
        source "${system_config}"
    else
        log_error "System configuration not found: ${system_config}"
        return 1
    fi

    # Load user configuration if exists
    if [[ -f "${user_config}" ]]; then
        source "${user_config}"
    fi

    # Load build-specific configuration if exists
    if [[ -f "${build_config}" ]]; then
        source "${build_config}"
    fi

    validate_config || return 1
    return 0
}

function validate_config() {
    # Purpose: Validates the loaded configuration
    # Arguments: None
    # Returns: 0 if valid, 1 if invalid
    local required_vars=("LFS_BASE" "BUILD_DIR" "LOG_DIR")
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${CONFIG[$var]:-}" ]]; then
            log_error "Required configuration variable missing: ${var}"
            return 1
        fi
    done
    return 0
}

function get_config() {
    # Purpose: Retrieves a configuration value
    # Arguments:
    #   $1 - Configuration key
    #   $2 - Default value (optional)
    # Returns: Configuration value or default
    local key="$1"
    local default="${2:-}"
    
    echo "${CONFIG[$key]:-$default}"
}

#######################################
# Logging System Functions
#######################################

function log_message() {
    # Purpose: Central logging function
    # Arguments:
    #   $1 - Log level
    #   $2 - Message
    # Returns: None
    local level="$1"
    local message="$2"
    local timestamp
    timestamp="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    
    # Check if we should log this message
    if [[ $level -ge $CURRENT_LOG_LEVEL ]]; then
        local level_str
        case $level in
            $LOG_DEBUG) level_str="DEBUG";;
            $LOG_INFO)  level_str="INFO ";;
            $LOG_WARN)  level_str="WARN ";;
            $LOG_ERROR) level_str="ERROR";;
            $LOG_FATAL) level_str="FATAL";;
            *)         level_str="UNKNOWN";;
        esac
        
        printf '[%s] [%s] %s\n' "$timestamp" "$level_str" "$message" >&2
        
        # Write to log file if configured
        if [[ -n "${CONFIG[LOG_FILE]:-}" ]]; then
            printf '[%s] [%s] %s\n' "$timestamp" "$level_str" "$message" >> "${CONFIG[LOG_FILE]}"
        fi
    fi
}

function log_debug() { log_message $LOG_DEBUG "$1"; }
function log_info()  { log_message $LOG_INFO  "$1"; }
function log_warn()  { log_message $LOG_WARN  "$1"; }
function log_error() { log_message $LOG_ERROR "$1"; }
function log_fatal() { log_message $LOG_FATAL "$1"; exit 1; }

#######################################
# Error Handling Functions
#######################################

function handle_error() {
    # Purpose: Central error handling function
    # Arguments:
    #   $1 - Error type
    #   $2 - Error message
    #   $3 - Error context (optional)
    # Returns: 1 (always indicates error)
    local error_type="$1"
    local error_message="$2"
    local error_context="${3:-}"
    
    # Log the error
    log_error "Error[$error_type]: $error_message${error_context:+ ($error_context)}"
    
    # Create error report
    local report_file="${CONFIG[LOG_DIR]}/error_report_$(date +%Y%m%d_%H%M%S).log"
    {
        echo "Error Report"
        echo "==========="
        echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
        echo "Type: $error_type"
        echo "Message: $error_message"
        echo "Context: $error_context"
        echo "State:"
        declare -p STATE
        echo "Environment:"
        env
    } > "$report_file"
    
    # Attempt recovery based on error type
    if recover_from_error "$error_type" "$error_message"; then
        log_info "Successfully recovered from error: $error_type"
        return 0
    fi
    
    return 1
}

function recover_from_error() {
    # Purpose: Attempts to recover from an error
    # Arguments:
    #   $1 - Error type
    #   $2 - Error message
    # Returns: 0 if recovery successful, 1 if failed
    local error_type="$1"
    local error_message="$2"
    
    case "$error_type" in
        "CONFIG")
            log_info "Attempting to restore default configuration..."
            if load_default_config; then
                return 0
            fi
            ;;
        "BUILD")
            log_info "Attempting to clean build environment..."
            if clean_build_environment; then
                return 0
            fi
            ;;
        *)
            log_warn "No recovery procedure for error type: $error_type"
            ;;
    esac
    
    return 1
}

#######################################
# State Management Functions
#######################################

function save_state() {
    # Purpose: Saves current state to file
    # Arguments: None
    # Returns: 0 on success, 1 on failure
    local state_file="${CONFIG[STATE_FILE]:-${WRAPPER_ROOT}/var/state.json}"
    
    if ! mkdir -p "$(dirname "$state_file")"; then
        log_error "Failed to create state directory"
        return 1
    fi
    
    if ! declare -p STATE > "$state_file"; then
        log_error "Failed to save state to: $state_file"
        return 1
    fi
    
    return 0
}

function load_state() {
    # Purpose: Loads state from file
    # Arguments: None
    # Returns: 0 on success, 1 on failure
    local state_file="${CONFIG[STATE_FILE]:-${WRAPPER_ROOT}/var/state.json}"
    
    if [[ -f "$state_file" ]]; then
        source "$state_file"
        return 0
    fi
    
    log_warn "No existing state file found: $state_file"
    return 1
}

#######################################
# Initialization
#######################################

function init_core_functions() {
    # Purpose: Initializes the core functions library
    # Arguments: None
    # Returns: 0 on success, 1 on failure
    
    # Set up initial configuration
    CONFIG[WRAPPER_ROOT]="$WRAPPER_ROOT"
    CONFIG[LIB_DIR]="${WRAPPER_ROOT}/lib"
    CONFIG[CONFIG_DIR]="${WRAPPER_ROOT}/config"
    CONFIG[LOG_DIR]="${WRAPPER_ROOT}/logs"
    CONFIG[STATE_FILE]="${WRAPPER_ROOT}/var/state.json"
    
    # Create required directories
    mkdir -p "${CONFIG[LOG_DIR]}" "${CONFIG[CONFIG_DIR]}" "$(dirname "${CONFIG[STATE_FILE]}")"
    
    # Initialize logging
    CONFIG[LOG_FILE]="${CONFIG[LOG_DIR]}/wrapper.log"
    touch "${CONFIG[LOG_FILE]}"
    
    log_info "Core functions library initialized"
    return 0
}

# Initialize library if sourced directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    log_error "This script should be sourced, not executed directly"
    exit 1
fi

init_core_functions || exit 1

