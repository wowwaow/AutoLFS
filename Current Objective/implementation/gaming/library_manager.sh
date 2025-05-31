#!/bin/bash

# Gaming Library Manager
# Provides gaming library management and compatibility layer handling

set -euo pipefail

# Configuration
GAMING_ROOT="/var/lib/lfs-wrapper/gaming"
GAMING_DB="${GAMING_ROOT}/gaming.db"
LIBRARY_ROOT="${GAMING_ROOT}/libraries"
COMPAT_ROOT="${GAMING_ROOT}/compatibility"

# Initialize library manager
init_library_manager() {
    mkdir -p "${LIBRARY_ROOT}"
    mkdir -p "${COMPAT_ROOT}"
    
    # Initialize library database
    sqlite3 "${GAMING_DB}" << 'EOF'
CREATE TABLE IF NOT EXISTS gaming_libraries (
    name TEXT PRIMARY KEY,
    version TEXT,
    type TEXT,
    path TEXT,
    status TEXT,
    installed_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS library_dependencies (
    library TEXT,
    depends_on TEXT,
    version_req TEXT,
    optional INTEGER DEFAULT 0,
    FOREIGN KEY(library) REFERENCES gaming_libraries(name),
    FOREIGN KEY(depends_on) REFERENCES gaming_libraries(name)
);

CREATE TABLE IF NOT EXISTS compatibility_layers (
    name TEXT PRIMARY KEY,
    version TEXT,
    type TEXT,
    status TEXT,
    config TEXT
);

CREATE TABLE IF NOT EXISTS library_performance (
    library TEXT,
    metric TEXT,
    value REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(library) REFERENCES gaming_libraries(name)
);
EOF
}

# Library installation
install_library() {
    local name="$1"
    local version="$2"
    local type="$3"
    local path="${LIBRARY_ROOT}/${name}-${version}"
    
    echo "Installing gaming library: $name ($version)"
    
    # Create library directory
    mkdir -p "$path"
    
    # Install library
    if install_gaming_library "$name" "$version" "$path"; then
        # Record installation
        sqlite3 "${GAMING_DB}" << EOF
INSERT INTO gaming_libraries (name, version, type, path, status)
VALUES ('${name}', '${version}', '${type}', '${path}', 'installed');
EOF
        
        # Install dependencies
        install_library_dependencies "$name"
        
        # Configure library
        configure_library "$name" "$version"
        
        echo "Library installation completed"
        return 0
    else
        echo "Library installation failed"
        return 1
    fi
}

# Dependency resolution
resolve_dependencies() {
    local library="$1"
    local type="${2:-runtime}"
    
    echo "Resolving dependencies for: $library"
    
    # Get dependencies
    local deps
    deps=$(sqlite3 "${GAMING_DB}" << EOF
SELECT depends_on, version_req
FROM library_dependencies
WHERE library = '${library}'
AND (type = '${type}' OR type = 'all');
EOF
)
    
    # Install dependencies
    echo "$deps" | while IFS='|' read -r dep version_req; do
        if ! check_library_installed "$dep" "$version_req"; then
            echo "Installing dependency: $dep ($version_req)"
            install_library "$dep" "$version_req" "dependency"
        fi
    done
}

# Version management
manage_versions() {
    local action="$1"
    local library="$2"
    shift 2
    
    case "$action" in
        install)
            install_version "$library" "$@"
            ;;
        remove)
            remove_version "$library" "$@"
            ;;
        switch)
            switch_version "$library" "$@"
            ;;
        list)
            list_versions "$library"
            ;;
    esac
}

install_version() {
    local library="$1"
    local version="$2"
    
    echo "Installing version $version of $library"
    
    # Install specific version
    install_library "$library" "$version" "version"
    
    # Update alternatives if needed
    update_alternatives "$library" "$version"
}

# Compatibility layers
manage_compatibility() {
    local action="$1"
    local layer="$2"
    shift 2
    
    case "$action" in
        install)
            install_compatibility_layer "$layer" "$@"
            ;;
        configure)
            configure_compatibility_layer "$layer" "$@"
            ;;
        remove)
            remove_compatibility_layer "$layer"
            ;;
        status)
            check_compatibility_status "$layer"
            ;;
    esac
}

