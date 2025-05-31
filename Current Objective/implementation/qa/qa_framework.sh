#!/bin/bash

# Quality Assurance Framework
# Provides comprehensive testing, quality metrics collection, and reporting

set -euo pipefail

# Configuration
QA_ROOT="/var/lib/lfs-wrapper/qa"
QA_DB="${QA_ROOT}/qa.db"
TEST_ROOT="${QA_ROOT}/tests"
COVERAGE_DIR="${QA_ROOT}/coverage"
METRICS_DIR="${QA_ROOT}/metrics"
REPORTS_DIR="${QA_ROOT}/reports"

# Initialize QA framework
init_qa_framework() {
    mkdir -p "${TEST_ROOT}"
    mkdir -p "${COVERAGE_DIR}"
    mkdir -p "${METRICS_DIR}"
    mkdir -p "${REPORTS_DIR}"
    
    # Initialize QA database
    sqlite3 "${QA_DB}" << 'EOF'
CREATE TABLE IF NOT EXISTS test_runs (
    id INTEGER PRIMARY KEY,
    suite TEXT,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    status TEXT,
    total_tests INTEGER,
    passed_tests INTEGER,
    failed_tests INTEGER
);

CREATE TABLE IF NOT EXISTS test_results (
    run_id INTEGER,
    test_name TEXT,
    status TEXT,
    duration REAL,
    output TEXT,
    error TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES test_runs(id)
);

CREATE TABLE IF NOT EXISTS coverage_data (
    run_id INTEGER,
    file TEXT,
    lines_total INTEGER,
    lines_covered INTEGER,
    branches_total INTEGER,
    branches_covered INTEGER,
    FOREIGN KEY(run_id) REFERENCES test_runs(id)
);

CREATE TABLE IF NOT EXISTS quality_metrics (
    run_id INTEGER,
    metric TEXT,
    value REAL,
    unit TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES test_runs(id)
);
EOF
}

