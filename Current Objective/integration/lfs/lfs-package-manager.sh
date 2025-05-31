#!/bin/bash

# LFS Package Manager
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Manage LFS package loading and configuration

# Package data structures
declare -A PACKAGE_CONFIGS
declare -A PACKAGE_VERSIONS
declare -A PACKAGE_DEPENDENCIES
declare -A PACKAGE_SOURCES

# Load package configurations
load_lfs_packages() {
    info "Loading LFS package configurations..."
    
    if [ ! -f "$LFS_PACKAGES_FILE" ]; then
        error "Package configuration file not found: $LFS_PACKAGES_FILE"
        return 1
    fi
    
    # Parse package configuration file
    while IFS=':' read -r package config; do
        if [ -n "$package" ]; then
            PACKAGE_CONFIGS[$package]="$config"
            parse_package_config "$package" "$config"
        fi
    done < "$LFS_PACKAGES_FILE"
    
    return 0
}

# Parse package configuration
parse_package_config() {
    local package=$1
    local config=$2
    
    # Extract version
    PACKAGE_VERSIONS[$package]=$(echo "$config" | awk -F';' '{print $1}')
    
    # Extract dependencies
    PACKAGE_DEPENDENCIES[$package]=$(echo "$config" | awk -F';' '{print $2}')
    
    # Extract source URL
    PACKAGE_SOURCES[$package]=$(echo "$config" | awk -F';' '{print $3}')
}

# Get package configuration
get_package_config() {
    local package=$1
    echo "${PACKAGE_CONFIGS[$package]}"
}

# Get package version
get_package_version() {
    local package=$1
    echo "${PACKAGE_VERSIONS[$package]}"
}

# Get package dependencies
get_package_dependencies() {
    local package=$1
    echo "${PACKAGE_DEPENDENCIES[$package]}"
}

# Get package source URL
get_package_source() {
    local package=$1
    echo "${PACKAGE_SOURCES[$package]}"
}

# Validate package configuration
validate_package_config() {
    local package=$1
    
    # Check required fields
    if [ -z "${PACKAGE_VERSIONS[$package]}" ]; then
        error "Package version not defined: $package"
        return 1
    fi
    
    if [ -z "${PACKAGE_SOURCES[$package]}" ]; then
        error "Package source not defined: $package"
        return 1
    fi
    
    return 0
}

# Get packages status
get_packages_status() {
    local packages_json="["
    local first=true
    
    for package in "${!PACKAGE_CONFIGS[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            packages_json+=","
        fi
        
        packages_json+=$(get_package_status "$package")
    done
    
    packages_json+="]"
    echo "$packages_json"
}

# Get individual package status
get_package_status() {
    local package=$1
    
    cat << EOF
{
    "name": "$package",
    "version": "${PACKAGE_VERSIONS[$package]}",
    "dependencies": "${PACKAGE_DEPENDENCIES[$package]}",
    "source": "${PACKAGE_SOURCES[$package]}"
}
EOF
}

# Download package source
download_package_source() {
    local package=$1
    local source_url="${PACKAGE_SOURCES[$package]}"
    local version="${PACKAGE_VERSIONS[$package]}"
    
    info "Downloading source for $package-$version"
    
    local source_file="$LFS/sources/$package-$version.tar.xz"
    if [ -f "$source_file" ]; then
        info "Source file already exists: $source_file"
        return 0
    fi
    
    wget -q "$source_url" -O "$source_file" || {
        error "Failed to download source: $source_url"
        return 1
    }
    
    return 0
}

# Verify package source
verify_package_source() {
    local package=$1
    local version="${PACKAGE_VERSIONS[$package]}"
    local source_file="$LFS/sources/$package-$version.tar.xz"
    
    info "Verifying source for $package-$version"
    
    # Check file exists
    if [ ! -f "$source_file" ]; then
        error "Source file not found: $source_file"
        return 1
    fi
    
    # Verify checksum
    if ! verify_checksum "$source_file" "$package"; then
        error "Checksum verification failed: $source_file"
        return 1
    fi
    
    return 0
}

# Export package information
export_package_info() {
    local package=$1
    
    cat << EOF
{
    "package": "$package",
    "version": "${PACKAGE_VERSIONS[$package]}",
    "dependencies": [${PACKAGE_DEPENDENCIES[$package]}],
    "source": "${PACKAGE_SOURCES[$package]}"
}
EOF
}

