#!/bin/bash

# QA Test Environment Setup Script
# Creates necessary directories and sets permissions for QA framework

# Define directory structure
QA_ROOT="/mnt/host/WARP_CURRENT/Current Objective/implementation/qa"
TEST_DIRS=(
    "tests/system_tests"
    "tests/integration_tests"
    "tests/performance_tests"
    "tests/security_tests"
    "results"
    "logs"
    "reports"
)

# Create directories with proper permissions
for dir in "${TEST_DIRS[@]}"; do
    mkdir -p "${QA_ROOT}/${dir}"
    chmod 755 "${QA_ROOT}/${dir}"
done

# Initialize log files
touch "${QA_ROOT}/logs/integration.log"
touch "${QA_ROOT}/logs/security.log"
touch "${QA_ROOT}/logs/performance.log"

# Set proper permissions for log files
chmod 644 "${QA_ROOT}/logs/"*.log

# Create results directory structure
mkdir -p "${QA_ROOT}/results/integration"
mkdir -p "${QA_ROOT}/results/security"
mkdir -p "${QA_ROOT}/results/performance"

# Set permissions for results directories
chmod 755 "${QA_ROOT}/results/"*

echo "QA test environment setup complete"

