#!/bin/bash
#
# BLFS Package Management System
# Manages BLFS packages, sources, and metadata
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
BLFS_DIR="/var/run/lfs-wrapper/blfs"
SOURCES_DIR="${BLFS_DIR}/sources"
ARCHIVES_DIR="${BLFS_DIR}/archives"
METADATA_DIR="${BLFS_DIR}/metadata"
STATE_DIR="${BLFS_DIR}/state"

# Ensure required directories exist
for dir in "$SOURCES_DIR" "$ARCHIVES_DIR" "$METADATA_DIR" "$STATE_DIR"; do
    mkdir -p "$dir"
done

# Package metadata format version
declare -r METADATA_VERSION="1.0"

# Package state constants
declare -r STATE_NOT_INSTALLED="not-installed"
declare -r STATE_INSTALLED="installed"
declare -r STATE_NEEDS_UPDATE="needs-update"
declare -r STATE_BROKEN="broken"

# Load package metadata
load_package_metadata() {
    local package="$1"
    local metadata_file="${METADATA_DIR}/${package}/metadata.json"
    
    if [ ! -f "$metadata_file" ]; then
        log_error "Metadata not found for package: ${package}"
        return 1
    fi
    
    # Validate metadata format
    if ! jq -e '.version' "$metadata_file" >/dev/null 2>&1; then
        log_error "Invalid metadata format for package: ${package}"
        return 1
    fi
    
    # Export metadata as environment variables
    while IFS='=' read -r key value; do
        export "PKG_${key}=${value}"
    done < <(jq -r 'to_entries | .[] | "\(.key)=\(.value)"' "$metadata_file")
    
    return 0
}

# Create package metadata
create_package_metadata() {
    local package="$1"
    local version="$2"
    local url="$3"
    local metadata_dir="${METADATA_DIR}/${package}"
    
    mkdir -p "$metadata_dir"
    
    # Create metadata file
    cat > "${metadata_dir}/metadata.json" << EOF
{
    "name": "${package}",
    "version": "${version}",
    "metadata_version": "${METADATA_VERSION}",
    "url": "${url}",
    "timestamp": "$(date -u +%Y%m%d%H%M%S)",
    "dependencies": {
        "required": [],
        "optional": [],
        "runtime": []
    },
    "checksums": {
        "md5": "",
        "sha256": "",
        "sha512": ""
    },
    "build": {
        "configure_options": "",
        "make_options": "",
        "install_options": ""
    }
}
EOF
}

# Update package metadata
update_package_metadata() {
    local package="$1"
    local key="$2"
    local value="$3"
    local metadata_file="${METADATA_DIR}/${package}/metadata.json"
    
    if [ ! -f "$metadata_file" ]; then
        log_error "Metadata not found for package: ${package}"
        return 1
    fi
    
    # Update metadata using jq
    local temp_file
    temp_file=$(mktemp)
    if ! jq --arg key "$key" --arg value "$value" \
        'setpath($key | split("."); $value)' "$metadata_file" > "$temp_file"; then
        rm -f "$temp_file"
        return 1
    fi
    
    mv "$temp_file" "$metadata_file"
}

# Download package source
download_package_source() {
    local package="$1"
    local version="$2"
    local url="$3"
    local status=0
    
    log_info "Downloading source for package: ${package}"
    
    # Create source directory
    local source_dir="${SOURCES_DIR}/${package}"
    mkdir -p "$source_dir"
    
    # Download source
    local filename
    filename=$(basename "$url")
    if ! wget -q --show-progress -O "${source_dir}/${filename}" "$url"; then
        log_error "Failed to download source: ${url}"
        status=1
    fi
    
    # Calculate checksums
    if [ $status -eq 0 ]; then
        calculate_checksums "$package" "${source_dir}/${filename}"
    fi
    
    return $status
}

# Calculate package checksums
calculate_checksums() {
    local package="$1"
    local file="$2"
    
    log_info "Calculating checksums for: ${file}"
    
    # Calculate checksums
    local md5sum
    local sha256sum
    local sha512sum
    md5sum=$(md5sum "$file" | cut -d' ' -f1)
    sha256sum=$(sha256sum "$file" | cut -d' ' -f1)
    sha512sum=$(sha512sum "$file" | cut -d' ' -f1)
    
    # Update metadata
    update_package_metadata "$package" "checksums.md5" "$md5sum"
    update_package_metadata "$package" "checksums.sha256" "$sha256sum"
    update_package_metadata "$package" "checksums.sha512" "$sha512sum"
}

