#!/bin/bash
#
# Configuration Schema Validator
# Validates configuration files against JSON Schema
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
SCHEMA_DIR="/var/run/lfs-wrapper/config/schemas"
SCHEMA_LOG="${SCHEMA_DIR}/validation.log"
mkdir -p "$SCHEMA_DIR"

# Schema Types
declare -r SCHEMA_TYPE_SYSTEM="system"
declare -r SCHEMA_TYPE_BUILD="build"
declare -r SCHEMA_TYPE_PACKAGE="package"
declare -r SCHEMA_TYPE_TOOL="tool"

# Validate configuration against schema
validate_schema() {
    local config_file="$1"
    local schema_file="$2"
    local config_type="$3"
    
    log_info "Validating configuration against schema: ${config_file}"
    
    # Check for required tools
    if ! command -v jq >/dev/null 2>&1; then
        log_error "jq command not found - required for schema validation"
        return 1
    fi
    
    # Determine file type
    case "${config_file##*.}" in
        json)
            validate_json_schema "$config_file" "$schema_file"
            ;;
        yaml|yml)
            if ! command -v yq >/dev/null 2>&1; then
                log_error "yq command not found - required for YAML validation"
                return 1
            fi
            validate_yaml_schema "$config_file" "$schema_file"
            ;;
        *)
            log_error "Unsupported file type: ${config_file}"
            return 1
            ;;
    esac
}

# Validate JSON against schema
validate_json_schema() {
    local config_file="$1"
    local schema_file="$2"
    
    # First validate schema itself
    if ! jq '.' "$schema_file" >/dev/null 2>&1; then
        log_error "Invalid JSON schema: ${schema_file}"
        return 1
    fi
    
    # Then validate configuration
    if ! jq '.' "$config_file" >/dev/null 2>&1; then
        log_error "Invalid JSON configuration: ${config_file}"
        return 1
    fi
    
    # Perform schema validation
    if command -v jsonschema >/dev/null 2>&1; then
        if ! jsonschema -i "$config_file" "$schema_file"; then
            log_error "Schema validation failed"
            return 1
        fi
    else
        log_warn "jsonschema not installed - performing basic validation only"
        # Basic structure validation using jq
        local schema_keys
        schema_keys=$(jq -r '.properties | keys[]' "$schema_file")
        
        for key in $schema_keys; do
            if ! jq -e ".$key" "$config_file" >/dev/null 2>&1; then
                log_error "Required field missing: ${key}"
                return 1
            fi
        done
    fi
    
    return 0
}

# Validate YAML against schema
validate_yaml_schema() {
    local config_file="$1"
    local schema_file="$2"
    
    # Convert YAML to JSON for validation
    local json_config
    local json_schema
    
    json_config=$(yq eval -o=json "$config_file")
    json_schema=$(yq eval -o=json "$schema_file")
    
    # Create temporary files
    local temp_config
    local temp_schema
    temp_config=$(mktemp)
    temp_schema=$(mktemp)
    
    echo "$json_config" > "$temp_config"
    echo "$json_schema" > "$temp_schema"
    
    # Validate using JSON schema
    validate_json_schema "$temp_config" "$temp_schema"
    local result=$?
    
    # Cleanup
    rm -f "$temp_config" "$temp_schema"
    
    return $result
}

# Create schema for configuration type
create_schema() {
    local schema_type="$1"
    local output_file="$2"
    
    case "$schema_type" in
        "$SCHEMA_TYPE_SYSTEM")
            create_system_schema "$output_file"
            ;;
        "$SCHEMA_TYPE_BUILD")
            create_build_schema "$output_file"
            ;;
        "$SCHEMA_TYPE_PACKAGE")
            create_package_schema "$output_file"
            ;;
        "$SCHEMA_TYPE_TOOL")
            create_tool_schema "$output_file"
            ;;
        *)
            log_error "Unknown schema type: ${schema_type}"
            return 1
            ;;
    esac
}

# Create system configuration schema
create_system_schema() {
    local output_file="$1"
    
    cat > "$output_file" << 'EOF'
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["build_dir", "log_dir", "tmp_dir"],
    "properties": {
        "build_dir": {
            "type": "string",
            "pattern": "^/"
        },
        "log_dir": {
            "type": "string",
            "pattern": "^/"
        },
        "tmp_dir": {
            "type": "string",
            "pattern": "^/"
        }
    }
}
EOF
}

# Create build configuration schema
create_build_schema() {
    local output_file="$1"
    
    cat > "$output_file" << 'EOF'
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["toolchain_prefix", "host_triplet", "build_triplet"],
    "properties": {
        "toolchain_prefix": {
            "type": "string"
        },
        "host_triplet": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "build_triplet": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9_-]+$"
        }
    }
}
EOF
}

# Create package configuration schema
create_package_schema() {
    local output_file="$1"
    
    cat > "$output_file" << 'EOF'
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "version", "source", "checksum"],
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^[a-zA-Z][a-zA-Z0-9_-]+$"
        },
        "version": {
            "type": "string",
            "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+(-[a-zA-Z0-9]+)?$"
        },
        "source": {
            "type": "string",
            "format": "uri"
        },
        "checksum": {
            "type": "string",
            "pattern": "^[a-fA-F0-9]{64}$"
        }
    }
}
EOF
}

# Create tool configuration schema
create_tool_schema() {
    local output_file="$1"
    
    cat > "$output_file" << 'EOF'
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "version", "binary_path"],
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^[a-zA-Z][a-zA-Z0-9_-]+$"
        },
        "version": {
            "type": "string",
            "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+(-[a-zA-Z0-9]+)?$"
        },
        "binary_path": {
            "type": "string",
            "pattern": "^/"
        }
    }
}
EOF
}

# Main entry point
main() {
    if [ "$#" -lt 2 ]; then
        log_error "Usage: $0 <command> [args...]"
        exit 

