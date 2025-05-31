#!/bin/bash

# Build Wrapper Main Script
# Version: 1.0
# Last Updated: 2025-05-31T15:03:28Z
# Purpose: Main entry point for LFS/BLFS build script wrapper system

# Exit on any error
set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load supporting modules
source "$SCRIPT_DIR/config-manager.sh"
source "$SCRIPT_DIR/script-registry.sh"
source "$SCRIPT_DIR/error-handler.sh"
source "$SCRIPT_DIR/logging-system.sh"
source "$SCRIPT_DIR/progress-tracker.sh"

# Default configuration
CONFIG_FILE="/etc/build-wrapper/config.yaml"
LOG_DIR="/var/log/build-wrapper"
VERBOSE=0
DEBUG=0

# Command line interface
usage() {
    cat << EOF
Usage: build-wrapper <command> [options] <target>

Commands:
  build     Execute build script
  status    Check build status
  clean     Clean build artifacts
  resume    Resume interrupted build
  validate  Verify build environment

Global Options:
  --config=<file>    Configuration file
  --verbose          Verbose output
  --debug           Debug mode
  --help            Show this help

Build Options:
  --parallel=<n>     Set parallel jobs
  --test            Run test suite
  --no-verify       Skip verification
  --force           Force rebuild

Status Options:
  --json            JSON output format
  --verbose         Detailed status

Clean Options:
  --all             Clean all packages
  --dry-run         Show what would be cleaned

Resume Options:
  --from=<step>     Resume from specific step
  --verify          Verify before resume

Validate Options:
  --fix             Attempt to fix issues
  --report          Generate report
EOF
}

# Parse command line arguments
parse_args() {
    local command=$1
    shift

    case $command in
        build)
            handle_build_command "$@"
            ;;
        status)
            handle_status_command "$@"
            ;;
        clean)
            handle_clean_command "$@"
            ;;
        resume)
            handle_resume_command "$@"
            ;;
        validate)
            handle_validate_command "$@"
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Build command handler
handle_build_command() {
    local parallel=4
    local run_tests=0
    local verify=1
    local force=0
    local target=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --parallel=*)
                parallel="${1#*=}"
                ;;
            --test)
                run_tests=1
                ;;
            --no-verify)
                verify=0
                ;;
            --force)
                force=1
                ;;
            -*)
                error "Unknown option: $1"
                exit 1
                ;;
            *)
                target="$1"
                ;;
        esac
        shift
    done
    
    if [ -z "$target" ]; then
        error "No build target specified"
        exit 1
    fi
    
    info "Starting build: $target"
    start_build "$target" $parallel $run_tests $verify $force
}

# Status command handler
handle_status_command() {
    local json=0
    local verbose=0
    local target=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --json)
                json=1
                ;;
            --verbose)
                verbose=1
                ;;
            -*)
                error "Unknown option: $1"
                exit 1
                ;;
            *)
                target="$1"
                ;;
        esac
        shift
    done
    
    get_status "$target" $json $verbose
}

# Clean command handler
handle_clean_command() {
    local all=0
    local dry_run=0
    local target=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                all=1
                ;;
            --dry-run)
                dry_run=1
                ;;
            -*)
                error "Unknown option: $1"
                exit 1
                ;;
            *)
                target="$1"
                ;;
        esac
        shift
    done
    
    clean_build "$target" $all $dry_run
}

# Resume command handler
handle_resume_command() {
    local from_step=""
    local verify=0
    local target=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --from=*)
                from_step="${1#*=}"
                ;;
            --verify)
                verify=1
                ;;
            -*)
                error "Unknown option: $1"
                exit 1
                ;;
            *)
                target="$1"
                ;;
        esac
        shift
    done
    
    if [ -z "$target" ]; then
        error "No target specified for resume"
        exit 1
    fi
    
    resume_build "$target" "$from_step" $verify
}

# Validate command handler
handle_validate_command() {
    local fix=0
    local report=0
    local checks=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --fix)
                fix=1
                ;;
            --report)
                report=1
                ;;
            -*)
                error "Unknown option: $1"
                exit 1
                ;;
            *)
                checks="$1"
                ;;
        esac
        shift
    done
    
    validate_environment "$checks" $fix $report
}

# Initialize wrapper system
init_wrapper() {
    # Load configuration
    load_config "$CONFIG_FILE"
    
    # Initialize logging
    init_logging "$LOG_DIR"
    
    # Initialize script registry
    init_registry
    
    # Initialize progress tracking
    init_progress_tracking
    
    # Validate environment
    validate_environment "" 0 0
}

# Main execution
main() {
    if [ $# -eq 0 ]; then
        usage
        exit 1
    fi
    
    init_wrapper
    parse_args "$@"
}

# Execute main function
main "$@"

