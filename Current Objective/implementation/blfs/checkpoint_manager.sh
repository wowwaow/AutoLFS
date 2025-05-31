#!/bin/bash
#
# BLFS Checkpoint Management System
# Manages build state preservation and restoration
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
BLFS_DIR="/var/run/lfs-wrapper/blfs"
CHECKPOINT_DIR="${BLFS_DIR}/checkpoints"
RESTORE_DIR="${BLFS_DIR}/restore"
mkdir -p "$CHECKPOINT_DIR" "$RESTORE_DIR"

# State file format version
declare -r STATE_VERSION="1.0"

# Create checkpoint
create_checkpoint() {
    local package="$1"
    local build_dir="$2"
    local timestamp
    timestamp=$(date -u +%Y%m%d%H%M%S)
    local checkpoint_path="${CHECKPOINT_DIR}/${package}_${timestamp}"
    
    log_info "Creating checkpoint for: ${package}"
    
    # Create checkpoint directory
    mkdir -p "$checkpoint_path"
    
    # Preserve build directory state
    tar -czf "${checkpoint_path}/build_state.tar.gz" -C "$build_dir" .
    
    # Save environment variables
    env > "${checkpoint_path}/environment.env"
    
    # Save package state
    get_package_state "$package" > "${checkpoint_path}/package_state.json"
    
    # Save system state
    {
        echo "STATE_VERSION=${STATE_VERSION}"
        echo "PACKAGE=${package}"
        echo "TIMESTAMP=${timestamp}"
        echo "BUILD_DIR=${build_dir}"
        echo "CHECKSUM=$(find "$build_dir" -type f -exec sha256sum {} \; | sort | sha256sum | cut -d' ' -f1)"
    } > "${checkpoint_path}/metadata"
    
    # Create checkpoint index entry
    {
        echo "CHECKPOINT: ${package}_${timestamp}"
        echo "PACKAGE: ${package}"
        echo "TIMESTAMP: ${timestamp}"
        echo "SIZE: $(du -sh "${checkpoint_path}" | cut -f1)"
        echo "---"
    } >> "${CHECKPOINT_DIR}/index.log"
    
    log_info "Checkpoint created: ${package}_${timestamp}"
    return 0
}

