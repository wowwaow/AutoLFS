#!/bin/bash

# Performance test helper functions with error handling and logging

# Source common utilities
SYSTEM_DIR="/mnt/host/WARP_CURRENT"
source "${SYSTEM_DIR}/System Commands/common_utils.sh"

# Initialize logging
LOG_FILE="${SYSTEM_DIR}/System Logs/performance_test.log"
REPORT_DIR="${SYSTEM_DIR}/Current Objective/test_reports"
METRICS_DIR="${SYSTEM_DIR}/Current Objective/performance_metrics"

# Error handling function
handle_performance_error() {
    local error_msg="$1"
    local metric="${2:-unknown}"
    local error_code="${3:-1}"
    echo "[ERROR][$metric] $(date '+%Y-%m-%d %H:%M:%S') - $error_msg" >> "$LOG_FILE"
    return "$error_code"
}

# Performance logging function
log_performance_event() {
    local msg="$1"
    local level="${2:-INFO}"
    local metric="${3:-PERFORMANCE}"
    echo "[$level][$metric] $(date '+%Y-%m-%d %H:%M:%S') - $msg" >> "$LOG_FILE"
}

# Measure build metric
measure_build_metric() {
    local build_phase="$1"
    local metric_type="$2"
    local threshold="${3:-}"
    
    log_performance_event "Measuring build metric: $metric_type for $build_phase"
    
    # Ensure metrics directory exists with correct permissions
    mkdir -p "$METRICS_DIR"
    chmod 755 "$METRICS_DIR"
    
    # Initialize measurement
    local start_time
    start_time=$(date +%s.%N)
    
    # Execute build phase
    if ! execute_build_phase "$build_phase"; then
        handle_performance_error "Build phase execution failed" "$build_phase"
        return 1
    }
    
    # Calculate duration
    local end_time
    end_time=$(date +%s.%N)
    local duration
    duration=$(echo "$end_time - $start_time" | bc)
    
    # Store metric
    local metric_file="$METRICS_DIR/${build_phase}_${metric_type}.metric"
    echo "$duration" > "$metric_file"
    chmod 644 "$metric_file"
    
    # Check threshold if specified
    if [[ -n "$threshold" ]] && (( $(echo "$duration > $threshold" | bc -l) )); then
        handle_performance_error "Build metric exceeded threshold" "$build_phase"
        return 1
    }
    
    log_performance_event "Build metric measured successfully: $duration seconds" "SUCCESS" "$build_phase"
    return 0
}

# Monitor resource
monitor_resource() {
    local resource_type="$1"
    local interval="${2:-1}"  # Default 1 second
    local duration="${3:-60}" # Default 60 seconds
    
    log_performance_event "Starting resource monitoring: $resource_type"
    
    # Initialize monitoring file
    local monitor_file="$METRICS_DIR/${resource_type}_$(date +%Y%m%d_%H%M%S).log"
    touch "$monitor_file"
    chmod 644 "$monitor_file"
    
    # Monitor resource for specified duration
    local count=0
    while [[ $count -lt $duration ]]; do
        case "$resource_type" in
            "cpu")
                mpstat 1 1 | tail -n 1 >> "$monitor_file"
                ;;
            "memory")
                free -m | grep Mem >> "$monitor_file"
                ;;
            "disk")
                df -h / >> "$monitor_file"
                ;;
            "network")
                netstat -i | grep -v "Kernel" >> "$monitor_file"
                ;;
            "process")
                ps -o pid,ppid,%cpu,%mem,cmd -p "$4" >> "$monitor_file"
                ;;
            *)
                handle_performance_error "Invalid resource type specified" "$resource_type"
                return 1
                ;;
        esac
        
        sleep "$interval"
        ((count += interval))
    done
    
    log_performance_event "Resource monitoring completed: $resource_type" "SUCCESS"
    return 0
}

