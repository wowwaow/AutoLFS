#!/bin/bash
#
# Configuration Validation Framework
# Validates build system configuration files
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
CONFIG_DIR="/var/run/lfs-wrapper/config"
CONFIG_LOG="${CONFIG_DIR}/config_validation.log"
mkdir -p "$CONFIG_DIR"

# Configuration Types
declare -r CONFIG_TYPE_SYSTEM="system"
declare -r CONFIG_TYPE_BUILD="build"
declare -r CONFIG_TYPE_PACKAGE="package"
declare -r CONFIG_TYPE_TOOL="tool"

# Validation Rules
declare -A CONFIG_RULES=(
    ["required_fields"]="name version description maintainer"
    ["optional_fields"]="dependencies tags category priority"
    ["version_pattern"]="^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$"
    ["name_pattern"]="^[a-zA-Z][a-zA-Z0-9_-]+$"
)

# Validate configuration file
validate_config() {
    local config_file="$1"
    local config_type="$2"
    local schema_file="$3"
    local status=0
    
    log_info "Validating configuration: ${config_file}"
    
    # Check file existence
    if [ ! -f "$config_file" ]; then
        log_error "Configuration file not found: ${config_file}"
        return 1
    fi
    
    # Check file format (YAML/JSON)
    case "${config_file##*.}" in
        yaml|yml)
            if ! command -v yq >/dev/null 2>&1; then
                log_error "yq command not found - required for YAML validation"
                return 1
            fi
            validate_yaml_config "$config_file" "$schema_file" || status=1
            ;;
        json)
            if ! command -v jq >/dev/null 2>&1; then
                log_error "jq command not found - required for JSON validation"
                return 1
            fi
            validate_json_config "$config_file" "$schema_file" || status=1
            ;;
        *)
            validate_plain_config "$config_file" || status=1
            ;;
    esac
    
    # Type-specific validation
    case "$config_type" in
        "$CONFIG_TYPE_SYSTEM")
            validate_system_config "$config_file" || status=1
            ;;
        "$CONFIG_TYPE_BUILD")
            validate_build_config "$config_file" || status=1
            ;;
        "$CONFIG_TYPE_PACKAGE")
            validate_package_config "$config_file" || status=1
            ;;
        "$CONFIG_TYPE_TOOL")
            validate_tool_config "$config_file" || status=1
            ;;
        *)
            log_error "Unknown configuration type: ${config_type}"
            status=1
            ;;
    esac
    
    return $status
}

# YAML configuration validation
validate_yaml_config() {
    local config_file="$1"
    local schema_file="$2"
    local status=0
    
    # Basic YAML syntax check
    if ! yq eval '.' "$config_file" >/dev/null 2>&1; then
        log_error "Invalid YAML syntax in: ${config_file}"
        return 1
    fi
    
    # Schema validation if schema file provided
    if [ -n "$schema_file" ]; then
        if ! yq eval-all '. as $item ireduce ({}; . * $item)' "$schema_file" "$config_file" >/dev/null 2>&1; then
            log_error "Configuration does not match schema: ${config_file}"
            status=1
        fi
    fi
    
    return $status
}

# JSON configuration validation
validate_json_config() {
    local config_file="$1"
    local schema_file="$2"
    local status=0
    
    # Basic JSON syntax check
    if ! jq '.' "$config_file" >/dev/null 2>&1; then
        log_error "Invalid JSON syntax in: ${config_file}"
        return 1
    fi
    
    # Schema validation if schema file provided
    if [ -n "$schema_file" ]; then
        if ! check_json_schema "$config_file" "$schema_file"; then
            log_error "Configuration does not match schema: ${config_file}"
            status=1
        fi
    fi
    
    return $status
}

# Plain text configuration validation
validate_plain_config() {
    local config_file="$1"
    local status=0
    
    # Check for required fields
    for field in ${CONFIG_RULES["required_fields"]}; do
        if ! grep -q "^${field}=" "$config_file"; then
            log_error "Required field missing: ${field}"
            status=1
        fi
    done
    
    # Validate field values
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [ -z "$key" ] && continue
        
        # Validate version format if present
        if [ "$key" = "version" ]; then
            if ! [[ "$value" =~ ${CONFIG_RULES["version_pattern"]} ]]; then
                log_error "Invalid version format: ${value}"
                status=1
            fi
        fi
        
        # Validate name format if present
        if [ "$key" = "name" ]; then
            if ! [[ "$value" =~ ${CONFIG_RULES["name_pattern"]} ]]; then
                log_error "Invalid name format: ${value}"
                status=1
            fi
        fi
    done < "$config_file"
    
    return $status
}

# System configuration validation
validate_system_config() {
    local config_file="$1"
    local status=0
    
    # System-specific validation rules
    local required_system_fields="build_dir log_dir tmp_dir"
    
    for field in $required_system_fields; do
        if ! grep -q "^${field}=" "$config_file"; then
            log_error "Required system field missing: ${field}"
            status=1
        fi
    done
    
    # Validate directory paths
    while IFS='=' read -r key value; do
        if [[ "$key" =~ _dir$ ]]; then
            # Remove quotes if present
            value=${value#\"}
            value=${value%\"}
            
            # Check if absolute path
            if [[ ! "$value" =~ ^/ ]]; then
                log_error "Directory path must be absolute: ${key}=${value}"
                status=1
            fi
        fi
    done < "$config_file"
    
    return $status
}

# Build configuration validation
validate_build_config() {
    local config_file="$1"
    local status=0
    
    # Build-specific validation rules
    local required_build_fields="toolchain_prefix host_triplet build_triplet"
    
    for field in $required_build_fields; do
        if ! grep -q "^${field}=" "$config_file"; then
            log_error "Required build field missing: ${field}"
            status=1
        fi
    done
    
    return $status
}

# Package configuration validation
validate_package_config() {
    local config_file="$1"
    local status=0
    
    # Package-specific validation rules
    local required_package_fields="name version source checksum"
    
    for field in $required_package_fields; do
        if ! grep -q "^${field}=" "$config_file"; then
            log_error "Required package field missing: ${field}"
            status=1
        fi
    done
    
    # Validate checksum format
    local checksum
    checksum=$(grep "^checksum=" "$config_file" | cut -d'=' -f2)
    if ! [[ "$checksum" =~ ^[a-fA-F0-9]{64}$ ]]; then
        log_error "Invalid checksum format"
        status=1
    fi
    
    return $status
}

# Tool configuration validation
validate_tool_config() {
    local config_file="$1"
    local status=0
    
    # Tool-specific validation rules
    local required_tool_fields="name version binary_path"
    
    for field in $required_tool_fields; do
        if ! grep -q "^${field}=" "$config_file"; then
            log_error "Required tool field missing: ${field}"
            status=1
        fi
    done
    
    return $status
}

# Main entry point
main() {
    if [ "$#" -lt 2 ]; then
        log_error "Usage: $0 <config_file> <config_type> [schema_file]"
        exit 1
    fi
    
    local config_file="$1"
    local config_type="$2"
    local schema_file="${3:-}"
    
    if validate_config "$config_file" "$config_type" "$schema_file"; then
        log_info "Configuration validation passed: ${config_file}"
        exit 0
    else
        log_error "Configuration validation failed: ${config_file}"
        exit 1
    fi
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

