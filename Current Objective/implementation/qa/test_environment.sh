#!/bin/bash

# Test Environment Automation
# Provides automated test environment setup and management

set -euo pipefail

# Configuration
QA_ROOT="/var/lib/lfs-wrapper/qa"
ENV_ROOT="${QA_ROOT}/environments"
ENV_DB="${QA_ROOT}/environment.db"
TEMPLATE_DIR="${QA_ROOT}/templates"
RESOURCE_DIR="${QA_ROOT}/resources"

# Initialize environment manager
init_environment_manager() {
    mkdir -p "${ENV_ROOT}"
    mkdir -p "${TEMPLATE_DIR}"
    mkdir -p "${RESOURCE_DIR}"
    
    # Initialize environment database
    sqlite3 "${ENV_DB}" << 'EOF'
CREATE TABLE IF NOT EXISTS environments (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    template TEXT,
    status TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used DATETIME
);

CREATE TABLE IF NOT EXISTS environment_resources (
    env_id INTEGER,
    resource TEXT,
    allocation TEXT,
    status TEXT,
    FOREIGN KEY(env_id) REFERENCES environments(id)
);

CREATE TABLE IF NOT EXISTS environment_state (
    env_id INTEGER,
    key TEXT,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(env_id) REFERENCES environments(id)
);
EOF
}

# Environment setup
create_environment() {
    local name="$1"
    local template="$2"
    local template_path="${TEMPLATE_DIR}/${template}.template"
    
    echo "Creating test environment: $name (template: $template)"
    
    # Create environment directory
    local env_path="${ENV_ROOT}/${name}"
    mkdir -p "$env_path"
    
    # Apply template
    if [ -f "$template_path" ]; then
        cp -r "$template_path"/* "$env_path/"
    fi
    
    # Record environment
    local env_id
    env_id=$(sqlite3 "${ENV_DB}" << EOF
INSERT INTO environments (name, template, status)
VALUES ('${name}', '${template}', 'creating');
SELECT last_insert_rowid();
EOF
)
    
    # Initialize environment
    if initialize_environment "$env_id" "$env_path"; then
        # Update status
        sqlite3 "${ENV_DB}" << EOF
UPDATE environments 
SET status = 'ready'
WHERE id = ${env_id};
EOF
        echo "Environment created successfully"
        return 0
    else
        echo "Environment creation failed"
        return 1
    fi
}

initialize_environment() {
    local env_id="$1"
    local env_path="$2"
    
    # Set up basic structure
    mkdir -p "${env_path}"/{bin,lib,etc,var}
    
    # Copy required resources
    cp -r "${RESOURCE_DIR}"/* "${env_path}/lib/"
    
    # Initialize configuration
    generate_environment_config "$env_id" > "${env_path}/etc/config.yaml"
    
    # Set up environment variables
    generate_environment_vars "$env_id" > "${env_path}/etc/env.sh"
    
    return 0
}

# State management
save_environment_state() {
    local env_id="$1"
    local key="$2"
    local value="$3"
    
    sqlite3 "${ENV_DB}" << EOF
INSERT OR REPLACE INTO environment_state (env_id, key, value)
VALUES (${env_id}, '${key}', '${value}');
EOF
}

restore_environment_state() {
    local env_id="$1"
    local key="$2"
    
    sqlite3 "${ENV_DB}" << EOF
SELECT value 
FROM environment_state 
WHERE env_id = ${env_id} 
AND key = '${key}';
EOF
}

# Resource allocation
allocate_resources() {
    local env_id="$1"
    local resource="$2"
    local amount="$3"
    
    echo "Allocating resources: $resource ($amount)"
    
    # Check resource availability
    if check_resource_availability "$resource" "$amount"; then
        # Record allocation
        sqlite3 "${ENV_DB}" << EOF
INSERT INTO environment_resources (env_id, resource, allocation, status)
VALUES (${env_id}, '${resource}', '${amount}', 'allocated');
EOF
        return 0
    else
        echo "Resource allocation failed: insufficient $resource"
        return 1
    fi
}

release_resources() {
    local env_id="$1"
    
    echo "Releasing resources for environment $env_id"
    
    sqlite3 "${ENV_DB}" << EOF
UPDATE environment_resources
SET status = 'released'
WHERE env_id = ${env_id};
EOF
}

# Resource management
check_resource_availability() {
    local resource="$1"
    local amount="$2"
    
    case "$resource" in
        memory)
            check_memory_availability "$amount"
            ;;
        disk)
            check_disk_availability "$amount"
            ;;
        cpu)
            check_cpu_availability "$amount"
            ;;
        *)
            echo "Unknown resource: $resource"
            return 1
            ;;
    esac
}

check_memory_availability() {
    local required="$1"
    local available
    available=$(free -m | awk '/^Mem:/ {print $7}')
    
    [ "$available" -ge "$required" ]
}

check_disk_availability() {
    local required="$1"
    local available
    available=$(df -m "${ENV_ROOT}" | awk 'NR==2 {print $4}')
    
    [ "$available" -ge "$required" ]
}

check_cpu_availability() {
    local required="$1"
    local available
    available=$(nproc)
    
    [ "$available" -ge "$required" ]
}

# Cleanup procedures
cleanup_environment() {
    local env_id="$1"
    local name
    name=$(get_environment_name "$env_id")
    local env_path="${ENV_ROOT}/${name}"
    
    echo "Cleaning up environment: $name"
    
    # Release resources
    release_resources "$env_id"
    
    # Remove environment directory
    if [ -d "$env_path" ]; then
        rm -rf "$env_path"
    fi
    
    # Update database
    sqlite3 "${ENV_DB}" << EOF
UPDATE environments 
SET status = 'cleaned'
WHERE id = ${env_id};
EOF
}

cleanup_old_environments() {
    local age_days="$1"
    
    echo "Cleaning up environments older than $age_days days"
    
    # Get old environments
    local old_envs
    old_envs=$(sqlite3 "${ENV_DB}" << EOF
SELECT id 
FROM environments 
WHERE created_at < datetime('now', '-${age_days} days')
AND status != 'cleaned';
EOF
)
    
    # Cleanup each environment
    for env_id in $old_envs; do
        cleanup_environment "$env_id"
    done
}

# Helper functions
get_environment_name() {
    local env_id="$1"
    
    sqlite3 "${ENV_DB}" << EOF
SELECT name 
FROM environments 
WHERE id = ${env_id};
EOF
}

generate_environment_config() {
    local env_id="$1"
    
    cat << EOF
# Environment Configuration
# Generated: $(date)
environment:
  id: ${env_id}
  created: $(date -Iseconds)
  template: $(get_environment_template "$env_id")
resources:
$(get_environment_resources "$env_id" | sed 's/^/  /')
EOF
}

get_environment_template() {
    local env_id="$1"
    
    sqlite3 "${ENV_DB}" << EOF
SELECT template 
FROM environments 
WHERE id = ${env_id};
EOF
}

get_environment_resources() {
    local env_id="$1"
    
    sqlite3 "${ENV_DB}" << EOF
SELECT resource || ': ' || allocation
FROM environment_resources
WHERE env_id = ${env_id}
AND status = 'allocated';
EOF
}

# Main functionality
main() {
    local command="$1"
    shift
    
    case "$command" in
        init)
            init_environment_manager
            ;;
        create)
            create_environment "$@"
            ;;
        state)
            save_environment_state "$@"
            ;;
        restore)
            restore_environment_state "$@"
            ;;
        allocate)
            allocate_resources "$@"
            ;;
        cleanup)
            cleanup_environment "$@"
            ;;
        clean-old)
            cleanup_old_environments "$@"
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

