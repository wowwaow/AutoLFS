#!/bin/bash
#
# Performance Monitoring System
# Tracks system resource usage during builds
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
METRICS_DIR="/var/run/lfs-wrapper/metrics"
mkdir -p "$METRICS_DIR"

# System metrics collection
collect_system_metrics() {
    local script_id="$1"
    local metrics_file="${METRICS_DIR}/${script_id}.system"
    
    # CPU metrics
    local cpu_idle
    cpu_idle=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}')
    local cpu_usage
    cpu_usage=$(bc <<< "100 - ${cpu_idle}")
    
    # Memory metrics
    local mem_total mem_used mem_free
    read -r mem_total mem_free mem_available < <(free | grep Mem | awk '{print $2,$4,$7}')
    mem_used=$(( mem_total - mem_available ))
    local mem_usage
    mem_usage=$(( (mem_used * 100) / mem_total ))
    
    # Disk metrics
    local disk_usage
    disk_usage=$(df -h . | awk 'NR==2 {print $5}' | tr -d '%')
    
    # Write metrics
    {
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        echo "CPU_USAGE=${cpu_usage}"
        echo "MEM_USAGE=${mem_usage}"
        echo "DISK_USAGE=${disk_usage}"
        echo "MEM_TOTAL=${mem_total}"
        echo "MEM_FREE=${mem_free}"
        echo "MEM_AVAILABLE=${mem_available}"
    } > "$metrics_file"
}

# Process-specific metrics
collect_process_metrics() {
    local script_id="$1"
    local pid="$2"
    local metrics_file="${METRICS_DIR}/${script_id}.process"
    
    if ! kill -0 "$pid" 2>/dev/null; then
        log_error "Process $pid not found"
        return 1
    fi
    
    # Process CPU and memory usage
    local cpu_usage mem_usage
    read -r cpu_usage mem_usage < <(ps -p "$pid" -o %cpu=,%mem=)
    
    # Process I/O statistics
    local read_bytes write_bytes
    read -r read_bytes write_bytes < <(cat "/proc/$pid/io" 2>/dev/null | awk '/read_bytes|write_bytes/{print $2}')
    
    # Write metrics
    {
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        echo "PID=${pid}"
        echo "CPU_USAGE=${cpu_usage}"
        echo "MEM_USAGE=${mem_usage}"
        echo "READ_BYTES=${read_bytes:-0}"
        echo "WRITE_BYTES=${write_bytes:-0}"
    } > "$metrics_file"
}

# Resource threshold checking
check_thresholds() {
    local script_id="$1"
    local metrics_file="${METRICS_DIR}/${script_id}.system"
    
    # Load thresholds
    local cpu_threshold=90
    local mem_threshold=85
    local disk_threshold=90
    
    # Read current metrics
    local cpu_usage mem_usage disk_usage
    while IFS='=' read -r key value; do
        case "$key" in
            CPU_USAGE) cpu_usage="$value" ;;
            MEM_USAGE) mem_usage="$value" ;;
            DISK_USAGE) disk_usage="$value" ;;
        esac
    done < "$metrics_file"
    
    # Check thresholds and trigger alerts
    if [ "${cpu_usage%.*}" -gt "$cpu_threshold" ]; then
        trigger_resource_alert "$script_id" "CPU" "$cpu_usage" "$cpu_threshold"
    fi
    
    if [ "$mem_usage" -gt "$mem_threshold" ]; then
        trigger_resource_alert "$script_id" "Memory" "$mem_usage" "$mem_threshold"
    fi
    
    if [ "$disk_usage" -gt "$disk_threshold" ]; then
        trigger_resource_alert "$script_id" "Disk" "$disk_usage" "$disk_threshold"
    fi
}

# Alert triggering
trigger_resource_alert() {
    local script_id="$1"
    local resource="$2"
    local usage="$3"
    local threshold="$4"
    
    log_warn "${resource} usage above threshold for ${script_id}: ${usage}% (threshold: ${threshold}%)"
    
    # Create alert file
    local alert_file="/var/run/lfs-wrapper/alerts/${script_id}.resource"
    {
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        echo "RESOURCE=${resource}"
        echo "USAGE=${usage}"
        echo "THRESHOLD=${threshold}"
    } > "$alert_file"
}

# Main monitoring loop
monitor_performance() {
    local script_id="$1"
    local pid="$2"
    local interval="${3:-30}"  # Default 30 second interval
    
    log_info "Starting performance monitoring for script ${script_id} (PID: ${pid})"
    
    while kill -0 "$pid" 2>/dev/null; do
        collect_system_metrics "$script_id"
        collect_process_metrics "$script_id" "$pid"
        check_thresholds "$script_id"
        sleep "$interval"
    done
    
    log_info "Performance monitoring ended for script ${script_id}"
}

# Main entry point
main() {
    if [ "$#" -lt 2 ]; then
        log_error "Usage: $0 <script_id> <pid> [interval]"
        exit 1
    fi
    
    monitor_performance "$@"
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

