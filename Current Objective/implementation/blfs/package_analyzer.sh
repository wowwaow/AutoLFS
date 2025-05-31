#!/bin/bash

# BLFS Package Analysis System
# Provides functionality for package analysis, dependency resolution, and build order optimization

set -euo pipefail

# Configuration
BLFS_ROOT="/var/lib/lfs-wrapper/blfs"
PACKAGE_DB="${BLFS_ROOT}/packages.db"
DEPENDENCY_GRAPH="${BLFS_ROOT}/dependency.dot"
BUILD_ORDER="${BLFS_ROOT}/build_order.txt"
PACKAGE_METADATA="${BLFS_ROOT}/metadata"

# Initialize package analysis system
init_analysis_system() {
    mkdir -p "${BLFS_ROOT}"
    mkdir -p "${PACKAGE_METADATA}"
    
    # Initialize SQLite database for package tracking
    sqlite3 "${PACKAGE_DB}" << 'EOF'
CREATE TABLE IF NOT EXISTS packages (
    name TEXT PRIMARY KEY,
    version TEXT,
    description TEXT,
    homepage TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS dependencies (
    package TEXT,
    depends_on TEXT,
    type TEXT,
    optional INTEGER,
    condition TEXT,
    FOREIGN KEY(package) REFERENCES packages(name),
    FOREIGN KEY(depends_on) REFERENCES packages(name)
);

CREATE TABLE IF NOT EXISTS features (
    package TEXT,
    feature TEXT,
    description TEXT,
    enabled INTEGER DEFAULT 0,
    FOREIGN KEY(package) REFERENCES packages(name)
);
EOF
}

# Package analysis functions
analyze_package() {
    local package="$1"
    local version="$2"
    
    echo "Analyzing package: ${package}-${version}"
    
    # Extract package metadata
    extract_package_metadata "$package" "$version"
    
    # Analyze dependencies
    analyze_package_dependencies "$package"
    
    # Check version compatibility
    check_version_compatibility "$package" "$version"
    
    # Update dependency graph
    update_dependency_graph "$package"
}

extract_package_metadata() {
    local package="$1"
    local version="$2"
    local metadata_file="${PACKAGE_METADATA}/${package}.xml"
    
    # Parse package XML and store in database
    sqlite3 "${PACKAGE_DB}" << EOF
INSERT OR REPLACE INTO packages (name, version, description, homepage)
VALUES (
    '${package}',
    '${version}',
    '$(xmllint --xpath "//description/text()" "$metadata_file")',
    '$(xmllint --xpath "//homepage/text()" "$metadata_file")'
);
EOF
}

analyze_package_dependencies() {
    local package="$1"
    local metadata_file="${PACKAGE_METADATA}/${package}.xml"
    
    # Clear existing dependencies
    sqlite3 "${PACKAGE_DB}" "DELETE FROM dependencies WHERE package = '${package}';"
    
    # Parse and store dependencies
    while IFS= read -r dep; do
        local dep_name=$(echo "$dep" | cut -d'|' -f1)
        local dep_type=$(echo "$dep" | cut -d'|' -f2)
        local dep_optional=$(echo "$dep" | cut -d'|' -f3)
        local dep_condition=$(echo "$dep" | cut -d'|' -f4)
        
        sqlite3 "${PACKAGE_DB}" << EOF
INSERT INTO dependencies (package, depends_on, type, optional, condition)
VALUES ('${package}', '${dep_name}', '${dep_type}', ${dep_optional}, '${dep_condition}');
EOF
    done < <(xmllint --xpath "//dependencies/dependency" "$metadata_file" | \
             awk -F'>' '{print $2}' | awk -F'<' '{print $1}')
}

check_version_compatibility() {
    local package="$1"
    local version="$2"
    
    # Check version compatibility with dependencies
    local incompatible_deps=$(sqlite3 "${PACKAGE_DB}" << EOF
SELECT d.depends_on, p.version
FROM dependencies d
JOIN packages p ON d.depends_on = p.name
WHERE d.package = '${package}'
AND NOT version_compatible('${version}', p.version);
EOF
)
    
    if [ -n "$incompatible_deps" ]; then
        echo "WARNING: Incompatible dependency versions found:"
        echo "$incompatible_deps"
        return 1
    fi
}

# Dependency graph management
update_dependency_graph() {
    local package="$1"
    
    # Generate GraphViz DOT file
    {
        echo "digraph dependencies {"
        echo "  node [shape=box];"
        
        # Add all package nodes
        sqlite3 "${PACKAGE_DB}" "SELECT name FROM packages;" | \
        while IFS= read -r pkg; do
            echo "  \"$pkg\";"
        done
        
        # Add dependency edges
        sqlite3 "${PACKAGE_DB}" \
        "SELECT package, depends_on, type, optional FROM dependencies;" | \
        while IFS='|' read -r pkg dep type opt; do
            local style="solid"
            [ "$opt" = "1" ] && style="dashed"
            echo "  \"$pkg\" -> \"$dep\" [style=$style,label=\"$type\"];"
        done
        
        echo "}"
    } > "${DEPENDENCY_GRAPH}"
}

# Build order optimization
generate_build_order() {
    # Implement topological sort with cycle detection
    {
        echo "strict digraph {"
        sqlite3 "${PACKAGE_DB}" \
        "SELECT package, depends_on FROM dependencies WHERE optional = 0;" | \
        while IFS='|' read -r pkg dep; do
            echo "  \"$pkg\" -> \"$dep\";"
        done
        echo "}"
    } | tsort > "${BUILD_ORDER}"
}

detect_circular_dependencies() {
    local cycles=$(mktemp)
    
    # Find cycles in dependency graph
    {
        echo "strict digraph {"
        sqlite3 "${PACKAGE_DB}" \
        "SELECT package, depends_on FROM dependencies WHERE optional = 0;" | \
        while IFS='|' read -r pkg dep; do
            echo "  \"$pkg\" -> \"$dep\";"
        done
        echo "}"
    } | graph-cycles > "$cycles"
    
    if [ -s "$cycles" ]; then
        echo "WARNING: Circular dependencies detected:"
        cat "$cycles"
        rm "$cycles"
        return 1
    fi
    
    rm "$cycles"
    return 0
}

# Package relationship mapping
generate_relationship_map() {
    local package="$1"
    local depth="${2:-1}"
    
    echo "Package relationships for $package (depth: $depth):"
    
    # Direct dependencies
    echo "Dependencies:"
    sqlite3 "${PACKAGE_DB}" << EOF
WITH RECURSIVE
    deps(pkg, dep, depth) AS (
        SELECT package, depends_on, 1
        FROM dependencies
        WHERE package = '${package}'
        UNION ALL
        SELECT d.package, d.depends_on, deps.depth + 1
        FROM dependencies d
        JOIN deps ON d.package = deps.dep
        WHERE deps.depth < ${depth}
    )
SELECT PRINTF('%s%s (%s)', REPLACE(SUBSTR('                ', 1, depth), ' ', '  '),
       dep, (SELECT type FROM dependencies WHERE package = deps.pkg AND depends_on = deps.dep))
FROM deps
ORDER BY depth, dep;
EOF
    
    # Reverse dependencies
    echo -e "\nRequired by:"
    sqlite3 "${PACKAGE_DB}" << EOF
WITH RECURSIVE
    rdeps(pkg, dep, depth) AS (
        SELECT package, depends_on, 1
        FROM dependencies
        WHERE depends_on = '${package}'
        UNION ALL
        SELECT d.package, d.depends_on, rdeps.depth + 1
        FROM dependencies d
        JOIN rdeps ON d.depends_on = rdeps.pkg
        WHERE rdeps.depth < ${depth}
    )
SELECT PRINTF('%s%s (%s)', REPLACE(SUBSTR('                ', 1, depth), ' ', '  '),
       pkg, (SELECT type FROM dependencies WHERE package = rdeps.pkg AND depends_on = rdeps.dep))
FROM rdeps
ORDER BY depth, pkg;
EOF
}

# Main functionality
main() {
    local command="$1"
    shift
    
    case "$command" in
        init)
            init_analysis_system
            ;;
        analyze)
            analyze_package "$@"
            ;;
        graph)
            update_dependency_graph "$@"
            ;;
        order)
            generate_build_order
            ;;
        check-cycles)
            detect_circular_dependencies
            ;;
        map)
            generate_relationship_map "$@"
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

