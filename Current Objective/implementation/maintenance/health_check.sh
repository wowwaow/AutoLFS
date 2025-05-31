#!/bin/bash
#
# System Health Monitoring
# Monitors and reports system health status
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
HEALTH_DIR="/var/run/lfs-wrapper/maintenance/health"
HEALTH_LOG="${HEALTH_DIR}/health.log"
mkdir -p "$HEALTH_DIR"

# Health check thresholds
declare -r CPU_THRESHOLD=90         # Percentage
declare -r MEM_THRESHOLD=85         # Percentage
declare -r DISK_THRESHOLD=90        # Percentage
declare -r LOAD_THRESHOLD=5.0       # Load average
declare -r PROCESS_THRESHOLD=1000   # Maximum processes
declare -r ZOMBIE_THRESHOLD=5       # Maximum zombie processes

# Check CPU usage
check_cpu() {
    local status=0
    
    log_info "Checking CPU usage..."
    
    # Get CPU usage percentage
    local cpu_usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
    
    if [ "${cpu_usage%.*}" -ge "$CPU_THRESHOLD" ]; then
        log_error "High CPU usage: ${cpu_usage}%"
        status=1
    fi
    
    # Get load average
    local load_avg
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    
    if [ "${load_avg%.*}" -ge "$LOAD_THRESHOLD" ]; then
        log_error "High load average: ${load_avg}"
        status=1
    fi
    
    return $status
}

# Check memory usage
check_memory() {
    local status=0
    
    log_info "Checking memory usage..."
    
    # Get memory statistics
    local mem_total mem_free mem_available
    read -r mem_total mem_free mem_available < <(free | grep Mem | awk '{print $2,$4,$7}')
    
    # Calculate usage percentage
    local mem_usage
    mem_usage=$(( 100 - (mem_available * 100 / mem_total) ))
    
    if [ "$mem_usage" -ge "$MEM_THRESHOLD" ]; then
        log_error "High memory usage: ${mem_usage}%"
        status=1
    fi
    
    # Check swap usage
    local swap_total swap_used
    read -r swap_total swap_used < <(free | grep Swap | awk '{print $2,$3}')
    
    if [ "$swap_total" -gt 0 ] && [ "$swap_used" -gt 0 ]; then
        local swap_usage
        swap_usage=$(( swap_used * 100 / swap_total ))
        if [ "$swap_usage" -ge "$MEM_THRESHOLD" ]; then
            log_warn "High swap usage: ${swap_usage}%"
        fi
    fi
    
    return $status
}

# Check disk health
check_disk() {
    local status=0
    
    log_info "Checking disk health..."
    
    # Check disk usage
    df -h | grep -vE '^(tmpfs|devtmpfs|udev)' | tail -n +2 | while read -r line; do
        local usage
        usage=$(echo "$line" | awk '{print $5}' | tr -d '%')
        local mount
        mount=$(echo "$line" | awk '{print $6}')
        
        if [ "$usage" -ge "$DISK_THRESHOLD" ]; then
            log_error "High disk usage on ${mount}: ${usage}%"
            status=1
        fi
    done
    
    # Check disk I/O
    if command -v iostat >/dev/null 2>&1; then
        local high_io
        high_io=$(iostat -x 1 2 | awk '$1 ~ /^[a-zA-Z]/ && $14 > 80.0 {print $1}' | uniq)
        if [ -n "$high_io" ]; then
            log_warn "High disk I/O on devices: ${high_io}"
        fi
    fi
    
    return $status
}

# Check process health
check_processes() {
    local status=0
    
    log_info "Checking process health..."
    
    # Check total processes
    local total_processes
    total_processes=$(ps aux | wc -l)
    
    if [ "$total_processes" -gt "$PROCESS_THRESHOLD" ]; then
        log_error "Too many processes: ${total_processes}"
        status=1
    fi
    
    # Check zombie processes
    local zombie_count
    zombie_count=$(ps aux | awk '$8=="Z"' | wc -l)
    
    if [ "$zombie_count" -gt "$ZOMBIE_THRESHOLD" ]; then
        log_error "Too many zombie processes: ${zombie_count}"
        status=1
    fi
    
    # Check high CPU processes
    ps aux | awk '$3>50.0 {print $2,$3,$11,$12}' | while read -r pid cpu cmd args; do
        log_warn "High CPU process: PID=${pid}, CPU=${cpu}%, CMD=${cmd} ${args}"
    done
    
    return $status
}

# Check system limits
check_limits() {
    local status=0
    
    log_info "Checking system limits..."
    
    # Check file descriptors
    local fd_count
    fd_count=$(lsof | wc -l)
    local fd_limit
    fd_limit=$(ulimit -n)
    
    if [ "$fd_count" -gt "$((fd_limit * 80 / 100))" ]; then
        log_warn "High file descriptor usage: ${fd_count}/${fd_limit}"
    fi
    
    # Check max user processes
    local proc_limit
    proc_limit=$(ulimit -u)
    if [ "$total_processes" -gt "$((proc_limit * 80 / 100))" ]; then
        log_warn "High process usage: ${total_processes}/${proc_limit}"
    fi
    
    return $status
}

# Generate health report
generate_health_report() {
    local report_file="${HEALTH_DIR}/health_report.txt"
    
    {
        echo "=== System Health Report ==="
        echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo
        echo "System Information:"
        uname -a
        echo
        echo "Uptime:"
        uptime
        echo
        echo "CPU Usage:"
        top -bn1 | head -n 3
        echo
        echo "Memory Usage:"
        free -h
        echo
        echo "Disk Usage:"
        df -h
        echo
        echo "Process Summary:"
        ps aux | awk 'BEGIN {printf "%-16s %8s %8s %8s\n", "USER", "TOTAL", "RUNNING", "SLEEPING"}
            {users[$1]++; if($8=="R") running[$1]++; if($8=="S") sleeping[$1]++}
            END {for(user in users) printf "%-16s %8d %8d %8d\n", user, users[user], running[user], sleeping[user]}'
        echo
        echo "System Limits:"
        ulimit -a
    } > "$report_file"
}

# Main health check
main_health_check() {
    local status=0
    
    log_info "Starting system health check..."
    
    # Run all health checks
    check_cpu || status=1
    check_memory || status=1
    check_disk || status=1
    check_processes || status=1
    check_limits || status=1
    
    # Generate report
    generate_health_report
    
    if [ $status -eq 0 ]; then
        log_info "System health check passed"
    else
        log_error "System health check failed"
    fi
    
    return $status
}

# Main entry point
main() {
    if [ "$#" -gt 0 ]; then
        # Run specific health check
        case "$1" in
            cpu)
                check_cpu
                ;;
            memory)
                check_memory
                ;;
            disk)
                check_disk
                ;;
            processes)
                check_processes
                ;;
            limits)
                check_limits
                ;;
            report)
                generate_health_report
                ;;
            *)
                log_error "Unknown health check: ${1}"
                exit 1
                ;;
        esac
    else
        # Run full health check
        main_health_check
    fi
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main

