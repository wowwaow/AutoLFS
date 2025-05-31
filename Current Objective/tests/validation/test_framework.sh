#!/bin/bash

# Validation Testing Framework for LFS/BLFS Wrapper System
# Provides functionality for system-wide validation testing

set -euo pipefail

# Framework Configuration
VALIDATION_LOG_DIR="/var/log/lfs-wrapper/validation"
VALIDATION_REPORT_DIR="/var/log/lfs-wrapper/reports/validation"
VALIDATION_DATA_DIR="/var/tmp/lfs-wrapper/validation"
CURRENT_VALIDATION_TEST=""

# Import unit test framework for common functionality
source ../unit/test_framework.sh

# Validation-specific environment setup
setup_validation_environment() {
    mkdir -p "${VALIDATION_DATA_DIR}"
    mkdir -p "${VALIDATION_LOG_DIR}"
    mkdir -p "${VALIDATION_REPORT_DIR}"
    
    echo "Setting up validation environment..."
    
    # Setup validation configuration
    cat > "${VALIDATION_DATA_DIR}/validation-config.yaml" << EOF
validation:
  mode: comprehensive
  checks:
    - system_state
    - build_artifacts
    - dependencies
    - configurations
    - permissions
    - resources
  thresholds:
    disk_usage: 90
    memory_usage: 85
    cpu_load: 95
EOF
}

# Validation test lifecycle functions
begin_validation_test() {
    CURRENT_VALIDATION_TEST="$1"
    echo -e "\n${YELLOW}Starting validation test: $CURRENT_VALIDATION_TEST${NC}"
    setup_validation_environment
}

end_validation_test() {
    echo -e "\n${YELLOW}Completed validation test: $CURRENT_VALIDATION_TEST${NC}"
    cleanup_validation_environment
}

cleanup_validation_environment() {
    if [ -d "${VALIDATION_DATA_DIR}" ]; then
        echo "Cleaning up validation environment..."
        rm -rf "${VALIDATION_DATA_DIR}"
    fi
}

# Validation-specific assertions
assert_system_state() {
    local component="$1"
    local expected_state="$2"
    local message="${3:-}"
    
    local state
    state=$(lfs-wrapper validate state "$component" --json | jq -r '.state')
    
    if [ "$state" = "$expected_state" ]; then
        test_pass "System state validation passed for $component - $message"
    else
        test_fail "System state validation failed for $component (expected: $expected_state, got: $state) - $message"
    fi
}

assert_build_artifacts() {
    local package="$1"
    local artifact_type="$2"
    local message="${3:-}"
    
    local result
    result=$(lfs-wrapper validate artifacts "$package" --type "$artifact_type" --json | jq -r '.valid')
    
    if [ "$result" = "true" ]; then
        test_pass "Build artifact validation passed for $package ($artifact_type) - $message"
    else
        test_fail "Build artifact validation failed for $package ($artifact_type) - $message"
    fi
}

assert_dependencies() {
    local package="$1"
    local message="${2:-}"
    
    local result
    result=$(lfs-wrapper validate dependencies "$package" --json | jq -r '.satisfied')
    
    if [ "$result" = "true" ]; then
        test_pass "Dependency validation passed for $package - $message"
    else
        test_fail "Dependency validation failed for $package - $message"
    fi
}

# Validation test execution
run_validation_test() {
    local test_name="$1"
    local test_function="$2"
    
    begin_validation_test "$test_name"
    
    if $test_function; then
        test_pass "$test_name"
    else
        test_fail "$test_name"
    fi
    
    end_validation_test
}

# Validation report generation
generate_validation_report() {
    local report_file="${VALIDATION_REPORT_DIR}/validation_report_$(date +%Y%m%d_%H%M%S).md"
    
    {
        echo "# System Validation Report"
        echo "## Summary"
        echo "- Date: $(date)"
        echo "- Total Validations: $TOTAL_TESTS"
        echo "- Passed: $PASSED_TESTS"
        echo "- Failed: $FAILED_TESTS"
        echo "- Success Rate: $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%"
        
        echo -e "\n## Validation Details"
        echo "- Environment: ${VALIDATION_DATA_DIR}"
        echo "- Configuration: validation-config.yaml"
        
        echo -e "\n## System State"
        lfs-wrapper system-state --json | jq '.'
        
        echo -e "\n## Build Artifacts"
        lfs-wrapper list-artifacts --json | jq '.'
        
        echo -e "\n## Dependencies"
        lfs-wrapper check-dependencies --json | jq '.'
        
        echo -e "\n## Failures"
        if [ -f "${VALIDATION_LOG_DIR}/failures.log" ]; then
            cat "${VALIDATION_LOG_DIR}/failures.log"
        else
            echo "No failures recorded"
        fi
    } > "$report_file"
    
    echo -e "\nValidation report generated: $report_file"
}

# Main validation test runner
main() {
    setup_validation_environment
    
    # Source all validation test suites
    for suite in test_suites/*.sh; do
        if [ -f "$suite" ]; then
            echo "Loading validation test suite: $suite"
            # shellcheck source=/dev/null
            source "$suite"
        fi
    done
    
    # Run validation test suites
    run_all_validation_test_suites
    
    # Generate validation report
    generate_validation_report
    
    # Cleanup
    cleanup_validation_environment
    
    # Return overall success/failure
    return $((FAILED_TESTS > 0))
}

# Execute if running directly
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