# Test scalability scenario
test_scalability_scenario() {
    local scenario_name="$1"
    local min_load="$2"
    local max_load="$3"
    local step="${4:-10}"
    
    log_performance_event "Starting scalability test: $scenario_name"
    
    local results_file="$METRICS_DIR/scalability_${scenario_name}_$(date +%Y%m%d_%H%M%S).csv"
    echo "Load,Response Time,Error Rate" > "$results_file"
    chmod 644 "$results_file"
    
    for load in $(seq "$min_load" "$step" "$max_load"); do
        local start_time
        start_time=$(date +%s.%N)
        
        if ! run_load_scenario "$scenario_name" "$load"; then
            handle_performance_error "Scalability test failed at load: $load" "$scenario_name"
            continue
        }
        
        local end_time
        end_time=$(date +%s.%N)
        local duration
        duration=$(echo "$end_time - $start_time" | bc)
        
        local error_rate
        error_rate=$(calculate_error_rate "$scenario_name")
        
        echo "$load,$duration,$error_rate" >> "$results_file"
    done
    
    log_performance_event "Scalability test completed: $scenario_name" "SUCCESS"
    return 0
}

# Run load scenario
run_load_scenario() {
    local scenario_name="$1"
    local load="$2"
    local duration="${3:-300}"  # Default 5 minutes
    
    log_performance_event "Running load scenario: $scenario_name with load: $load"
    
    # Start resource monitoring
    monitor_resource "cpu" 5 "$duration" &
    monitor_resource "memory" 5 "$duration" &
    local monitor_pids="$!"
    
    # Execute load test
    if ! execute_load_test "$scenario_name" "$load" "$duration"; then
        handle_performance_error "Load scenario execution failed" "$scenario_name"
        kill "$monitor_pids" 2>/dev/null
        return 1
    }
    
    # Wait for monitoring to complete
    wait "$monitor_pids"
    
    log_performance_event "Load scenario completed: $scenario_name" "SUCCESS"
    return 0
}

# Run benchmark test
run_benchmark_test() {
    local benchmark_name="$1"
    local iterations="${2:-10}"
    
    log_performance_event "Starting benchmark test: $benchmark_name"
    
    local results_file="$METRICS_DIR/benchmark_${benchmark_name}_$(date +%Y%m%d_%H%M%S).csv"
    echo "Iteration,Duration" > "$results_file"
    chmod 644 "$results_file"
    
    for ((i=1; i<=iterations; i++)); do
        local start_time
        start_time=$(date +%s.%N)
        
        if ! execute_benchmark "$benchmark_name"; then
            handle_performance_error "Benchmark execution failed at iteration $i" "$benchmark_name"
            continue
        }
        
        local end_time
        end_time=$(date +%s.%N)
        local duration
        duration=$(echo "$end_time - $start_time" | bc)
        
        echo "$i,$duration" >> "$results_file"
    done
    
    log_performance_event "Benchmark test completed: $benchmark_name" "SUCCESS"
    return 0
}

# Generate performance report
generate_performance_report() {
    local test_suite="$1"
    local report_file="$REPORT_DIR/performance_report_${test_suite}_$(date +%Y%m%d_%H%M%S).md"
    
    log_performance_event "Generating performance report: $test_suite"
    
    # Ensure report directory exists with correct permissions
    mkdir -p "$REPORT_DIR"
    chmod 755 "$REPORT_DIR"
    
    # Create report header
    {
        echo "# Performance Test Report: $test_suite"
        echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
        echo
        echo "## Summary"
        
        # Process metrics files
        echo "### Build Metrics"
        find "$METRICS_DIR" -name "${test_suite}_*.metric" -type f | while read -r metric_file; do
            local metric_name
            metric_name=$(basename "$metric_file" .metric)
            echo "- $metric_name: $(cat "$metric_file") seconds"
        done
        
        echo
        echo "### Resource Utilization"
        find "$METRICS_DIR" -name "*_$(date +%Y%m%d)*.log" -type f | while read -r log_file; do
            echo "#### $(basename "$log_file" .log)"
            echo '```'
            tail -n 5 "$log_file"
            echo '```'
        done
        
        echo
        echo "### Test Results"
        find "$METRICS_DIR" -name "*.csv" -type f | while read -r csv_file; do
            echo "#### $(basename "$csv_file" .csv)"
            echo '```'
            head -n 5 "$csv_file"
            echo '```'
        done
        
    } > "$report_file"
    
    chmod 644 "$report_file"
    
    log_performance_event "Performance report generated successfully: $test_suite" "SUCCESS"
    return 0
}
