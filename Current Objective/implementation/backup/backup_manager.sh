#!/bin/bash
#
# Backup Management System
# Manages system-wide backups and snapshots
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
BACKUP_DIR="/var/run/lfs-wrapper/backup"
BACKUP_LOG="${BACKUP_DIR}/backup.log"
mkdir -p "$BACKUP_DIR"/{daily,weekly,monthly,snapshots}

# Backup types
declare -r BACKUP_TYPE_FULL="full"
declare -r BACKUP_TYPE_INCREMENTAL="incremental"
declare -r BACKUP_TYPE_SNAPSHOT="snapshot"

# Backup settings
declare -r MAX_DAILY_BACKUPS=7
declare -r MAX_WEEKLY_BACKUPS=4
declare -r MAX_MONTHLY_BACKUPS=12
declare -r MIN_FREE_SPACE=10240  # MB

# Create backup
create_backup() {
    local source_dir="$1"
    local backup_type="$2"
    local comment="${3:-}"
    local timestamp
    timestamp=$(date -u +%Y%m%d%H%M%S)
    local backup_path
    
    case "$backup_type" in
        "$BACKUP_TYPE_FULL")
            backup_path="${BACKUP_DIR}/full_${timestamp}"
            create_full_backup "$source_dir" "$backup_path"
            ;;
        "$BACKUP_TYPE_INCREMENTAL")
            backup_path="${BACKUP_DIR}/inc_${timestamp}"
            create_incremental_backup "$source_dir" "$backup_path"
            ;;
        "$BACKUP_TYPE_SNAPSHOT")
            backup_path="${BACKUP_DIR}/snapshots/snap_${timestamp}"
            create_snapshot "$source_dir" "$backup_path"
            ;;
        *)
            log_error "Unknown backup type: ${backup_type}"
            return 1
            ;;
    esac
    
    # Create backup metadata
    create_backup_metadata "$backup_path" "$backup_type" "$source_dir" "$comment"
    
    # Update backup history
    update_backup_history "$backup_path" "$backup_type" "$comment"
    
    # Manage retention
    manage_backup_retention "$backup_type"
    
    log_info "Backup created: $(basename "$backup_path")"
    return 0
}

# Create full backup
create_full_backup() {
    local source_dir="$1"
    local backup_path="$2"
    
    log_info "Creating full backup of: ${source_dir}"
    
    # Create backup directory
    mkdir -p "$backup_path"
    
    # Create tar archive with progress
    tar --create \
        --verbose \
        --preserve-permissions \
        --acls \
        --xattrs \
        --gzip \
        --file "${backup_path}/backup.tar.gz" \
        --directory "$source_dir" \
        . 2> >(log_debug) | \
        while read -r file; do
            log_debug "Backing up: ${file}"
        done
}

# Create incremental backup
create_incremental_backup() {
    local source_dir="$1"
    local backup_path="$2"
    
    log_info "Creating incremental backup of: ${source_dir}"
    
    # Find latest full backup for reference
    local latest_full
    latest_full=$(find "${BACKUP_DIR}" -maxdepth 1 -name "full_*" -type d | sort | tail -n1)
    
    if [ -z "$latest_full" ]; then
        log_error "No full backup found for incremental backup"
        return 1
    fi
    
    # Create backup directory
    mkdir -p "$backup_path"
    
    # Create incremental backup
    tar --create \
        --verbose \
        --preserve-permissions \
        --acls \
        --xattrs \
        --gzip \
        --listed-incremental "${latest_full}/snapshot.snar" \
        --file "${backup_path}/backup.tar.gz" \
        --directory "$source_dir" \
        . 2> >(log_debug) | \
        while read -r file; do
            log_debug "Backing up: ${file}"
        done
}

# Create snapshot
create_snapshot() {
    local source_dir="$1"
    local backup_path="$2"
    
    log_info "Creating snapshot of: ${source_dir}"
    
    # Create snapshot directory
    mkdir -p "$backup_path"
    
    # Use rsync for snapshot
    rsync -av \
        --delete \
        --link-dest="${BACKUP_DIR}/snapshots/latest" \
        "$source_dir/" \
        "$backup_path/" \
        2> >(log_debug)
    
    # Update latest snapshot link
    ln -snf "$backup_path" "${BACKUP_DIR}/snapshots/latest"
}

