#!/bin/bash

# Load Testing Suite
# Tests system behavior under various load conditions

# Concurrent build tests
test_concurrent_package_builds() {
    run_load_test "concurrent_packages" build_multiple_packages 4
}

test_concurrent_system_operations() {
    run_load_test "concurrent_operations" perform_mixed_operations 3
}

# System capacity tests
test_max_concurrent_builds() {
    run_load_test "max_builds" build_packages_until_failure 8
}

test_max_concurrent_downloads() {
    run_load_test "max_downloads" download_packages_until_failure 6
}

# Resource exhaustion tests
test_memory_exhaustion() {
    run_load_test "memory_exhaustion" memory_intensive_build 4
}

test_disk_exhaustion() {
    run_load_test "disk_exhaustion" disk_intensive_build 3
}

# Helper functions
build_multiple_packages() {
    lfs-wrapper build packages --concurrent base-packages
}

perform_mixed_operations() {
    {
        lfs-wrapper build package gtk &
        lfs-wrapper validate system &
        lfs-wrapper download packages qt
    } &> /dev/null
}

build_packages_until_failure() {
    while lfs-wrapper build package test-package; do
        sleep 1
    done
}

download_packages_until_failure() {
    while lfs-wrapper download package test-package; do
        sleep 1
    done
}

memory_intensive_build() {
    lfs-wrapper build package --memory-intensive webkit
}

disk_intensive_build() {
    lfs-wrapper build package --disk-intensive llvm
}

# Load test scenarios
test_build_system_load() {
    # Test concurrent package builds
    run_load_test "build_load" concurrent_build_scenario 4
}

test_validation_system_load() {
    # Test concurrent validation operations
    run_load_test "validation_load" concurrent_validation_scenario 3
}

test_mixed_system_load() {
    # Test mixed operations load
    run_load_test "mixed_load" mixed_operation_scenario 5
}

# Scenario helper functions
concurrent_build_scenario() {
    # Run multiple builds with different configurations
    {
        lfs-wrapper build package base-system --config minimal &
        lfs-wrapper build package x-system --config desktop &
        lfs-wrapper build package dev-tools --config development
    } &> /dev/null
}

concurrent_validation_scenario() {
    # Run multiple validation operations
    {
        lfs-wrapper validate system &
        lfs-wrapper validate packages &
        lfs-wrapper validate dependencies
    } &> /dev/null
}

mixed_operation_scenario() {
    # Run mixed operations
    {
        lfs-wrapper build package gtk &
        lfs-wrapper validate system &
        lfs-wrapper download packages qt &
        lfs-wrapper clean cache &
        lfs-wrapper update system
    } &> /dev/null
}

# Register test suite
register_load_suite() {
    begin_test_suite "Load Tests"
    
    # Concurrent build tests
    test_concurrent_package_builds
    test_concurrent_system_operations
    
    # System capacity tests
    [[ $FULL_TEST == "true" ]] && test_max_concurrent_builds
    [[ $FULL_TEST == "true" ]] && test_max_concurrent_downloads
    
    # Resource exhaustion tests
    [[ $STRESS_TEST == "true" ]] && test_memory_exhaustion
    [[ $STRESS_TEST == "true" ]] && test_disk_exhaustion
    
    # Load scenarios
    test_build_system_load
    test_validation_system_load
    test_mixed_system_load
    
    end_test_suite
}

