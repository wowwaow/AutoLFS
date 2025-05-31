#!/bin/bash

# Integration test helper functions

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common_utils.sh"

# Test HTTP endpoint
test_http_endpoint() {
    local endpoint="$1"
    local method="${2:-GET}"
    local data="$3"
    local expected_status="${4:-200}"
    
    log "INFO" "Testing HTTP endpoint: $endpoint (method: $method)"
    
    # Prepare curl command
    local curl_cmd=(curl -s -o /dev/null -w "%{http_code}" -X "$method")
    
    # Add data if provided
    if [[ -n "$data" ]]; then
        curl_cmd+=(-H "Content-Type: application/json" -d "$data")
    fi
    
    # Add endpoint
    curl_cmd+=("$endpoint")
    
    # Make request
    local status_code
    status_code=$("${curl_cmd[@]}")
    
    if [[ "$status_code" == "$expected_status" ]]; then
        log "INFO" "Endpoint test passed: $endpoint"
        return 0
    else
        log "ERROR" "Endpoint test failed: $endpoint (expected: $expected_status, got: $status_code)"
        return 1
    fi
}

# Test database connection
test_db_connection() {
    local host="$1"
    local port="$2"
    local user="$3"
    local password="$4"
    local database="$5"
    
    log "INFO" "Testing database connection: $host:$port/$database"
    
    # Check if required tools are available
    if ! check_command_exists "psql"; then
        log "ERROR" "PostgreSQL client not found. Cannot test database connection."
        return 1
    fi
    
    # Try to connect
    if ! PGPASSWORD="$password" psql -h "$host" -p "$port" -U "$user" -d "$database" -c "SELECT 1" >/dev/null 2>&1; then
        log "ERROR" "Database connection failed: $host:$port/$database"
        return 1
    fi
    
    log "INFO" "Database connection test passed"
    return 0
}

# Test message queue connection
test_mq_connection() {
    local host="$1"
    local port="$2"
    local vhost="$3"
    local user="$4"
    local password="$5"
    
    log "INFO" "Testing message queue connection: $host:$port$vhost"
    
    # Check if required tools are available
    if ! check_command_exists "rabbitmqctl"; then
        log "ERROR" "RabbitMQ client not found. Cannot test message queue connection."
        return 1
    fi
    
    # Try to connect
    if ! rabbitmqctl -n "$host:$port" -u "$user" -p "$password" list_queues >/dev/null 2>&1; then
        log "ERROR" "Message queue connection failed: $host:$port$vhost"
        return 1
    fi
    
    log "INFO" "Message queue connection test passed"
    return 0
}

# Test service dependency
test_service_dependency() {
    local service="$1"
    local dependency="$2"
    local timeout="${3:-30}"
    local retry_interval="${4:-2}"
    
    log "INFO" "Testing service dependency: $service -> $dependency"
    
    # Validate input
    if [[ -z "$service" || -z "$dependency" ]]; then
        log "ERROR" "Service and dependency must be specified"
        return 1
    }
    
    # Check if services exist
    for svc in "$service" "$dependency"; do
        if ! systemctl list-unit-files "$svc.service" >/dev/null 2>&1; then
            log "ERROR" "Service not found: $svc"
            return 1
        fi
    done
    
    # Stop the dependent service
    log "DEBUG" "Stopping service: $service"
    if ! systemctl stop "$service"; then
        log "ERROR" "Failed to stop service: $service"
        return 1
    fi
    
    # Stop the dependency
    log "DEBUG" "Stopping dependency: $dependency"
    if ! systemctl stop "$dependency"; then
        log "ERROR" "Failed to stop dependency: $dependency"
        systemctl start "$service"  # Attempt to restore service
        return 1
    fi
    
    # Start the dependency
    log "DEBUG" "Starting dependency: $dependency"
    if ! systemctl start "$dependency"; then
        log "ERROR" "Failed to start dependency: $dependency"
        systemctl start "$service"  # Attempt to restore service
        return 1
    fi
    
    # Wait for dependency to be ready
    local count=0
    while ! systemctl is-active "$dependency" >/dev/null 2>&1; do
        sleep "$retry_interval"
        ((count+=retry_interval))
        if ((count >= timeout)); then
            log "ERROR" "Timeout waiting for dependency to start: $dependency"
            systemctl start "$service"  # Attempt to restore service
            return 1
        fi
    done
    
    # Start the dependent service
    log "DEBUG" "Starting service: $service"
    if ! systemctl start "$service"; then
        log "ERROR" "Failed to start service: $service"
        return 1
    fi
    
    # Verify services are running
    for svc in "$dependency" "$service"; do
        if ! systemctl is-active "$svc" >/dev/null 2>&1; then
            log "ERROR" "Service failed to start: $svc"
            return 1
        fi
    done
    
    log "INFO" "Service dependency test passed: $service -> $dependency"
    return 0
}

