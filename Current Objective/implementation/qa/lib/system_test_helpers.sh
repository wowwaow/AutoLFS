#!/bin/bash

# System test helper functions

# Verify system requirements are met
verify_system_requirements() {
    local min_memory=4 # GB
    local min_cores=2
    
    # Get system memory in GB
    local total_memory
    total_memory=$(free -g | awk '/^Mem:/{print $2}')
    
    # Get CPU cores
    local cpu_cores
    cpu_cores=$(nproc)
    
    if (( total_memory < min_memory )); then
        echo "Error: Insufficient memory. Required: ${min_memory}GB, Available: ${total_memory}GB" >&2
        return 1
    fi
    
    if (( cpu_cores < min_cores )); then
        echo "Error: Insufficient CPU cores. Required: ${min_cores}, Available: ${cpu_cores}" >&2
        return 1
    fi
    
    return 0
}

# Collect system metrics
collect_system_metrics() {
    local output_file="$1"
    
    # CPU usage (average over 1 second)
    local cpu_usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
    
    # Memory usage
    local memory_info
    memory_info=$(free -m | grep Mem)
    local total_mem
    total_mem=$(echo "$memory_info" | awk '{print $2}')
    local used_mem
    used_mem=$(echo "$memory_info" | awk '{print $3}')
    local used_percent
    used_percent=$(( (used_mem * 100) / total_mem ))
    
    # Disk usage
    local disk_usage
    disk_usage=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
    
    # Create metrics JSON
    cat > "$output_file" << EOL
{
    "cpu_usage_percent": ${cpu_usage},
    "memory_usage_percent": ${used_percent},
    "disk_usage_percent": ${disk_usage}
}
EOL
}

# Validate test environment
validate_test_environment() {
    local test_dir="$1"
    
    # Check directory exists and is writable
    if [[ ! -d "$test_dir" ]]; then
        echo "Error: Test directory does not exist: $test_dir" >&2
        return 1
    fi
    
    if [[ ! -w "$test_dir" ]]; then
        echo "Error: Test directory is not writable: $test_dir" >&2
        return 1
    fi
    
    # Verify system requirements
    if ! verify_system_requirements; then
        return 1
    fi
    
    return 0
}

# Format test results
format_test_results() {
    local total="$1"
    local passed="$2"
    local failed="$3"
    local duration="$4"
    local output_file="$5"
    
    cat > "$output_file" << EOL
{
    "total_tests": ${total},
    "tests_passed": ${passed},
    "tests_failed": ${failed},
    "duration": ${duration}
}
EOL
}

# Initialize test environment
init_test_env() {
    local test_dir="$1"
    
    # Create required directories
    mkdir -p "${test_dir}/results"
    mkdir -p "${test_dir}/logs"
    mkdir -p "${test_dir}/tmp"
    
    # Set proper permissions
    chmod 755 "${test_dir}/results" "${test_dir}/logs" "${test_dir}/tmp"
    
    # Validate environment
    validate_test_environment "$test_dir"
}
