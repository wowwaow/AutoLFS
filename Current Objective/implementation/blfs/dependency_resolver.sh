#!/bin/bash

# BLFS Dependency Resolution System
# Provides advanced dependency resolution with support for optional and conditional dependencies

set -euo pipefail

# Configuration
BLFS_ROOT="/var/lib/lfs-wrapper/blfs"
PACKAGE_DB="${BLFS_ROOT}/packages.db"
RESOLUTION_CACHE="${BLFS_ROOT}/resolution_cache"
FEATURE_CONFIG="${BLFS_ROOT}/features.conf"

# Initialize dependency resolver
init_resolver() {
    mkdir -p "${BLFS_ROOT}"
    mkdir -p "${RESOLUTION_CACHE}"
    
    # Initialize feature configuration if not exists
    [ -f "${FEATURE_CONFIG}" ] || {
        cat > "${FEATURE_CONFIG}" << EOF
# BLFS Feature Configuration
# Format: feature_name=enabled|disabled

# System features
x11=enabled
wayland=disabled
systemd=enabled
pulseaudio=enabled

# Optional components
qt=enabled
gtk=enabled
gnome=enabled
kde=disabled

# Development features
python=enabled
perl=enabled
ruby=disabled
java=disabled

# Multimedia support
gstreamer=enabled
ffmpeg=enabled
opengl=enabled
vulkan=enabled

# Security features
ssl=enabled
crypto=enabled
selinux=disabled
EOF
    }
}

# Feature management
is_feature_enabled() {
    local feature="$1"
    grep "^${feature}=enabled$" "${FEATURE_CONFIG}" >/dev/null 2>&1
}

get_enabled_features() {
    grep "=enabled$" "${FEATURE_CONFIG}" | cut -d'=' -f1
}

# Dependency resolution functions
resolve_dependencies() {
    local package="$1"
    local resolve_optional="${2:-false}"
    local cache_file="${RESOLUTION_CACHE}/${package}.deps"
    
    # Check cache first
    if [ -f "$cache_file" ] && [ "$(stat -c %Y "$cache_file")" -gt "$(stat -c %Y "${PACKAGE_DB}")" ]; then
        cat "$cache_file"
        return
    fi
    
    # Resolve and cache dependencies
    {
        echo "# Dependencies for $package"
        echo "# Generated: $(date)"
        echo "# Options: resolve_optional=$resolve_optional"
        echo
        
        # Get direct dependencies
        local query="SELECT depends_on, type, optional, condition FROM dependencies WHERE package = '${package}'"
        sqlite3 "${PACKAGE_DB}" "$query" | while IFS='|' read -r dep type opt cond; do
            if [ "$opt" = "0" ] || [ "$resolve_optional" = "true" ]; then
                if evaluate_condition "$cond"; then
                    echo "${dep}|${type}"
                    # Recursively resolve dependencies
                    resolve_dependencies "$dep" "$resolve_optional" | sed 's/^/  /'
                fi
            fi
        done
    } | tee "$cache_file"
}

