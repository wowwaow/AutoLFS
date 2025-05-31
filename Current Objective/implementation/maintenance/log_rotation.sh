#!/bin/bash
#
# Log Rotation System
# Manages log rotation and archival
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
ROTATION_DIR="/var/run/lfs-wrapper/maintenance/rotation"
ROTATION_LOG="${ROTATION_DIR}/rotation.log"
mkdir -p "$ROTATION_DIR"

# Rotation settings
declare -r MAX_LOG_SIZE=100        # MB
declare -r MAX_ROTATIONS=5         # Number of rotations to keep
declare -r COMPRESSION_AGE=7       # Days before compressing
declare -r DELETION_AGE=30         # Days before deleting
declare -r MIN_FREE_SPACE=1024     # MB required for rotation

# Rotate single log file
rotate_log() {
    local log_file="$1"
    local max_size="${2:-$MAX_LOG_SIZE}"
    local max_rotations="${3:-$MAX_ROTATIONS}"
    local status=0
    
    # Check if file exists and needs rotation
    if [ ! -f "$log_file" ]; then
        return 0
    fi
    
    local size_mb
    size_mb=$(du -m "$log_file" | cut -f1)
    
    if [ "$size_mb" -gt "$max_size" ]; then
        log_info "Rotating log file: ${log_file}"
        
        # Remove oldest rotation if it exists
        if [ -f "${log_file}.${max_rotations}.gz" ]; then
            rm -f "${log_file}.${max_rotations}.gz"
        fi
        
        # Shift existing rotations
        for ((i=max_rotations-1; i>=1; i--)); do
            if [ -f "${log_file}.${i}.gz" ]; then
                mv "${log_file}.${i}.gz" "${log_file}.$((i+1)).gz"
            fi
        done
        
        # Create new rotation
        cp "$log_file" "${log_file}.1"
        gzip "${log_file}.1"
        
        # Clear original log
        : > "$log_file"
        
        log_info "Log rotation completed: ${log_file}"
    fi
    
    return $status
}

# Compress old logs
compress_old_logs() {
    local log_dir="$1"
    local age="${2:-$COMPRESSION_AGE}"
    local status=0
    
    log_info "Compressing old logs in: ${log_dir}"
    
    # Find and compress old log files
    find "$log_dir" -type f -name "*.log" -mtime +"$age" ! -name "*.gz" | while read -r log; do
        if gzip -9 "$log"; then
            log_debug "Compressed log: ${log}"
        else
            log_error "Failed to compress: ${log}"
            status=1
        fi
    done
    
    return $status
}

# Delete old logs
delete_old_logs() {
    local log_dir="$1"
    local age="${2:-$DELETION_AGE}"
    local status=0
    
    log_info "Deleting old logs in: ${log_dir}"
    
    # Find and delete old compressed logs
    find "$log_dir" -type f -name "*.log.gz" -mtime +"$age" -delete || status=1
    
    return $status
}

# Check available space
check_space() {
    local log_dir="$1"
    local min_space="${2:-$MIN_FREE_SPACE}"
    
    local free_space
    free_space=$(df -m "$log_dir" | awk 'NR==2 {print $4}')
    
    if [ "$free_space" -lt "$min_space" ]; then
        log_error "Insufficient free space: ${free_space}MB (minimum ${min_space}MB required)"
        return 1
    fi
    
    return 0
}

# Generate rotation report
generate_report() {
    local log_dir="$1"
    local report_file="${ROTATION_DIR}/rotation_report.txt"
    
    {
        echo "=== Log Rotation Report ==="
        echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo
        echo "Directory: ${log_dir}"
        echo
        echo "Current Log Sizes:"
        find "$log_dir" -type f -name "*.log" -exec du -h {} \;
        echo
        echo "Rotation Status:"
        find "$log_dir" -type f -name "*.log.*" | sort
        echo
        echo "Space Usage:"
        df -h "$log_dir"
    } > "$report_file"
}

# Rotate all logs in directory
rotate_directory() {
    local log_dir="$1"
    local status=0
    
    log_info "Processing directory: ${log_dir}"
    
    # Check space before starting
    check_space "$log_dir" || return 1
    
    # Process each log file
    find "$log_dir" -type f -name "*.log" | while read -r log; do
        rotate_log "$log" || status=1
    done
    
    # Compress old logs
    compress_old_logs "$log_dir" || status=1
    
    # Delete very old logs
    delete_old_logs "$log_dir" || status=1
    
    # Generate report
    generate_report "$log_dir"
    
    return $status
}

# Main entry point
main() {
    if [ "$#" -lt 1 ]; then
        log_error "Usage: $0 <log_directory> [max_size_mb] [max_rotations]"
        exit 1
    fi
    
    local log_dir="$1"
    local max_size="${2:-$MAX_LOG_SIZE}"
    local max_rotations="${3:-$MAX_ROTATIONS}"
    
    if ! rotate_directory "$log_dir"; then
        log_error "Log rotation failed"
        exit 1
    fi
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