# Test API integration points
test_api_integration() {
    local api_endpoint="$1"
    local method="${2:-GET}"
    local payload="$3"
    local expected_status="${4:-200}"
    local headers_file="${5:-}"
    local timeout="${6:-30}"
    
    log "INFO" "Testing API integration: $method $api_endpoint"
    
    # Prepare curl command
    local curl_cmd=(curl -s -X "$method" -w "%{http_code}")
    
    # Add headers if specified
    if [[ -n "$headers_file" && -f "$headers_file" ]]; then
        while IFS=: read -r key value; do
            curl_cmd+=(-H "$key:$value")
        done < "$headers_file"
    fi
    
    # Add payload for POST/PUT methods
    if [[ -n "$payload" && "$method" =~ ^(POST|PUT)$ ]]; then
        curl_cmd+=(-H "Content-Type: application/json" -d "$payload")
    fi
    
    # Add timeout
    curl_cmd+=(--max-time "$timeout")
    
    # Add endpoint
    curl_cmd+=("$api_endpoint")
    
    # Execute request
    local response
    response=$("${curl_cmd[@]}" 2>&1)
    local status_code=${response: -3}
    local response_body=${response:0:${#response}-3}
    
    # Verify status code
    if [[ "$status_code" != "$expected_status" ]]; then
        log "ERROR" "API request failed. Expected status $expected_status, got $status_code"
        log "DEBUG" "Response body: $response_body"
        return 1
    fi
    
    log "INFO" "API integration test passed: $method $api_endpoint"
    echo "$response_body"  # Return response body for additional verification
    return 0
}

# Verify service health
verify_service_health() {
    local service="$1"
    local health_endpoint="${2:-/health}"
    local expected_status="${3:-200}"
    local timeout="${4:-30}"
    
    log "INFO" "Verifying health for service: $service"
    
    # Get service URL from configuration or environment
    local service_url
    service_url=$(get_service_url "$service")
    if [[ $? -ne 0 ]]; then
        log "ERROR" "Failed to get URL for service: $service"
        return 1
    fi
    
    # Build health check URL
    local health_url="${service_url}${health_endpoint}"
    
    # Test health endpoint
    if ! test_api_integration "$health_url" "GET" "" "$expected_status" "" "$timeout"; then
        log "ERROR" "Health check failed for service: $service"
        return 1
    fi
    
    log "INFO" "Health check passed for service: $service"
    return 0
}

# Test data flow between components
test_data_flow() {
    local source_component="$1"
    local target_component="$2"
    local test_data="$3"
    local timeout="${4:-30}"
    local retry_interval="${5:-2}"
    
    log "INFO" "Testing data flow: $source_component -> $target_component"
    
    # Validate components are running
    for component in "$source_component" "$target_component"; do
        if ! verify_service_health "$component"; then
            log "ERROR" "Component not healthy: $component"
            return 1
        fi
    done
    
    # Send test data to source component
    local source_url
    source_url=$(get_service_url "$source_component")
    if ! test_api_integration "$source_url/data" "POST" "$test_data" "202"; then
        log "ERROR" "Failed to send test data to source component"
        return 1
    fi
    
    # Wait for data to propagate
    local target_url
    target_url=$(get_service_url "$target_component")
    local count=0
    while true; do
        # Check if data arrived at target
        if verify_test_data "$target_url" "$test_data"; then
            log "INFO" "Data flow test passed"
            return 0
        fi
        
        sleep "$retry_interval"
        ((count+=retry_interval))
        if ((count >= timeout)); then
            log "ERROR" "Timeout waiting for data propagation"
            return 1
        fi
    done
}

# Clean up test resources
cleanup_test_resources() {
    local test_id="$1"
    local resource_types="${2:-all}"  # all, containers, files, services
    
    log "INFO" "Cleaning up test resources for test ID: $test_id"
    
    local cleanup_status=0
    
    case "$resource_types" in
        *all*|*containers*)
            log "DEBUG" "Cleaning up containers"
            if ! cleanup_containers "$test_id"; then
                log "WARN" "Container cleanup failed"
                cleanup_status=1
            fi
            ;;
    esac
    
    case "$resource_types" in
        *all*|*files*)
            log "DEBUG" "Cleaning up test files"
            if ! cleanup_files "$test_id"; then
                log "WARN" "File cleanup failed"
                cleanup_status=1
            fi
            ;;
    esac
    
    case "$resource_types" in
        *all*|*services*)
            log "DEBUG" "Cleaning up services"
            if ! cleanup_services "$test_id"; then
                log "WARN" "Service cleanup failed"
                cleanup_status=1
            fi
            ;;
    esac
    
    if [[ $cleanup_status -eq 0 ]]; then
        log "INFO" "Resource cleanup completed successfully"
    else
        log "WARN" "Resource cleanup completed with warnings"
    fi
    
    return $cleanup_status
}

# Helper function to get service URL
get_service_url() {
    local service="$1"
    # Implementation depends on service discovery mechanism
    echo "http://localhost:8080"  # Placeholder
    return 0
}

# Helper function to verify test data
verify_test_data() {
    local target_url="$1"
    local test_data="$2"
    # Implementation depends on verification mechanism
    return 0
}

# Helper function to cleanup containers
cleanup_containers() {
    local test_id="$1"
    # Implementation depends on container runtime
    return 0
}

# Helper function to cleanup files
cleanup_files() {
    local test_id="$1"
    # Implementation depends on file locations
    return 0
}

# Helper function to cleanup services
cleanup_services() {
    local test_id="$1"
    # Implementation depends on service management system
    return 0
}

