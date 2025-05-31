#!/bin/bash

# System Configuration Transfer Script
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Securely migrate system configuration files

# Exit on any error
set -e

# Configuration
SOURCE_DIR="/home/ubuntu"
DEST_DIR="/mnt/host"
LOG_DIR="$DEST_DIR/WARP_CURRENT/System Logs"
REPORT_DIR="$DEST_DIR/WARP_CURRENT/Current Objective/phase2/system-config/reports"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Config files to transfer
DOTFILES=(
    ".bashrc"
    ".bash_profile"
    ".profile"
    ".vimrc"
    ".gitconfig"
    ".inputrc"
)

# Logging function
log() {
    local timestamp=$(date -u --iso-8601=seconds)
    local level=$1
    local message=$2
    local color=$3
    echo -e "${color}[$timestamp] $level: $message${NC}" | tee -a "$LOG_DIR/config_transfer.log"
}

# Error handling
error() { log "ERROR" "$1" "$RED"; }
warn() { log "WARN" "$1" "$YELLOW"; }
info() { log "INFO" "$1" "$GREEN"; }

# Error trap
trap 'error "Error on line $LINENO" >&2; exit 1' ERR

# Setup directories
setup_transfer() {
    info "Setting up transfer environment..."
    mkdir -p "$REPORT_DIR"
    chmod 700 "$REPORT_DIR"
}

# Verify file integrity
verify_integrity() {
    local source=$1
    local dest=$2
    
    if [ -f "$source" ]; then
        local source_sum=$(sha256sum "$source" | cut -d' ' -f1)
        local dest_sum=$(sha256sum "$dest" | cut -d' ' -f1)
        
        if [ "$source_sum" = "$dest_sum" ]; then
            return 0
        fi
    fi
    return 1
}

# Transfer .config directory
transfer_config() {
    info "Transferring .config directory..."
    local config_src="$SOURCE_DIR/.config"
    local config_dest="$DEST_DIR/.config"
    
    if [ -d "$config_src" ]; then
        rsync -avz --progress "$config_src/" "$config_dest/"
        
        {
            echo "# Config Transfer Log"
            echo "Generated: $(date -u --iso-8601=seconds)"
            echo
            echo "## Transferred Configuration Files"
            echo "\`\`\`"
            find "$config_dest" -type f -exec ls -l {} \;
            echo "\`\`\`"
        } > "$REPORT_DIR/config-transfer-log.md"
    else
        warn "No .config directory found"
    fi
}

# Transfer .cache directory
transfer_cache() {
    info "Transferring .cache directory..."
    local cache_src="$SOURCE_DIR/.cache"
    local cache_dest="$DEST_DIR/.cache"
    
    if [ -d "$cache_src" ]; then
        rsync -avz --progress "$cache_src/" "$cache_dest/"
        
        # Add to transfer log
        {
            echo
            echo "## Cache Transfer"
            echo "- Source: $cache_src"
            echo "- Destination: $cache_dest"
            echo "- Size: $(du -sh "$cache_dest" | cut -f1)"
            echo "- Files: $(find "$cache_dest" -type f | wc -l)"
        } >> "$REPORT_DIR/config-transfer-log.md"
    else
        warn "No .cache directory found"
    fi
}

# Secure copy of sensitive directories
transfer_secure() {
    info "Transferring secure directories..."
    local ssh_src="$SOURCE_DIR/.ssh"
    local gnupg_src="$SOURCE_DIR/.gnupg"
    local ssh_dest="$DEST_DIR/.ssh"
    local gnupg_dest="$DEST_DIR/.gnupg"
    
    {
        echo "# Security Verification Report"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## SSH Directory Transfer"
    } > "$REPORT_DIR/security-verification.md"
    
    if [ -d "$ssh_src" ]; then
        # Secure SSH transfer
        mkdir -p "$ssh_dest"
        chmod 700 "$ssh_dest"
        rsync -avz --chmod=go= "$ssh_src/" "$ssh_dest/"
        
        echo "- SSH directory transferred with secure permissions" >> "$REPORT_DIR/security-verification.md"
        echo "- Permissions verified: $(ls -ld "$ssh_dest")" >> "$REPORT_DIR/security-verification.md"
    fi
    
    if [ -d "$gnupg_src" ]; then
        # Secure GPG transfer
        mkdir -p "$gnupg_dest"
        chmod 700 "$gnupg_dest"
        rsync -avz --chmod=go= "$gnupg_src/" "$gnupg_dest/"
        
        echo
        echo "## GnuPG Directory Transfer" >> "$REPORT_DIR/security-verification.md"
        echo "- GnuPG directory transferred with secure permissions" >> "$REPORT_DIR/security-verification.md"
        echo "- Permissions verified: $(ls -ld "$gnupg_dest")" >> "$REPORT_DIR/security-verification.md"
    fi
}

