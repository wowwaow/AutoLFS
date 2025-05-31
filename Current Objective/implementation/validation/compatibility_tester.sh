#!/bin/bash
#
# Compatibility Testing Framework
# Validates system compatibility for LFS/BLFS builds
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
COMPAT_DIR="/var/run/lfs-wrapper/compatibility"
COMPAT_LOG="${COMPAT_DIR}/compatibility.log"
mkdir -p "$COMPAT_DIR"

# Required kernel version and features
declare -r MIN_KERNEL_VERSION="4.19.0"
declare -a REQUIRED_KERNEL_CONFIGS=(
    "CONFIG_DEVTMPFS"
    "CONFIG_DEVPTS_FILESYSTEM"
    "CONFIG_PROC_FS"
    "CONFIG_SYSFS"
    "CONFIG_TMPFS"
)

# Required CPU features
declare -a REQUIRED_CPU_FEATURES=(
    "sse2"
    "cx8"
    "fpu"
    "fxsr"
    "mmx"
    "syscall"
)

# Architecture Verification
verify_architecture() {
    local status=0
    
    # Check system architecture
    local arch
    arch=$(uname -m)
    
    log_info "Checking system architecture: ${arch}"
    
    case "$arch" in
        x86_64)
            # Check if running in 64-bit mode
            if ! grep -q "64-bit" /proc/cpuinfo; then
                log_error "CPU is not running in 64-bit mode"
                status=1
            fi
            ;;
        i?86)
            log_warn "32-bit architecture detected - some packages may not build"
            ;;
        *)
            log_error "Unsupported architecture: ${arch}"
            status=1
            ;;
    esac
    
    # Check CPU features
    for feature in "${REQUIRED_CPU_FEATURES[@]}"; do
        if ! grep -q "^flags.*\\b${feature}\\b" /proc/cpuinfo; then
            log_error "Required CPU feature not found: ${feature}"
            status=1
        fi
    done
    
    return $status
}

# Kernel Feature Validation
validate_kernel_features() {
    local status=0
    
    # Check kernel version
    local kernel_version
    kernel_version=$(uname -r | cut -d'-' -f1)
    
    log_info "Checking kernel version: ${kernel_version}"
    
    if ! version_compare "$kernel_version" "$MIN_KERNEL_VERSION"; then
        log_error "Kernel version too old: ${kernel_version} (minimum: ${MIN_KERNEL_VERSION})"
        status=1
    fi
    
    # Check kernel configuration
    if [ -f "/boot/config-$(uname -r)" ]; then
        local config_file="/boot/config-$(uname -r)"
    elif [ -f "/proc/config.gz" ]; then
        local config_file="/proc/config.gz"
        if ! command -v zcat >/dev/null 2>&1; then
            log_error "zcat not found - cannot read kernel config"
            return 1
        fi
    else
        log_error "Kernel config not found"
        return 1
    fi
    
    for config in "${REQUIRED_KERNEL_CONFIGS[@]}"; do
        if [ -f "$config_file" ]; then
            if ! grep -q "^${config}=y" "$config_file"; then
                log_error "Required kernel config not enabled: ${config}"
                status=1
            fi
        else
            if ! zcat "$config_file" | grep -q "^${config}=y"; then
                log_error "Required kernel config not enabled: ${config}"
                status=1
            fi
        fi
    done
    
    return $status
}

# Toolchain Compatibility Testing
test_toolchain_compatibility() {
    local status=0
    
    # Test GCC compatibility
    log_info "Testing GCC compatibility..."
    
    # Create test directory
    local test_dir
    test_dir=$(mktemp -d)
    cd "$test_dir" || exit 1
    
    # Create test source
    cat > test.c << 'EOF'
#include <stdio.h>
int main() {
    printf("Hello, world!\n");
    return 0;
}
EOF
    
    # Test compilation
    if ! gcc -o test test.c; then
        log_error "Basic GCC compilation test failed"
        status=1
    fi
    
    # Test linking
    cat > test_lib.c << 'EOF'
int test_function() { return 42; }
EOF
    
    cat > test_main.c << 'EOF'
extern int test_function();
int main() { return test_function() - 42; }
EOF
    
    if ! gcc -c test_lib.c -o test_lib.o; then
        log_error "GCC compilation of library failed"
        status=1
    fi
    
    if ! gcc -c test_main.c -o test_main.o; then
        log_error "GCC compilation of main failed"
        status=1
    fi
    
    if ! gcc test_main.o test_lib.o -o test_linked; then
        log_error "GCC linking test failed"
        status=1
    fi
    
    # Cleanup
    cd - > /dev/null
    rm -rf "$test_dir"
    
    return $status
}

