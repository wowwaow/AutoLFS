#!/bin/bash
#
# Resource Verification System
# Validates and monitors system resources for LFS/BLFS builds
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
RESOURCE_DIR="/var/run/lfs-wrapper/resources"
RESOURCE_LOG="${RESOURCE_DIR}/resources.log"
mkdir -p "$RESOURCE_DIR"

# Resource Requirements
declare -r MIN_RAM_GB=4
declare -r MIN_SWAP_GB=2
declare -r MIN_DISK_GB=20
declare -r MIN_CPU_CORES=2
declare -r MIN_IOPS=100
declare -r MIN_READ_SPEED_MB=50
declare -r MIN_WRITE_SPEED_MB=30

# System limits to verify
declare -A SYSTEM_LIMITS=(
    ["max_open_files"]="1048576"
    ["max_processes"]="32768"
    ["max_file_size"]="-1"  # unlimited
    ["max_memory_lock"]="-1" # unlimited
)

# Detailed Resource Availability Check
check_resource_availability() {
    local status=0
    
    log_info "Checking system resources..."
    
    # Memory verification
    local mem_info
    mem_info=$(get_memory_info)
    local total_ram_gb=$((${mem_info[0]} / 1024 / 1024))
    local available_ram_gb=$((${mem_info[1]} / 1024 / 1024))
    local total_swap_gb=$((${mem_info[2]} / 1024 / 1024))
    
    if [ "$total_ram_gb" -lt "$MIN_RAM_GB" ]; then
        log_error "Insufficient RAM: ${total_ram_gb}GB (minimum ${MIN_RAM_GB}GB required)"
        status=1
    fi
    
    if [ "$total_swap_gb" -lt "$MIN_SWAP_GB" ]; then
        log_error "Insufficient swap: ${total_swap_gb}GB (minimum ${MIN_SWAP_GB}GB required)"
        status=1
    fi
    
    # Disk space verification
    local disk_info
    disk_info=$(get_disk_info)
    local available_space_gb=$((${disk_info[0]} / 1024 / 1024))
    
    if [ "$available_space_gb" -lt "$MIN_DISK_GB" ]; then
        log_error "Insufficient disk space: ${available_space_gb}GB (minimum ${MIN_DISK_GB}GB required)"
        status=1
    fi
    
    # CPU verification
    local cpu_cores
    cpu_cores=$(nproc)
    
    if [ "$cpu_cores" -lt "$MIN_CPU_CORES" ]; then
        log_error "Insufficient CPU cores: ${cpu_cores} (minimum ${MIN_CPU_CORES} required)"
        status=1
    fi
    
    return $status
}

# Resource monitoring and forecasting
monitor_resources() {
    local duration="${1:-300}"  # Default 5 minutes
    local interval="${2:-5}"    # Default 5 seconds
    local samples=$((duration / interval))
    local metrics_file="${RESOURCE_DIR}/resource_metrics.log"
    
    log_info "Monitoring system resources for ${duration} seconds..."
    
    for ((i=1; i<=samples; i++)); do
        # Collect resource metrics
        local mem_info
        mem_info=$(get_memory_info)
        local cpu_usage
        cpu_usage=$(get_cpu_usage)
        local disk_io
        disk_io=$(get_disk_io)
        
        # Record metrics
        {
            echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
            echo "RAM_USED=$((${mem_info[0]} - ${mem_info[1]}))"
            echo "RAM_FREE=${mem_info[1]}"
            echo "SWAP_USED=$((${mem_info[2]} - ${mem_info[3]}))"
            echo "CPU_USAGE=${cpu_usage}"
            echo "DISK_READ=${disk_io[0]}"
            echo "DISK_WRITE=${disk_io[1]}"
        } >> "$metrics_file"
        
        sleep "$interval"
    done
    
    # Generate resource forecast
    generate_resource_forecast "$metrics_file"
}

# Resource allocation validation
validate_resource_allocation() {
    local status=0
    
    # Check system limits
    for limit in "${!SYSTEM_LIMITS[@]}"; do
        local current_limit
        current_limit=$(ulimit -a | grep -i "$limit" | awk '{print $NF}')
        local required_limit="${SYSTEM_LIMITS[$limit]}"
        
        if [ "$required_limit" = "-1" ]; then
            if [ "$current_limit" != "unlimited" ] && [ "$current_limit" -ne -1 ]; then
                log_error "System limit ${limit} should be unlimited"
                status=1
            fi
        elif [ "$current_limit" != "unlimited" ] && [ "$current_limit" -lt "$required_limit" ]; then
            log_error "System limit ${limit} too low: ${current_limit} (minimum ${required_limit})"
            status=1
        fi
    done
    
    # Check I/O scheduling
    local scheduler
    scheduler=$(cat /sys/block/$(df . | awk 'NR==2 {print $1}' | sed 's/.*\///g')/queue/scheduler)
    if [[ ! $scheduler =~ "deadline" ]] && [[ ! $scheduler =~ "cfq" ]]; then
        log_warn "I/O scheduler might not be optimal for builds: ${scheduler}"
    fi
    
    return $status
}

