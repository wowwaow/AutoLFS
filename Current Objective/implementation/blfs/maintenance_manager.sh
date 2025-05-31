#!/bin/bash

# BLFS Maintenance Management System
# Provides package updates and system maintenance functionality

set -euo pipefail

# Configuration
BLFS_ROOT="/var/lib/lfs-wrapper/blfs"
PACKAGE_DB="${BLFS_ROOT}/packages.db"
UPDATE_LOG_DIR="${BLFS_ROOT}/update_logs"
BACKUP_DIR="${BLFS_ROOT}/backups"
ROLLBACK_DIR="${BLFS_ROOT}/rollbacks"

# Initialize maintenance system
init_maintenance_system() {
    mkdir -p "${UPDATE_LOG_DIR}"
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "${ROLLBACK_DIR}"
    
    # Initialize maintenance database
    sqlite3 "${PACKAGE_DB}" << 'EOF'
CREATE TABLE IF NOT EXISTS updates (
    package TEXT,
    old_version TEXT,
    new_version TEXT,
    status TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(package) REFERENCES packages(name)
);

CREATE TABLE IF NOT EXISTS maintenance_logs (
    operation TEXT,
    status TEXT,
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rollbacks (
    package TEXT,
    version TEXT,
    backup_path TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(package) REFERENCES packages(name)
);
EOF
}

# Package updates
check_for_updates() {
    local package="$1"
    
    echo "Checking for updates: $package"
    local current_version
    current_version=$(get_installed_version "$package")
    
    local latest_version
    latest_version=$(get_latest_version "$package")
    
    if [ "$current_version" != "$latest_version" ]; then
        echo "Update available: $current_version -> $latest_version"
        return 0
    else
        echo "Package is up to date: $current_version"
        return 1
    fi
}

update_package() {
    local package="$1"
    local log_file="${UPDATE_LOG_DIR}/${package}_update.log"
    
    echo "Updating package: $package"
    {
        echo "Package Update: $package"
        echo "Started: $(date)"
        echo
        
        # Get versions
        local old_version
        old_version=$(get_installed_version "$package")
        local new_version
        new_version=$(get_latest_version "$package")
        
        # Create backup
        echo "Creating backup..."
        local backup_path
        backup_path=$(create_package_backup "$package")
        
        # Perform update
        echo "Performing update..."
        if perform_package_update "$package" "$new_version"; then
            log_update "$package" "$old_version" "$new_version" "success"
            echo "Update successful"
            
            # Verify update
            if verify_update "$package" "$new_version"; then
                echo "Update verification passed"
            else
                echo "Update verification failed - rolling back"
                rollback_update "$package" "$backup_path"
                log_update "$package" "$old_version" "$new_version" "failed_verification"
                return 1
            fi
        else
            log_update "$package" "$old_version" "$new_version" "failed"
            echo "Update failed"
            return 1
        fi
        
        echo
        echo "Completed: $(date)"
    } | tee "$log_file"
}

# System maintenance
perform_system_maintenance() {
    local log_file="${UPDATE_LOG_DIR}/system_maintenance.log"
    
    echo "Performing system maintenance"
    {
        echo "System Maintenance"
        echo "Started: $(date)"
        echo
        
        # Clean package cache
        echo "Cleaning package cache..."
        if clean_package_cache; then
            log_maintenance "cache_clean" "success" "Package cache cleaned"
        else
            log_maintenance "cache_clean" "failed" "Failed to clean package cache"
        fi
        
        # Update package database
        echo "Updating package database..."
        if update_package_database; then
            log_maintenance "db_update" "success" "Package database updated"
        else
            log_maintenance "db_update" "failed" "Failed to update package database"
        fi
        
        # Verify system integrity
        echo "Verifying system integrity..."
        if verify_system_integrity; then
            log_maintenance "integrity_check" "success" "System integrity verified"
        else
            log_maintenance "integrity_check" "failed" "System integrity issues detected"
        fi
        
        # Clean old backups
        echo "Cleaning old backups..."
        if clean_old_backups; then
            log_maintenance "backup_clean" "success" "Old backups cleaned"
        else
            log_maintenance "backup_clean" "failed" "Failed to clean old backups"
        fi
        
        echo
        echo "Completed: $(date)"
    } | tee "$log_file"
}

# Health checks
run_health_checks() {
    local log_file="${UPDATE_LOG_DIR}/health_check.log"
    
    echo "Running health checks"
    {
        echo "System Health Check"
        echo "Started: $(date)"
        echo
        
        # Check disk usage
        echo "Checking disk usage..."
        if check_disk_usage; then
            log_maintenance "disk_check" "success" "Disk usage within limits"
        else
            log_maintenance "disk_check" "warning" "High disk usage detected"
        fi
        
        # Check package integrity
        echo "Checking package integrity..."
        if check_package_integrity; then
            log_maintenance "pkg_integrity" "success" "All packages intact"
        else
            log_maintenance "pkg_integrity" "warning" "Package integrity issues detected"
        fi
        
        # Check system configuration
        echo "Checking system configuration..."
        if check_system_config; then
            log_maintenance "config_check" "success" "Configuration valid"
        else
            log_maintenance "config_check" "warning" "Configuration issues detected"
        fi
        
        echo
        echo "Completed: $(date)"
    } | tee "$log_file"
}

# Update verification
verify_update() {
    local package="$1"
    local version="$2"
    
    # Verify package files
    echo "Verifying package files..."
    lfs-wrapper verify files "$package" || return 1
    
    # Check version
    echo "Checking installed version..."
    [ "$(get_installed_version "$package")" = "$version" ] || return 1
    
    # Verify dependencies
    echo "Verifying dependencies..."
    lfs-wrapper verify dependencies "$package" || return 1
    
    # Test functionality
    echo "Testing package functionality..."
    lfs-wrapper test functionality "$package" || return 1
    
    return 0
}

# Rollback handling
create_package_backup() {
    local package="$1"
    local backup_path="${BACKUP_DIR}/${package}_$(date +%Y%m%d_%H%M%S)"
    
    echo "Creating backup at: $backup_path"
    if lfs-wrapper backup create "$package" "$backup_path"; then
        # Record backup
        sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO rollbacks (package, version, backup_path)
VALUES (
    '${package}',
    '$(get_installed_version "$package")',
    '${backup_path}'
);
EOF
        echo "$backup_path"
        return 0
    else
        return 1
    fi
}

rollback_update() {
    local package="$1"
    local backup_path="$2"
    
    echo "Rolling back update for: $package"
    if lfs-wrapper backup restore "$package" "$backup_path"; then
        log_maintenance "rollback" "success" "Package rolled back: $package"
        return 0
    else
        log_maintenance "rollback" "failed" "Rollback failed: $package"
        return 1
    fi
}

# Helper functions
get_installed_version() {
    local package="$1"
    sqlite3 "${PACKAGE_DB}" \
        "SELECT version FROM packages WHERE name = '${package}';"
}

get_latest_version() {
    local package="$1"
    lfs-wrapper query latest-version "$package"
}

perform_package_update() {
    local package="$1"
    local version="$2"
    lfs-wrapper update package "$package" "$version"
}

clean_package_cache() {
    lfs-wrapper clean cache
}

update_package_database() {
    lfs-wrapper update database
}

verify_system_integrity() {
    lfs-wrapper verify system
}

clean_old_backups() {
    find "${BACKUP_DIR}" -type d -mtime +30 -exec rm -rf {} +
}

check_disk_usage() {
    local usage
    usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    [ "$usage" -lt 90 ]
}

check_package_integrity() {
    lfs-wrapper verify packages
}

check_system_config() {
    lfs-wrapper verify config
}

# Logging functions
log_update() {
    local package="$1"
    local old_version="$2"
    local new_version="$3"
    local status="$4"
    
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO updates (package, old_version, new_version, status)
VALUES ('${package}', '${old_version}', '${new_version}', '${status}');
EOF
}

log_maintenance() {
    local operation="$1"
    local status="$2"
    local details="$3"
    
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO maintenance_logs (operation, status, details)
VALUES ('${operation}', '${status}', '${details}');
EOF
}

# Report generation
generate_maintenance_report() {
    local report_file="${UPDATE_LOG_DIR}/maintenance_report_$(date +%Y%m%d).md"
    
    {
        echo "# System Maintenance Report"
        echo "Generated: $(date)"
        echo
        
        echo "## Recent Updates"
        sqlite3 "${PACKAGE_DB}" << EOF
SELECT package, old_version, new_version, status, timestamp
FROM updates
WHERE timestamp >= datetime('now', '-7 days')
ORDER BY timestamp DESC;
EOF
        echo
        
        echo "## Maintenance Activities"
        sqlite3 "${PACKAGE_DB}" << EOF
SELECT operation, status, details, timestamp
FROM maintenance_logs
WHERE timestamp >= datetime('now', '-7 days')
ORDER BY timestamp DESC;
EOF
        echo
        
        echo "## Available Rollbacks"
        sqlite3 "${PACKAGE_DB}" << EOF
SELECT package, version, backup_path, timestamp
FROM rollbacks
ORDER BY timestamp DESC
LIMIT 10;
EOF
        
    } > "$report_file"
    
    echo "Maintenance report generated: $report_file"
}

# Main functionality
main() {
    local command="$1"
    shift
    
    case "$command" in
        init)
            init_maintenance_system
            ;;
        check-updates)
            check_for_updates "$@"
            ;;
        update)
            update_package "$@"
            ;;
        maintain)
            perform_system_maintenance
            ;;
        health)
            run_health_checks
            ;;
        verify)
            verify_update "$@"
            ;;
        backup)
            create_package_backup "$@"
            ;;
        rollback)
            rollback_update "$@"
            ;;
        report)
            generate_maintenance_report
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

