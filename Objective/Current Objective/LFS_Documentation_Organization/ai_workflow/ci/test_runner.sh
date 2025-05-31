#!/bin/bash

# AI Workflow Test Runner
# Executes all test suites and generates comprehensive reports

set -e  # Exit on any error
set -u  # Error on undefined variables

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="${SCRIPT_DIR}/../tests"
REPORT_DIR="${SCRIPT_DIR}/reports"
LOG_DIR="${SCRIPT_DIR}/logs"

# Create necessary directories
mkdir -p "${REPORT_DIR}" "${LOG_DIR}"

# Initialize log file
LOG_FILE="${LOG_DIR}/test_run_$(date +%Y%m%d_%H%M%S).log"
exec 1> >(tee -a "${LOG_FILE}")
exec 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

run_test_suite() {
    local suite=$1
    local test_file="${TEST_DIR}/${suite}_tests.yaml"
    
    log "Running test suite: ${suite}"
    
    if [ ! -f "${test_file}" ]; then
        log "ERROR: Test file not found: ${test_file}"
        return 1
    }
    
    # Run the test suite
    python3 -m pytest "${test_file}" \
        --junitxml="${REPORT_DIR}/${suite}_report.xml" \
        --html="${REPORT_DIR}/${suite}_report.html" \
        || return 1
    
    log "Completed test suite: ${suite}"
    return 0
}

generate_summary_report() {
    local report_file="${REPORT_DIR}/summary_report.html"
    
    log "Generating summary report"
    
    # Combine all test results
    python3 -m coverage combine
    python3 -m coverage html -d "${REPORT_DIR}/coverage"
    python3 -m coverage report > "${REPORT_DIR}/coverage_summary.txt"
    
    # Generate summary HTML
    cat > "${report_file}" << EOF
<!DOCTYPE html>
<html>
<head><title>AI Workflow Test Summary</title></head>
<body>
<h1>Test Execution Summary</h1>
<p>Generated: $(date)</p>
<h2>Test Results</h2>
<ul>
EOF
    
    # Add results for each suite
    for suite in validation review update; do
        if [ -f "${REPORT_DIR}/${suite}_report.xml" ]; then
            echo "<li><a href='${suite}_report.html'>${suite} Tests</a></li>" >> "${report_file}"
        fi
    done
    
    # Add coverage report link
    echo "<li><a href='coverage/index.html'>Coverage Report</a></li>" >> "${report_file}"
    
    # Close HTML
    echo "</ul></body></html>" >> "${report_file}"
    
    log "Summary report generated: ${report_file}"
}

main() {
    log "Starting AI workflow test execution"
    
    # Load environment
    if [ -f "${SCRIPT_DIR}/environment.yaml" ]; then
        log "Loading test environment"
        python3 -m venv "${SCRIPT_DIR}/.venv"
        source "${SCRIPT_DIR}/.venv/bin/activate"
        pip install -r "${SCRIPT_DIR}/requirements.txt"
    else
        log "WARNING: environment.yaml not found"
    fi
    
    # Run all test suites
    local failed=0
    for suite in validation review update; do
        if ! run_test_suite "${suite}"; then
            log "ERROR: ${suite} test suite failed"
            failed=1
        fi
    done
    
    # Generate reports
    generate_summary_report
    
    if [ ${failed} -eq 1 ]; then
        log "One or more test suites failed"
        exit 1
    fi
    
    log "All test suites completed successfully"
}

main "$@"

