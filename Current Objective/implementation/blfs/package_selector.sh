#!/bin/bash

# BLFS Package Selection System
# Provides package set management and selection based on profiles and features

set -euo pipefail

# Configuration
BLFS_ROOT="/var/lib/lfs-wrapper/blfs"
PACKAGE_DB="${BLFS_ROOT}/packages.db"
PROFILE_DIR="${BLFS_ROOT}/profiles"
PACKAGE_SETS="${BLFS_ROOT}/package_sets"

# Initialize package selector
init_selector() {
    mkdir -p "${BLFS_ROOT}"
    mkdir -p "${PROFILE_DIR}"
    mkdir -p "${PACKAGE_SETS}"
    
    # Initialize package sets database
    sqlite3 "${PACKAGE_DB}" << 'EOF'
CREATE TABLE IF NOT EXISTS package_sets (
    name TEXT PRIMARY KEY,
    description TEXT,
    parent_set TEXT,
    required INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS set_packages (
    set_name TEXT,
    package TEXT,
    required INTEGER DEFAULT 0,
    FOREIGN KEY(set_name) REFERENCES package_sets(name),
    FOREIGN KEY(package) REFERENCES packages(name)
);

CREATE TABLE IF NOT EXISTS profiles (
    name TEXT PRIMARY KEY,
    description TEXT,
    base_profile TEXT,
    features TEXT
);

CREATE TABLE IF NOT EXISTS profile_sets (
    profile TEXT,
    set_name TEXT,
    FOREIGN KEY(profile) REFERENCES profiles(name),
    FOREIGN KEY(set_name) REFERENCES package_sets(name)
);
EOF

    # Create default package sets
    create_default_package_sets
}

# Package set management
create_default_package_sets() {
    # Define core package sets
    declare -A package_sets=(
        ["minimal"]="Basic system functionality"
        ["desktop"]="Basic desktop environment"
        ["development"]="Development tools and libraries"
        ["server"]="Server packages and tools"
        ["multimedia"]="Audio and video support"
        ["graphics"]="Graphics and image manipulation"
        ["gaming"]="Gaming support packages"
        ["security"]="Security tools and libraries"
    )
    
    for set_name in "${!package_sets[@]}"; do
        local description="${package_sets[$set_name]}"
        sqlite3 "${PACKAGE_DB}" << EOF
INSERT OR REPLACE INTO package_sets (name, description, required)
VALUES ('${set_name}', '${description}', 0);
EOF
    done
}

create_package_set() {
    local name="$1"
    local description="$2"
    local parent_set="${3:-}"
    local required="${4:-0}"
    
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO package_sets (name, description, parent_set, required)
VALUES ('${name}', '${description}', '${parent_set}', ${required});
EOF
}

add_package_to_set() {
    local set_name="$1"
    local package="$2"
    local required="${3:-0}"
    
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO set_packages (set_name, package, required)
VALUES ('${set_name}', '${package}', ${required});
EOF
}

# Profile management
create_profile() {
    local name="$1"
    local description="$2"
    local base_profile="${3:-}"
    local features="${4:-}"
    
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO profiles (name, description, base_profile, features)
VALUES ('${name}', '${description}', '${base_profile}', '${features}');
EOF
}

add_set_to_profile() {
    local profile="$1"
    local set_name="$2"
    
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO profile_sets (profile, set_name)
VALUES ('${profile}', '${set_name}');
EOF
}

# Package selection
select_packages_for_profile() {
    local profile="$1"
    local include_optional="${2:-false}"
    
    # Get all package sets for profile including inherited ones
    local sets=$(get_profile_sets "$profile")
    
    # Get all packages from selected sets
    for set_name in $sets; do
        if [ "$include_optional" = "true" ]; then
            sqlite3 "${PACKAGE_DB}" << EOF
SELECT package FROM set_packages WHERE set_name = '${set_name}';
EOF
        else
            sqlite3 "${PACKAGE_DB}" << EOF
SELECT package FROM set_packages 
WHERE set_name = '${set_name}' AND required = 1;
EOF
        fi
    done | sort -u
}

get_profile_sets() {
    local profile="$1"
    
    sqlite3 "${PACKAGE_DB}" << EOF
WITH RECURSIVE
    profile_tree(name, base_profile) AS (
        SELECT name, base_profile FROM profiles WHERE name = '${profile}'
        UNION ALL
        SELECT p.name, p.base_profile
        FROM profiles p
        JOIN profile_tree pt ON p.name = pt.base_profile
    )
SELECT DISTINCT ps.set_name
FROM profile_tree pt
JOIN profile_sets ps ON ps.profile = pt.name;
EOF
}

# Feature-based selection
select_packages_by_feature() {
    local feature="$1"
    
    sqlite3 "${PACKAGE_DB}" << EOF
SELECT DISTINCT p.name
FROM packages p
JOIN dependencies d ON d.package = p.name
WHERE d.condition LIKE 'feature:${feature}'
ORDER BY p.name;
EOF
}

# Package filtering
filter_packages() {
    local criteria="$1"
    local value="$2"
    
    case "$criteria" in
        feature)
            select_packages_by_feature "$value"
            ;;
        set)
            sqlite3 "${PACKAGE_DB}" \
                "SELECT package FROM set_packages WHERE set_name = '${value}';"
            ;;
        profile)
            select_packages_for_profile "$value"
            ;;
        status)
            sqlite3 "${PACKAGE_DB}" \
                "SELECT name FROM packages WHERE status = '${value}';"
            ;;
        *)
            echo "Unknown filter criteria: $criteria"
            return 1
            ;;
    esac
}

