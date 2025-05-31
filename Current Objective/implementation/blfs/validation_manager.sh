#!/bin/bash
#
# BLFS Validation Framework
# Manages build validation and system checks
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
BLFS_DIR="/var/run/lfs-wrapper/blfs"
VALIDATION_DIR="${BLFS_DIR}/validation"
TEST_DIR="${BLFS_DIR}/tests"
REPORT_DIR="${BLFS_DIR}/reports"
mkdir -p "$VALIDATION_DIR" "$TEST_DIR" "$REPORT_DIR"

# Validation types
declare -r VALIDATE_BUILD="build"
declare -r VALIDATE_SYSTEM="system"
declare -r VALIDATE_INTEGRATION="integration"
declare -r VALIDATE_PERFORMANCE="performance"

# Validate build process
validate_build() {
    local package="$1"
    local build_dir="$2"
    local status=0
    
    log_info "Validating build: ${package}"
    
    # Check build directory
    if [ ! -d "$build_dir" ]; then
        log_error "Build directory not found: ${build_dir}"
        return 1
    fi
    
    # Run build validation steps
    validate_build_files "$package" "$build_dir" || status=1
    validate_build_dependencies "$package" || status=1
    validate_build_outputs "$package" "$build_dir" || status=1
    
    return $status
}

# Validate build files
validate_build_files() {
    local package="$1"
    local build_dir="$2"
    local status=0
    
    # Check required files
    local required_files
    required_files=$(get_required_files "$package")
    
    for file in $required_files; do
        if [ ! -f "${build_dir}/${file}" ]; then
            log_error "Required file missing: ${file}"
            status=1
        fi
    done
    
    # Check file permissions
    find "$build_dir" -type f -executable | while read -r exe; do
        local perms
        perms=$(stat -c "%a" "$exe")
        if [[ ! "$perms" =~ ^[567][0-7][0-7]$ ]]; then
            log_error "Invalid permissions on executable: ${exe} (${perms})"
            status=1
        fi
    done
    
    return $status
}