# Transfer dotfiles
transfer_dotfiles() {
    info "Transferring dotfiles..."
    
    {
        echo "# Dotfile Inventory"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Transferred Dotfiles"
        echo "| File | Status | Permissions | Checksum |"
        echo "|------|--------|-------------|----------|"
    } > "$REPORT_DIR/dotfile-inventory.md"
    
    for file in "${DOTFILES[@]}"; do
        local source="$SOURCE_DIR/$file"
        local dest="$DEST_DIR/$file"
        
        if [ -f "$source" ]; then
            cp -p "$source" "$dest"
            local perms=$(stat -c "%a" "$dest")
            local checksum=$(sha256sum "$dest" | cut -d' ' -f1)
            
            if verify_integrity "$source" "$dest"; then
                echo "| $file | ✓ | $perms | $checksum |" >> "$REPORT_DIR/dotfile-inventory.md"
            else
                echo "| $file | ❌ | $perms | $checksum |" >> "$REPORT_DIR/dotfile-inventory.md"
                error "Integrity check failed for $file"
            fi
        else
            echo "| $file | Not Found | - | - |" >> "$REPORT_DIR/dotfile-inventory.md"
        fi
    done
}

# Validate transfer
validate_transfer() {
    info "Validating transfer..."
    local errors=0
    
    {
        echo "# Transfer Validation Report"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Validation Results"
        echo "| Component | Status | Details |"
        echo "|-----------|--------|----------|"
    } > "$REPORT_DIR/transfer-validation.md"
    
    # Validate .config
    if [ -d "$DEST_DIR/.config" ]; then
        echo "| .config | ✓ | $(find "$DEST_DIR/.config" -type f | wc -l) files |" >> "$REPORT_DIR/transfer-validation.md"
    else
        echo "| .config | ❌ | Directory missing |" >> "$REPORT_DIR/transfer-validation.md"
        ((errors++))
    fi
    
    # Validate .cache
    if [ -d "$DEST_DIR/.cache" ]; then
        echo "| .cache | ✓ | $(find "$DEST_DIR/.cache" -type f | wc -l) files |" >> "$REPORT_DIR/transfer-validation.md"
    else
        echo "| .cache | ❌ | Directory missing |" >> "$REPORT_DIR/transfer-validation.md"
        ((errors++))
    fi
    
    # Validate secure directories
    if [ -d "$DEST_DIR/.ssh" ] && [ "$(stat -c "%a" "$DEST_DIR/.ssh")" = "700" ]; then
        echo "| .ssh | ✓ | Secure permissions verified |" >> "$REPORT_DIR/transfer-validation.md"
    else
        echo "| .ssh | ❌ | Permission verification failed |" >> "$REPORT_DIR/transfer-validation.md"
        ((errors++))
    fi
    
    if [ -d "$DEST_DIR/.gnupg" ] && [ "$(stat -c "%a" "$DEST_DIR/.gnupg")" = "700" ]; then
        echo "| .gnupg | ✓ | Secure permissions verified |" >> "$REPORT_DIR/transfer-validation.md"
    else
        echo "| .gnupg | ❌ | Permission verification failed |" >> "$REPORT_DIR/transfer-validation.md"
        ((errors++))
    fi
    
    # Validate dotfiles
    local dotfile_errors=0
    for file in "${DOTFILES[@]}"; do
        if [ -f "$DEST_DIR/$file" ] && verify_integrity "$SOURCE_DIR/$file" "$DEST_DIR/$file"; then
            true
        else
            ((dotfile_errors++))
        fi
    done
    
    if [ $dotfile_errors -eq 0 ]; then
        echo "| Dotfiles | ✓ | All files verified |" >> "$REPORT_DIR/transfer-validation.md"
    else
        echo "| Dotfiles | ❌ | $dotfile_errors files failed verification |" >> "$REPORT_DIR/transfer-validation.md"
        ((errors++))
    fi
    
    return $errors
}

# Main execution
main() {
    info "Starting system configuration transfer..."
    local errors=0

    setup_transfer

    info "Executing transfer phases..."
    transfer_config || ((errors++))
    transfer_cache || ((errors++))
    transfer_secure || ((errors++))
    transfer_dotfiles || ((errors++))
    validate_transfer || ((errors++))

    if [[ $errors -eq 0 ]]; then
        info "Configuration transfer completed successfully!"
        return 0
    else
        error "Transfer completed with $errors error(s)"
        return 1
    fi
}

# Execute main function
main "$@"

