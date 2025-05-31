#!/bin/bash

# Script Registry Manager
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Handle script registration and management

# Registry data structure
declare -A SCRIPT_REGISTRY
declare -A SCRIPT_DEPENDENCIES
declare -A SCRIPT_METADATA

# Initialize registry
init_registry() {
    info "Initializing script registry"
    SCRIPT_REGISTRY=()
    SCRIPT_DEPENDENCIES=()
    SCRIPT_METADATA=()
}

# Register script
register_script() {
    local script_path=$1
    local script_name=$(basename "$script_path")
    
    info "Registering script: $script_name"
    
    # Validate script
    if ! validate_script "$script_path"; then
        error "Script validation failed: $script_path"
        return 1
    fi
    
    # Extract metadata
    local metadata=$(extract_metadata "$script_path")
    SCRIPT_METADATA[$script_name]="$metadata"
    
    # Extract dependencies
    local dependencies=$(extract_dependencies "$script_path")
    SCRIPT_DEPENDENCIES[$script_name]="$dependencies"
    
    # Add to registry
    SCRIPT_REGISTRY[$script_name]="$script_path"
    
    info "Script registered successfully: $script_name"
    return 0
}

# Validate script
validate_script() {
    local script_path=$1
    
    # Check file exists
    if [ ! -f "$script_path" ]; then
        error "Script file not found: $script_path"
        return 1
    fi
    
    # Check executable
    if [ ! -x "$script_path" ]; then
        error "Script not executable: $script_path"
        return 1
    fi
    
    # Check required functions
    local required_functions=(
        "initialize"
        "configure"
        "build"
        "test"
        "install"
        "cleanup"
    )
    
    for func in "${required_functions[@]}"; do
        if ! grep -q "^${func}()" "$script_path"; then
            error "Required function missing: $func"
            return 1
        fi
    done
    
    # Check required variables
    local required_variables=(
        "PACKAGE_NAME"
        "PACKAGE_VERSION"
        "BUILD_REQUIREMENTS"
        "TEST_SUITE"
    )
    
    for var in "${required_variables[@]}"; do
        if ! grep -q "^${var}=" "$script_path"; then
            error "Required variable missing: $var"
            return 1
        fi
    done
    
    return 0
}

# Extract script metadata
extract_metadata() {
    local script_path=$1
    local metadata=""
    
    # Extract package information
    local package_name=$(grep "^PACKAGE_NAME=" "$script_path" | cut -d'=' -f2)
    local package_version=$(grep "^PACKAGE_VERSION=" "$script_path" | cut -d'=' -f2)
    
    # Build metadata string
    metadata="name=$package_name;version=$package_version"
    
    # Extract additional metadata
    if grep -q "^# META:" "$script_path"; then
        local extra_meta=$(grep "^# META:" "$script_path" | sed 's/^# META: //')
        metadata="$metadata;$extra_meta"
    fi
    
    echo "$metadata"
}

# Extract script dependencies
extract_dependencies() {
    local script_path=$1
    local deps=""
    
    # Extract build requirements
    if grep -q "^BUILD_REQUIREMENTS=" "$script_path"; then
        deps=$(grep "^BUILD_REQUIREMENTS=" "$script_path" | cut -d'=' -f2)
    fi
    
    echo "$deps"
}

# Get script path
get_script_path() {
    local script_name=$1
    echo "${SCRIPT_REGISTRY[$script_name]}"
}

# Get script dependencies
get_script_dependencies() {
    local script_name=$1
    echo "${SCRIPT_DEPENDENCIES[$script_name]}"
}

# Get script metadata
get_script_metadata() {
    local script_name=$1
    echo "${SCRIPT_METADATA[$script_name]}"
}

# Check if script is registered
is_script_registered() {
    local script_name=$1
    [ -n "${SCRIPT_REGISTRY[$script_name]}" ]
}

# Unregister script
unregister_script() {
    local script_name=$1
    
    if is_script_registered "$script_name"; then
        unset SCRIPT_REGISTRY[$script_name]
        unset SCRIPT_DEPENDENCIES[$script_name]
        unset SCRIPT_METADATA[$script_name]
        return 0
    fi
    
    return 1
}

# List registered scripts
list_scripts() {
    for script_name in "${!SCRIPT_REGISTRY[@]}"; do
        echo "$script_name: ${SCRIPT_REGISTRY[$script_name]}"
    done
}

# Resolve dependencies
resolve_dependencies() {
    local script_name=$1
    local -a deps=()
    
    if ! is_script_registered "$script_name"; then
        error "Script not registered: $script_name"
        return 1
    fi
    
    # Get direct dependencies
    IFS=',' read -ra direct_deps <<< "${SCRIPT_DEPENDENCIES[$script_name]}"
    
    # Resolve each dependency
    for dep in "${direct_deps[@]}"; do
        if ! is_script_registered "$dep"; then
            error "Dependency not found: $dep"
            return 1
        fi
        deps+=("$dep")
        
        # Resolve recursive dependencies
        local sub_deps=($(resolve_dependencies "$dep"))
        deps+=("${sub_deps[@]}")
    done
    
    # Remove duplicates and return
    echo "${deps[@]}" | tr ' ' '\n' | sort -u | tr '\n' ' '
}

# Validate dependencies
validate_dependencies() {
    local script_name=$1
    local -a missing_deps=()
    
    # Get all dependencies
    local deps=($(resolve_dependencies "$script_name"))
    
    # Check each dependency
    for dep in "${deps[@]}"; do
        if ! is_script_registered "$dep"; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        error "Missing dependencies for $script_name: ${missing_deps[*]}"
        return 1
    fi
    
    return 0
}

