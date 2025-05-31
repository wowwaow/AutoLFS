#!/bin/bash

# System Health Check Script
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Validate system readiness for file migration

# Exit on any error
set -e

# Configuration
SOURCE_DIR="/home/ubuntu"
DEST_DIR="/mnt/host"
LOG_DIR="$DEST_DIR/WARP_CURRENT/System Logs"
REPORT_DIR="$DEST_DIR/WARP_CURRENT/Current Objective/phase1/reports"
MIN_SPACE_GB=2

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Required tools
REQUIRED_TOOLS=(
    "rsync:3.1.0"
    "find:4.5.0"
    "stat:8.30"
    "sha256sum:8.30"
    "tree:1.7.0"
    "du:8.30"
    "file:5.30"
)

# Logging function
log() {
    local timestamp=$(date -u --iso-8601=seconds)
    local level=$1
    local message=$2
    local color=$3
    echo -e "${color}[$timestamp] $level: $message${NC}" | tee -a "$LOG_DIR/health_check.log"
}

# Error handling
error() { log "ERROR" "$1" "$RED"; }
warn() { log "WARN" "$1" "$YELLOW"; }
info() { log "INFO" "$1" "$GREEN"; }

# Error trap
trap 'error "Error on line $LINENO" >&2; exit 1' ERR

# Create required directories
setup_directories() {
    info "Setting up directories..."
    mkdir -p "$REPORT_DIR"
    chmod 755 "$REPORT_DIR"
}

# Check tool versions
check_tool_version() {
    local tool=$1
    local min_version=$2
    local version_output
    local actual_version

    if ! version_output=$($tool --version 2>&1 | head -n1); then
        error "Failed to get version for $tool"
        return 1
    fi

    actual_version=$(echo "$version_output" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+|[0-9]+\.[0-9]+' | head -n1)
    if [[ $(echo -e "$min_version\n$actual_version" | sort -V | head -n1) == "$min_version" ]]; then
        info "✓ $tool version $actual_version meets minimum requirement ($min_version)"
        return 0
    else
        error "✗ $tool version $actual_version does not meet minimum requirement ($min_version)"
        return 1
    fi
}

# Validate permissions
check_permissions() {
    info "Checking directory permissions..."
    local errors=0

    # Source checks
    if [[ ! -r "$SOURCE_DIR" ]]; then
        error "Cannot read source directory: $SOURCE_DIR"
        ((errors++))
    fi
    if [[ ! -x "$SOURCE_DIR" ]]; then
        error "Cannot traverse source directory: $SOURCE_DIR"
        ((errors++))
    fi

    # Destination checks
    if [[ ! -w "$DEST_DIR" ]]; then
        error "Cannot write to destination directory: $DEST_DIR"
        ((errors++))
    fi

    # Generate permission report
    {
        echo "# Permission Validation Report"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Source Directory Permissions"
        echo "\`\`\`"
        ls -ld "$SOURCE_DIR"
        echo "\`\`\`"
        echo
        echo "## Destination Directory Permissions"
        echo "\`\`\`"
        ls -ld "$DEST_DIR"
        echo "\`\`\`"
    } > "$REPORT_DIR/permissions.md"

    return $errors
}

# Check available space
check_space() {
    info "Verifying space requirements..."
    local source_size=$(du -s "$SOURCE_DIR" | awk '{print $1}')
    local source_size_gb=$(echo "scale=2; $source_size/1024/1024" | bc)
    local dest_free=$(df -BG "$DEST_DIR" | awk 'NR==2 {print $4}' | tr -d 'G')

    {
        echo "# Space Analysis Report"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Current Space Usage"
        echo "- Source Directory Size: ${source_size_gb}GB"
        echo "- Destination Free Space: ${dest_free}GB"
        echo "- Required Space: ${MIN_SPACE_GB}GB"
        echo "- Safety Factor: 2x source size required"
        echo
        if (( $(echo "$dest_free < $MIN_SPACE_GB" | bc -l) )); then
            echo "**WARNING:** Insufficient space available"
            error "Insufficient space available"
            return 1
        else
            echo "**OK:** Sufficient space available"
            info "Space requirements met"
        fi
    } > "$REPORT_DIR/space.md"
}

# Generate source inventory
create_inventory() {
    info "Generating source inventory..."
    
    {
        echo "# Source Directory Inventory"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Directory Structure"
        echo "\`\`\`"
        tree -a --du -h --filelimit 100 "$SOURCE_DIR" 2>/dev/null || warn "Tree command limited output"
        echo "\`\`\`"
        echo
        echo "## Large Files (>10MB)"
        echo "\`\`\`"
        find "$SOURCE_DIR" -type f -size +10M -exec ls -lh {} \; | sort -k5,5hr
        echo "\`\`\`"
        echo
        echo "## File Types"
        echo "\`\`\`"
        find "$SOURCE_DIR" -type f -exec file {} \; | sort | uniq -c | sort -nr
        echo "\`\`\`"
    } > "$REPORT_DIR/inventory.md"
}

# Verify system dependencies
verify_dependencies() {
    info "Checking system dependencies..."
    local errors=0

    {
        echo "# System Dependencies Report"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Tool Versions"
        echo "| Tool | Required Version | Installed Version | Status |"
        echo "|------|-----------------|------------------|---------|"

        for tool_info in "${REQUIRED_TOOLS[@]}"; do
            IFS=':' read -r tool min_version <<< "$tool_info"
            if ! check_tool_version "$tool" "$min_version"; then
                ((errors++))
                echo "| $tool | $min_version | NOT FOUND/ERROR | ❌ |"
            else
                version=$($tool --version 2>&1 | head -n1)
                echo "| $tool | $min_version | $version | ✓ |"
            fi
        done
    } > "$REPORT_DIR/dependencies.md"

    return $errors
}

# Generate summary report
generate_summary() {
    local status=$1
    {
        echo "# System Health Check Summary"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Overall Status: ${status}"
        echo
        echo "## Component Status"
        echo "- Permissions: $(test -f "$REPORT_DIR/permissions.md" && echo "✓" || echo "❌")"
        echo "- Space Analysis: $(test -f "$REPORT_DIR/space.md" && echo "✓" || echo "❌")"
        echo "- Source Inventory: $(test -f "$REPORT_DIR/inventory.md" && echo "✓" || echo "❌")"
        echo "- Dependencies: $(test -f "$REPORT_DIR/dependencies.md" && echo "✓" || echo "❌")"
        echo
        echo "## Next Steps"
        if [[ "$status" == "PASSED" ]]; then
            echo "- Proceed with migration preparation"
            echo "- Review inventory for special handling cases"
            echo "- Create backup strategy based on inventory"
        else
            echo "- Address failed checks"
            echo "- Review error logs"
            echo "- Consult system administrator if needed"
        fi
    } > "$REPORT_DIR/summary.md"
}

# Main execution
main() {
    info "Starting system health check..."
    local errors=0

    setup_directories

    info "Running system checks..."
    check_permissions || ((errors++))
    check_space || ((errors++))
    create_inventory || ((errors++))
    verify_dependencies || ((errors++))

    if [[ $errors -eq 0 ]]; then
        info "All health checks passed successfully!"
        generate_summary "PASSED"
        return 0
    else
        error "Health check completed with $errors error(s)"
        generate_summary "FAILED"
        return 1
    fi
}

# Execute main function
main "$@"

