#!/bin/bash
#
# BLFS Script Integration Layer
# Manages BLFS package building and installation
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
BLFS_DIR="/var/run/lfs-wrapper/blfs"
PACKAGE_DIR="${BLFS_DIR}/packages"
CONFIG_DIR="${BLFS_DIR}/config"
BUILD_DIR="${BLFS_DIR}/build"
TEST_DIR="${BLFS_DIR}/test"
LOG_DIR="${BLFS_DIR}/logs"

# Ensure required directories exist
for dir in "$PACKAGE_DIR" "$CONFIG_DIR" "$BUILD_DIR" "$TEST_DIR" "$LOG_DIR"; do
    mkdir -p "$dir"
done

# Package Categories
declare -A PACKAGE_CATEGORIES=(
    ["base"]="Essential system packages"
    ["libs"]="Libraries"
    ["net"]="Networking packages"
    ["dev"]="Development tools"
    ["x11"]="X Window System"
    ["gtk"]="GTK+ and GNOME"
    ["kde"]="KDE Plasma and frameworks"
    ["xfce"]="Xfce Desktop"
    ["media"]="Multimedia packages"
    ["office"]="Office applications"
    ["security"]="Security tools"
    ["utils"]="System utilities"
)

# Package state constants
declare -r PKG_STATE_PENDING="pending"
declare -r PKG_STATE_BUILDING="building"
declare -r PKG_STATE_TESTING="testing"
declare -r PKG_STATE_INSTALLED="installed"
declare -r PKG_STATE_FAILED="failed"

# Dependency resolution
resolve_dependencies() {
    local package="$1"
    local -a dep_chain=()
    local status=0
    
    log_info "Resolving dependencies for package: ${package}"
    
    # Read package dependencies
    local deps_file="${PACKAGE_DIR}/${package}/dependencies.conf"
    if [ ! -f "$deps_file" ]; then
        log_error "Dependencies file not found: ${deps_file}"
        return 1
    fi
    
    # Build dependency chain
    while IFS=':' read -r dep_type dep_name version_req; do
        # Skip comments and empty lines
        [[ "$dep_type" =~ ^[[:space:]]*# ]] && continue
        [ -z "$dep_type" ] && continue
        
        case "$dep_type" in
            "required")
                if ! check_dependency "$dep_name" "$version_req"; then
                    install_dependency "$dep_name" "$version_req" || status=1
                fi
                dep_chain+=("$dep_name")
                ;;
            "optional")
                if should_install_optional "$dep_name"; then
                    if ! check_dependency "$dep_name" "$version_req"; then
                        install_dependency "$dep_name" "$version_req" || true
                    fi
                fi
                ;;
            "runtime")
                # Note runtime dependency for post-install validation
                echo "$dep_name:$version_req" >> "${BUILD_DIR}/${package}.runtime_deps"
                ;;
            *)
                log_warn "Unknown dependency type: ${dep_type}"
                ;;
        esac
    done < "$deps_file"
    
    # Write dependency chain
    printf "%s\n" "${dep_chain[@]}" > "${BUILD_DIR}/${package}.dep_chain"
    
    return $status
}

# Check if dependency is satisfied
check_dependency() {
    local package="$1"
    local version_req="$2"
    local installed_version
    
    if ! installed_version=$(get_installed_version "$package"); then
        return 1
    fi
    
    if ! version_satisfies "$installed_version" "$version_req"; then
        log_error "Package ${package} version ${installed_version} does not satisfy requirement: ${version_req}"
        return 1
    fi
    
    return 0
}

# Install dependency
install_dependency() {
    local package="$1"
    local version_req="$2"
    
    log_info "Installing dependency: ${package} (${version_req})"
    
    # Recursively handle dependency's own dependencies
    if ! resolve_dependencies "$package"; then
        log_error "Failed to resolve dependencies for ${package}"
        return 1
    fi
    
    # Build and install the dependency
    if ! build_package "$package"; then
        log_error "Failed to build dependency: ${package}"
        return 1
    fi
    
    return 0
}

# Optimize build order
optimize_build_order() {
    local package="$1"
    local dep_chain_file="${BUILD_DIR}/${package}.dep_chain"
    local order_file="${BUILD_DIR}/${package}.build_order"
    
    log_info "Optimizing build order for: ${package}"
    
    # Create directed acyclic graph of dependencies
    local -A dep_graph
    while IFS= read -r dep; do
        local dep_deps_file="${BUILD_DIR}/${dep}.dep_chain"
        if [ -f "$dep_deps_file" ]; then
            dep_graph["$dep"]=$(cat "$dep_deps_file")
        fi
    done < "$dep_chain_file"
    
    # Perform topological sort
    {
        echo "digraph G {"
        for pkg in "${!dep_graph[@]}"; do
            for dep in ${dep_graph[$pkg]}; do
                echo "\"$pkg\" -> \"$dep\";"
            done
        done
        echo "}"
    } | tsort > "$order_file"
    
    # Add parallel build markers
    detect_parallel_builds "$order_file"
}

# Detect which packages can be built in parallel
detect_parallel_builds() {
    local order_file="$1"
    local parallel_file="${order_file}.parallel"
    
    # Create groups of packages that can be built simultaneously
    local current_level=0
    local -A pkg_levels
    
    while IFS= read -r pkg; do
        local max_dep_level=-1
        local deps_file="${BUILD_DIR}/${pkg}.dep_chain"
        
        if [ -f "$deps_file" ]; then
            while IFS= read -r dep; do
                if [ -n "${pkg_levels[$dep]:-}" ]; then
                    max_dep_level=$(( max_dep_level > pkg_levels[$dep] ? max_dep_level : pkg_levels[$dep] ))
                fi
            done < "$deps_file"
        fi
        
        pkg_levels["$pkg"]=$((max_dep_level + 1))
    done < "$order_file"
    
    # Write parallel build groups
    local max_level
    max_level=$(printf "%d\n" "${pkg_levels[@]}" | sort -n | tail -n1)
    
    {
        echo "# Parallel build groups"
        for level in $(seq 0 "$max_level"); do
            echo "Level ${level}:"
            for pkg in "${!pkg_levels[@]}"; do
                if [ "${pkg_levels[$pkg]}" -eq "$level" ]; then
                    echo "  ${pkg}"
                fi
            done
        done
    } > "$parallel_file"
}

