#!/bin/bash
#
# Configuration Backup System
# Manages configuration backups and restoration
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
BACKUP_DIR="/var/run/lfs-wrapper/config/backups"
BACKUP_LOG="${BACKUP_DIR}/backup_history.log"
mkdir -p "$BACKUP_DIR"

# Create configuration backup
create_backup() {
    local config_dir="$1"
    local comment="${2:-}"
    local timestamp
    timestamp=$(date -u +%Y%m%d%H%M%S)
    local backup_path="${BACKUP_DIR}/backup_${timestamp}"
    
    log_info "Creating configuration backup..."
    
    # Create backup directory
    mkdir -p "$backup_path"
    
    # Copy configuration files
    cp -r "$config_dir"/* "$backup_path/"
    
    # Create backup metadata
    {
        echo "TIMESTAMP=${timestamp}"
        echo "SOURCE=${config_dir}"
        echo "COMMENT=${comment}"
        echo "FILES=$(find "$backup_path" -type f | wc -l)"
        echo "SIZE=$(du -sh "$backup_path" | cut -f1)"
        echo "CHECKSUM=$(find "$backup_path" -type f -exec sha256sum {} \; | sort | sha256sum | cut -d' ' -f1)"
    } > "${backup_path}/metadata"
    
    # Update backup history
    {
        echo "BACKUP: backup_${timestamp}"
        echo "TIMESTAMP: ${timestamp}"
        echo "SOURCE: ${config_dir}"
        echo "COMMENT: ${comment}"
        echo "---"
    } >> "$BACKUP_LOG"
    
    log_info "Backup created: backup_${timestamp}"
    return 0
}

# Restore configuration from backup
restore_backup() {
    local backup_id="$1"
    local target_dir="$2"
    local backup_path="${BACKUP_DIR}/${backup_id}"
    
    if [ ! -d "$backup_path" ]; then
        log_error "Backup not found: ${backup_id}"
        return 1
    fi
    
    log_info "Restoring configuration from backup: ${backup_id}"
    
    # Verify backup integrity
    local stored_checksum
    local current_checksum
    stored_checksum=$(grep "^CHECKSUM=" "${backup_path}/metadata" | cut -d'=' -f2)
    current_checksum=$(find "$backup_path" -type f ! -name metadata -exec sha256sum {} \; | sort | sha256sum | cut -d' ' -f1)
    
    if [ "$stored_checksum" != "$current_checksum" ]; then
        log_error "Backup integrity check failed"
        return 1
    fi
    
    # Create restoration point
    create_backup "$target_dir" "Auto-backup before restoration of ${backup_id}"
    
    # Restore files
    rm -rf "${target_dir:?}"/*
    cp -r "$backup_path"/* "$target_dir/"
    rm -f "${target_dir}/metadata"
    
    log_info "Configuration restored from backup: ${backup_id}"
    return 0
}

# List available backups
list_backups() {
    if [ ! -f "$BACKUP_LOG" ]; then
        log_error "No backup history found"
        return 1
    fi
    
    awk '/^BACKUP: / { backup=$2 }
         /^TIMESTAMP: / { timestamp=$2 }
         /^COMMENT: / {
             comment=substr($0, 9)
             printf "%-30s  %-20s  %s\n", backup, timestamp, comment
         }' "$BACKUP_LOG"
}

# Verify backup integrity
verify_backup() {
    local backup_id="$1"
    local backup_path="${BACKUP_DIR}/${backup_id}"
    
    if [ ! -d "$backup_path" ]; then
        log_error "Backup not found: ${backup_id}"
        return 1
    fi
    
    log_info "Verifying backup integrity: ${backup_id}"
    
    # Check metadata file
    if [ ! -f "${backup_path}/metadata" ]; then
        log_error "Backup metadata not found"
        return 1
    fi
    
    # Verify checksum
    local stored_checksum
    local current_checksum
    stored_checksum=$(grep "^CHECKSUM=" "${backup_path}/metadata" | cut -d'=' -f2)
    current_checksum=$(find "$backup_path" -type f ! -name metadata -exec sha256sum {} \; | sort | sha256sum | cut -d' ' -f1)
    
    if [ "$stored_checksum" = "$current_checksum" ]; then
        log_info "Backup integrity verified: ${backup_id}"
        return 0
    else
        log_error "Backup integrity check failed: ${backup_id}"
        return 1
    fi
}

# Clean old backups
clean_backups() {
    local days="$1"
    local timestamp_threshold
    timestamp_threshold=$(date -d "$days days ago" +%Y%m%d%H%M%S)
    
    log_info "Cleaning backups older than ${days} days..."
    
    find "$BACKUP_DIR" -maxdepth 1 -type d -name "backup_*" | while read -r backup_dir; do
        local backup_timestamp
        backup_timestamp=$(basename "$backup_dir" | cut -d'_' -f2)
        
        if [ "$backup_timestamp" -lt "$timestamp_threshold" ]; then
            log_info "Removing old backup: $(basename "$backup_dir")"
            rm -rf "$backup_dir"
        fi
    done
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
            if [ "$#" -lt 1 ]; then
                log_error "Usage: $0 create <config_dir> [comment]"
                exit 1
            fi
            create_backup "$@"
            ;;
        restore)
            if [ "$#" -lt 2 ]; then
                log_error "Usage: $0 restore <backup_id> <target_dir>"
                exit 1
            fi
            restore_backup "$@"
            ;;
        list)
            list_backups
            ;;
        verify)
            if [ "$#" -lt 1 ]; then
                log_error "Usage: $0 verify <backup_id>"
                exit 1
            fi
            verify_backup "$1"
            ;;
        clean)
            if [ "$#" -lt 1 ]; then
                log_error "Usage: $0 clean <days>"
                exit 1
            fi
            clean_backups "$1"
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