# Validate build dependencies
validate_build_dependencies() {
    local package="$1"
    local status=0
    
    # Check runtime dependencies
    local deps_file="${BLFS_DIR}/metadata/${package}/dependencies.conf"
    if [ -f "$deps_file" ]; then
        while IFS=':' read -r dep_type dep_name version_req; do
            # Skip comments and empty lines
            [[ "$dep_type" =~ ^[[:space:]]*# ]] && continue
            [ -z "$dep_type" ] && continue
            
            if [ "$dep_type" = "runtime" ]; then
                if ! check_runtime_dependency "$dep_name" "$version_req"; then
                    log_error "Runtime dependency not satisfied: ${dep_name} (${version_req})"
                    status=1
                fi
            fi
        done < "$deps_file"
    fi
    
    return $status
}

# Validate build outputs
validate_build_outputs() {
    local package="$1"
    local build_dir="$2"
    local status=0
    
    # Check build artifacts
    local artifacts_file="${VALIDATION_DIR}/${package}/artifacts.list"
    if [ -f "$artifacts_file" ]; then
        while IFS= read -r artifact; do
            # Skip comments and empty lines
            [[ "$artifact" =~ ^[[:space:]]*# ]] && continue
            [ -z "$artifact" ] && continue
            
            if [ ! -e "${build_dir}/${artifact}" ]; then
                log_error "Required artifact missing: ${artifact}"
                status=1
            fi
        done < "$artifacts_file"
    fi
    
    return $status
}

# Run system checks
run_system_checks() {
    local status=0
    
    log_info "Running system checks..."
    
    # Check system resources
    check_system_resources || status=1
    
    # Check system configuration
    check_system_configuration || status=1
    
    # Check system stability
    check_system_stability || status=1
    
    return $status
}

# Check system resources
check_system_resources() {
    local status=0
    
    # Check disk space
    local disk_free
    disk_free=$(df -m . | awk 'NR==2 {print $4}')
    if [ "$disk_free" -lt 10240 ]; then  # 10GB minimum
        log_error "Insufficient disk space: ${disk_free}MB"
        status=1
    fi
    
    # Check memory
    local mem_free
    mem_free=$(($(grep MemAvailable /proc/meminfo | awk '{print $2}') / 1024))
    if [ "$mem_free" -lt 2048 ]; then  # 2GB minimum
        log_error "Insufficient memory: ${mem_free}MB"
        status=1
    fi
    
    # Check load average
    local load_avg
    load_avg=$(cut -d' ' -f1 /proc/loadavg)
    if [ "${load_avg%.*}" -gt 8 ]; then  # Max load 8
        log_error "System load too high: ${load_avg}"
        status=1
    fi
    
    return $status
}

# Check system configuration
check_system_configuration() {
    local status=0
    
    # Check kernel parameters
    local required_params=(
        "fs.file-max:100000"
        "kernel.pid_max:32768"
        "vm.max_map_count:262144"
    )
    
    for param in "${required_params[@]}"; do
        local key value
        key=${param%:*}
        value=${param#*:}
        
        local current
        current=$(sysctl -n "$key")
        if [ "$current" -lt "$value" ]; then
            log_error "Kernel parameter too low: ${key}=${current} (min: ${value})"
            status=1
        fi
    done
    
    # Check user limits
    check_user_limits || status=1
    
    return $status
}

# Check system stability
check_system_stability() {
    local status=0
    
    # Run quick stress test
    log_info "Running stability test..."
    
    # CPU test
    if ! stress-ng --cpu 1 --timeout 10s >/dev/null 2>&1; then
        log_error "CPU stability test failed"
        status=1
    fi
    
    # Memory test
    if ! stress-ng --vm 1 --vm-bytes 256M --timeout 10s >/dev/null 2>&1; then
        log_error "Memory stability test failed"
        status=1
    fi
    
    # I/O test
    if ! stress-ng --io 1 --timeout 10s >/dev/null 2>&1; then
        log_error "I/O stability test failed"
        status=1
    fi
    
    return $status
}

# Run integration tests
run_integration_tests() {
    local package="$1"
    local status=0
    
    log_info "Running integration tests for: ${package}"
    
    # Run package-specific tests
    local test_dir="${TEST_DIR}/${package}"
    if [ -d "$test_dir" ]; then
        for test in "$test_dir"/*_test.sh; do
            if [ -x "$test" ]; then
                if ! "$test"; then
                    log_error "Integration test failed: ${test}"
                    status=1
                fi
            fi
        done
    fi
    
    # Run system integration tests
    local system_test="${VALIDATION_DIR}/system_integration_test.sh"
    if [ -x "$system_test" ]; then
        if ! "$system_test" "$package"; then
            log_error "System integration test failed"
            status=1
        fi
    fi
    
    return $status
}

# Generate validation report
generate_validation_report() {
    local package="$1"
    local report_file="${REPORT_DIR}/${package}_validation_report.txt"
    
    {
        echo "=== Validation Report ==="
        echo "Package: ${package}"
        echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo
        
        echo "Build Validation:"
        validate_build "$package" "${BLFS_DIR}/build/${package}" > >(sed 's/^/  /')
        echo
        
        echo "System Checks:"
        run_system_checks > >(sed 's/^/  /')
        echo
        
        echo "Integration Tests:"
        run_integration_tests "$package" > >(sed 's/^/  /')
        echo
        
        echo "Resource Usage:"
        echo "  CPU: $(get_cpu_usage)%"
        echo "  Memory: $(get_memory_usage)MB"
        echo "  Disk: $(get_disk_usage)MB"
    } > "$report_file"
}

# Main entry point
main() {
    if [ "$#" -lt 2 ]; then
        log_error "Usage: $0 <command> [args...]"
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        validate)
            if [ "$#" -lt 2 ]; then
                log_error "Usage: $0 validate <type> <package> [build_dir]"
                exit 1
            fi
            local type="$1"
            local package="$2"
            local build_dir="${3:-${BLFS_DIR}/build/${package}}"
            
            case "$type" in
                "$VALIDATE_BUILD")
                    validate_build "$package" "$build_dir"
                    ;;
                "$VALIDATE_SYSTEM")
                    run_system_checks
                    ;;
                "$VALIDATE_INTEGRATION")
                    run_integration_tests "$package"
                    ;;
                *)
                    log_error "Unknown validation type: ${type}"
                    exit 1
                    ;;
            esac
            ;;
        report)
            if [ "$#" -lt 1 ]; then
                log_error "Usage: $0 report <package>"
                exit 1
            fi
            generate_validation_report "$1"
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