# Build package
build_package() {
    local package="$1"
    local status=0
    
    log_info "Building package: ${package}"
    
    # Update package state
    update_package_state "$package" "$PKG_STATE_BUILDING"
    
    # Create build directory
    local build_dir="${BUILD_DIR}/${package}"
    mkdir -p "$build_dir"
    
    # Execute pre-build hooks
    run_hooks "pre-build" "$package" || status=1
    
    # Extract source
    if ! extract_source "$package" "$build_dir"; then
        log_error "Failed to extract source for ${package}"
        update_package_state "$package" "$PKG_STATE_FAILED"
        return 1
    fi
    
    # Apply patches if any
    apply_patches "$package" "$build_dir" || status=1
    
    # Configure package
    if ! configure_package "$package" "$build_dir"; then
        log_error "Failed to configure ${package}"
        update_package_state "$package" "$PKG_STATE_FAILED"
        return 1
    fi
    
    # Build package
    if ! make_package "$package" "$build_dir"; then
        log_error "Failed to build ${package}"
        update_package_state "$package" "$PKG_STATE_FAILED"
        return 1
    fi
    
    # Run tests if enabled
    if should_run_tests "$package"; then
        update_package_state "$package" "$PKG_STATE_TESTING"
        run_package_tests "$package" "$build_dir" || status=1
    fi
    
    # Install package
    if ! install_package "$package" "$build_dir"; then
        log_error "Failed to install ${package}"
        update_package_state "$package" "$PKG_STATE_FAILED"
        return 1
    fi
    
    # Execute post-install hooks
    run_hooks "post-install" "$package" || status=1
    
    # Validate installation
    if ! validate_installation "$package"; then
        log_error "Installation validation failed for ${package}"
        update_package_state "$package" "$PKG_STATE_FAILED"
        return 1
    fi
    
    # Update package state
    update_package_state "$package" "$PKG_STATE_INSTALLED"
    
    return $status
}

# Configuration management
configure_package() {
    local package="$1"
    local build_dir="$2"
    local status=0
    
    log_info "Configuring package: ${package}"
    
    # Load package configuration
    local config_file="${CONFIG_DIR}/${package}/config"
    if [ -f "$config_file" ]; then
        source "$config_file"
    fi
    
    # Generate configure options
    local configure_opts
    configure_opts=$(generate_configure_options "$package")
    
    # Run configure script
    cd "$build_dir" || return 1
    if [ -x ./configure ]; then
        ./configure $configure_opts || status=1
    elif [ -f ./meson.build ]; then
        meson setup build $configure_opts || status=1
    elif [ -f ./CMakeLists.txt ]; then
        cmake -B build $configure_opts . || status=1
    fi
    
    return $status
}

# Installation validation
validate_installation() {
    local package="$1"
    local status=0
    
    log_info "Validating installation: ${package}"
    
    # Check installed files
    if ! validate_installed_files "$package"; then
        status=1
    fi
    
    # Check runtime dependencies
    if ! validate_runtime_dependencies "$package"; then
        status=1
    fi
    
    # Run package-specific validation
    local validate_script="${PACKAGE_DIR}/${package}/validate.sh"
    if [ -x "$validate_script" ]; then
        if ! "$validate_script"; then
            log_error "Package-specific validation failed"
            status=1
        fi
    fi
    
    return $status
}

# Post-installation testing
run_package_tests() {
    local package="$1"
    local build_dir="$2"
    local status=0
    
    log_info "Running tests for package: ${package}"
    
    # Create test directory
    local test_dir="${TEST_DIR}/${package}"
    mkdir -p "$test_dir"
    
    # Run standard test suite
    cd "$build_dir" || return 1
    if [ -f Makefile ] || [ -f GNUmakefile ]; then
        make check || status=1
        make test || status=1
    elif [ -d build ]; then
        cd build || return 1
        if [ -f build.ninja ]; then
            ninja test || status=1
        else
            make test || status=1
        fi
    fi
    
    # Run package-specific tests
    local test_script="${PACKAGE_DIR}/${package}/test.sh"
    if [ -x "$test_script" ]; then
        if ! "$test_script" "$test_dir"; then
            log_error "Package-specific tests failed"
            status=1
        fi
    fi
    
    return $status
}

# Main entry point
main() {
    if [ "$#" -lt 2 ]; then
        log_error "Usage: $0 <command> <package> [options...]"
        exit 1
    fi
    
    local command="$1"
    local package="$2"
    shift 2
    
    case "$command" in
        install)
            if ! resolve_dependencies "$package"; then
                log_error "Dependency resolution failed"
                exit 1
            fi
            
            if ! optimize_build_order "$package"; then
                log_error "Build order optimization failed"
                exit 1
            fi
            
            if ! build_package "$package"; then
                log_error "Package build failed"
                exit 1
            fi
            ;;
        remove)
            remove_package "$package"
            ;;
        upgrade)
            upgrade_package "$package"
            ;;
        check)
            check_package "$package"
            ;;
        *)
            log_error "Unknown command: ${command}"
            exit 1
            ;;
    esac
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

