#!/bin/bash

# Error Handler
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Provide comprehensive error handling and recovery

# Error severity levels
declare -A ERROR_SEVERITY=(
    [ENV_001]="CRITICAL"
    [ENV_002]="CRITICAL"
    [ENV_003]="CRITICAL"
    [BUILD_001]="ERROR"
    [BUILD_002]="ERROR"
    [BUILD_003]="WARNING"
    [SYS_001]="CRITICAL"
    [SYS_002]="CRITICAL"
    [SYS_003]="ERROR"
)

# Error recovery types
declare -A ERROR_RECOVERY=(
    [ENV_001]="MANUAL"
    [ENV_002]="AUTOMATIC"
    [ENV_003]="MANUAL"
    [BUILD_001]="AUTOMATIC"
    [BUILD_002]="AUTOMATIC"
    [BUILD_003]="MANUAL"
    [SYS_001]="AUTOMATIC"
    [SYS_002]="AUTOMATIC"
    [SYS_003]="AUTOMATIC"
)

# Initialize error handler
init_error_handler() {
    trap 'handle_error $? $LINENO ${FUNCNAME[@]}' ERR
}

# Main error handler
handle_error() {
    local exit_code=$1
    local line_number=$2
    shift 2
    local function_stack=("$@")
    
    # Build error context
    local context=$(build_error_context "$exit_code" "$line_number" "${function_stack[@]}")
    
    # Determine error type
    local error_type=$(determine_error_type "$exit_code" "$context")
    
    # Log error
    log_error "$error_type" "$context"
    
    # Attempt recovery if possible
    if [ "${ERROR_RECOVERY[$error_type]}" = "AUTOMATIC" ]; then
        attempt_recovery "$error_type" "$context"
    else
        escalate_error "$error_type" "$context"
    fi
}

# Build error context
build_error_context() {
    local exit_code=$1
    local line_number=$2
    shift 2
    local function_stack=("$@")
    
    # Create context object
    local context=(
        "timestamp=$(date -u --iso-8601=seconds)"
        "exit_code=$exit_code"
        "line_number=$line_number"
        "function_stack=${function_stack[*]}"
        "pwd=$(pwd)"
        "script=${BASH_SOURCE[1]}"
    )
    
    # Add system state
    context+=(
        "disk_space=$(df -h . | awk 'NR==2 {print $4}')"
        "memory_free=$(free -h | awk '/^Mem:/ {print $4}')"
        "load_average=$(uptime | awk -F'average:' '{print $2}')"
    )
    
    echo "${context[*]}"
}

# Determine error type
determine_error_type() {
    local exit_code=$1
    local context=$2
    
    case $exit_code in
        1)  # General errors
            echo "BUILD_001"
            ;;
        2)  # Configuration errors
            echo "BUILD_002"
            ;;
        126|127) # Command not found/Permission denied
            echo "ENV_002"
            ;;
        137|143) # Process killed
            echo "SYS_003"
            ;;
        *)  # Unknown errors
            echo "BUILD_003"
            ;;
    esac
}

# Attempt error recovery
attempt_recovery() {
    local error_type=$1
    local context=$2
    
    info "Attempting recovery for error: $error_type"
    
    case $error_type in
        ENV_*)
            recover_environment "$context"
            ;;
        BUILD_*)
            recover_build "$context"
            ;;
        SYS_*)
            recover_system "$context"
            ;;
        *)
            warn "No recovery procedure for error type: $error_type"
            return 1
            ;;
    esac
}

# Environment recovery
recover_environment() {
    local context=$1
    
    info "Recovering environment..."
    
    # Verify directory structure
    check_directories || return 1
    
    # Validate permissions
    check_permissions || return 1
    
    # Verify tools
    check_required_tools || return 1
    
    info "Environment recovery completed"
    return 0
}

# Build recovery
recover_build() {
    local context=$1
    
    info "Recovering build state..."
    
    # Clean build directory
    clean_build_dir || return 1
    
    # Reset build state
    reset_build_state || return 1
    
    # Retry build step
    retry_build_step || return 1
    
    info "Build recovery completed"
    return 0
}

# System recovery
recover_system() {
    local context=$1
    
    info "Recovering system state..."
    
    # Check system resources
    check_resources || return 1
    
    # Clean temporary files
    clean_temp_files || return 1
    
    # Adjust resource limits
    adjust_limits || return 1
    
    info "System recovery completed"
    return 0
}

# Error escalation
escalate_error() {
    local error_type=$1
    local context=$2
    
    # Log escalation
    error "Escalating error: $error_type"
    log_error "$error_type" "$context"
    
    # Generate alert
    generate_alert "$error_type" "$context"
    
    # Exit if critical
    if [ "${ERROR_SEVERITY[$error_type]}" = "CRITICAL" ]; then
        exit 1
    fi
}

# Generate error alert
generate_alert() {
    local error_type=$1
    local context=$2
    
    # Create alert message
    local alert_message=$(create_alert_message "$error_type" "$context")
    
    # Log alert
    log_alert "$alert_message"
    
    # Send notification if critical
    if [ "${ERROR_SEVERITY[$error_type]}" = "CRITICAL" ]; then
        send_notification "$alert_message"
    fi
}

# Create alert message
create_alert_message() {
    local error_type=$1
    local context=$2
    
    cat << EOF
ALERT: $error_type (${ERROR_SEVERITY[$error_type]})
Timestamp: $(date -u --iso-8601=seconds)
Context: $context
Recovery: ${ERROR_RECOVERY[$error_type]}
EOF
}

# Error prevention checks
verify_environment() {
    # Check disk space
    check_disk_space || return 1
    
    # Check memory
    check_memory || return 1
    
    # Check required tools
    check_tools || return 1
    
    # Verify permissions
    check_permissions || return 1
    
    return 0
}

# Runtime monitoring
monitor_execution() {
    while true; do
        # Check resource usage
        check_resources
        
        # Monitor process health
        check_process_health
        
        # Check for timeouts
        check_timeouts
        
        sleep 30
    done
}

