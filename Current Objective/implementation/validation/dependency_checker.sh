#!/bin/bash
#
# Dependency Checking System
# Validates and manages build dependencies
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
DEPS_DIR="/var/run/lfs-wrapper/deps"
DEPS_CACHE="${DEPS_DIR}/deps.cache"
mkdir -p "$DEPS_DIR"

# Dependency Types
declare -r DEP_TYPE_BUILD="BUILD"
declare -r DEP_TYPE_RUNTIME="RUNTIME"
declare -r DEP_TYPE_TEST="TEST"

# Check package dependencies
check_package_deps() {
    local package="$1"
    local deps_file="$2"
    local status=0
    
    log_info "Checking dependencies for package: ${package}"
    
    while IFS=: read -r dep_type dep_name version; do
        # Skip comments and empty lines
        [[ "$dep_type" =~ ^[[:space:]]*# ]] && continue
        [ -z "$dep_type" ] && continue
        
        case "$dep_type" in
            "$DEP_TYPE_BUILD")
                check_build_dependency "$dep_name" "$version" || status=1
                ;;
            "$DEP_TYPE_RUNTIME")
                check_runtime_dependency "$dep_name" "$version" || status=1
                ;;
            "$DEP_TYPE_TEST")
                check_test_dependency "$dep_name" "$version" || status=1
                ;;
            *)
                log_error "Unknown dependency type: ${dep_type}"
                status=1
                ;;
        esac
    done < "$deps_file"
    
    return $status
}

# Check build dependencies
check_build_dependency() {
    local dep_name="$1"
    local required_version="$2"
    
    log_debug "Checking build dependency: ${dep_name} (${required_version})"
    
    # First check for binary
    if command -v "$dep_name" >/dev/null 2>&1; then
        local current_version
        current_version=$("$dep_name" --version 2>/dev/null | head -n1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+|[0-9]+\.[0-9]+' || echo "0.0")
        
        if version_compare "$current_version" "$required_version"; then
            return 0
        fi
        
        log_error "Dependency version mismatch: ${dep_name} (found: ${current_version}, required: ${required_version})"
        return 1
    fi
    
    log_error "Build dependency not found: ${dep_name}"
    return 1
}

# Check runtime dependencies
check_runtime_dependency() {
    local dep_name="$1"
    local required_version="$2"
    
    log_debug "Checking runtime dependency: ${dep_name} (${required_version})"
    
    # Check for library
    if ldconfig -p | grep -q "lib${dep_name}\.so"; then
        # Version check depends on the specific library
        case "$dep_name" in
            *) 
                # Default case: just check presence
                return 0
                ;;
        esac
    fi
    
    log_error "Runtime dependency not found: ${dep_name}"
    return 1
}

# Check test dependencies
check_test_dependency() {
    local dep_name="$1"
    local required_version="$2"
    
    log_debug "Checking test dependency: ${dep_name} (${required_version})"
    
    # Similar to build dependency check but for test tools
    if command -v "$dep_name" >/dev/null 2>&1; then
        return 0
    fi
    
    log_error "Test dependency not found: ${dep_name}"
    return 1
}

# Dependency resolution suggestion
suggest_dependency_resolution() {
    local dep_name="$1"
    local dep_type="$2"
    
    case "$dep_type" in
        "$DEP_TYPE_BUILD")
            echo "To install build dependency '${dep_name}':"
            echo "  For Ubuntu/Debian: sudo apt-get install ${dep_name}"
            echo "  For RedHat/CentOS: sudo yum install ${dep_name}"
            ;;
        "$DEP_TYPE_RUNTIME")
            echo "To install runtime dependency '${dep_name}':"
            echo "  For Ubuntu/Debian: sudo apt-get install lib${dep_name}-dev"
            echo "  For RedHat/CentOS: sudo yum install ${dep_name}-devel"
            ;;
        "$DEP_TYPE_TEST")
            echo "To install test dependency '${dep_name}':"
            echo "  For Ubuntu/Debian: sudo apt-get install ${dep_name}"
            echo "  For RedHat/CentOS: sudo yum install ${dep_name}"
            ;;
    esac
}

# Cache management
update_deps_cache() {
    local package="$1"
    local deps_file="$2"
    
    # Create cache entry
    {
        echo "PACKAGE=${package}"
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        cat "$deps_file"
    } > "${DEPS_CACHE}.${package}"
}

# Main entry point
main() {
    if [ "$#" -lt 2 ]; then
        log_error "Usage: $0 <package> <deps_file>"
        exit 1
    fi
    
    local package="$1"
    local deps_file="$2"
    
    if [ ! -f "$deps_file" ]; then
        log_error "Dependencies file not found: ${deps_file}"
        exit 1
    fi
    
    # Check dependencies
    if check_package_deps "$package" "$deps_file"; then
        log_info "All dependencies satisfied for package: ${package}"
        update_deps_cache "$package" "$deps_file"
        exit 0
    else
        log_error "Dependency check failed for package: ${package}"
        exit 1
    fi
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

