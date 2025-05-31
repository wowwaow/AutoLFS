#!/bin/bash

# BLFS Configuration Management System
# Provides package configuration management and template handling

set -euo pipefail

# Configuration
BLFS_ROOT="/var/lib/lfs-wrapper/blfs"
CONFIG_ROOT="${BLFS_ROOT}/configs"
TEMPLATE_ROOT="${BLFS_ROOT}/templates"
PROFILE_ROOT="${BLFS_ROOT}/profiles"
PACKAGE_DB="${BLFS_ROOT}/packages.db"

# Initialize configuration manager
init_config_manager() {
    mkdir -p "${CONFIG_ROOT}"
    mkdir -p "${TEMPLATE_ROOT}"
    mkdir -p "${PROFILE_ROOT}"
    
    # Initialize configuration database
    sqlite3 "${PACKAGE_DB}" << 'EOF'
CREATE TABLE IF NOT EXISTS config_templates (
    name TEXT PRIMARY KEY,
    package TEXT,
    description TEXT,
    content TEXT,
    variables TEXT,
    FOREIGN KEY(package) REFERENCES packages(name)
);

CREATE TABLE IF NOT EXISTS config_profiles (
    name TEXT PRIMARY KEY,
    description TEXT,
    parent_profile TEXT,
    variables TEXT
);

CREATE TABLE IF NOT EXISTS profile_configs (
    profile TEXT,
    template TEXT,
    overrides TEXT,
    FOREIGN KEY(profile) REFERENCES config_profiles(name),
    FOREIGN KEY(template) REFERENCES config_templates(name)
);

CREATE TABLE IF NOT EXISTS feature_toggles (
    feature TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    affects TEXT
);
EOF
}

# Template management
create_config_template() {
    local name="$1"
    local package="$2"
    local description="$3"
    local template_file="$4"
    
    # Read template content and escape for SQL
    local content
    content=$(cat "$template_file" | sed "s/'/''/g")
    
    # Extract variables from template
    local variables
    variables=$(grep -o '\${[^}]*}' "$template_file" | sort -u | tr '\n' ',' | sed 's/,$//')
    
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO config_templates (name, package, description, content, variables)
VALUES ('${name}', '${package}', '${description}', '${content}', '${variables}');
EOF
}

apply_template() {
    local template="$1"
    local output_file="$2"
    shift 2
    local variables=("$@")
    
    # Get template content
    local content
    content=$(sqlite3 "${PACKAGE_DB}" \
        "SELECT content FROM config_templates WHERE name = '${template}';")
    
    # Apply variables
    for var in "${variables[@]}"; do
        local name="${var%%=*}"
        local value="${var#*=}"
        content=${content//\$\{$name\}/$value}
    done
    
    echo "$content" > "$output_file"
}

# Profile management
create_config_profile() {
    local name="$1"
    local description="$2"
    local parent="${3:-}"
    local variables="${4:-}"
    
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO config_profiles (name, description, parent_profile, variables)
VALUES ('${name}', '${description}', '${parent}', '${variables}');
EOF
}

add_template_to_profile() {
    local profile="$1"
    local template="$2"
    local overrides="${3:-}"
    
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO profile_configs (profile, template, overrides)
VALUES ('${profile}', '${template}', '${overrides}');
EOF
}

# Configuration validation
validate_config() {
    local template="$1"
    local config_file="$2"
    
    # Get required variables
    local required_vars
    required_vars=$(sqlite3 "${PACKAGE_DB}" \
        "SELECT variables FROM config_templates WHERE name = '${template}';")
    
    # Check all required variables are set
    local missing_vars=()
    IFS=',' read -ra VARS <<< "$required_vars"
    for var in "${VARS[@]}"; do
        if ! grep -q "\${$var}" "$config_file"; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "ERROR: Missing required variables: ${missing_vars[*]}"
        return 1
    fi
    
    return 0
}

# Configuration inheritance
resolve_inherited_config() {
    local profile="$1"
    local template="$2"
    
    # Get inheritance chain
    local inheritance_chain
    inheritance_chain=$(sqlite3 "${PACKAGE_DB}" << EOF
WITH RECURSIVE
    profile_chain(name, parent, level) AS (
        SELECT name, parent_profile, 0
        FROM config_profiles WHERE name = '${profile}'
        UNION ALL
        SELECT p.name, p.parent_profile, pc.level + 1
        FROM config_profiles p
        JOIN profile_chain pc ON p.name = pc.parent
    )
SELECT name FROM profile_chain ORDER BY level DESC;
EOF
)
    
    # Combine configurations
    local combined_config=""
    for p in $inheritance_chain; do
        local overrides
        overrides=$(sqlite3 "${PACKAGE_DB}" \
            "SELECT overrides FROM profile_configs WHERE profile = '${p}' AND template = '${template}';")
        if [ -n "$overrides" ]; then
            combined_config=$(echo -e "${overrides}\n${combined_config}")
        fi
    done
    
    echo "$combined_config"
}

# Feature toggles
set_feature_toggle() {
    local feature="$1"
    local enabled="$2"
    local affects="${3:-}"
    
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT OR REPLACE INTO feature_toggles (feature, enabled, affects)
VALUES ('${feature}', ${enabled}, '${affects}');
EOF
}

get_feature_state() {
    local feature="$1"
    
    sqlite3 "${PACKAGE_DB}" \
        "SELECT enabled FROM feature_toggles WHERE feature = '${feature}';"
}

get_affected_configs() {
    local feature="$1"
    
    sqlite3 "${PACKAGE_DB}" \
        "SELECT affects FROM feature_toggles WHERE feature = '${feature}';" | \
    tr ',' '\n'
}

# Configuration report generation
generate_config_report() {
    local profile="$1"
    local report_file="${PROFILE_ROOT}/${profile}_config.md"
    
    {
        echo "# Configuration Report for Profile: $profile"
        echo "Generated: $(date)"
        echo
        
        echo "## Profile Information"
        sqlite3 "${PACKAGE_DB}" << EOF
SELECT description, parent_profile, variables
FROM config_profiles WHERE name = '${profile}';
EOF
        echo
        
        echo "## Templates"
        sqlite3 "${PACKAGE_DB}" << EOF
SELECT t.name, t.description, t.variables
FROM config_templates t
JOIN profile_configs pc ON pc.template = t.name
WHERE pc.profile = '${profile}';
EOF
        echo
        
        echo "## Feature Toggles"
        sqlite3 "${PACKAGE_DB}" << EOF
SELECT feature, 
       CASE WHEN enabled = 1 THEN 'enabled' ELSE 'disabled' END,
       affects
FROM feature_toggles;
EOF
        
    } > "$report_file"
    
    echo "Configuration report generated: $report_file"
}

# Main functionality
main() {
    local command="$1"
    shift
    
    case "$command" in
        init)
            init_config_manager
            ;;
        create-template)
            create_config_template "$@"
            ;;
        apply-template)
            apply_template "$@"
            ;;
        create-profile)
            create_config_profile "$@"
            ;;
        add-to-profile)
            add_template_to_profile "$@"
            ;;
        validate)
            validate_config "$@"
            ;;
        resolve)
            resolve_inherited_config "$@"
            ;;
        set-feature)
            set_feature_toggle "$@"
            ;;
        report)
            generate_config_report "$@"
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