install_compatibility_layer() {
    local name="$1"
    local version="$2"
    local type="$3"
    local config="${4:-}"
    
    echo "Installing compatibility layer: $name ($version)"
    
    # Install layer
    if install_compat_layer "$name" "$version"; then
        # Record installation
        sqlite3 "${GAMING_DB}" << EOF
INSERT INTO compatibility_layers (name, version, type, status, config)
VALUES ('${name}', '${version}', '${type}', 'installed', '${config}');
EOF
        
        echo "Compatibility layer installation completed"
        return 0
    else
        echo "Compatibility layer installation failed"
        return 1
    fi
}

# Performance optimization
optimize_library() {
    local library="$1"
    local target="${2:-performance}"
    
    echo "Optimizing library: $library"
    
    # Get current performance metrics
    local metrics
    metrics=$(get_library_performance "$library")
    
    # Apply optimizations
    case "$target" in
        performance)
            optimize_for_performance "$library" "$metrics"
            ;;
        memory)
            optimize_for_memory "$library" "$metrics"
            ;;
        compatibility)
            optimize_for_compatibility "$library" "$metrics"
            ;;
    esac
    
    # Verify optimization
    verify_library_optimization "$library"
}

# Performance monitoring
monitor_library_performance() {
    local library="$1"
    local duration="${2:-60}"
    
    echo "Monitoring library performance: $library"
    
    # Start monitoring
    {
        local end_time=$((SECONDS + duration))
        while [ $SECONDS -lt $end_time ]; do
            # Collect metrics
            local cpu_usage=$(get_library_cpu_usage "$library")
            local memory_usage=$(get_library_memory_usage "$library")
            local load_time=$(get_library_load_time "$library")
            
            # Record metrics
            sqlite3 "${GAMING_DB}" << EOF
INSERT INTO library_performance (library, metric, value)
VALUES 
    ('${library}', 'cpu_usage', ${cpu_usage}),
    ('${library}', 'memory_usage', ${memory_usage}),
    ('${library}', 'load_time', ${load_time});
EOF
            
            sleep 1
        done
    } &
    
    # Wait for monitoring to complete
    wait
    
    # Generate performance report
    generate_library_report "$library"
}

# Helper functions
check_library_installed() {
    local library="$1"
    local version_req="$2"
    
    sqlite3 "${GAMING_DB}" << EOF
SELECT 1 FROM gaming_libraries 
WHERE name = '${library}' 
AND version ${version_req}
AND status = 'installed';
EOF
}

update_alternatives() {
    local library="$1"
    local version="$2"
    
    # Update system alternatives
    update-alternatives --install \
        "/usr/lib/games/${library}" \
        "${library}" \
        "${LIBRARY_ROOT}/${library}-${version}/lib${library}.so" \
        50
}

# Report generation
generate_library_report() {
    local library="$1"
    local report_file="${LIBRARY_ROOT}/reports/${library}_$(date +%Y%m%d_%H%M%S).md"
    
    mkdir -p "${LIBRARY_ROOT}/reports"
    
    {
        echo "# Gaming Library Report"
        echo "Library: $library"
        echo "Generated: $(date)"
        echo
        
        echo "## Performance Metrics"
        sqlite3 "${GAMING_DB}" << EOF
SELECT metric, round(avg(value), 2) as avg_value
FROM library_performance
WHERE library = '${library}'
AND timestamp >= datetime('now', '-1 hour')
GROUP BY metric;
EOF
        
        echo
        echo "## Dependencies"
        sqlite3 "${GAMING_DB}" << EOF
SELECT depends_on, version_req
FROM library_dependencies
WHERE library = '${library}';
EOF
        
        echo
        echo "## Compatibility Status"
        sqlite3 "${GAMING_DB}" << EOF
SELECT cl.name, cl.version, cl.status
FROM compatibility_layers cl
JOIN gaming_libraries gl ON gl.name = '${library}';
EOF
        
    } > "$report_file"
    
    echo "Library report generated: $report_file"
}

# Main functionality
main() {
    local command="$1"
    shift
    
    case "$command" in
        init)
            init_library_manager
            ;;
        install)
            install_library "$@"
            ;;
        deps)
            resolve_dependencies "$@"
            ;;
        version)
            manage_versions "$@"
            ;;
        compat)
            manage_compatibility "$@"
            ;;
        optimize)
            optimize_library "$@"
            ;;
        monitor)
            monitor_library_performance "$@"
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

