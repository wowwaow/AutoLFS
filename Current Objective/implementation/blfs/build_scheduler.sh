#!/bin/bash
#
# BLFS Build Scheduler
# Manages and orchestrates BLFS package builds
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
BLFS_DIR="/var/run/lfs-wrapper/blfs"
SCHEDULER_DIR="${BLFS_DIR}/scheduler"
QUEUE_DIR="${SCHEDULER_DIR}/queue"
ACTIVE_DIR="${SCHEDULER_DIR}/active"
COMPLETED_DIR="${SCHEDULER_DIR}/completed"
FAILED_DIR="${SCHEDULER_DIR}/failed"

# Ensure required directories exist
for dir in "$SCHEDULER_DIR" "$QUEUE_DIR" "$ACTIVE_DIR" "$COMPLETED_DIR" "$FAILED_DIR"; do
    mkdir -p "$dir"
done

# Build status constants
declare -r STATUS_QUEUED="queued"
declare -r STATUS_ACTIVE="active"
declare -r STATUS_COMPLETED="completed"
declare -r STATUS_FAILED="failed"
declare -r STATUS_BLOCKED="blocked"

# Resource allocation settings
declare -r MAX_PARALLEL_BUILDS=4
declare -r MAX_RAM_PER_BUILD=2048  # MB
declare -r MAX_CPU_PER_BUILD=2     # CPU cores

# Queue package for building
queue_package() {
    local package="$1"
    local priority="${2:-50}"  # Default priority: 50 (range: 0-99)
    local queue_file="${QUEUE_DIR}/${priority}_${package}"
    
    log_info "Queueing package: ${package} (priority: ${priority})"
    
    # Create queue entry
    {
        echo "PACKAGE=${package}"
        echo "PRIORITY=${priority}"
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        echo "STATUS=${STATUS_QUEUED}"
    } > "$queue_file"
    
    # Update build order
    update_build_order
}

