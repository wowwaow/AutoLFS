#!/bin/bash
#
# System Cleanup Routines
# Manages system cleanup and maintenance tasks
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
CLEANUP_DIR="/var/run/lfs-wrapper/maintenance/cleanup"
CLEANUP_LOG="${CLEANUP_DIR}/cleanup.log"
mkdir -p "$CLEANUP_DIR"

# Cleanup thresholds
declare -r MAX_LOG_AGE=30        # days
declare -r MAX_TEMP_AGE=7        # days
declare -r MAX_BACKUP_AGE=90     # days
declare -r MAX_CACHE_SIZE=5120   # MB
declare -r MIN_FREE_SPACE=10240  # MB (10GB)

# Cleanup temporary files
cleanup_temp_files() {
    local status=0
    local temp_dirs=(
        "/tmp"
        "/var/tmp"
        "${CLEANUP_DIR}/temp"
    )
    
    log_info "Cleaning temporary files..."
    
    for dir in "${temp_dirs[@]}"; do
        if [ -d "$dir" ]; then
            find "$dir" -type f -atime +"$MAX_TEMP_AGE" -delete || status=1
            find "$dir" -type d -empty -delete || status=1
        fi
    done
    
    return $status
}

# Cleanup build artifacts
cleanup_build_artifacts() {
    local status=0
    local build_dir="$1"
    
    log_info "Cleaning build artifacts in: ${build_dir}"
    
    # Remove object files and temporary build artifacts
    find "$build_dir" \( \
        -name "*.o" -o \
        -name "*.lo" -o \
        -name "*.la" -o \
        -name "*.a" -o \
        -name "*.so" -o \
        -name "*.pyc" -o \
        -name "__pycache__" -o \
        -name "*.class" \
    \) -delete || status=1
    
    # Clean empty directories
    find "$build_dir" -type d -empty -delete || status=1
    
    return $status
}

# Cleanup old logs
cleanup_old_logs() {
    local status=0
    local log_dir="$1"
    
    log_info "Cleaning old logs in: ${log_dir}"
    
    # Remove old log files
    find "$log_dir" -type f -name "*.log" -mtime +"$MAX_LOG_AGE" -delete || status=1
    
    # Remove old compressed logs
    find "$log_dir" -type f -name "*.log.gz" -mtime +"$MAX_LOG_AGE" -delete || status=1
    
    # Clean empty directories
    find "$log_dir" -type d -empty -delete || status=1
    
    return $status
}

# Cleanup old backups
cleanup_old_backups() {
    local status=0
    local backup_dir="$1"
    
    log_info "Cleaning old backups in: ${backup_dir}"
    
    # Remove old backup files
    find "$backup_dir" -type f -name "backup_*" -mtime +"$MAX_BACKUP_AGE" -delete || status=1
    
    # Clean empty directories
    find "$backup_dir" -type d -empty -delete || status=1
    
    return $status
}

# Cleanup package cache
cleanup_package_cache() {
    local status=0
    local cache_dir="$1"
    local cache_size
    
    log_info "Cleaning package cache in: ${cache_dir}"
    
    # Get current cache size in MB
    cache_size=$(du -sm "$cache_dir" | cut -f1)
    
    if [ "$cache_size" -gt "$MAX_CACHE_SIZE" ]; then
        log_info "Cache size ${cache_size}MB exceeds limit ${MAX_CACHE_SIZE}MB"
        
        # Remove old cached packages
        find "$cache_dir" -type f -atime +30 -delete || status=1
        
        # If still over limit, remove more aggressively
        cache_size=$(du -sm "$cache_dir" | cut -f1)
        if [ "$cache_size" -gt "$MAX_CACHE_SIZE" ]; then
            find "$cache_dir" -type f -atime +7 -delete || status=1
        fi
    fi
    
    # Clean empty directories
    find "$cache_dir" -type d -empty -delete || status=1
    
    return $status
}

# Verify system space
verify_free_space() {
    local dir="$1"
    local free_space
    
    free_space=$(df -m "$dir" | awk 'NR==2 {print $4}')
    
    if [ "$free_space" -lt "$MIN_FREE_SPACE" ]; then
        log_error "Insufficient free space on ${dir}: ${free_space}MB (minimum ${MIN_FREE_SPACE}MB required)"
        return 1
    fi
    
    return 0
}

# Generate cleanup report
generate_cleanup_report() {
    local report_file="${CLEANUP_DIR}/cleanup_report.txt"
    local start_time="$1"
    local end_time
    end_time=$(date -u +%Y%m%d%H%M%S)
    
    {
        echo "=== Cleanup Report ==="
        echo "Start Time: $(date -d "@$start_time" -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo "End Time: $(date -d "@$end_time" -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo
        echo "Space Before:"
        df -h | grep -v tmpfs
        echo
        echo "Space After:"
        df -h | grep -v tmpfs
        echo
        echo "Cleaned Items:"
        find "$CLEANUP_DIR" -type f -name "cleanup_*.log" -newer "@$start_time" -exec cat {} \;
    } > "$report_file"
}

# Main cleanup routine
main_cleanup() {
    local status=0
    local start_time
    start_time=$(date -u +%s)
    
    log_info "Starting system cleanup..."
    
    # Check if we have enough space to work
    verify_free_space "/var/run" || status=1
    
    # Perform cleanup tasks
    cleanup_temp_files || status=1
    cleanup_build_artifacts "/var/cache/lfs-build" || status=1
    cleanup_old_logs "/var/log/lfs-wrapper" || status=1
    cleanup_old_backups "/var/backups/lfs-wrapper" || status=1
    cleanup_package_cache "/var/cache/lfs-packages" || status=1
    
    # Generate report
    generate_cleanup_report "$start_time"
    
    if [ $status -eq 0 ]; then
        log_info "Cleanup completed successfully"
    else
        log_error "Cleanup completed with errors"
    fi
    
    return $status
}

# Main entry point
main() {
    if [ "$#" -gt 0 ]; then
        # Execute specific cleanup task
        case "$1" in
            temp)
                cleanup_temp_files
                ;;
            build)
                if [ "$#" -lt 2 ]; then
                    log_error "Usage: $0 build <build_directory>"
                    exit 1
                fi
                cleanup_build_artifacts "$2"
                ;;
            logs)
                if [ "$#" -lt 2 ]; then
                    log_error "Usage: $0 logs <log_directory>"
                    exit 1
                fi
                cleanup_old_logs "$2"
                ;;
            backups)
                if [ "$#" -lt 2 ]; then
                    log_error "Usage: $0 backups <backup_directory>"
                    exit 1
                fi
                cleanup_old_backups "$2"
                ;;
            cache)
                if [ "$#" -lt 2 ]; then
                    log_error "Usage: $0 cache <cache_directory>"
                    exit 1
                fi
                cleanup_package_cache "$2"
                ;;
            *)
                log_error "Unknown cleanup task: ${1}"
                exit 1
                ;;
        esac
    else
        # Execute full cleanup
        main_cleanup
    fi
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

