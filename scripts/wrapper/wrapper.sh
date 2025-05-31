#!/bin/bash
#===============================================================================
# Title: LFS/BLFS Build Scripts Wrapper System
# Description: Main wrapper script for managing LFS and BLFS build processes
# Author: System
# Date: 2025-05-31
# Version: 0.1.0
#===============================================================================

set -euo pipefail
IFS=$'\n\t'

#===============================================================================
# Global Variables and Environment Setup
#===============================================================================

# Script metadata
readonly SCRIPT_VERSION="0.1.0"
readonly SCRIPT_NAME="${0##*/}"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly WRAPPER_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Directory paths
readonly CONFIG_DIR="${WRAPPER_ROOT}/config"
readonly LOGS_DIR="${WRAPPER_ROOT}/logs"
readonly SCRIPTS_DIR="${WRAPPER_ROOT}/scripts"
readonly ARTIFACTS_DIR="${WRAPPER_ROOT}/artifacts"
readonly TEMP_DIR="${WRAPPER_ROOT}/temp"

# Log files
readonly SYSTEM_LOG="${LOGS_DIR}/system/wrapper.log"
readonly ERROR_LOG="${LOGS_DIR}/error/wrapper.log"
readonly BUILD_LOG="${LOGS_DIR}/build/current.log"

# Exit codes
readonly E_SUCCESS=0
readonly E_ERROR=1
readonly E_CONFIG=2
readonly E_ENVIRONMENT=3
readonly E_ARGS=4
readonly E_PERMISSION=5
readonly E_DEPENDENCY=6

#===============================================================================
# Logging Functions
#===============================================================================

# Log levels
readonly LOG_DEBUG=0
readonly LOG_INFO=1
readonly LOG_WARN=2
readonly LOG_ERROR=3

# Current log level (can be overridden via config)
LOG_LEVEL=${LOG_INFO}

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp
    timestamp="$(date +'%Y-%m-%d %H:%M:%S')"
    
    if [[ ${level} -ge ${LOG_LEVEL} ]]; then
        case ${level} in
            ${LOG_DEBUG}) prefix="DEBUG";;
            ${LOG_INFO})  prefix="INFO ";;
            ${LOG_WARN})  prefix="WARN ";;
            ${LOG_ERROR}) prefix="ERROR";;
            *)           prefix="OTHER";;
        esac
        
        echo "[${timestamp}] ${prefix}: ${message}" | tee -a "${SYSTEM_LOG}"
        
        # Also write errors to error log
        if [[ ${level} -eq ${LOG_ERROR} ]]; then
            echo "[${timestamp}] ${prefix}: ${message}" >> "${ERROR_LOG}"
        fi
    fi
}

debug() { log ${LOG_DEBUG} "$*"; }
info()  { log ${LOG_INFO}  "$*"; }
warn()  { log ${LOG_WARN}  "$*"; }
error() { log ${LOG_ERROR} "$*"; }

#===============================================================================
# Error Handling
#===============================================================================

