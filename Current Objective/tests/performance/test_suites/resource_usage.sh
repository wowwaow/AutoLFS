#!/bin/bash

# Resource Usage Test Suite
# Tests system resource utilization during various operations

# CPU usage tests
test_cpu_usage_during_build() {
    run_benchmark "cpu_build_usage" monitor_cpu_build 1
}

test_cpu_usage_under_load() {
    run_load_test "cpu_load" stress_cpu 4
}

# Memory usage tests
test_memory_usage_during_build() {
    run_benchmark "memory_build_usage" monitor_memory_build 1
}

test_memory_usage_under_load() {
    run_load_test "memory_load" stress_memory 2
}

# Disk I/O tests
test_disk_io_during_build() {
    run_benchmark "disk_build_usage" monitor_disk_build 1
}

test_disk_io_under_load() {
    run_load_test "disk_load" stress_disk 2
}

# Network usage tests
test_network_usage_during_download() {
    run_benchmark "network_download" monitor_network_usage 1
}

# Helper functions
monitor_cpu_build() {
    start_resource_monitoring "cpu_build"
    lfs-wrapper build package cpu-intensive
    stop_resource_monitoring "cpu_build"
}

monitor_memory_build() {
    start_resource_monitoring "memory_build"
    lfs-wrapper build package memory-intensive
    stop_resource_monitoring "memory_build"
}

monitor_disk_build() {
    start_resource_monitoring "disk_build"
    lfs-wrapper build package io-intensive
    stop_resource_monitoring "disk_build"
}

monitor_network_usage() {
    start_resource_monitoring "network"
    lfs-wrapper download packages base-system
    stop_resource_monitoring "network"
}

stress_cpu() {
    lfs-wrapper build package --cpu-stress test-package
}

stress_memory() {
    lfs-wrapper build package --memory-stress test-package
}

stress_disk() {
    lfs-wrapper build package --io-stress test-package
}

# Resource limit tests
test_resource_limits() {
    # Test CPU limits
    assert_resource_usage "cpu_build" "cpu" 95
    
    # Test memory limits
    assert_resource_usage "memory_build" "memory" 90
    
    # Test disk usage limits
    assert_resource_usage "disk_build" "disk" 85
}

# Register test suite
register_resource_suite() {
    begin_test_suite "Resource Usage Tests"
    
    # CPU tests
    test_cpu_usage_during_build
    test_cpu_usage_under_load
    
    # Memory tests
    test_memory_usage_during_build
    test_memory_usage_under_load
    
    # Disk I/O tests
    test_disk_io_during_build
    test_disk_io_under_load
    
    # Network tests
    test_network_usage_during_download
    
    # Resource limits
    test_resource_limits
    
    end_test_suite
}

