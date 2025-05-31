#!/bin/bash
#
# Script Status Monitoring Daemon
# Provides real-time monitoring of LFS/BLFS build processes
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
MONITOR_DIR="/var/run/lfs-wrapper"
STATUS_DIR="${MONITOR_DIR}/status"
METRICS_DIR="${MONITOR_DIR}/metrics"
ALERTS_DIR="${MONITOR_DIR}/alerts"
LOG_DIR="${MONITOR_DIR}/logs"

# Ensure required directories exist
for dir in "$STATUS_DIR" "$METRICS_DIR" "$ALERTS_DIR" "$LOG_DIR"; do
    mkdir -p "$dir"
done

# Status Constants
declare -r STATUS_INITIALIZING="INITIALIZING"
declare -r STATUS_RUNNING="RUNNING"
declare -r STATUS_COMPLETED="COMPLETED"
declare -r STATUS_FAILED="FAILED"
declare -r STATUS_PAUSED="PAUSED"

# Alert Levels
declare -r ALERT_INFO="INFO"
declare -r ALERT_WARNING="WARNING"
declare -r ALERT_ERROR="ERROR"
declare -r ALERT_CRITICAL="CRITICAL"

# Performance Thresholds
declare -r CPU_THRESHOLD=90  # percentage
declare -r MEM_THRESHOLD=85  # percentage
declare -r DISK_THRESHOLD=90 # percentage

# Monitoring interval (seconds)
declare -r MONITOR_INTERVAL=5

# Status Tracking
track_script_status() {
    local script_id="$1"
    local status_file="${STATUS_DIR}/${script_id}.status"
    local pid_file="${STATUS_DIR}/${script_id}.pid"
    
    if [ ! -f "$pid_file" ]; then
        log_error "PID file not found for script: ${script_id}"
        return 1
    fi
    
    local pid
    pid=$(cat "$pid_file")
    
    if ! kill -0 "$pid" 2>/dev/null; then
        # Process no longer exists
        if [ -f "$status_file" ] && [ "$(cat "$status_file")" = "$STATUS_RUNNING" ]; then
            # Script was running but died unexpectedly
            echo "$STATUS_FAILED" > "$status_file"
            trigger_alert "$script_id" "$ALERT_ERROR" "Script process died unexpectedly"
        fi
        return 1
    fi
    
    # Update last seen timestamp
    date -u +%s > "${STATUS_DIR}/${script_id}.timestamp"
    return 0
}

# Progress Reporting
update_progress() {
    local script_id="$1"
    local progress_file="${METRICS_DIR}/${script_id}.progress"
    
    # Get build progress from script's progress marker
    if [ -f "${MONITOR_DIR}/progress/${script_id}.marker" ]; then
        cp "${MONITOR_DIR}/progress/${script_id}.marker" "$progress_file"
    fi
    
    # Update progress history
    {
        date -u +%s
        cat "$progress_file"
    } >> "${LOG_DIR}/${script_id}.progress.log"
}

# Performance Monitoring
monitor_performance() {
    local script_id="$1"
    local pid_file="${STATUS_DIR}/${script_id}.pid"
    local metrics_file="${METRICS_DIR}/${script_id}.metrics"
    
    if [ ! -f "$pid_file" ]; then
        return 1
    fi
    
    local pid
    pid=$(cat "$pid_file")
    
    # CPU Usage
    local cpu_usage
    cpu_usage=$(ps -p "$pid" -o %cpu= || echo "0")
    
    # Memory Usage
    local mem_usage
    mem_usage=$(ps -p "$pid" -o %mem= || echo "0")
    
    # Disk I/O
    local disk_io
    disk_io=$(iotop -b -n 1 -p "$pid" 2>/dev/null | tail -n 1 | awk '{print $10}' || echo "0")
    
    # Record metrics
    {
        date -u +%s
        echo "CPU=${cpu_usage}"
        echo "MEM=${mem_usage}"
        echo "IO=${disk_io}"
    } > "$metrics_file"
    
    # Check thresholds and trigger alerts
    if [ "${cpu_usage%.*}" -gt "$CPU_THRESHOLD" ]; then
        trigger_alert "$script_id" "$ALERT_WARNING" "High CPU usage: ${cpu_usage}%"
    fi
    
    if [ "${mem_usage%.*}" -gt "$MEM_THRESHOLD" ]; then
        trigger_alert "$script_id" "$ALERT_WARNING" "High memory usage: ${mem_usage}%"
    fi
}

# Alert System
trigger_alert() {
    local script_id="$1"
    local level="$2"
    local message="$3"
    local alert_file="${ALERTS_DIR}/${script_id}.alerts"
    
    # Generate alert
    {
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        echo "LEVEL=${level}"
        echo "MESSAGE=${message}"
    } >> "$alert_file"
    
    # Log alert
    log_warn "Alert for ${script_id}: [${level}] ${message}"
    
    # Critical alerts need immediate attention
    if [ "$level" = "$ALERT_CRITICAL" ]; then
        notify_admin "$script_id" "$message"
    fi
}

# Admin Notification
notify_admin() {
    local script_id="$1"
    local message="$2"
    
    # Log to system log
    logger -t "lfs-wrapper" "CRITICAL ALERT - Script ${script_id}: ${message}"
    
    # Additional notification methods can be added here
    # (email, SMS, etc.)
}

# Main Monitoring Loop
monitor_script() {
    local script_id="$1"
    
    log_info "Starting monitoring for script: ${script_id}"
    
    while true; do
        if ! track_script_status "$script_id"; then
            log_info "Script ${script_id} monitoring ended"
            break
        fi
        
        update_progress "$script_id"
        monitor_performance "$script_id"
        
        sleep "$MONITOR_INTERVAL"
    done
    
    # Final status update
    local final_status
    final_status=$(cat "${STATUS_DIR}/${script_id}.status" 2>/dev/null || echo "$STATUS_FAILED")
    log_info "Script ${script_id} finished with status: ${final_status}"
}

# Cleanup on exit
cleanup() {
    local script_id="$1"
    log_info "Cleaning up monitoring for script: ${script_id}"
    rm -f "${STATUS_DIR}/${script_id}."*
    rm -f "${METRICS_DIR}/${script_id}."*
}

# Main entry point
main() {
    if [ "$#" -lt 1 ]; then
        log_error "Usage: $0 <script_id>"
        exit 1
    fi
    
    local script_id="$1"
    
    # Set up trap for cleanup
    trap 'cleanup "$script_id"' EXIT
    
    # Initialize status
    echo "$STATUS_INITIALIZING" > "${STATUS_DIR}/${script_id}.status"
    
    # Start monitoring
    monitor_script "$script_id"
}

# Execute main function
main "$@"

