#!/bin/bash
#
# Storage Space Management System
# Manages disk space and storage allocation
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
SPACE_DIR="/var/run/lfs-wrapper/maintenance/space"
SPACE_LOG="${SPACE_DIR}/space.log"
mkdir -p "$SPACE_DIR"

# Space thresholds
declare -r CRITICAL_THRESHOLD=90  # Percentage
declare -r WARNING_THRESHOLD=80   # Percentage
declare -r MIN_FREE_SPACE=5120    # MB (5GB)
declare -r MIN_INODES=100000      # Minimum free inodes

# Monitor space usage
monitor_space() {
    local directory="$1"
    local threshold="${2:-$WARNING_THRESHOLD}"
    local status=0
    
    log_info "Monitoring space usage in: ${directory}"
    
    # Check disk space
    local usage
    usage=$(df -h "$directory" | awk 'NR==2 {print $5}' | tr -d '%')
    
    if [ "$usage" -ge "$CRITICAL_THRESHOLD" ]; then
        log_error "Critical disk usage: ${usage}% in ${directory}"
        status=1
    elif [ "$usage" -ge "$threshold" ]; then
        log_warn "High disk usage: ${usage}% in ${directory}"
    fi
    
    # Check inodes
    local inodes_usage
    inodes_usage=$(df -i "$directory" | awk 'NR==2 {print $5}' | tr -d '%')
    
    if [ "$inodes_usage" -ge "$CRITICAL_THRESHOLD" ]; then
        log_error "Critical inode usage: ${inodes_usage}% in ${directory}"
        status=1
    elif [ "$inodes_usage" -ge "$threshold" ]; then
        log_warn "High inode usage: ${inodes_usage}% in ${directory}"
    fi
    
    return $status
}

# Check free space
check_free_space() {
    local directory="$1"
    local required="${2:-$MIN_FREE_SPACE}"
    
    local free_space
    free_space=$(df -m "$directory" | awk 'NR==2 {print $4}')
    
    if [ "$free_space" -lt "$required" ]; then
        log_error "Insufficient free space: ${free_space}MB (minimum ${required}MB required)"
        return 1
    fi
    
    return 0
}

# Check free inodes
check_free_inodes() {
    local directory="$1"
    local required="${2:-$MIN_INODES}"
    
    local free_inodes
    free_inodes=$(df -i "$directory" | awk 'NR==2 {print $4}')
    
    if [ "$free_inodes" -lt "$required" ]; then
        log_error "Insufficient free inodes: ${free_inodes} (minimum ${required} required)"
        return 1
    fi
    
    return 0
}

# Find large files
find_large_files() {
    local directory="$1"
    local size_threshold="${2:-100}"  # MB
    local report_file="${SPACE_DIR}/large_files.txt"
    
    log_info "Finding files larger than ${size_threshold}MB in ${directory}"
    
    {
        echo "=== Large Files Report ==="
        echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo "Directory: ${directory}"
        echo "Threshold: ${size_threshold}MB"
        echo
        find "$directory" -type f -size +"${size_threshold}M" -exec ls -lh {} \; | sort -rh -k5
    } > "$report_file"
}

# Find old files
find_old_files() {
    local directory="$1"
    local days="${2:-30}"
    local report_file="${SPACE_DIR}/old_files.txt"
    
    log_info "Finding files older than ${days} days in ${directory}"
    
    {
        echo "=== Old Files Report ==="
        echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo "Directory: ${directory}"
        echo "Age Threshold: ${days} days"
        echo
        find "$directory" -type f -mtime +"$days" -exec ls -lh {} \; | sort -rh -k5
    } > "$report_file"
}

# Generate space usage report
generate_space_report() {
    local directory="$1"
    local report_file="${SPACE_DIR}/space_report.txt"
    
    {
        echo "=== Space Usage Report ==="
        echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo
        echo "Overall Usage:"
        df -h "$directory"
        echo
        echo "Inode Usage:"
        df -i "$directory"
        echo
        echo "Directory Sizes:"
        du -h --max-depth=2 "$directory" | sort -rh
        echo
        echo "File Type Distribution:"
        find "$directory" -type f -exec file {} \; | awk -F: '{print $2}' | sort | uniq -c | sort -rn
    } > "$report_file"
}

# Automatic space recovery
recover_space() {
    local directory="$1"
    local status=0
    
    log_info "Attempting to recover space in: ${directory}"
    
    # Remove temporary files
    find "$directory" -type f -name "*.tmp" -delete || status=1
    find "$directory" -type f -name "*.temp" -delete || status=1
    
    # Remove old log files
    find "$directory" -type f -name "*.log" -mtime +30 -delete || status=1
    
    # Remove empty directories
    find "$directory" -type d -empty -delete || status=1
    
    # Compress old files
    find "$directory" -type f -mtime +7 ! -name "*.gz" -exec gzip {} \; || status=1
    
    return $status
}

# Main entry point
main() {
    if [ "$#" -lt 1 ]; then
        log_error "Usage: $0 <command> <directory> [args...]"
        exit 1
    fi
    
    local command="$1"
    local directory="$2"
    shift 2
    
    case "$command" in
        monitor)
            monitor_space "$directory" "$@"
            ;;
        check)
            check_free_space "$directory" "$@" && check_free_inodes "$directory" "$@"
            ;;
        large)
            find_large_files "$directory" "$@"
            ;;
        old)
            find_old_files "$directory" "$@"
            ;;
        report)
            generate_space_report "$directory"
            ;;
        recover)
            recover_space "$directory"
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

