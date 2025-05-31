#!/bin/bash

# LFS Host System Verification Script
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z

# Exit on any error
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${2:-$NC}$1${NC}"
}

# Check system architecture
check_architecture() {
    local arch=$(uname -m)
    log "Checking system architecture..."
    if [ "$arch" = "x86_64" ]; then
        log "Architecture: $arch ✓" "$GREEN"
        return 0
    else
        log "Architecture $arch is not supported. x86_64 required." "$RED"
        return 1
    fi
}

# Check available memory
check_memory() {
    local total_mem=$(free -g | awk '/^Mem:/{print $2}')
    log "Checking available memory..."
    if [ "$total_mem" -ge 4 ]; then
        log "Memory: ${total_mem}GB available ✓" "$GREEN"
        return 0
    else
        log "Insufficient memory. 4GB minimum required, found ${total_mem}GB." "$RED"
        return 1
    fi
}

# Check available disk space
check_disk_space() {
    local available_space=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    log "Checking available disk space..."
    if [ "$available_space" -ge 8 ]; then
        log "Disk space: ${available_space}GB available ✓" "$GREEN"
        return 0
    else
        log "Insufficient disk space. 8GB minimum required, found ${available_space}GB." "$RED"
        return 1
    fi
}

# Check tool version
check_tool_version() {
    local tool=$1
    local min_version=$2
    local version_cmd=$3
    local version

    log "Checking $tool version..."
    if ! command -v "$tool" >/dev/null 2>&1; then
        log "$tool not found!" "$RED"
        return 1
    fi

    version=$($version_cmd 2>&1 | head -n1 | awk '{print $NF}' | cut -d- -f1)
    if printf '%s\n' "$min_version" "$version" | sort -V -C; then
        log "$tool version $version ✓" "$GREEN"
        return 0
    else
        log "$tool version $version is too old. Minimum required: $min_version" "$RED"
        return 1
    fi
}

# Check core tools
check_core_tools() {
    local errors=0
    
    # Array of tool versions to check
    declare -A tools=(
        ["bash"]="3.2"
        ["binutils"]="2.13.1"
        ["gcc"]="5.1"
        ["grep"]="2.5.1"
        ["make"]="4.0"
        ["sed"]="4.1.5"
    )

    log "Checking core tool versions..."
    for tool in "${!tools[@]}"; do
        if ! check_tool_version "$tool" "${tools[$tool]}" "$tool --version"; then
            ((errors++))
        fi
    done

    return $errors
}

# Check file system permissions
check_fs_permissions() {
    log "Checking file system permissions..."
    local build_dir=${1:-"."}
    
    if [ -w "$build_dir" ]; then
        log "Build directory is writable ✓" "$GREEN"
        return 0
    else
        log "Build directory is not writable!" "$RED"
        return 1
    fi
}

# Check mount points
check_mount_points() {
    log "Checking required mount points..."
    local errors=0
    local required_mounts=("/dev" "/proc" "/sys" "/run")

    for mount in "${required_mounts[@]}"; do
        if mountpoint -q "$mount"; then
            log "$mount is mounted ✓" "$GREEN"
        else
            log "$mount is not mounted!" "$RED"
            ((errors++))
        fi
    done

    return $errors
}

# Main function
main() {
    local errors=0
    
    log "LFS Host System Verification" "$YELLOW"
    log "=============================" "$YELLOW"

    # Run all checks
    check_architecture || ((errors++))
    check_memory || ((errors++))
    check_disk_space || ((errors++))
    check_core_tools || ((errors++))
    check_fs_permissions || ((errors++))
    check_mount_points || ((errors++))

    # Summary
    echo
    log "Verification Summary" "$YELLOW"
    log "===================" "$YELLOW"
    if [ $errors -eq 0 ]; then
        log "All checks passed! System meets LFS requirements." "$GREEN"
        exit 0
    else
        log "Found $errors error(s). Please fix issues before proceeding." "$RED"
        exit 1
    fi
}

# Run main function
main

