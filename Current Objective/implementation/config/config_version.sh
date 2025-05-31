#!/bin/bash
#
# Configuration Versioning System
# Manages configuration versions and history
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
VERSION_DIR="/var/run/lfs-wrapper/config/versions"
VERSION_LOG="${VERSION_DIR}/version_history.log"
mkdir -p "$VERSION_DIR"

# Create new configuration version
create_version() {
    local config_file="$1"
    local version="$2"
    local comment="$3"
    local timestamp
    timestamp=$(date -u +%Y%m%d%H%M%S)
    
    # Create version directory
    local version_path="${VERSION_DIR}/${version}"
    mkdir -p "$version_path"
    
    # Copy configuration
    cp "$config_file" "${version_path}/$(basename "$config_file")"
    
    # Create version metadata
    {
        echo "VERSION=${version}"
        echo "TIMESTAMP=${timestamp}"
        echo "COMMENT=${comment}"
        echo "CHECKSUM=$(sha256sum "$config_file" | cut -d' ' -f1)"
    } > "${version_path}/metadata"
    
    # Update version history
    {
        echo "VERSION: ${version}"
        echo "TIMESTAMP: ${timestamp}"
        echo "FILE: ${config_file}"
        echo "COMMENT: ${comment}"
        echo "---"
    } >> "$VERSION_LOG"
    
    log_info "Created configuration version ${version}"
}

# Get configuration version
get_version() {
    local config_file="$1"
    local version="$2"
    local output_file="$3"
    
    local version_path="${VERSION_DIR}/${version}"
    if [ ! -d "$version_path" ]; then
        log_error "Version not found: ${version}"
        return 1
    fi
    
    cp "${version_path}/$(basename "$config_file")" "$output_file"
    log_info "Retrieved configuration version ${version}"
}

# List all versions
list_versions() {
    local config_file="$1"
    
    if [ ! -f "$VERSION_LOG" ]; then
        log_error "No version history found"
        return 1
    fi
    
    awk '/^VERSION: / { version=$2 }
         /^TIMESTAMP: / { timestamp=$2 }
         /^COMMENT: / {
             comment=substr($0, 9)
             printf "%-10s  %-20s  %s\n", version, timestamp, comment
         }' "$VERSION_LOG"
}

# Compare versions
compare_versions() {
    local old_version="$1"
    local new_version="$2"
    
    local old_path="${VERSION_DIR}/${old_version}"
    local new_path="${VERSION_DIR}/${new_version}"
    
    if [ ! -d "$old_path" ] || [ ! -d "$new_path" ]; then
        log_error "Version not found"
        return 1
    fi
    
    # Compare configuration files
    for file in "$old_path"/*; do
        [ -f "$file" ] || continue
        [ "$(basename "$file")" = "metadata" ] && continue
        
        local new_file="${new_path}/$(basename "$file")"
        if [ -f "$new_file" ]; then
            diff -u "$file" "$new_file" || true
        fi
    done
}

# Check if version exists
version_exists() {
    local version="$1"
    [ -d "${VERSION_DIR}/${version}" ]
}

# Get latest version
get_latest_version() {
    local config_file="$1"
    
    if [ ! -f "$VERSION_LOG" ]; then
        echo "0.0.0"
        return
    fi
    
    awk '/^VERSION: / { version=$2 } END { print version }' "$VERSION_LOG"
}

# Generate next version number
generate_next_version() {
    local current_version
    current_version=$(get_latest_version)
    
    local major minor patch
    IFS='.' read -r major minor patch <<< "$current_version"
    
    # Increment patch version
    patch=$((patch + 1))
    echo "${major}.${minor}.${patch}"
}

# Main entry point
main() {
    if [ "$#" -lt 2 ]; then
        log_error "Usage: $0 <command> <config_file> [args...]"
        exit 1
    fi
    
    local command="$1"
    local config_file="$2"
    shift 2
    
    case "$command" in
        create)
            if [ "$#" -lt 2 ]; then
                log_error "Usage: $0 create <config_file> <version> <comment>"
                exit 1
            fi
            create_version "$config_file" "$1" "$2"
            ;;
        get)
            if [ "$#" -lt 2 ]; then
                log_error "Usage: $0 get <config_file> <version> <output_file>"
                exit 1
            fi
            get_version "$config_file" "$1" "$2"
            ;;
        list)
            list_versions "$config_file"
            ;;
        compare)
            if [ "$#" -lt 2 ]; then
                log_error "Usage: $0 compare <old_version> <new_version>"
                exit 1
            fi
            compare_versions "$1" "$2"
            ;;
        *)
            log_error "Unknown command: ${command}"
            exit 1
            ;;
    esac
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

