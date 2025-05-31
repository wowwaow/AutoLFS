#!/bin/bash

# LFS Validation Script
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Validate LFS build environment and results

# Validation states
declare -A VALIDATION_STATES=(
    [PASS]="✓"
    [FAIL]="✗"
    [WARN]="!"
)

# Initialize validation system
init_validation() {
    info "Initializing LFS validation system..."
    
    # Create validation log directory
    mkdir -p "$LFS/var/log/validation"
    
    return 0
}

# Validate LFS script
validate_lfs_script() {
    local script_path=$1
    local package_name=$2
    
    info "Validating LFS script: $package_name"
    
    # Check file exists
    if [ ! -f "$script_path" ]; then
        error "Script file not found: $script_path"
        return 1
    fi
    
    # Check file is executable
    if [ ! -x "$script_path" ]; then
        error "Script is not executable: $script_path"
        return 1
    fi
    
    # Validate script structure
    local required_functions=(
        "prepare"
        "configure"
        "build"
        "test"
        "install"
        "cleanup"
    )
    
    for func in "${required_functions[@]}"; do
        if ! grep -q "^${func}()" "$script_path"; then
            error "Required function missing: $func"
            return 1
        fi
    done
    
    return 0
}

# Validate build environment
validate_build_environment() {
    local phase=$1
    
    info "Validating build environment for phase: $phase"
    
    # Check system requirements
    validate_system_requirements || return 1
    
    # Check directory structure
    validate_directory_structure || return 1
    
    # Check toolchain
    validate_toolchain "$phase" || return 1
    
    # Check permissions
    validate_permissions || return 1
    
    return 0
}

# Validate system requirements
validate_system_requirements() {
    info "Validating system requirements..."
    local errors=0
    
    # Check disk space
    local available_space=$(df -BG "$LFS" | awk 'NR==2 {print $4}' | tr -d 'G')
    if [ "$available_space" -lt 8 ]; then
        error "Insufficient disk space: ${available_space}G (minimum 8G required)"
        ((errors++))
    fi
    
    # Check memory
    local available_memory=$(free -g | awk '/^Mem:/ {print $2}')
    if [ "$available_memory" -lt 4 ]; then
        error "Insufficient memory: ${available_memory}G (minimum 4G required)"
        ((errors++))
    fi
    
    return $errors
}

# Validate directory structure
validate_directory_structure() {
    info "Validating directory structure..."
    local errors=0
    
    # Required directories
    local required_dirs=(
        "$LFS"
        "$LFS/tools"
        "$LFS/sources"
        "$LFS/var/log"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            error "Required directory missing: $dir"
            ((errors++))
        fi
    done
    
    return $errors
}

# Validate toolchain
validate_toolchain() {
    local phase=$1
    info "Validating toolchain for phase: $phase"
    
    case $phase in
        PASS1)
            validate_pass1_toolchain
            ;;
        PASS2)
            validate_pass2_toolchain
            ;;
        FINAL)
            validate_final_toolchain
            ;;
        *)
            error "Unknown phase: $phase"
            return 1
            ;;
    esac
}

# Validate Pass 1 toolchain
validate_pass1_toolchain() {
    local errors=0
    
    # Check cross-compiler
    if ! "$LFS/tools/bin/$LFS_TGT-gcc" --version >/dev/null 2>&1; then
        error "Cross-compiler not functional"
        ((errors++))
    fi
    
    return $errors
}

# Validate Pass 2 toolchain
validate_pass2_toolchain() {
    local errors=0
    
    # Check temporary tools
    local required_tools=(
        "gcc"
        "make"
        "ld"
        "as"
    )
    
    for tool in "${required_tools[@]}"; do
        if ! "$LFS/tools/bin/$tool" --version >/dev/null 2>&1; then
            error "Required tool not functional: $tool"
            ((errors++))
        fi
    done
    
    return $errors
}

# Validate final toolchain
validate_final_toolchain() {
    local errors=0
    
    # Check final system tools
    local required_tools=(
        "/bin/bash"
        "/bin/gcc"
        "/bin/make"
        "/bin/ld"
    )
    
    for tool in "${required_tools[@]}"; do
        if [ ! -x "$tool" ]; then
            error "Required tool not found: $tool"
            ((errors++))
        fi
    done
    
    return $errors
}

# Validate permissions
validate_permissions() {
    info "Validating permissions..."
    local errors=0
    
    # Check LFS directory ownership
    if [ "$(stat -c '%U:%G' "$LFS")" != "lfs:lfs" ]; then
        error "Incorrect LFS directory ownership"
        ((errors++))
    fi
    
    # Check tools directory permissions
    if [ "$(stat -c '%a' "$LFS/tools")" != "755" ]; then
        error "Incorrect tools directory permissions"
        ((errors++))
    fi
    
    return $errors
}

# Validate package build
validate_package_build() {
    local package=$1
    info "Validating package build: $package"
    
    # Check build artifacts
    if ! validate_build_artifacts "$package"; then
        return 1
    fi
    
    # Run package tests if available
    if ! run_package_tests "$package"; then
        return 1
    fi
    
    return 0
}

# Validate build artifacts
validate_build_artifacts() {
    local package=$1
    local errors=0
    
    # Check installed files
    if [ ! -f "$LFS/.${package}_installed" ]; then
        error "Package installation record not found: $package"
        ((errors++))
    fi
    
    # Verify critical files
    while read -r file; do
        if [ ! -f "$LFS/$file" ]; then
            error "Required file missing: $file"
            ((errors++))
        fi
    done < "$LFS/.${package}_installed"
    
    return $errors
}

# Run package tests
run_package_tests() {
    local package=$1
    
    if [ -f "$LFS/sources/$package/test.sh" ]; then
        info "Running package tests: $package"
        (
            cd "$LFS/sources/$package"
            ./test.sh
        )
        return $?
    fi
    
    return 0
}

# Generate validation report
generate_validation_report() {
    local phase=$1
    local report_file="$LFS/var/log/validation/${phase}_validation.md"
    
    {
        echo "# LFS Validation Report"
        echo "Phase: $phase"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## System Requirements"
        echo "- Disk Space: $(df -h "$LFS" | awk 'NR==2 {print $4}')"
        echo "- Memory: $(free -h | awk '/^Mem:/ {print $2}')"
        echo
        echo "## Directory Structure"
        find "$LFS" -maxdepth 2 -type d -ls
        echo
        echo "## Toolchain Status"
        echo "$(get_toolchain_status)"
        echo
        echo "## Validation Results"
        echo "$(get_validation_results "$phase")"
    } > "$report_file"
}

# Export validation status
export_validation_status() {
    local phase=$1
    
    cat << EOF
{
    "phase": "$phase",
    "timestamp": "$(date -u --iso-8601=seconds)",
    "results": $(get_validation_results "$phase" "json")
}
EOF
}

