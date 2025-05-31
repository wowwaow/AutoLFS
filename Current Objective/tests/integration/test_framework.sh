#!/bin/bash

# Integration Testing Framework for LFS/BLFS Wrapper System
# Provides functionality for testing component interactions

set -euo pipefail

# Framework Configuration
INTEGRATION_LOG_DIR="/var/log/lfs-wrapper/integration"
INTEGRATION_REPORT_DIR="/var/log/lfs-wrapper/reports/integration"
TEST_ENVIRONMENT_DIR="/var/tmp/lfs-wrapper/test-env"
CURRENT_INTEGRATION_TEST=""

# Import unit test framework for common functionality
source ../unit/test_framework.sh

# Integration-specific test environment setup
setup_integration_environment() {
    mkdir -p "${TEST_ENVIRONMENT_DIR}"
    mkdir -p "${INTEGRATION_LOG_DIR}"
    mkdir -p "${INTEGRATION_REPORT_DIR}"
    
    # Create isolated test environment
    echo "Setting up integration test environment..."
    
    # Setup test configuration
    cat > "${TEST_ENVIRONMENT_DIR}/test-config.yaml" << EOF
system:
  build_dir: ${TEST_ENVIRONMENT_DIR}/build
  log_dir: ${TEST_ENVIRONMENT_DIR}/logs
  checkpoint_dir: ${TEST_ENVIRONMENT_DIR}/checkpoints

test:
  mode: integration
  cleanup: true
  verbose: true
EOF
}

# Integration test lifecycle functions
begin_integration_test() {
    CURRENT_INTEGRATION_TEST="$1"
    echo -e "\n${YELLOW}Starting integration test: $CURRENT_INTEGRATION_TEST${NC}"
    setup_integration_environment
}

end_integration_test() {
    echo -e "\n${YELLOW}Completed integration test: $CURRENT_INTEGRATION_TEST${NC}"
    cleanup_integration_environment
}

cleanup_integration_environment() {
    if [ -d "${TEST_ENVIRONMENT_DIR}" ]; then
        echo "Cleaning up test environment..."
        rm -rf "${TEST_ENVIRONMENT_DIR}"
    fi
}

# Integration-specific assertions
assert_system_integration() {
    local component="$1"
    local expected_status="$2"
    local message="${3:-}"
    
    local status
    status=$(lfs-wrapper check "$component" --json | jq -r '.status')
    
    if [ "$status" = "$expected_status" ]; then
        test_pass "Integration check passed for $component - $message"
    else
        test_fail "Integration check failed for $component (expected: $expected_status, got: $status) - $message"
    fi
}

assert_component_interaction() {
    local component1="$1"
    local component2="$2"
    local interaction_type="$3"
    local message="${4:-}"
    
    local result
    result=$(lfs-wrapper verify-interaction "$component1" "$component2" --type "$interaction_type" --json | jq -r '.success')
    
    if [ "$result" = "true" ]; then
        test_pass "Interaction check passed between $component1 and $component2 - $message"
    else
        test_fail "Interaction check failed between $component1 and $component2 - $message"
    fi
}

# Integration test execution
run_integration_test() {
    local test_name="$1"
    local test_function="$2"
    
    begin_integration_test "$test_name"
    
    if $test_function; then
        test_pass "$test_name"
    else
        test_fail "$test_name"
    fi
    
    end_integration_test
}

# Integration test report generation
generate_integration_report() {
    local report_file="${INTEGRATION_REPORT_DIR}/integration_report_$(date +%Y%m%d_%H%M%S).md"
    
    {
        echo "# Integration Test Report"
        echo "## Summary"
        echo "- Date: $(date)"
        echo "- Total Tests: $TOTAL_TESTS"
        echo "- Passed: $PASSED_TESTS"
        echo "- Failed: $FAILED_TESTS"
        echo "- Success Rate: $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%"
        
        echo -e "\n## Test Details"
        echo "- Environment: ${TEST_ENVIRONMENT_DIR}"
        echo "- Configuration: test-config.yaml"
        
        echo -e "\n## Integration Tests"
        echo "- $CURRENT_INTEGRATION_TEST"
        
        echo -e "\n## Component Interactions"
        lfs-wrapper list-interactions --json | jq '.'
        
        echo -e "\n## Failures"
        if [ -f "${INTEGRATION_LOG_DIR}/failures.log" ]; then
            cat "${INTEGRATION_LOG_DIR}/failures.log"
        else
            echo "No failures recorded"
        fi
    } > "$report_file"
    
    echo -e "\nIntegration test report generated: $report_file"
}

# Main integration test runner
main() {
    setup_integration_environment
    
    # Source all integration test suites
    for suite in test_suites/*.sh; do
        if [ -f "$suite" ]; then
            echo "Loading integration test suite: $suite"
            # shellcheck source=/dev/null
            source "$suite"
        fi
    done
    
    # Run integration test suites
    run_all_integration_test_suites
    
    # Generate integration report
    generate_integration_report
    
    # Cleanup
    cleanup_integration_environment
    
    # Return overall success/failure
    return $((FAILED_TESTS > 0))
}

# Execute if running directly
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

