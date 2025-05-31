#!/bin/bash

# Backup Creation Script
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Generate comprehensive backup metadata for file migration

# Exit on any error
set -e

# Configuration
SOURCE_DIR="/home/ubuntu"
BACKUP_DIR="$PWD"
LOG_DIR="/mnt/host/WARP_CURRENT/System Logs"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging function
log() {
    local timestamp=$(date -u --iso-8601=seconds)
    local level=$1
    local message=$2
    local color=$3
    echo -e "${color}[$timestamp] $level: $message${NC}" | tee -a "$LOG_DIR/backup_creation.log"
}

# Error handling
error() { log "ERROR" "$1" "$RED"; }
warn() { log "WARN" "$1" "$YELLOW"; }
info() { log "INFO" "$1" "$GREEN"; }

# Error trap
trap 'error "Error on line $LINENO" >&2; exit 1' ERR

# Setup backup environment
setup_backup() {
    info "Setting up backup environment..."
    mkdir -p "$BACKUP_DIR"
    chmod 755 "$BACKUP_DIR"
}

# Generate file checksums
generate_checksums() {
    info "Generating SHA256 checksums..."
    local checksum_file="$BACKUP_DIR/checksum-manifest.md"

    {
        echo "# File Checksum Manifest"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## File Integrity Information"
        echo "| File Path | SHA256 Checksum |"
        echo "|-----------|-----------------|"
        
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                local rel_path=${file#$SOURCE_DIR/}
                local checksum=$(sha256sum "$file" | cut -d' ' -f1)
                echo "| $rel_path | $checksum |"
            fi
        done < <(find "$SOURCE_DIR" -type f)

        echo
        echo "## Verification Command"
        echo "\`\`\`bash"
        echo "sha256sum -c checksum-manifest.sha256"
        echo "\`\`\`"
    } > "$checksum_file"

    # Create raw checksum file for verification
    find "$SOURCE_DIR" -type f -exec sha256sum {} + > "$BACKUP_DIR/checksum-manifest.sha256"
}

# Create permissions map
create_permissions_map() {
    info "Creating permissions map..."
    local perm_file="$BACKUP_DIR/permissions-map.md"

    {
        echo "# File Permissions Map"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## File Permissions"
        echo "| File Path | Owner | Group | Permissions | Special Bits |"
        echo "|-----------|-------|-------|-------------|--------------|"
        
        while IFS= read -r file; do
            local rel_path=${file#$SOURCE_DIR/}
            local stat=$(stat -c "%U|%G|%a|%A" "$file")
            IFS='|' read -r owner group perms full_perms <<< "$stat"
            echo "| $rel_path | $owner | $group | $perms | $full_perms |"
        done < <(find "$SOURCE_DIR" \( -type f -o -type d \))

        echo
        echo "## Special Permission Details"
        echo "\`\`\`bash"
        find "$SOURCE_DIR" -perm /6000 -ls
        echo "\`\`\`"
    } > "$perm_file"
}

# Build symbolic link inventory
create_symlink_inventory() {
    info "Building symbolic link inventory..."
    local link_file="$BACKUP_DIR/symlink-inventory.md"

    {
        echo "# Symbolic Link Inventory"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Link Relationships"
        echo "| Link Path | Target Path | Status |"
        echo "|-----------|-------------|---------|"
        
        while IFS= read -r link; do
            local rel_path=${link#$SOURCE_DIR/}
            local target=$(readlink "$link")
            local status="Valid"
            
            if [[ "$target" = /* ]]; then
                if [ ! -e "$target" ]; then
                    status="Broken (Absolute)"
                fi
            else
                if [ ! -e "$(dirname "$link")/$target" ]; then
                    status="Broken (Relative)"
                fi
            fi
            
            echo "| $rel_path | $target | $status |"
        done < <(find "$SOURCE_DIR" -type l)

        echo
        echo "## Link Statistics"
        echo "- Total Links: $(find "$SOURCE_DIR" -type l | wc -l)"
        echo "- Absolute Links: $(find "$SOURCE_DIR" -type l -exec readlink {} \; | grep -c '^/')"
        echo "- Relative Links: $(find "$SOURCE_DIR" -type l -exec readlink {} \; | grep -cv '^/')"
    } > "$link_file"
}

# Record timestamp baseline
create_timestamp_baseline() {
    info "Recording timestamp baseline..."
    local time_file="$BACKUP_DIR/timestamp-baseline.md"

    {
        echo "# File Timestamp Baseline"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## File Timestamps"
        echo "| File Path | Access Time | Modify Time | Change Time |"
        echo "|-----------|-------------|-------------|-------------|"
        
        while IFS= read -r file; do
            local rel_path=${file#$SOURCE_DIR/}
            local stat=$(stat -c "%x|%y|%z" "$file")
            IFS='|' read -r atime mtime ctime <<< "$stat"
            echo "| $rel_path | $atime | $mtime | $ctime |"
        done < <(find "$SOURCE_DIR" \( -type f -o -type d \))

        echo
        echo "## Timestamp Statistics"
        echo "\`\`\`"
        find "$SOURCE_DIR" -type f -printf '%TY-%Tm-%Td %TH:%TM:%TS %p\n' | sort -n | head -n 5
        echo "..."
        find "$SOURCE_DIR" -type f -printf '%TY-%Tm-%Td %TH:%TM:%TS %p\n' | sort -n | tail -n 5
        echo "\`\`\`"
    } > "$time_file"
}

# Generate summary report
generate_summary() {
    local status=$1
    local summary_file="$BACKUP_DIR/backup-summary.md"

    {
        echo "# Backup Creation Summary"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Overall Status: ${status}"
        echo
        echo "## Component Status"
        echo "- Checksum Generation: $(test -f "$BACKUP_DIR/checksum-manifest.md" && echo "✓" || echo "❌")"
        echo "- Permissions Map: $(test -f "$BACKUP_DIR/permissions-map.md" && echo "✓" || echo "❌")"
        echo "- Symlink Inventory: $(test -f "$BACKUP_DIR/symlink-inventory.md" && echo "✓" || echo "❌")"
        echo "- Timestamp Baseline: $(test -f "$BACKUP_DIR/timestamp-baseline.md" && echo "✓" || echo "❌")"
        echo
        echo "## File Statistics"
        echo "- Total Files: $(find "$SOURCE_DIR" -type f | wc -l)"
        echo "- Total Size: $(du -sh "$SOURCE_DIR" | cut -f1)"
        echo "- Symlinks: $(find "$SOURCE_DIR" -type l | wc -l)"
        echo "- Directories: $(find "$SOURCE_DIR" -type d | wc -l)"
        echo
        echo "## Verification Instructions"
        echo "1. Use checksum-manifest.sha256 for integrity verification"
        echo "2. Compare permissions using permissions-map.md"
        echo "3. Validate symlinks against symlink-inventory.md"
        echo "4. Check timestamps against timestamp-baseline.md"
    } > "$summary_file"
}

# Main execution
main() {
    info "Starting backup creation process..."
    local errors=0

    setup_backup

    info "Creating backup components..."
    generate_checksums || ((errors++))
    create_permissions_map || ((errors++))
    create_symlink_inventory || ((errors++))
    create_timestamp_baseline || ((errors++))

    if [[ $errors -eq 0 ]]; then
        info "All backup components created successfully!"
        generate_summary "COMPLETED"
        return 0
    else
        error "Backup creation completed with $errors error(s)"
        generate_summary "FAILED"
        return 1
    fi
}

# Execute main function
main "$@"