# Restore from checkpoint
restore_checkpoint() {
    local checkpoint_id="$1"
    local target_dir="$2"
    local checkpoint_path="${CHECKPOINT_DIR}/${checkpoint_id}"
    
    log_info "Restoring from checkpoint: ${checkpoint_id}"
    
    # Verify checkpoint
    if ! verify_checkpoint "$checkpoint_id"; then
        log_error "Checkpoint verification failed"
        return 1
    fi
    
    # Create backup of current state
    create_restoration_point "$target_dir"
    
    # Clear target directory
    rm -rf "${target_dir:?}"/*
    
    # Restore build state
    tar -xzf "${checkpoint_path}/build_state.tar.gz" -C "$target_dir"
    
    # Restore environment
    while IFS='=' read -r key value; do
        export "${key}=${value}"
    done < "${checkpoint_path}/environment.env"
    
    # Restore package state
    local package
    package=$(grep "^PACKAGE=" "${checkpoint_path}/metadata" | cut -d'=' -f2)
    cp "${checkpoint_path}/package_state.json" "$(get_package_state_path "$package")"
    
    log_info "Checkpoint restored: ${checkpoint_id}"
    return 0
}

# Verify checkpoint integrity
verify_checkpoint() {
    local checkpoint_id="$1"
    local checkpoint_path="${CHECKPOINT_DIR}/${checkpoint_id}"
    local status=0
    
    log_info "Verifying checkpoint: ${checkpoint_id}"
    
    # Check required files
    local required_files=(
        "metadata"
        "build_state.tar.gz"
        "environment.env"
        "package_state.json"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "${checkpoint_path}/${file}" ]; then
            log_error "Missing required file: ${file}"
            status=1
        fi
    done
    
    # Verify metadata version
    local version
    version=$(grep "^STATE_VERSION=" "${checkpoint_path}/metadata" | cut -d'=' -f2)
    if [ "$version" != "$STATE_VERSION" ]; then
        log_error "Invalid state version: ${version}"
        status=1
    fi
    
    # Verify build state integrity
    local stored_checksum current_checksum
    stored_checksum=$(grep "^CHECKSUM=" "${checkpoint_path}/metadata" | cut -d'=' -f2)
    current_checksum=$(tar -xzf "${checkpoint_path}/build_state.tar.gz" -O | sha256sum | cut -d' ' -f1)
    
    if [ "$stored_checksum" != "$current_checksum" ]; then
        log_error "Checkpoint integrity check failed"
        status=1
    fi
    
    return $status
}

# Create restoration point
create_restoration_point() {
    local target_dir="$1"
    local timestamp
    timestamp=$(date -u +%Y%m%d%H%M%S)
    local restore_point="${RESTORE_DIR}/restore_${timestamp}"
    
    log_info "Creating restoration point..."
    
    # Save current state
    if [ -d "$target_dir" ]; then
        mkdir -p "$restore_point"
        tar -czf "${restore_point}/state.tar.gz" -C "$target_dir" .
        
        # Save metadata
        {
            echo "TIMESTAMP=${timestamp}"
            echo "TARGET=${target_dir}"
            echo "SIZE=$(du -sh "${restore_point}/state.tar.gz" | cut -f1)"
            echo "CHECKSUM=$(sha256sum "${restore_point}/state.tar.gz" | cut -d' ' -f1)"
        } > "${restore_point}/metadata"
    fi
}

# Clean old checkpoints
clean_checkpoints() {
    local days="$1"
    local timestamp_threshold
    timestamp_threshold=$(date -d "$days days ago" +%Y%m%d%H%M%S)
    
    log_info "Cleaning checkpoints older than ${days} days..."
    
    # Find and remove old checkpoints
    find "$CHECKPOINT_DIR" -maxdepth 1 -type d -name "*_*" | while read -r checkpoint; do
        local timestamp
        timestamp=$(basename "$checkpoint" | cut -d'_' -f2)
        
        if [ "$timestamp" -lt "$timestamp_threshold" ]; then
            log_info "Removing old checkpoint: $(basename "$checkpoint")"
            rm -rf "$checkpoint"
        fi
    done
    
    # Clean old restoration points
    find "$RESTORE_DIR" -maxdepth 1 -type d -name "restore_*" -mtime +"$days" -delete
    
    # Update index
    update_checkpoint_index
}

# Update checkpoint index
update_checkpoint_index() {
    local index_file="${CHECKPOINT_DIR}/index.log"
    local temp_index
    temp_index=$(mktemp)
    
    # Rebuild index from existing checkpoints
    {
        echo "# Checkpoint Index"
        echo "# Updated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo
        
        find "$CHECKPOINT_DIR" -maxdepth 1 -type d -name "*_*" | while read -r checkpoint; do
            local checkpoint_id
            checkpoint_id=$(basename "$checkpoint")
            local package timestamp
            package=$(grep "^PACKAGE=" "${checkpoint}/metadata" | cut -d'=' -f2)
            timestamp=$(grep "^TIMESTAMP=" "${checkpoint}/metadata" | cut -d'=' -f2)
            
            echo "CHECKPOINT: ${checkpoint_id}"
            echo "PACKAGE: ${package}"
            echo "TIMESTAMP: ${timestamp}"
            echo "SIZE: $(du -sh "$checkpoint" | cut -f1)"
            echo "---"
        done
    } > "$temp_index"
    
    mv "$temp_index" "$index_file"
}

# List checkpoints
list_checkpoints() {
    local format="${1:-simple}"
    
    case "$format" in
        simple)
            find "$CHECKPOINT_DIR" -maxdepth 1 -type d -name "*_*" -exec basename {} \;
            ;;
        detailed)
            if [ -f "${CHECKPOINT_DIR}/index.log" ]; then
                cat "${CHECKPOINT_DIR}/index.log"
            else
                log_error "Checkpoint index not found"
                return 1
            fi
            ;;
        json)
            {
                echo "{"
                find "$CHECKPOINT_DIR" -maxdepth 1 -type d -name "*_*" | while read -r checkpoint; do
                    local checkpoint_id
                    checkpoint_id=$(basename "$checkpoint")
                    jq -n --arg id "$checkpoint_id" \
                        --arg pkg "$(grep '^PACKAGE=' "${checkpoint}/metadata" | cut -d'=' -f2)" \
                        --arg ts "$(grep '^TIMESTAMP=' "${checkpoint}/metadata" | cut -d'=' -f2)" \
                        --arg size "$(du -sh "$checkpoint" | cut -f1)" \
                        '{"id": $id, "package": $pkg, "timestamp": $ts, "size": $size}'
                done | paste -sd "," -
                echo "}"
            }
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
            if [ "$#" -lt 2 ]; then
                log_error "Usage: $0 create <package> <build_dir>"
                exit 1
            fi
            create_checkpoint "$@"
            ;;
        restore)
            if [ "$#" -lt 2 ]; then
                log_error "Usage: $0 restore <checkpoint_id> <target_dir>"
                exit 1
            fi
            restore_checkpoint "$@"
            ;;
        verify)
            if [ "$#" -lt 1 ]; then
                log_error "Usage: $0 verify <checkpoint_id>"
                exit 1
            fi
            verify_checkpoint "$1"
            ;;
        clean)
            if [ "$#" -lt 1 ]; then
                log_error "Usage: $0 clean <days>"
                exit 1
            fi
            clean_checkpoints "$1"
            ;;
        list)
            list_checkpoints "${1:-simple}"
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