# Package groups
create_package_group() {
    local name="$1"
    local packages="$2"
    
    create_package_set "$name" "Package group: $name"
    
    for package in $packages; do
        add_package_to_set "$name" "$package"
    done
}

# Selection reporting
generate_selection_report() {
    local profile="$1"
    local report_file="${PROFILE_DIR}/${profile}_selection.md"
    
    {
        echo "# Package Selection Report for Profile: $profile"
        echo "Generated: $(date)"
        echo
        
        echo "## Profile Information"
        sqlite3 "${PACKAGE_DB}" << EOF
SELECT description, base_profile, features
FROM profiles WHERE name = '${profile}';
EOF
        echo
        
        echo "## Package Sets"
        get_profile_sets "$profile" | while read -r set_name; do
            echo "### Set: $set_name"
            sqlite3 "${PACKAGE_DB}" << EOF
SELECT description FROM package_sets WHERE name = '${set_name}';
EOF
            echo
            echo "Packages:"
            sqlite3 "${PACKAGE_DB}" << EOF
SELECT '- ' || package || 
       CASE WHEN required = 1 THEN ' (required)' ELSE '' END
FROM set_packages WHERE set_name = '${set_name}';
EOF
            echo
        done
        
        echo "## Feature-based Selections"
        sqlite3 "${PACKAGE_DB}" \
            "SELECT features FROM profiles WHERE name = '${profile}';" | \
        tr ',' '\n' | while read -r feature; do
            [ -n "$feature" ] || continue
            echo "### Feature: $feature"
            select_packages_by_feature "$feature" | sed 's/^/- /'
            echo
        done
        
    } > "$report_file"
    
    echo "Selection report generated: $report_file"
}

# Main functionality
main() {
    local command="$1"
    shift
    
    case "$command" in
        init)
            init_selector
            ;;
        create-set)
            create_package_set "$@"
            ;;
        add-to-set)
            add_package_to_set "$@"
            ;;
        create-profile)
            create_profile "$@"
            ;;
        add-to-profile)
            add_set_to_profile "$@"
            ;;
        select)
            select_packages_for_profile "$@"
            ;;
        filter)
            filter_packages "$@"
            ;;
        group)
            create_package_group "$@"
            ;;
        report)
            generate_selection_report "$@"
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