# Verify package source
verify_package_source() {
    local package="$1"
    local file="$2"
    local status=0
    
    log_info "Verifying package source: ${file}"
    
    # Load metadata
    load_package_metadata "$package" || return 1
    
    # Verify checksums
    local actual_md5
    local actual_sha256
    local actual_sha512
    actual_md5=$(md5sum "$file" | cut -d' ' -f1)
    actual_sha256=$(sha256sum "$file" | cut -d' ' -f1)
    actual_sha512=$(sha512sum "$file" | cut -d' ' -f1)
    
    if [ "$actual_md5" != "${PKG_checksums_md5}" ]; then
        log_error "MD5 checksum mismatch"
        status=1
    fi
    
    if [ "$actual_sha256" != "${PKG_checksums_sha256}" ]; then
        log_error "SHA256 checksum mismatch"
        status=1
    fi
    
    if [ "$actual_sha512" != "${PKG_checksums_sha512}" ]; then
        log_error "SHA512 checksum mismatch"
        status=1
    fi
    
    return $status
}

# Archive package source
archive_package_source() {
    local package="$1"
    local version="$2"
    local status=0
    
    log_info "Archiving source for package: ${package}"
    
    # Create archive directory
    local archive_dir="${ARCHIVES_DIR}/${package}"
    mkdir -p "$archive_dir"
    
    # Archive source files
    local source_dir="${SOURCES_DIR}/${package}"
    local archive_file="${archive_dir}/${package}-${version}.tar.gz"
    
    if ! tar -czf "$archive_file" -C "$source_dir" .; then
        log_error "Failed to create source archive"
        status=1
    fi
    
    # Create archive metadata
    if [ $status -eq 0 ]; then
        {
            echo "PACKAGE=${package}"
            echo "VERSION=${version}"
            echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
            echo "SIZE=$(du -h "$archive_file" | cut -f1)"
            echo "CHECKSUM=$(sha256sum "$archive_file" | cut -d' ' -f1)"
        } > "${archive_file}.meta"
    fi
    
    return $status
}

# Track package state
track_package_state() {
    local package="$1"
    local state="$2"
    local state_file="${STATE_DIR}/${package}.state"
    
    # Update state file
    {
        echo "PACKAGE=${package}"
        echo "STATE=${state}"
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
    } > "$state_file"
    
    # Log state change
    log_info "Package ${package} state changed to: ${state}"
}

# Get package state
get_package_state() {
    local package="$1"
    local state_file="${STATE_DIR}/${package}.state"
    
    if [ ! -f "$state_file" ]; then
        echo "$STATE_NOT_INSTALLED"
        return 0
    fi
    
    grep "^STATE=" "$state_file" | cut -d'=' -f2
}

# Check if package needs update
check_package_update() {
    local package="$1"
    local current_version="$2"
    
    # Load metadata
    load_package_metadata "$package" || return 1
    
    # Compare versions
    if version_compare "$current_version" "${PKG_version}"; then
        track_package_state "$package" "$STATE_NEEDS_UPDATE"
        return 0
    fi
    
    return 1
}

# List all packages
list_packages() {
    local format="${1:-simple}"
    local metadata_files
    
    case "$format" in
        simple)
            find "$METADATA_DIR" -type f -name "metadata.json" -exec dirname {} \; | \
                xargs -n1 basename
            ;;
        detailed)
            find "$METADATA_DIR" -type f -name "metadata.json" | while read -r metadata; do
                local package
                package=$(dirname "$metadata" | xargs basename)
                local state
                state=$(get_package_state "$package")
                jq -r --arg pkg "$package" --arg state "$state" \
                    '"\($pkg):\(.version):\($state)"' "$metadata"
            done
            ;;
        json)
            echo "{"
            find "$METADATA_DIR" -type f -name "metadata.json" | while read -r metadata; do
                local package
                package=$(dirname "$metadata" | xargs basename)
                local state
                state=$(get_package_state "$package")
                jq -r --arg pkg "$package" --arg state "$state" \
                    '"\($pkg)": . + {"state": $state}' "$metadata"
            done
            echo "}"
            ;;
        *)
            log_error "Unknown format: ${format}"
            return 1
            ;;
    esac
}

# Main entry point
main() {
    if [ "$#" -lt 2 ]; then
        log_error "Usage: $0 <command> [args...]"
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        create)
            if [ "$#" -lt 3 ]; then
                log_error "Usage: $0 create <package> <version> <url>"
                exit 1
            fi
            create_package_metadata "$@"
            ;;
        download)
            if [ "$#" -lt 3 ]; then
                log_error "Usage: $0 download <package> <version> <url>"
                exit 1
            fi
            download_package_source "$@"
            ;;
        verify)
            if [ "$#" -lt 2 ]; then
                log_error "Usage: $0 verify <package> <file>"
                exit 1
            fi
            verify_package_source "$@"
            ;;
        archive)
            if [ "$#" -lt 2 ]; then
                log_error "Usage: $0 archive <package> <version>"
                exit 1
            fi
            archive_package_source "$@"
            ;;
        update)
            if [ "$#" -lt 2 ]; then
                log_error "Usage: $0 update <package> <current_version>"
                exit 1
            fi
            check_package_update "$@"
            ;;
        list)
            list_packages "${1:-simple}"
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

