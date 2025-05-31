#!/bin/bash

# Development Project Migration Script
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Migrate development projects with VCS preservation

# Exit on any error
set -e

# Configuration
SOURCE_DIR="/home/ubuntu"
DEST_DIR="/mnt/host"
LOG_DIR="$DEST_DIR/WARP_CURRENT/System Logs"
REPORT_DIR="$DEST_DIR/WARP_CURRENT/Current Objective/phase2/dev-projects/reports"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")

# Project directories
PROJECTS=(
    "lfsbuilder"
    "holyc-lang"
    "modular-lfs-builder-v1"
    "WARP_CURRENT"
)

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
    echo -e "${color}[$timestamp] $level: $message${NC}" | tee -a "$LOG_DIR/dev_migration.log"
}

# Error handling
error() { log "ERROR" "$1" "$RED"; }
warn() { log "WARN" "$1" "$YELLOW"; }
info() { log "INFO" "$1" "$GREEN"; }

# Error trap
trap 'error "Error on line $LINENO" >&2; exit 1' ERR

# Setup directories
setup_migration() {
    info "Setting up migration environment..."
    mkdir -p "$REPORT_DIR"
    chmod 755 "$REPORT_DIR"
}

# Check git repository status
check_git_status() {
    local repo_path=$1
    if [ -d "$repo_path/.git" ]; then
        cd "$repo_path"
        if ! git status &>/dev/null; then
            error "Invalid git repository: $repo_path"
            return 1
        fi
        if [ -n "$(git status --porcelain)" ]; then
            warn "Uncommitted changes in repository: $repo_path"
        fi
        return 0
    fi
    return 1
}

# Document git repository state
document_git_state() {
    local repo_path=$1
    local repo_name=$(basename "$repo_path")
    
    cd "$repo_path"
    {
        echo "# Git Repository State: $repo_name"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Repository Information"
        echo "\`\`\`"
        git remote -v
        echo "\`\`\`"
        echo
        echo "## Current Branch"
        echo "\`\`\`"
        git branch --show-current
        echo "\`\`\`"
        echo
        echo "## Recent Commits"
        echo "\`\`\`"
        git log --oneline -n 5
        echo "\`\`\`"
        echo
        echo "## Status"
        echo "\`\`\`"
        git status --short
        echo "\`\`\`"
    } >> "$REPORT_DIR/vcs-preservation.md"
}

# Migrate project directory
migrate_project() {
    local project=$1
    local source="$SOURCE_DIR/$project"
    local dest="$DEST_DIR/$project"
    
    info "Migrating project: $project"
    
    # Document project state
    {
        echo "# Project Migration: $project"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Project Structure"
        echo "\`\`\`"
        tree -a -L 3 "$source" 2>/dev/null || find "$source" -maxdepth 3 -type d
        echo "\`\`\`"
    } >> "$REPORT_DIR/project-transfer-log.md"

    # Check for VCS
    if check_git_status "$source"; then
        document_git_state "$source"
    fi

    # Transfer project files
    rsync -avz --progress "$source/" "$dest/"

    # Record build artifacts
    if [ -d "$source/build" ] || [ -d "$source/target" ]; then
        {
            echo
            echo "## Build Artifacts ($project)"
            echo "\`\`\`"
            find "$source" -type f \( -path "*/build/*" -o -path "*/target/*" \) -ls
            echo "\`\`\`"
        } >> "$REPORT_DIR/build-verification.md"
    fi
}

# Verify build environment
verify_build_env() {
    local project=$1
    local dest="$DEST_DIR/$project"
    
    info "Verifying build environment for: $project"
    
    {
        echo "# Build Environment Verification: $project"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
        echo "## Environment Status"
        
        # Check build system
        if [ -f "$dest/Makefile" ]; then
            echo "- Build System: Make"
            make -C "$dest" -n clean || warn "Make verification failed"
        elif [ -f "$dest/build.gradle" ]; then
            echo "- Build System: Gradle"
            (cd "$dest" && ./gradlew tasks) || warn "Gradle verification failed"
        elif [ -f "$dest/pom.xml" ]; then
            echo "- Build System: Maven"
            (cd "$dest" && mvn validate) || warn "Maven verification failed"
        elif [ -f "$dest/package.json" ]; then
            echo "- Build System: NPM"
            (cd "$dest" && npm list) || warn "NPM verification failed"
        fi
        
        # Check dependencies
        echo
        echo "## Dependencies"
        if [ -f "$dest/requirements.txt" ]; then
            echo "\`\`\`"
            cat "$dest/requirements.txt"
            echo "\`\`\`"
        fi
        
        # Check build artifacts
        echo
        echo "## Build Artifacts"
        echo "\`\`\`"
        find "$dest" -type f \( -name "*.o" -o -name "*.a" -o -name "*.so" -o -name "*.jar" \)
        echo "\`\`\`"
    } >> "$REPORT_DIR/environment-check.md"
}

# Validate project migration
validate_project() {
    local project=$1
    local source="$SOURCE_DIR/$project"
    local dest="$DEST_DIR/$project"
    local errors=0

    info "Validating project migration: $project"

    # Verify file count
    local source_files=$(find "$source" -type f | wc -l)
    local dest_files=$(find "$dest" -type f | wc -l)
    if [ "$source_files" -ne "$dest_files" ]; then
        error "File count mismatch for $project"
        ((errors++))
    fi

    # Verify git repository
    if [ -d "$source/.git" ]; then
        if ! [ -d "$dest/.git" ]; then
            error "Git repository not transferred for $project"
            ((errors++))
        else
            # Verify git history
            local source_commits=$(cd "$source" && git rev-list --count HEAD)
            local dest_commits=$(cd "$dest" && git rev-list --count HEAD)
            if [ "$source_commits" -ne "$dest_commits" ]; then
                error "Git history mismatch for $project"
                ((errors++))
            fi
        fi
    fi

    # Verify build artifacts
    if [ -d "$source/build" ]; then
        if ! [ -d "$dest/build" ]; then
            warn "Build artifacts not transferred for $project"
        fi
    fi

    return $errors
}

# Main execution
main() {
    info "Starting development project migration..."
    local errors=0

    setup_migration

    # Initialize documentation files
    {
        echo "# Project Transfer Log"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
    } > "$REPORT_DIR/project-transfer-log.md"

    {
        echo "# VCS Preservation Report"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
    } > "$REPORT_DIR/vcs-preservation.md"

    {
        echo "# Build Verification Report"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
    } > "$REPORT_DIR/build-verification.md"

    {
        echo "# Environment Check Report"
        echo "Generated: $(date -u --iso-8601=seconds)"
        echo
    } > "$REPORT_DIR/environment-check.md"

    # Process each project
    for project in "${PROJECTS[@]}"; do
        info "Processing project: $project"
        migrate_project "$project" || ((errors++))
        verify_build_env "$project" || ((errors++))
        validate_project "$project" || ((errors++))
    done

    if [[ $errors -eq 0 ]]; then
        info "Development project migration completed successfully!"
        return 0
    else
        error "Migration completed with $errors error(s)"
        return 1
    fi
}

# Execute main function
main "$@"