cleanup() {
    local exit_code=$?
    
    # Perform cleanup operations
    if [[ -d "${TEMP_DIR}" ]]; then
        rm -rf "${TEMP_DIR:?}"/*
    fi
    
    # Log exit status
    if [[ ${exit_code} -ne ${E_SUCCESS} ]]; then
        error "Script terminated with error code: ${exit_code}"
    else
        info "Script completed successfully"
    fi
    
    exit ${exit_code}
}

fail() {
    local message=$1
    local code=${2:-${E_ERROR}}
    error "${message}"
    exit "${code}"
}

trap cleanup EXIT
trap 'fail "Caught interrupt signal"' INT TERM

#===============================================================================
# Environment Validation
#===============================================================================

validate_environment() {
    # Check for required commands
    local required_commands=(bash grep sed awk)
    for cmd in "${required_commands[@]}"; do
        if ! command -v "${cmd}" >/dev/null 2>&1; then
            fail "Required command not found: ${cmd}" ${E_DEPENDENCY}
        fi
    done
    
    # Check for required directories
    local required_dirs=(
        "${CONFIG_DIR}"
        "${LOGS_DIR}"
        "${SCRIPTS_DIR}"
        "${ARTIFACTS_DIR}"
        "${TEMP_DIR}"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "${dir}" ]]; then
            fail "Required directory not found: ${dir}" ${E_ENVIRONMENT}
        fi
        
        if [[ ! -w "${dir}" ]]; then
            fail "Directory not writable: ${dir}" ${E_PERMISSION}
        fi
    done
    
    # Validate configuration
    if [[ ! -f "${CONFIG_DIR}/core/config.sh" ]]; then
        fail "Core configuration file not found" ${E_CONFIG}
    fi
    
    return ${E_SUCCESS}
}

#===============================================================================
# Usage and Help
#===============================================================================

show_usage() {
    cat << EOF
Usage: ${SCRIPT_NAME} [OPTIONS] COMMAND [ARGS]

LFS/BLFS Build Scripts Wrapper System
Version: ${SCRIPT_VERSION}

Commands:
    build       Start or resume a build process
    clean       Clean build artifacts and temporary files
    config      Manage system configuration
    list        List available build scripts
    status      Show current build status
    verify      Verify build environment and dependencies

Options:
    -h, --help              Show this help message
    -v, --version           Show version information
    -d, --debug            Enable debug logging
    -q, --quiet            Minimize output (only errors)
    -c, --config FILE      Use alternative config file
    
Examples:
    ${SCRIPT_NAME} build lfs-chapter6
    ${SCRIPT_NAME} --debug status
    ${SCRIPT_NAME} config show

For more information, see the documentation in the docs directory.
EOF
}

show_version() {
    echo "${SCRIPT_NAME} version ${SCRIPT_VERSION}"
}

#===============================================================================
# Command-line Argument Parsing
#===============================================================================

parse_args() {
    local args=()
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit ${E_SUCCESS}
                ;;
            -v|--version)
                show_version
                exit ${E_SUCCESS}
                ;;
            -d|--debug)
                LOG_LEVEL=${LOG_DEBUG}
                shift
                ;;
            -q|--quiet)
                LOG_LEVEL=${LOG_ERROR}
                shift
                ;;
            -c|--config)
                if [[ -z "$2" ]]; then
                    fail "Config file path required" ${E_ARGS}
                fi
                CONFIG_FILE="$2"
                shift 2
                ;;
            -*)
                fail "Unknown option: $1" ${E_ARGS}
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done
    
    # Validate command
    if [[ ${#args[@]} -eq 0 ]]; then
        show_usage
        exit ${E_ARGS}
    fi
    
    # Set command and arguments
    COMMAND="${args[0]}"
    COMMAND_ARGS=("${args[@]:1}")
}

#===============================================================================
# Command Implementation
#===============================================================================

# Build state tracking functions
get_build_state() {
    local script_name=$1
    local state_file="${ARTIFACTS_DIR}/state/${script_name}.state"
    
    if [[ -f "${state_file}" ]]; then
        cat "${state_file}"
    else
        echo "READY"
    fi
}

set_build_state() {
    local script_name=$1
    local state=$2
    local state_file="${ARTIFACTS_DIR}/state/${script_name}.state"
    
    mkdir -p "$(dirname "${state_file}")"
    echo "${state}" > "${state_file}"
}

# Build log management
setup_build_logging() {
    local script_name=$1
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local log_dir="${LOGS_DIR}/build/${script_name}"
    local current_log="${log_dir}/${timestamp}.log"
    
    mkdir -p "${log_dir}"
    
    # Create new log file
    touch "${current_log}"
    
    # Update current.log symlink
    ln -sf "${current_log}" "${LOGS_DIR}/build/current.log"
    
    echo "${current_log}"
}

# Build script location and validation
find_build_script() {
    local script_name=$1
    local script_path=""
    
    # Search directories in order: lfs, blfs, custom
    local search_dirs=(
        "${SCRIPTS_DIR}/lfs"
        "${SCRIPTS_DIR}/blfs"
        "${SCRIPTS_DIR}/custom"
    )
    
    for dir in "${search_dirs[@]}"; do
        local full_path="${dir}/${script_name}"
        if [[ -x "${full_path}" ]]; then
            script_path="${full_path}"
            break
        fi
    done
    
    echo "${script_path}"
}

validate_build_script() {
    local script_path=$1
    local metadata
    metadata=$(parse_metadata "${script_path}")
    
    # Check required metadata fields
    local required_fields=("NAME" "VERSION" "DESCRIPTION" "CATEGORY")
    local missing_fields=()
    
    for field in "${required_fields[@]}"; do
        if ! echo "${metadata}" | grep -q "^${field}="; then
            missing_fields+=("${field}")
        fi
    done
    
    if [[ ${#missing_fields[@]} -gt 0 ]]; then
        fail "Build script missing required metadata: ${missing_fields[*]}" ${E_CONFIG}
    fi
    
    return ${E_SUCCESS}
}

cmd_build() {
    # Validate arguments
    if [[ ${#COMMAND_ARGS[@]} -lt 1 ]]; then
        fail "Build script name required" ${E_ARGS}
    fi
    
    local script_name="${COMMAND_ARGS[0]}"
    info "Processing build request for: ${script_name}"
    
    # Locate build script
    local script_path
    script_path=$(find_build_script "${script_name}")
    if [[ -z "${script_path}" ]]; then
        fail "Build script not found: ${script_name}" ${E_ARGS}
    fi
    
    # Validate script metadata
    info "Validating build script"
    validate_build_script "${script_path}"
    
    # Check current state
    local current_state
    current_state=$(get_build_state "${script_name}")
    if [[ "${current_state}" == "RUNNING" ]]; then
        warn "Build appears to be already running"
        read -rp "Force start new build? [y/N] " response
        if [[ "${response,,}" != "y" ]]; then
            fail "Build aborted" ${E_ERROR}
        fi
    fi
    
    # Setup build logging
    local build_log
    build_log=$(setup_build_logging "${script_name}")
    info "Build log: ${build_log}"
    
    # Update build state
    set_build_state "${script_name}" "RUNNING"
    
    # Execute build script
    info "Starting build execution"
    {
        echo "=== Build Started at $(date) ==="
        echo "Script: ${script_path}"
        echo "Arguments: ${COMMAND_ARGS[*]:1}"
        echo "==============================="
        echo
    } >> "${build_log}"
    
    if "${script_path}" "${COMMAND_ARGS[@]:1}" >> "${build_log}" 2>&1; then
        {
            echo
            echo "=== Build Completed Successfully at $(date) ==="
            echo "=============================================="
        } >> "${build_log}"
        
        set_build_state "${script_name}" "COMPLETED"
        info "Build completed successfully"
        
        # Archive build artifacts if present
        if [[ -d "${TEMP_DIR}/artifacts" ]]; then
            local archive_dir="${ARTIFACTS_DIR}/${script_name}/$(date +%Y%m%d_%H%M%S)"
            mkdir -p "${archive_dir}"
            mv "${TEMP_DIR}/artifacts"/* "${archive_dir}/"
            info "Build artifacts archived to: ${archive_dir}"
        fi
    else
        local exit_code=$?
        {
            echo
            echo "=== Build Failed at $(date) ==="
            echo "Exit Code: ${exit_code}"
            echo "=============================="
        } >> "${build_log}"
        
        set_build_state "${script_name}" "FAILED"
        error "Build failed with exit code: ${exit_code}"
        
        # Preserve failed build artifacts for investigation
        if [[ -d "${TEMP_DIR}/artifacts" ]]; then
            local failed_dir="${ARTIFACTS_DIR}/failed/${script_name}/$(date +%Y%m%d_%H%M%S)"
            mkdir -p "${failed_dir}"
            mv "${TEMP_DIR}/artifacts"/* "${failed_dir}/"
            warn "Failed build artifacts preserved at: ${failed_dir}"
        fi
        
        exit ${exit_code}
    fi
}

cmd_clean() {
    info "Cleaning build artifacts"
    # TODO: Implement clean command
}

cmd_config() {
    info "Managing configuration"
    # TODO: Implement config command
}

# Script discovery and metadata parsing functions
parse_metadata() {
    local script_file=$1
    local metadata=()
    local in_metadata=false
    
    while IFS= read -r line; do
        if [[ "${line}" == "# METADATA_BEGIN" ]]; then
            in_metadata=true
            continue
        fi
        if [[ "${line}" == "# METADATA_END" ]]; then
            break
        fi
        if [[ "${in_metadata}" == "true" && "${line}" =~ ^[A-Z_]+=.*$ ]]; then
            metadata+=("${line}")
        fi
    done < "${script_file}"
    
    printf "%s\n" "${metadata[@]}"
}

get_metadata_value() {
    local metadata=$1
    local key=$2
    local value
    
    value=$(echo "${metadata}" | grep "^${key}=" | cut -d'=' -f2- | tr -d '"')
    echo "${value}"
}

format_script_info() {
    local script_path=$1
    local script_name
    script_name=$(basename "${script_path}")
    local metadata
    metadata=$(parse_metadata "${script_path}")
    
    local name version category description
    name=$(get_metadata_value "${metadata}" "NAME")
    version=$(get_metadata_value "${metadata}" "VERSION")
    category=$(get_metadata_value "${metadata}" "CATEGORY")
    description=$(get_metadata_value "${metadata}" "DESCRIPTION")
    
    printf "%-20s %-10s %-15s %s\n" \
        "${name:-Unknown}" \
        "${version:-N/A}" \
        "${category:-uncategorized}" \
        "${description:-No description available}"
}

cmd_list() {
    info "Scanning for available build scripts"
    
    local script_dirs=(
        "${SCRIPTS_DIR}/lfs"
        "${SCRIPTS_DIR}/blfs"
        "${SCRIPTS_DIR}/custom"
    )
    
    # Verify script directories exist
    for dir in "${script_dirs[@]}"; do
        if [[ ! -d "${dir}" ]]; then
            warn "Script directory not found: ${dir}"
            continue
        fi
    done
    
    # Initialize category arrays
    declare -A scripts_by_category
    
    # Scan for scripts and organize by category
    for dir in "${script_dirs[@]}"; do
        if [[ -d "${dir}" ]]; then
            while IFS= read -r -d '' script; do
                if [[ -x "${script}" && "${script}" =~ \.(sh|bash)$ ]]; then
                    local metadata
                    metadata=$(parse_metadata "${script}")
                    local category
                    category=$(get_metadata_value "${metadata}" "CATEGORY")
                    category=${category:-uncategorized}
                    
                    # Append script info to appropriate category
                    scripts_by_category["${category}"]+="${script}"$'\n'
                fi
            done < <(find "${dir}" -type f -print0)
        fi
    done
    
    # Display scripts by category
    echo "Available Build Scripts"
    echo "======================"
    echo
    
    # Header format
    printf "%-20s %-10s %-15s %s\n" "NAME" "VERSION" "CATEGORY" "DESCRIPTION"
    printf "%s\n" "-------------------- ---------- --------------- ------------------------"
    
    # Sort and display categories
    local categories
    mapfile -t categories < <(printf '%s\n' "${!scripts_by_category[@]}" | sort)
    
    for category in "${categories[@]}"; do
        if [[ -n "${scripts_by_category[${category}]}" ]]; then
            echo
            echo "Category: ${category}"
            echo "----------------------------------------"
            
            # Sort scripts within category
            while IFS= read -r script; do
                if [[ -n "${script}" ]]; then
                    format_script_info "${script}"
                fi
            done < <(echo "${scripts_by_category[${category}]}" | sort)
        fi
    done
    
    # Display summary
    local total_scripts=0
    for category in "${categories[@]}"; do
        local count
        count=$(echo -n "${scripts_by_category[${category}]}" | grep -c '^')
        total_scripts=$((total_scripts + count))
    done
    
    echo
    echo "Summary:"
    echo "  Total Categories: ${#categories[@]}"
    echo "  Total Scripts: ${total_scripts}"
    
    if [[ ${total_scripts} -eq 0 ]]; then
        warn "No build scripts found"
    fi
}

cmd_status() {
    info "Checking build status"
    # TODO: Implement status command
}

cmd_verify() {
    info "Verifying environment"
    # TODO: Implement verify command
}

#===============================================================================
# Main Execution
#===============================================================================

main() {
    # Parse command-line arguments
    parse_args "$@"
    
    # Initialize logging
    info "Starting ${SCRIPT_NAME} version ${SCRIPT_VERSION}"
    debug "Log level set to ${LOG_LEVEL}"
    
    # Validate environment
    info "Validating environment"
    validate_environment
    
    # Execute requested command
    case ${COMMAND} in
        build)   cmd_build   "${COMMAND_ARGS[@]:-}";;
        clean)   cmd_clean   "${COMMAND_ARGS[@]:-}";;
        config)  cmd_config  "${COMMAND_ARGS[@]:-}";;
        list)    cmd_list    "${COMMAND_ARGS[@]:-}";;
        status)  cmd_status  "${COMMAND_ARGS[@]:-}";;
        verify)  cmd_verify  "${COMMAND_ARGS[@]:-}";;
        *)       fail "Unknown command: ${COMMAND}" ${E_ARGS};;
    esac
    
    return ${E_SUCCESS}
}

# Execute main function
main "$@"

