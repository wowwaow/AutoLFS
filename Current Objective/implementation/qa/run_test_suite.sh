#!/bin/bash

# Test Suite Runner
# Manages execution of all test suites and generates reports

set -euo pipefail

# Script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QA_ROOT="$SCRIPT_DIR"

# Load helper libraries
source "${QA_ROOT}/lib/common_utils.sh"
source "${QA_ROOT}/lib/system_test_helpers.sh"
source "${QA_ROOT}/lib/performance_test_helpers.sh"
source "${QA_ROOT}/lib/security_test_helpers.sh"
source "${QA_ROOT}/lib/integration_test_helpers.sh"

# Initialize directories
RESULTS_DIR="${QA_ROOT}/results"
LOGS_DIR="${QA_ROOT}/logs"
mkdir -p "$RESULTS_DIR" "$LOGS_DIR"

# Set up logging
LOG_FILE="${LOGS_DIR}/test_run_$(date +%Y%m%d_%H%M%S).log"
init_logging "$LOG_FILE"

# Print usage information
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] SUITE

Run specified test suite(s) and generate reports.

Options:
    -h, --help              Show this help message
    -d, --debug            Enable debug output
    -v, --verbose          Enable verbose output
    -q, --quiet            Minimize output
    -p, --parallel         Run tests in parallel when possible
    --report-only          Only generate reports from existing results
    --no-report            Skip report generation
    
Available Test Suites:
    system                 Run system tests
    security              Run security tests
    performance           Run performance tests
    integration           Run integration tests
    all                   Run all test suites
EOF
}

# Parse command line arguments
VERBOSE=0
DEBUG=0
QUIET=0
PARALLEL=0
REPORT_ONLY=0
NO_REPORT=0
SUITE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        -d|--debug)
            DEBUG=1
            CURRENT_LOG_LEVEL=0  # Set to DEBUG level
            shift
            ;;
        -v|--verbose)
            VERBOSE=1
            CURRENT_LOG_LEVEL=1  # Set to INFO level
            shift
            ;;
        -q|--quiet)
            QUIET=1
            CURRENT_LOG_LEVEL=3  # Set to ERROR level
            shift
            ;;
        -p|--parallel)
            PARALLEL=1
            shift
            ;;
        --report-only)
            REPORT_ONLY=1
            shift
            ;;
        --no-report)
            NO_REPORT=1
            shift
            ;;
        system|security|performance|integration|all)
            SUITE="$1"
            shift
            ;;
        *)
            log "ERROR" "Unknown option or argument: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate arguments
if [[ -z "$SUITE" && "$REPORT_ONLY" -eq 0 ]]; then
    log "ERROR" "Test suite must be specified"
    usage
    exit 1
fi

if [[ "$REPORT_ONLY" -eq 1 && "$NO_REPORT" -eq 1 ]]; then
    log "ERROR" "Cannot specify both --report-only and --no-report"
    exit 1
fi

# Run specified test suite
run_test_suite() {
    local suite="$1"
    local suite_dir="${QA_ROOT}/tests/${suite}_tests"
    local start_time=$SECONDS
    
    log "INFO" "Running $suite test suite..."
    
    # Initialize test environment
    if ! init_test_env "$suite_dir"; then
        log "ERROR" "Failed to initialize test environment for $suite"
        return 1
    fi
    
    # Start resource monitoring if enabled
    if [[ "$VERBOSE" -eq 1 ]]; then
        monitor_resources "$suite_dir" &
        local monitor_pid=$!
    fi
    
    # Run test suite specific functions
    case "$suite" in
        system)
            run_system_tests "$suite_dir"
            ;;
        security)
            run_security_tests "$suite_dir"
            ;;
        performance)
            run_performance_tests "$suite_dir"
            ;;
        integration)
            run_integration_tests "$suite_dir"
            ;;
        *)
            log "ERROR" "Unknown test suite: $suite"
            return 1
            ;;
    esac
    local status=$?
    
    # Stop resource monitoring if enabled
    if [[ "$VERBOSE" -eq 1 ]]; then
        kill "$monitor_pid" 2>/dev/null
        wait "$monitor_pid" 2>/dev/null
    fi
    
    # Calculate duration
    local duration=$((SECONDS - start_time))
    log "INFO" "$suite test suite completed in ${duration}s with status $status"
    
    return $status
}

# Generate test reports
generate_test_reports() {
    log "INFO" "Generating test reports..."
    
    # Collect all test results
    local all_results=()
    for suite in system security performance integration; do
        if [[ -d "${RESULTS_DIR}/${suite}" ]]; then
            all_results+=("${RESULTS_DIR}/${suite}")
        fi
    done
    
    if [[ ${#all_results[@]} -eq 0 ]]; then
        log "WARN" "No test results found to generate reports"
        return 0
    fi
    
    # Generate consolidated report
    local report_file="${RESULTS_DIR}/test_report_$(date +%Y%m%d_%H%M%S).html"
    {
        create_html_header "Test Execution Report"
        
        # Summary section
        echo "<h2>Test Summary</h2>"
        format_test_summary "${all_results[@]}"
        
        # Detailed results by suite
        for suite in "${all_results[@]}"; do
            echo "<h2>$(basename "$suite") Results</h2>"
            format_test_results_table "$suite"
        done
        
        create_html_footer
    } > "$report_file"
    
    log "INFO" "Test report generated: $report_file"
    return 0
}

# Main execution
main() {
    local start_time=$SECONDS
    local exit_code=0
    
    # Validate test environment
    if ! validate_test_environment "$QA_ROOT"; then
        log "ERROR" "Test environment validation failed"
        exit 1
    fi
    
    # Run test suites
    if [[ "$REPORT_ONLY" -eq 0 ]]; then
        case "$SUITE" in
            all)
                for s in system security performance integration; do
                    if ! run_test_suite "$s"; then
                        exit_code=1
                    fi
                done
                ;;
            *)
                if ! run_test_suite "$SUITE"; then
                    exit_code=1
                fi
                ;;
        esac
    fi
    
    # Generate reports if needed
    if [[ "$NO_REPORT" -eq 0 ]]; then
        if ! generate_test_reports; then
            log "ERROR" "Report generation failed"
            exit_code=1
        fi
    fi
    
    # Calculate and log execution time
    local duration=$((SECONDS - start_time))
    log "INFO" "Test execution completed in ${duration}s"
    log "INFO" "Results available in: $RESULTS_DIR"
    log "INFO" "Logs available in: $LOG_FILE"
    
    return "$exit_code"
}

# Run main function
main