# System limits verification
verify_system_limits() {
    local status=0
    
    # File descriptor limits
    local file_max
    file_max=$(cat /proc/sys/fs/file-max)
    if [ "$file_max" -lt 1048576 ]; then
        log_error "Maximum file descriptors too low: ${file_max}"
        status=1
    fi
    
    # Process limits
    local pid_max
    pid_max=$(cat /proc/sys/kernel/pid_max)
    if [ "$pid_max" -lt 32768 ]; then
        log_error "Maximum process ID too low: ${pid_max}"
        status=1
    fi
    
    # Memory limits
    local max_map_count
    max_map_count=$(cat /proc/sys/vm/max_map_count)
    if [ "$max_map_count" -lt 262144 ]; then
        log_error "Maximum memory map count too low: ${max_map_count}"
        status=1
    fi
    
    return $status
}

# Performance baseline validation
validate_performance_baseline() {
    local status=0
    local test_file="${RESOURCE_DIR}/io_test"
    
    # I/O performance test
    log_info "Testing I/O performance..."
    
    # Write test
    if ! dd if=/dev/zero of="$test_file" bs=1M count=1024 conv=fdatasync 2>&1; then
        log_error "Write performance test failed"
        status=1
    else
        local write_speed
        write_speed=$(tail -n 1 "$test_file.log" | awk '{print $NF}' | tr -d 'MB/s')
        if [ "${write_speed%.*}" -lt "$MIN_WRITE_SPEED_MB" ]; then
            log_error "Write speed too low: ${write_speed}MB/s"
            status=1
        fi
    fi
    
    # Read test
    if ! dd if="$test_file" of=/dev/null bs=1M 2>&1; then
        log_error "Read performance test failed"
        status=1
    else
        local read_speed
        read_speed=$(tail -n 1 "$test_file.log" | awk '{print $NF}' | tr -d 'MB/s')
        if [ "${read_speed%.*}" -lt "$MIN_READ_SPEED_MB" ]; then
            log_error "Read speed too low: ${read_speed}MB/s"
            status=1
        fi
    fi
    
    # Cleanup
    rm -f "$test_file" "$test_file.log"
    
    return $status
}

# Helper functions
get_memory_info() {
    local total_ram free_ram total_swap free_swap
    read -r total_ram free_ram total_swap free_swap <<< \
        $(grep -E '^(MemTotal|MemFree|SwapTotal|SwapFree)' /proc/meminfo | awk '{print $2}')
    echo "$total_ram $free_ram $total_swap $free_swap"
}

get_cpu_usage() {
    top -bn1 | grep "Cpu(s)" | awk '{print $2}'
}

get_disk_io() {
    local disk_device
    disk_device=$(df . | awk 'NR==2 {print $1}' | sed 's/.*\///g')
    iostat -d "$disk_device" 1 2 | tail -n 1 | awk '{print $3" "$4}'
}

generate_resource_forecast() {
    local metrics_file="$1"
    local forecast_file="${RESOURCE_DIR}/resource_forecast.txt"
    
    # Simple linear projection based on current trends
    {
        echo "=== Resource Usage Forecast ==="
        echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo
        echo "Projected resource usage for next 24 hours:"
        
        # Calculate trends from metrics
        awk '
            BEGIN { ram_sum=0; cpu_sum=0; count=0 }
            /RAM_USED/ { ram_sum+=$2; count++ }
            /CPU_USAGE/ { cpu_sum+=$2 }
            END {
                ram_avg=ram_sum/count;
                cpu_avg=cpu_sum/count;
                print "RAM Usage Trend: "ram_avg" KB/hour";
                print "CPU Usage Trend: "cpu_avg"%";
            }
        ' "$metrics_file"
    } > "$forecast_file"
}

# Main entry point
main() {
    local status=0
    
    log_info "Starting resource verification..."
    
    # Run all resource checks
    check_resource_availability || status=1
    validate_resource_allocation || status=1
    verify_system_limits || status=1
    validate_performance_baseline || status=1
    
    # Start resource monitoring in background
    monitor_resources &
    
    if [ $status -eq 0 ]; then
        log_info "All resource checks passed"
    else
        log_error "Some resource checks failed"
    fi
    
    return $status
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

