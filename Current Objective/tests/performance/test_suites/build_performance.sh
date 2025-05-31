#!/bin/bash

# Build Performance Test Suite
# Tests build system performance and resource usage

# Build performance benchmarks
test_basic_build_performance() {
    run_benchmark "basic_build" build_basic_package 3
}

test_full_system_build_performance() {
    run_benchmark "full_system_build" build_full_system 1
}

test_incremental_build_performance() {
    run_benchmark "incremental_build" build_incremental 3
}

# Build load tests
test_concurrent_builds() {
    run_load_test "concurrent_builds" build_test_package 4
}

test_parallel_package_builds() {
    run_load_test "parallel_builds" build_multiple_packages 2
}

# Build stress tests
test_continuous_build_stress() {
    run_stress_test "continuous_build" build_stress_package 1800 "medium"
}

# Helper functions
build_basic_package() {
    lfs-wrapper build package base-system
}

build_full_system() {
    lfs-wrapper build system full
}

build_incremental() {
    lfs-wrapper build package --incremental desktop-packages
}

build_test_package() {
    lfs-wrapper build package test-suite
}

build_multiple_packages() {
    lfs-wrapper build packages common-tools
}

build_stress_package() {
    lfs-wrapper build package stress-test
}

# Register test suite
register_performance_suite() {
    begin_test_suite "Build Performance Tests"
    
    # Benchmarks
    test_basic_build_performance
    test_incremental_build_performance
    [[ $FULL_TEST == "true" ]] && test_full_system_build_performance
    
    # Load tests
    test_concurrent_builds
    test_parallel_package_builds
    
    # Stress tests
    [[ $STRESS_TEST == "true" ]] && test_continuous_build_stress
    
    end_test_suite
}