# Update build order
update_build_order() {
    local order_file="${SCHEDULER_DIR}/build_order"
    local -A dependencies
    local -A build_levels
    
    log_info "Updating build order..."
    
    # Collect dependencies for all queued packages
    for queue_file in "$QUEUE_DIR"/*; do
        [ -f "$queue_file" ] || continue
        local package
        package=$(grep "^PACKAGE=" "$queue_file" | cut -d'=' -f2)
        dependencies["$package"]=$(get_package_dependencies "$package")
    done
    
    # Perform topological sort
    {
        echo "digraph G {"
        for package in "${!dependencies[@]}"; do
            for dep in ${dependencies[$package]}; do
                echo "\"$package\" -> \"$dep\";"
            done
        done
        echo "}"
    } | tsort > "$order_file"
    
    # Calculate build levels
    local level=0
    while IFS= read -r package; do
        local max_dep_level=-1
        for dep in ${dependencies[$package]}; do
            if [ -n "${build_levels[$dep]:-}" ]; then
                max_dep_level=$(( max_dep_level > build_levels[$dep] ? max_dep_level : build_levels[$dep] ))
            fi
        done
        build_levels["$package"]=$((max_dep_level + 1))
    done < "$order_file"
    
    # Write build levels file
    {
        echo "# Build levels"
        for package in "${!build_levels[@]}"; do
            echo "${build_levels[$package]} ${package}"
        done
    } | sort -n > "${order_file}.levels"
}

# Get package dependencies
get_package_dependencies() {
    local package="$1"
    local deps_file="${BLFS_DIR}/metadata/${package}/dependencies.conf"
    
    if [ -f "$deps_file" ]; then
        grep "^required:" "$deps_file" | cut -d':' -f2
    fi
}

# Start build process
start_build() {
    local package="$1"
    local build_dir="${ACTIVE_DIR}/${package}"
    
    log_info "Starting build: ${package}"
    
    # Create build directory
    mkdir -p "$build_dir"
    
    # Update status
    update_build_status "$package" "$STATUS_ACTIVE"
    
    # Allocate resources
    allocate_resources "$package"
    
    # Start build process
    if ! build_package "$package"; then
        log_error "Build failed: ${package}"
        move_to_failed "$package"
        release_resources "$package"
        return 1
    fi
    
    # Move to completed
    move_to_completed "$package"
    
    # Release resources
    release_resources "$package"
    
    return 0
}

# Allocate resources for build
allocate_resources() {
    local package="$1"
    local resource_file="${ACTIVE_DIR}/${package}/resources"
    
    # Calculate available resources
    local available_ram available_cpu
    available_ram=$(get_available_ram)
    available_cpu=$(get_available_cpu)
    
    # Allocate resources
    local ram_allocation cpu_allocation
    ram_allocation=$((available_ram < MAX_RAM_PER_BUILD ? available_ram : MAX_RAM_PER_BUILD))
    cpu_allocation=$((available_cpu < MAX_CPU_PER_BUILD ? available_cpu : MAX_CPU_PER_BUILD))
    
    # Record allocation
    {
        echo "RAM=${ram_allocation}"
        echo "CPU=${cpu_allocation}"
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
    } > "$resource_file"
    
    # Set resource limits
    ulimit -v $((ram_allocation * 1024))
    # CPU limits handled through taskset in build process
}

# Release allocated resources
release_resources() {
    local package="$1"
    local resource_file="${ACTIVE_DIR}/${package}/resources"
    
    [ -f "$resource_file" ] && rm -f "$resource_file"
}

# Check available system resources
get_available_ram() {
    local total_allocated=0
    
    # Sum currently allocated RAM
    for resource_file in "$ACTIVE_DIR"/*/resources; do
        [ -f "$resource_file" ] || continue
        total_allocated=$((total_allocated + $(grep "^RAM=" "$resource_file" | cut -d'=' -f2)))
    done
    
    # Get total system RAM
    local total_ram
    total_ram=$(($(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024))
    
    # Return available RAM
    echo $((total_ram - total_allocated))
}

# Get available CPU cores
get_available_cpu() {
    local total_allocated=0
    
    # Sum currently allocated CPU cores
    for resource_file in "$ACTIVE_DIR"/*/resources; do
        [ -f "$resource_file" ] || continue
        total_allocated=$((total_allocated + $(grep "^CPU=" "$resource_file" | cut -d'=' -f2)))
    done
    
    # Get total CPU cores
    local total_cpu
    total_cpu=$(nproc)
    
    # Return available cores
    echo $((total_cpu - total_allocated))
}

# Update build status
update_build_status() {
    local package="$1"
    local status="$2"
    local status_file
    
    case "$status" in
        "$STATUS_QUEUED")
            status_file="${QUEUE_DIR}/${package}"
            ;;
        "$STATUS_ACTIVE")
            status_file="${ACTIVE_DIR}/${package}/status"
            ;;
        "$STATUS_COMPLETED")
            status_file="${COMPLETED_DIR}/${package}"
            ;;
        "$STATUS_FAILED")
            status_file="${FAILED_DIR}/${package}"
            ;;
        *)
            log_error "Invalid status: ${status}"
            return 1
            ;;
    esac
    
    # Update status file
    {
        echo "PACKAGE=${package}"
        echo "STATUS=${status}"
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
    } > "$status_file"
}

# Move package to completed
move_to_completed() {
    local package="$1"
    mv "${ACTIVE_DIR:?}/${package}" "${COMPLETED_DIR}/"
    update_build_status "$package" "$STATUS_COMPLETED"
}

# Move package to failed
move_to_failed() {
    local package="$1"
    mv "${ACTIVE_DIR:?}/${package}" "${FAILED_DIR}/"
    update_build_status "$package" "$STATUS_FAILED"
}

# Get next package to build
get_next_package() {
    local build_order="${SCHEDULER_DIR}/build_order"
    local next_package=""
    
    # Check build order file exists
    if [ ! -f "$build_order" ]; then
        update_build_order
    fi
    
    # Find next buildable package
    while IFS= read -r package; do
        # Skip if not queued
        [ -f "${QUEUE_DIR}/${package}" ] || continue
        
        # Check if dependencies are satisfied
        if check_dependencies "$package"; then
            next_package="$package"
            break
        fi
    done < "$build_order"
    
    echo "$next_package"
}

# Check if dependencies are satisfied
check_dependencies() {
    local package="$1"
    local status=0
    
    for dep in $(get_package_dependencies "$package"); do
        if [ ! -f "${COMPLETED_DIR}/${dep}" ]; then
            status=1
            break
        fi
    done
    
    return $status
}

# Main scheduler loop
run_scheduler() {
    local stop_file="${SCHEDULER_DIR}/stop"
    
    log_info "Starting build scheduler..."
    
    while [ ! -f "$stop_file" ]; do
        # Count active builds
        local active_builds
        active_builds=$(find "$ACTIVE_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)
        
        # Start new builds if capacity available
        while [ "$active_builds" -lt "$MAX_PARALLEL_BUILDS" ]; do
            local next_package
            next_package=$(get_next_package)
            
            if [ -z "$next_package" ]; then
                break
            fi
            
            start_build "$next_package" &
            active_builds=$((active_builds + 1))
        done
        
        sleep 5
    done
    
    log_info "Scheduler stopped"
}

# Main entry point
main() {
    if [ "$#" -lt 2 ]; then
        log_error "Usage: $0 <command> [args...]"
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        queue)
            if [ "$#" -lt 1 ]; then
                log_error "Usage: $0 queue <package> [priority]"
                exit 1
            fi
            queue_package "$@"
            ;;
        start)
            run_scheduler
            ;;
        stop)
            touch "${SCHEDULER_DIR}/stop"
            ;;
        status)
            if [ "$#" -lt 1 ]; then
                log_error "Usage: $0 status <package>"
                exit 1
            fi
            get_build_status "$1"
            ;;
        list)
            list_builds "${1:-all}"
            ;;
        *)
            log_error "Unknown command: ${command}"
            exit 1
            ;;
    esac
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

