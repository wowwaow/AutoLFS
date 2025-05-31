#!/bin/bash

# Logging System
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Provide unified logging functionality

# Log levels
declare -A LOG_LEVELS=(
    [DEBUG]=0
    [INFO]=1
    [WARN]=2
    [ERROR]=3
    [CRITICAL]=4
)

# Current log level
CURRENT_LOG_LEVEL=${LOG_LEVELS[INFO]}

# Log colors
declare -A LOG_COLORS=(
    [DEBUG]='\033[0;36m'    # Cyan
    [INFO]='\033[0;32m'     # Green
    [WARN]='\033[1;33m'     # Yellow
    [ERROR]='\033[0;31m'    # Red
    [CRITICAL]='\033[1;31m' # Bright Red
)

# Color reset
NC='\033[0m'

# Initialize logging system
init_logging() {
    local log_dir=$1
    
    # Create log directory if it doesn't exist
    mkdir -p "$log_dir"
    
    # Set up log files
    MAIN_LOG="$log_dir/build.log"
    ERROR_LOG="$log_dir/error.log"
    DEBUG_LOG="$log_dir/debug.log"
    
    # Initialize log files
    > "$MAIN_LOG"
    > "$ERROR_LOG"
    > "$DEBUG_LOG"
    
    # Set log rotation
    setup_log_rotation
}

# Set log level
set_log_level() {
    local level=$1
    if [ -n "${LOG_LEVELS[$level]}" ]; then
        CURRENT_LOG_LEVEL=${LOG_LEVELS[$level]}
    else
        echo "Invalid log level: $level" >&2
    fi
}

# Main logging function
log() {
    local level=$1
    local message=$2
    local timestamp=$(date -u --iso-8601=seconds)
    local color=${LOG_COLORS[$level]}
    
    # Check if we should log this level
    if [ ${LOG_LEVELS[$level]} -ge $CURRENT_LOG_LEVEL ]; then
        # Format message
        local formatted_message="[$timestamp] $level: $message"
        
        # Console output with color
        echo -e "${color}${formatted_message}${NC}"
        
        # Log to file without color
        echo "$formatted_message" >> "$MAIN_LOG"
        
        # Additional logging based on level
        case $level in
            ERROR|CRITICAL)
                echo "$formatted_message" >> "$ERROR_LOG"
                ;;
            DEBUG)
                echo "$formatted_message" >> "$DEBUG_LOG"
                ;;
        esac
    fi
}

# Convenience logging functions
debug() { log "DEBUG" "$1"; }
info() { log "INFO" "$1"; }
warn() { log "WARN" "$1"; }
error() { log "ERROR" "$1"; }
critical() { log "CRITICAL" "$1"; }

# Log with context
log_with_context() {
    local level=$1
    local message=$2
    local context=$3
    
    # Format context
    local context_str=""
    for key in "${!context[@]}"; do
        context_str="$context_str[$key=${context[$key]}]"
    done
    
    # Log with context
    log "$level" "$message $context_str"
}

# Setup log rotation
setup_log_rotation() {
    # Log rotation configuration
    local max_size=$((100*1024*1024))  # 100MB
    local keep_logs=5
    
    # Check log sizes and rotate if needed
    check_and_rotate_log "$MAIN_LOG" $max_size $keep_logs
    check_and_rotate_log "$ERROR_LOG" $max_size $keep_logs
    check_and_rotate_log "$DEBUG_LOG" $max_size $keep_logs
}

# Check and rotate log
check_and_rotate_log() {
    local log_file=$1
    local max_size=$2
    local keep_logs=$3
    
    if [ -f "$log_file" ]; then
        local size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file")
        if [ $size -gt $max_size ]; then
            rotate_log "$log_file" $keep_logs
        fi
    fi
}

# Rotate log file
rotate_log() {
    local log_file=$1
    local keep_logs=$2
    
    # Remove oldest log
    rm -f "${log_file}.${keep_logs}"
    
    # Rotate existing logs
    for i in $(seq $((keep_logs-1)) -1 1); do
        if [ -f "${log_file}.$i" ]; then
            mv "${log_file}.$i" "${log_file}.$((i+1))"
        fi
    done
    
    # Rotate current log
    mv "$log_file" "${log_file}.1"
    
    # Create new log file
    touch "$log_file"
}

# Log system stats
log_system_stats() {
    local stats=(
        "Disk Usage: $(df -h . | awk 'NR==2 {print $5}')"
        "Memory Free: $(free -h | awk '/^Mem:/ {print $4}')"
        "Load Average: $(uptime | awk -F'average:' '{print $2}')"
        "Process Count: $(ps aux | wc -l)"
    )
    
    debug "System Stats: ${stats[*]}"
}

# Log build progress
log_build_progress() {
    local package=$1
    local phase=$2
    local progress=$3
    local status=$4
    
    local timestamp=$(date -u --iso-8601=seconds)
    local context=(
        ["package"]="$package"
        ["phase"]="$phase"
        ["progress"]="$progress%"
        ["status"]="$status"
        ["timestamp"]="$timestamp"
    )
    
    # Log to build progress file
    echo "$timestamp,$package,$phase,$progress,$status" >> "$MAIN_LOG.progress"
    
    # Log with context
    log_with_context "INFO" "Build Progress:" context
    
    # If build completed or failed, log accordingly
    case $status in
        "COMPLETED")
            log "INFO" "Package $package completed successfully"
            ;;
        "FAILED")
            log "ERROR" "Package $package failed during $phase at $progress%"
            ;;
        "RUNNING")
            debug "Package $package $phase in progress: $progress%"
            ;;
    esac
}

# Export functions for use by other scripts
export LOG_LEVELS
export LOG_COLORS
export NC
export CURRENT_LOG_LEVEL
export MAIN_LOG
export ERROR_LOG
export DEBUG_LOG

export -f init_logging
export -f set_log_level
export -f log
export -f debug
export -f info
export -f warn
export -f error
export -f critical
export -f log_with_context
export -f setup_log_rotation
export -f check_and_rotate_log
export -f rotate_log
export -f log_system_stats
export -f log_build_progress

# Initialize logging if not already initialized
if [ -z "$MAIN_LOG" ]; then
    init_logging "/var/log/lfs-build"
fi