# Test execution management
run_test_suite() {
    local suite="$1"
    local suite_path="${TEST_ROOT}/${suite}"
    
    echo "Running test suite: $suite"
    
    # Start test run
    local run_id
    run_id=$(start_test_run "$suite")
    
    # Run all tests in suite
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    
    for test_file in "${suite_path}"/*.test; do
        if [ -f "$test_file" ]; then
            local test_name
            test_name=$(basename "$test_file" .test)
            
            echo "Running test: $test_name"
            if run_single_test "$run_id" "$test_name" "$test_file"; then
                ((passed_tests++))
            else
                ((failed_tests++))
            fi
            ((total_tests++))
        fi
    done
    
    # End test run
    end_test_run "$run_id" $total_tests $passed_tests $failed_tests
    
    # Generate reports
    generate_test_report "$run_id"
    generate_coverage_report "$run_id"
    generate_quality_report "$run_id"
}

run_single_test() {
    local run_id="$1"
    local test_name="$2"
    local test_file="$3"
    
    # Start coverage tracking
    start_coverage_tracking "$test_name"
    
    # Record start time
    local start_time
    start_time=$(date +%s.%N)
    
    # Run test
    local output
    local status=0
    output=$(bash "$test_file" 2>&1) || status=$?
    
    # Record end time and duration
    local end_time
    end_time=$(date +%s.%N)
    local duration
    duration=$(echo "$end_time - $start_time" | bc)
    
    # Stop coverage tracking
    stop_coverage_tracking "$test_name"
    
    # Record test result
    if [ $status -eq 0 ]; then
        record_test_result "$run_id" "$test_name" "pass" "$duration" "$output" ""
        return 0
    else
        record_test_result "$run_id" "$test_name" "fail" "$duration" "$output" "Exit code: $status"
        return 1
    fi
}

# Coverage tracking
start_coverage_tracking() {
    local test_name="$1"
    local coverage_file="${COVERAGE_DIR}/${test_name}.gcov"
    
    # Enable coverage tracking
    export BASH_XTRACEFD=1
    set -x
    
    # Clear previous coverage data
    rm -f "$coverage_file"
    touch "$coverage_file"
}

stop_coverage_tracking() {
    local test_name="$1"
    
    # Disable coverage tracking
    set +x
    unset BASH_XTRACEFD
    
    # Process coverage data
    process_coverage_data "$test_name"
}

process_coverage_data() {
    local test_name="$1"
    local coverage_file="${COVERAGE_DIR}/${test_name}.gcov"
    
    # Parse coverage data
    local lines_total=0
    local lines_covered=0
    local branches_total=0
    local branches_covered=0
    
    while IFS= read -r line; do
        ((lines_total++))
        if [[ "$line" =~ ^[[:space:]]*[1-9] ]]; then
            ((lines_covered++))
        fi
        if [[ "$line" =~ branch ]]; then
            ((branches_total++))
            if [[ "$line" =~ taken ]]; then
                ((branches_covered++))
            fi
        fi
    done < "$coverage_file"
    
    # Record coverage data
    record_coverage_data "$test_name" $lines_total $lines_covered $branches_total $branches_covered
}

# Quality metrics collection
collect_quality_metrics() {
    local run_id="$1"
    
    # Collect various quality metrics
    collect_code_metrics "$run_id"
    collect_performance_metrics "$run_id"
    collect_resource_metrics "$run_id"
    collect_security_metrics "$run_id"
}

collect_code_metrics() {
    local run_id="$1"
    
    # Calculate code quality metrics
    local complexity
    complexity=$(calculate_complexity)
    
    local duplication
    duplication=$(detect_duplication)
    
    local style_issues
    style_issues=$(check_code_style)
    
    # Record metrics
    record_quality_metric "$run_id" "complexity" "$complexity" "score"
    record_quality_metric "$run_id" "duplication" "$duplication" "percent"
    record_quality_metric "$run_id" "style_issues" "$style_issues" "count"
}

# Database functions
start_test_run() {
    local suite="$1"
    
    sqlite3 "${QA_DB}" << EOF
INSERT INTO test_runs (suite, status)
VALUES ('${suite}', 'running');
EOF
    
    sqlite3 "${QA_DB}" "SELECT last_insert_rowid();"
}

end_test_run() {
    local run_id="$1"
    local total="$2"
    local passed="$3"
    local failed="$4"
    
    sqlite3 "${QA_DB}" << EOF
UPDATE test_runs 
SET 
    end_time = datetime('now'),
    status = 'completed',
    total_tests = ${total},
    passed_tests = ${passed},
    failed_tests = ${failed}
WHERE id = ${run_id};
EOF
}

record_test_result() {
    local run_id="$1"
    local test_name="$2"
    local status="$3"
    local duration="$4"
    local output="$5"
    local error="$6"
    
    sqlite3 "${QA_DB}" << EOF
INSERT INTO test_results (run_id, test_name, status, duration, output, error)
VALUES (
    ${run_id},
    '${test_name}',
    '${status}',
    ${duration},
    '${output//\'/\'\'}',
    '${error//\'/\'\'}'
);
EOF
}

record_coverage_data() {
    local test_name="$1"
    local lines_total="$2"
    local lines_covered="$3"
    local branches_total="$4"
    local branches_covered="$5"
    
    sqlite3 "${QA_DB}" << EOF
INSERT INTO coverage_data (
    run_id,
    file,
    lines_total,
    lines_covered,
    branches_total,
    branches_covered
)
VALUES (
    (SELECT max(id) FROM test_runs),
    '${test_name}',
    ${lines_total},
    ${lines_covered},
    ${branches_total},
    ${branches_covered}
);
EOF
}

record_quality_metric() {
    local run_id="$1"
    local metric="$2"
    local value="$3"
    local unit="$4"
    
    sqlite3 "${QA_DB}" << EOF
INSERT INTO quality_metrics (run_id, metric, value, unit)
VALUES (${run_id}, '${metric}', ${value}, '${unit}');
EOF
}

# Report generation
generate_test_report() {
    local run_id="$1"
    local report_file="${REPORTS_DIR}/test_report_${run_id}.md"
    
    {
        echo "# Test Execution Report"
        echo "Run ID: $run_id"
        echo "Generated: $(date)"
        echo
        
        echo "## Summary"
        sqlite3 "${QA_DB}" << EOF
SELECT 
    suite,
    total_tests,
    passed_tests,
    failed_tests,
    ROUND(CAST(passed_tests AS FLOAT) / total_tests * 100, 2) as pass_rate,
    strftime('%Y-%m-%d %H:%M:%S', start_time) as started,
    strftime('%Y-%m-%d %H:%M:%S', end_time) as completed
FROM test_runs
WHERE id = ${run_id};
EOF
        
        echo
        echo "## Test Results"
        sqlite3 "${QA_DB}" << EOF
SELECT 
    test_name,
    status,
    ROUND(duration, 3) as duration_sec,
    CASE 
        WHEN error != '' THEN error
        ELSE 'No errors'
    END as error
FROM test_results
WHERE run_id = ${run_id}
ORDER BY test_name;
EOF
        
    } > "$report_file"
    
    echo "Test report generated: $report_file"
}

generate_coverage_report() {
    local run_id="$1"
    local report_file="${REPORTS_DIR}/coverage_report_${run_id}.md"
    
    {
        echo "# Code Coverage Report"
        echo "Run ID: $run_id"
        echo "Generated: $(date)"
        echo
        
        echo "## Coverage Summary"
        sqlite3 "${QA_DB}" << EOF
SELECT 
    SUM(lines_covered) as total_lines_covered,
    SUM(lines_total) as total_lines,
    ROUND(CAST(SUM(lines_covered) AS FLOAT) / SUM(lines_total) * 100, 2) as line_coverage,
    SUM(branches_covered) as total_branches_covered,
    SUM(branches_total) as total_branches,
    ROUND(CAST(SUM(branches_covered) AS FLOAT) / SUM(branches_total) * 100, 2) as branch_coverage
FROM coverage_data
WHERE run_id = ${run_id};
EOF
        
        echo
        echo "## Per-File Coverage"
        sqlite3 "${QA_DB}" << EOF
SELECT 
    file,
    lines_covered,
    lines_total,
    ROUND(CAST(lines_covered AS FLOAT) / lines_total * 100, 2) as line_coverage,
    branches_covered,
    branches_total,
    ROUND(CAST(branches_covered AS FLOAT) / branches_total * 100, 2) as branch_coverage
FROM coverage_data
WHERE run_id = ${run_id}
ORDER BY file;
EOF
        
    } > "$report_file"
    
    echo "Coverage report generated: $report_file"
}

generate_quality_report() {
    local run_id="$1"
    local report_file="${REPORTS_DIR}/quality_report_${run_id}.md"
    
    {
        echo "# Quality Metrics Report"
        echo "Run ID: $run_id"
        echo "Generated: $(date)"
        echo
        
        echo "## Metrics Summary"
        sqlite3 "${QA_DB}" << EOF
SELECT 
    metric,
    ROUND(AVG(value), 2) as avg_value,
    unit,
    COUNT(*) as measurements
FROM quality_metrics
WHERE run_id = ${run_id}
GROUP BY metric, unit
ORDER BY metric;
EOF
        
        echo
        echo "## Trends"
        sqlite3 "${QA_DB}" << EOF
SELECT 
    metric,
    ROUND(value, 2) as value,
    unit,
    strftime('%Y-%m-%d %H:%M:%S', timestamp) as measured_at
FROM quality_metrics
WHERE run_id = ${run_id}
ORDER BY metric, timestamp;
EOF
        
    } > "$report_file"
    
    echo "Quality report generated: $report_file"
}

# Main functionality
main() {
    local command="$1"
    shift
    
    case "$command" in
        init)
            init_qa_framework
            ;;
        run)
            run_test_suite "$@"
            ;;
        coverage)
            generate_coverage_report "$@"
            ;;
        metrics)
            collect_quality_metrics "$@"
            ;;
        report)
            generate_test_report "$@"
            ;;
        *)
            echo "Unknown command: $command"
            exit 1
            ;;
    esac
}

# Execute if running directly
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

