#!/bin/bash
#
# Progress Tracking System
# Tracks and reports build progress for LFS/BLFS scripts
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
PROGRESS_DIR="/var/run/lfs-wrapper/progress"
mkdir -p "$PROGRESS_DIR"

# Progress tracking functions
update_progress_marker() {
    local script_id="$1"
    local current="$2"
    local total="$3"
    local stage="$4"
    
    local progress_file="${PROGRESS_DIR}/${script_id}.marker"
    
    # Calculate percentage
    local percentage
    percentage=$(( (current * 100) / total ))
    
    # Update progress file
    {
        echo "CURRENT=${current}"
        echo "TOTAL=${total}"
        echo "PERCENTAGE=${percentage}"
        echo "STAGE=${stage}"
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
    } > "$progress_file"
    
    log_debug "Updated progress for ${script_id}: ${percentage}% (${stage})"
}

get_progress() {
    local script_id="$1"
    local progress_file="${PROGRESS_DIR}/${script_id}.marker"
    
    if [ -f "$progress_file" ]; then
        cat "$progress_file"
    else
        echo "No progress data available for ${script_id}"
        return 1
    fi
}

clear_progress() {
    local script_id="$1"
    rm -f "${PROGRESS_DIR}/${script_id}.marker"
}

# Main entry point
main() {
    if [ "$#" -lt 4 ]; then
        log_error "Usage: $0 <script_id> <current> <total> <stage>"
        exit 1
    fi
    
    update_progress_marker "$@"
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