# Environment Conflicts Detection
detect_environment_conflicts() {
    local status=0
    
    log_info "Checking for environment conflicts..."
    
    # Check for conflicting packages
    if command -v dpkg >/dev/null 2>&1; then
        # Debian-based system
        if dpkg -l | grep -q "^ii.*automake1."; then
            local automake_versions
            automake_versions=$(dpkg -l | grep "^ii.*automake1." | wc -l)
            if [ "$automake_versions" -gt 1 ]; then
                log_warn "Multiple automake versions installed - may cause conflicts"
            fi
        fi
    fi
    
    # Check for conflicting environment variables
    local -a CONFLICTING_VARS=(
        "LD_LIBRARY_PATH"
        "LD_PRELOAD"
        "LD_DEBUG"
        "CFLAGS"
        "CXXFLAGS"
        "LDFLAGS"
    )
    
    for var in "${CONFLICTING_VARS[@]}"; do
        if [ -n "${!var+x}" ]; then
            log_warn "Potentially conflicting environment variable set: ${var}=${!var}"
        fi
    done
    
    # Check for conflicting libraries
    if ldconfig -p | grep -q "libbsd\.so"; then
        log_warn "libbsd detected - may conflict with system libraries"
    fi
    
    return $status
}

# Compatibility Report Generation
generate_compatibility_report() {
    local report_file="${COMPAT_DIR}/compatibility_report.txt"
    
    {
        echo "=== LFS Build Environment Compatibility Report ==="
        echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        echo
        echo "System Information:"
        echo "- Architecture: $(uname -m)"
        echo "- Kernel: $(uname -r)"
        echo "- Distribution: $(get_distribution)"
        echo
        echo "CPU Information:"
        echo "- Processor: $(grep "model name" /proc/cpuinfo | head -n1 | cut -d: -f2)"
        echo "- Features: $(grep "flags" /proc/cpuinfo | head -n1 | cut -d: -f2)"
        echo
        echo "Toolchain Information:"
        echo "- GCC Version: $(gcc --version | head -n1)"
        echo "- Binutils Version: $(ld --version | head -n1)"
        echo "- Glibc Version: $(ldd --version | head -n1)"
        echo
        echo "Environment Variables:"
        env | sort
    } > "$report_file"
}

# Distribution Detection
get_distribution() {
    if [ -f /etc/os-release ]; then
        # freedesktop.org and systemd
        . /etc/os-release
        echo "$NAME $VERSION_ID"
    elif type lsb_release >/dev/null 2>&1; then
        # linuxbase.org
        lsb_release -si | tr -d '\n'
        echo -n " "
        lsb_release -sr
    elif [ -f /etc/lsb-release ]; then
        # For some versions of Debian/Ubuntu without lsb_release
        . /etc/lsb-release
        echo "$DISTRIB_ID $DISTRIB_RELEASE"
    elif [ -f /etc/debian_version ]; then
        # Older Debian/Ubuntu/etc.
        echo "Debian $(cat /etc/debian_version)"
    else
        # Fall back to uname
        uname -s -r
    fi
}

# Main entry point
main() {
    local status=0
    
    log_info "Starting compatibility tests..."
    
    # Run all compatibility checks
    verify_architecture || status=1
    validate_kernel_features || status=1
    test_toolchain_compatibility || status=1
    detect_environment_conflicts || status=1
    
    # Generate report regardless of status
    generate_compatibility_report
    
    if [ $status -eq 0 ]; then
        log_info "All compatibility tests passed"
    else
        log_error "Some compatibility tests failed"
    fi
    
    return $status
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

