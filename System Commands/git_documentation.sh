#!/bin/bash

# Add safety measures
set -euo pipefail

# Verification functions
verify_file_access() {
    local file_path="$1"
    if [[ ! -f "$file_path" ]]; then
        echo "ERROR: File does not exist: $file_path" >&2
        return 1
    fi
    if [[ ! -r "$file_path" ]]; then
        echo "ERROR: File is not readable: $file_path" >&2
        return 1
    fi
    if [[ ! -w "$file_path" ]]; then
        echo "ERROR: File is not writable: $file_path" >&2
        return 1
    fi
    return 0
}

verify_directory_access() {
    local dir_path="$1"
    if [[ ! -d "$dir_path" ]]; then
        echo "ERROR: Directory does not exist: $dir_path" >&2
        return 1
    fi
    if [[ ! -r "$dir_path" ]]; then
        echo "ERROR: Directory is not readable: $dir_path" >&2
        return 1
    fi
    if [[ ! -w "$dir_path" ]]; then
        echo "ERROR: Directory is not writable: $dir_path" >&2
        return 1
    fi
    if [[ ! -x "$dir_path" ]]; then
        echo "ERROR: Directory is not executable: $dir_path" >&2
        return 1
    fi
    return 0
}

log_critical_error() {
    local error_message="$1"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "❌ CRITICAL ERROR: $error_message" >&2
    return 1
}

audit_specific_permissions() {
    local path_list=("$@")
    local has_issues=false
    local issues_found=()
    
    for path in "${path_list[@]}"; do
        if [[ -e "$path" ]]; then
            local ownership
            local permissions
            ownership=$(stat -c '%U:%G' "$path" 2>/dev/null) || continue
            permissions=$(stat -c '%a' "$path" 2>/dev/null) || continue
            
            if [[ "$ownership" != "ubuntu:ubuntu" ]]; then
                issues_found+=("Wrong ownership on $path: $ownership (should be ubuntu:ubuntu)")
                has_issues=true
            fi
            
            if [[ -f "$path" && "$permissions" != "644" && "$permissions" != "755" ]]; then
                issues_found+=("Wrong file permissions on $path: $permissions (should be 644 or 755)")
                has_issues=true
            fi
            
            if [[ -d "$path" && "$permissions" != "755" ]]; then
                issues_found+=("Wrong directory permissions on $path: $permissions (should be 755)")
                has_issues=true
            fi
        else
            issues_found+=("Path does not exist: $path")
            has_issues=true
        fi
    done
    
    if [[ "$has_issues" == "true" ]]; then
        echo "has_issues"
        printf '%s\n' "${issues_found[@]}"
        return 1
    fi
    return 0
}

# Base directories
export WARP_HOST_DIR="${WARP_HOST_DIR:-/mnt/host}"
export WARP_SYSTEM_DIR="${WARP_SYSTEM_DIR:-$WARP_HOST_DIR/WARP_CURRENT}"
export SYSTEM_DIR="$WARP_SYSTEM_DIR"

# Create and ensure permissions for essential directories
ensure_base_directories() {
    local dirs=(
        "$WARP_SYSTEM_DIR/Git Documentation"
        "$WARP_SYSTEM_DIR/System Commands"
        "$WARP_SYSTEM_DIR/System Logs"
    )
    
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            sudo mkdir -p "$dir"
        fi
        sudo chown ubuntu:ubuntu "$dir"
        sudo chmod 755 "$dir"
    done
}

# Initialize log files
initialize_log_files() {
    local log_files=(
        "COMMIT_LOG.md"
        "BRANCH_LOG.md"
        "MERGE_LOG.md"
        "TAG_LOG.md"
        "HOOK_LOG.md"
        "CONFIG_LOG.md"
        "WORKFLOW_LOG.md"
        "REPOSITORY_STATUS.md"
        "COLLABORATION_LOG.md"
    )
    
    for file in "${log_files[@]}"; do
        local full_path="$WARP_SYSTEM_DIR/Git Documentation/$file"
        if [[ ! -f "$full_path" ]]; then
            touch "$full_path"
        fi
        sudo chown ubuntu:ubuntu "$full_path"
        sudo chmod 644 "$full_path"
    done
}

# Main execution
main() {
    echo "🚀 Starting Enhanced Warp System with Git Documentation..."
    
    # Ensure base directories exist with correct permissions
    ensure_base_directories
    
    # Initialize log files
    initialize_log_files
    
    echo "✅ Git documentation system initialized successfully!"
    echo "📊 Git Documentation directory: $WARP_SYSTEM_DIR/Git Documentation"
    echo "📝 System Commands directory: $WARP_SYSTEM_DIR/System Commands"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
