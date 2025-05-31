#!/bin/bash
#
# Backup Verification System
# Verifies backup integrity and performs testing
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
VERIFY_DIR="/var/run/lfs-wrapper/backup/verify"
VERIFY_LOG="${VERIFY_DIR}/verify.log"
mkdir -p "$VERIFY_DIR"

# Verification settings
declare -r TEST_RESTORE_DIR="${VERIFY_DIR}/test_restore"
declare -r VERIFY_TEMP_DIR="${VERIFY_DIR}/temp"
declare -r MIN_FREE_SPACE=5120  # MB

# Verify backup integrity
verify_backup_integrity() {
    local backup_path="$1"
    local status=0
    
    log_info "Verifying backup integrity: ${backup_path}"
    
    # Check backup existence
    if [ ! -d "$backup_path" ]; then
        log_error "Backup not found: ${backup_path}"
        return 1
    fi
    
    # Check metadata
    if [ ! -f "${backup_path}/metadata" ]; then
        log_error "Backup metadata not found"
        return 1
    fi
    
    # Read metadata
    local backup_type
    backup_type=$(grep "^TYPE=" "${backup_path}/metadata" | cut -d'=' -f2)
    
    # Type-specific verification
    case "$backup_type" in
        "full"|"incremental")
            verify_tar_backup "$backup_path" || status=1
            ;;
        "snapshot")
            verify_snapshot_backup "$backup_path" || status=1
            ;;
        *)
            log_error "Unknown backup type: ${backup_type}"
            return 1
            ;;
    esac
    
    return $status
}

# Verify tar backup
verify_tar_backup() {
    local backup_path="$1"
    local status=0
    
    log_info "Verifying tar backup..."
    
    # Check tar file existence
    if [ ! -f "${backup_path}/backup.tar.gz" ]; then
        log_error "Backup archive not found"
        return 1
    fi
    
    # Test tar file integrity
    if ! tar -tzf "${backup_path}/backup.tar.gz" >/dev/null 2>&1; then
        log_error "Backup archive is corrupted"
        return 1
    fi
    
    # Verify checksums
    local stored_checksum current_checksum
    stored_checksum=$(grep "^CHECKSUM=" "${backup_path}/metadata" | cut -d'=' -f2)
    current_checksum=$(sha256sum "${backup_path}/backup.tar.gz" | cut -d' ' -f1)
    
    if [ "$stored_checksum" != "$current_checksum" ]; then
        log_error "Backup checksum verification failed"
        return 1
    fi
    
    return $status
}

# Verify snapshot backup
verify_snapshot_backup() {
    local backup_path="$1"
    local status=0
    
    log_info "Verifying snapshot backup..."
    
    # Check if snapshot is complete
    if [ ! -L "${backup_path}/../latest" ]; then
        log_error "Snapshot link missing"
        status=1
    fi
    
    # Verify files
    find "$backup_path" -type f ! -name "metadata" -print0 | while IFS= read -r -d '' file; do
        if [ ! -s "$file" ]; then
            log_error "Empty file found: ${file}"
            status=1
        fi
    done
    
    return $status
}

# Test backup restore
test_backup_restore() {
    local backup_path="$1"
    local status=0
    
    log_info "Testing backup restore: ${backup_path}"
    
    # Prepare test directory
    rm -rf "$TEST_RESTORE_DIR"
    mkdir -p "$TEST_RESTORE_DIR"
    
    # Read backup type
    local backup_type
    backup_type=$(grep "^TYPE=" "${backup_path}/metadata" | cut -d'=' -f2)
    
    # Perform test restore
    case "$backup_type" in
        "full"|"incremental")
            test_tar_restore "$backup_path" || status=1
            ;;
        "snapshot")
            test_snapshot_restore "$backup_path" || status=1
            ;;
        *)
            log_error "Unknown backup type: ${backup_type}"
            return 1
            ;;
    esac
    
    # Clean up
    rm -rf "$TEST_RESTORE_DIR"
    
    return $status
}

# Test tar backup restore
test_tar_restore() {
    local backup_path="$1"
    local status=0
    
    # Extract backup
    if ! tar -xzf "${backup_path}/backup.tar.gz" -C "$TEST_RESTORE_DIR"; then
        log_error "Failed to extract backup for testing"
        return 1
    fi
    
    # Verify extraction
    local expected_files actual_files
    expected_files=$(tar -tzf "${backup_path}/backup.tar.gz" | wc -l)
    actual_files=$(find "$TEST_RESTORE_DIR" -type f | wc -l)
    
    if [ "$expected_files" -ne "$actual_files" ]; then
        log_error "File count mismatch after test restore"
        status=1
    fi
    
    return $status
}

# Test snapshot restore
test_snapshot_restore() {
    local backup_path="$1"
    local status=0
    
    # Copy snapshot
    if ! cp -a "$backup_path/." "$TEST_RESTORE_DIR/"; then
        log_error "Failed to copy snapshot for testing"
        return 1
    fi
    
    # Verify copy
    if ! diff -r "$backup_path" "$TEST_RESTORE_DIR" >/dev/null; then
        log_error "Snapshot restore verification failed"
        status=1
    fi
    
    return $status
}

# Generate verification report
generate_verify_report() {
    local backup_path="$1"
    local report_file="${VERIFY_DIR}/verify_report.txt"
    
    {
        echo "=== Backup Verification Report ==="
        echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo
        echo "Backup: $(basename "$backup_path")"
        echo "Type: $(grep "^TYPE=" "${backup_path}/metadata" | cut -d'=' -f2)"
        echo "Created: $(grep "^TIMESTAMP=" "${backup_path}/metadata" | cut -d'=' -f2)"
        echo
        echo "Integrity Check:"
        if verify_backup_integrity "$backup_path"; then
            echo "- Passed"
        else
            echo "- Failed"
        fi
        echo
        echo "Restore Test:"
        if test_backup_restore "$backup_path"; then
            echo "- Passed"
        else
            echo "- Failed"
        fi
        echo
        echo "File Statistics:"
        echo "- Total Files: $(find "$backup_path" -type f | wc -l)"
        echo "- Total Size: $(du -sh "$backup_path" | cut -f1)"
        echo
        echo "Verification Details:"
        grep -v "^CHECKSUM=" "${backup_path}/metadata"
    } > "$report_file"
}

# Main entry point
main() {
    if [ "$#" -lt 2 ]; then
        log_error "Usage: $0 <command> <backup_path>"
        exit 1
    fi
    
    local command="$1"
    local backup_path="$2"
    
    case "$command" in
        verify)
            verify_backup_integrity "$backup_path"
            ;;
        test)
            test_backup_restore "$backup_path"
            ;;
        report)
            generate_verify_report "$backup_path"
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