evaluate_condition() {
    local condition="$1"
    
    # Empty condition always evaluates to true
    [ -z "$condition" ] && return 0
    
    # Evaluate feature-based conditions
    if [[ "$condition" =~ ^feature: ]]; then
        local feature=${condition#feature:}
        is_feature_enabled "$feature"
        return
    fi
    
    # Evaluate version-based conditions
    if [[ "$condition" =~ ^version: ]]; then
        local version_req=${condition#version:}
        check_version_requirement "$version_req"
        return
    fi
    
    # Evaluate package presence conditions
    if [[ "$condition" =~ ^requires: ]]; then
        local required_pkg=${condition#requires:}
        check_package_installed "$required_pkg"
        return
    fi
    
    # Default to true for unknown conditions
    return 0
}

check_version_requirement() {
    local requirement="$1"
    local package=$(echo "$requirement" | cut -d'>' -f1)
    local version=$(echo "$requirement" | cut -d'>' -f2)
    
    # Compare installed version with requirement
    local installed_version=$(sqlite3 "${PACKAGE_DB}" \
        "SELECT version FROM packages WHERE name = '${package}';")
    
    [ "$(version_compare "$installed_version" "$version")" -ge 0 ]
}

version_compare() {
    local v1="$1"
    local v2="$2"
    
    # Compare version strings
    printf '%s\n%s\n' "$v1" "$v2" | sort -V | head -n1 | grep -q "^$v1\$"
    [ $? -eq 0 ] && echo -1 || echo 1
}

check_package_installed() {
    local package="$1"
    
    sqlite3 "${PACKAGE_DB}" \
        "SELECT 1 FROM packages WHERE name = '${package}' AND status = 'installed';" | \
        grep -q 1
}

# Build-time vs Runtime dependency handling
get_build_dependencies() {
    local package="$1"
    
    sqlite3 "${PACKAGE_DB}" << EOF
SELECT depends_on
FROM dependencies
WHERE package = '${package}'
AND type = 'build'
AND (optional = 0 OR optional = $([ "$RESOLVE_OPTIONAL" = "true" ] && echo 1 || echo 0))
ORDER BY depends_on;
EOF
}

get_runtime_dependencies() {
    local package="$1"
    
    sqlite3 "${PACKAGE_DB}" << EOF
SELECT depends_on
FROM dependencies
WHERE package = '${package}'
AND type = 'runtime'
AND (optional = 0 OR optional = $([ "$RESOLVE_OPTIONAL" = "true" ] && echo 1 || echo 0))
ORDER BY depends_on;
EOF
}

# Feature-based dependency resolution
resolve_feature_dependencies() {
    local feature="$1"
    
    # Get all packages that depend on this feature
    sqlite3 "${PACKAGE_DB}" << EOF
SELECT DISTINCT p.name
FROM packages p
JOIN dependencies d ON d.package = p.name
WHERE d.condition LIKE 'feature:${feature}'
ORDER BY p.name;
EOF
}

# Optional dependency handling
get_optional_dependencies() {
    local package="$1"
    
    sqlite3 "${PACKAGE_DB}" << EOF
SELECT depends_on, condition
FROM dependencies
WHERE package = '${package}'
AND optional = 1
ORDER BY depends_on;
EOF
}

enable_optional_dependency() {
    local package="$1"
    local dependency="$2"
    
    sqlite3 "${PACKAGE_DB}" << EOF
UPDATE dependencies
SET optional = 0
WHERE package = '${package}'
AND depends_on = '${dependency}';
EOF
}

# Dependency resolution report
generate_dependency_report() {
    local package="$1"
    local report_file="${RESOLUTION_CACHE}/${package}_report.md"
    
    {
        echo "# Dependency Resolution Report for $package"
        echo "Generated: $(date)"
        echo
        
        echo "## Required Dependencies"
        resolve_dependencies "$package" false | sed 's/^/- /'
        echo
        
        echo "## Optional Dependencies"
        get_optional_dependencies "$package" | while IFS='|' read -r dep cond; do
            echo "- $dep (Condition: ${cond:-none})"
        done
        echo
        
        echo "## Feature Dependencies"
        get_enabled_features | while read -r feature; do
            echo "### Feature: $feature"
            resolve_feature_dependencies "$feature" | sed 's/^/- /'
            echo
        done
        
        echo "## Build vs Runtime Dependencies"
        echo "### Build-time Dependencies"
        get_build_dependencies "$package" | sed 's/^/- /'
        echo
        echo "### Runtime Dependencies"
        get_runtime_dependencies "$package" | sed 's/^/- /'
    } > "$report_file"
    
    echo "Report generated: $report_file"
}

# Main functionality
main() {
    local command="$1"
    shift
    
    case "$command" in
        init)
            init_resolver
            ;;
        resolve)
            resolve_dependencies "$@"
            ;;
        report)
            generate_dependency_report "$@"
            ;;
        check-feature)
            is_feature_enabled "$@"
            ;;
        list-features)
            get_enabled_features
            ;;
        enable-optional)
            enable_optional_dependency "$@"
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