# Create backup metadata
create_backup_metadata() {
    local backup_path="$1"
    local backup_type="$2"
    local source_dir="$3"
    local comment="$4"
    
    {
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        echo "TYPE=${backup_type}"
        echo "SOURCE=${source_dir}"
        echo "COMMENT=${comment}"
        echo "SIZE=$(du -sh "$backup_path" | cut -f1)"
        echo "FILES=$(find "$backup_path" -type f | wc -l)"
        echo "CHECKSUM=$(find "$backup_path" -type f -exec sha256sum {} \; | sort | sha256sum | cut -d' ' -f1)"
    } > "${backup_path}/metadata"
}

# Update backup history
update_backup_history() {
    local backup_path="$1"
    local backup_type="$2"
    local comment="$3"
    
    {
        echo "BACKUP: $(basename "$backup_path")"
        echo "TYPE: ${backup_type}"
        echo "TIMESTAMP: $(date -u +%Y%m%d%H%M%S)"
        echo "COMMENT: ${comment}"
        echo "---"
    } >> "${BACKUP_DIR}/backup_history.log"
}

# Manage backup retention
manage_backup_retention() {
    local backup_type="$1"
    
    case "$backup_type" in
        "$BACKUP_TYPE_FULL")
            # Keep only specified number of backups
            local daily_backups
            daily_backups=$(find "${BACKUP_DIR}" -maxdepth 1 -name "full_*" -type d | sort)
            local count
            count=$(echo "$daily_backups" | wc -l)
            
            if [ "$count" -gt "$MAX_DAILY_BACKUPS" ]; then
                echo "$daily_backups" | head -n $(( count - MAX_DAILY_BACKUPS )) | while read -r backup; do
                    log_info "Removing old backup: $(basename "$backup")"
                    rm -rf "$backup"
                done
            fi
            ;;
        "$BACKUP_TYPE_INCREMENTAL")
            # Keep incrementals only if their full backup exists
            find "${BACKUP_DIR}" -maxdepth 1 -name "inc_*" -type d | while read -r inc; do
                local timestamp
                timestamp=$(echo "$inc" | grep -o "[0-9]\{14\}")
                if [ ! -d "${BACKUP_DIR}/full_${timestamp}" ]; then
                    log_info "Removing orphaned incremental backup: $(basename "$inc")"
                    rm -rf "$inc"
                fi
            done
            ;;
        "$BACKUP_TYPE_SNAPSHOT")
            # Keep only recent snapshots
            find "${BACKUP_DIR}/snapshots" -maxdepth 1 -name "snap_*" -type d -mtime +7 -delete
            ;;
    esac
}

# Verify backup
verify_backup() {
    local backup_path="$1"
    
    log_info "Verifying backup: ${backup_path}"
    
    # Check metadata file
    if [ ! -f "${backup_path}/metadata" ]; then
        log_error "Backup metadata not found"
        return 1
    fi
    
    # Verify checksum
    local stored_checksum current_checksum
    stored_checksum=$(grep "^CHECKSUM=" "${backup_path}/metadata" | cut -d'=' -f2)
    current_checksum=$(find "$backup_path" -type f ! -name metadata -exec sha256sum {} \; | sort | sha256sum | cut -d' ' -f1)
    
    if [ "$stored_checksum" != "$current_checksum" ]; then
        log_error "Backup integrity check failed"
        return 1
    fi
    
    log_info "Backup verification successful"
    return 0
}

# List backups
list_backups() {
    if [ ! -f "${BACKUP_DIR}/backup_history.log" ]; then
        log_error "No backup history found"
        return 1
    fi
    
    awk '/^BACKUP: / { backup=$2 }
         /^TYPE: / { type=$2 }
         /^TIMESTAMP: / { timestamp=$2 }
         /^COMMENT: / {
             comment=substr($0, 9)
             printf "%-30s  %-12s  %-20s  %s\n", backup, type, timestamp, comment
         }' "${BACKUP_DIR}/backup_history.log"
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
                log_error "Usage: $0 create <source_dir> <type> [comment]"
                exit 1
            fi
            create_backup "$@"
            ;;
        verify)
            if [ "$#" -lt 1 ]; then
                log_error "Usage: $0 verify <backup_path>"
                exit 1
            fi
            verify_backup "$1"
            ;;
        list)
            list_backups
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

