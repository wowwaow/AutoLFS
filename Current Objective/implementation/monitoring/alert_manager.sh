#!/bin/bash
#
# Alert Management System
# Handles alerts and notifications for the build system
#

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "${SCRIPT_DIR}/../../lib/core_functions.sh"

# Configuration
ALERTS_DIR="/var/run/lfs-wrapper/alerts"
ALERT_LOG="${ALERTS_DIR}/alert.log"
mkdir -p "$ALERTS_DIR"

# Alert levels and their numeric values
declare -r ALERT_INFO=0
declare -r ALERT_WARNING=1
declare -r ALERT_ERROR=2
declare -r ALERT_CRITICAL=3

# Alert colors for terminal output
declare -r COLOR_INFO="\033[0;34m"    # Blue
declare -r COLOR_WARNING="\033[1;33m"  # Yellow
declare -r COLOR_ERROR="\033[0;31m"    # Red
declare -r COLOR_CRITICAL="\033[1;31m" # Bright Red
declare -r COLOR_RESET="\033[0m"

# Create a new alert
create_alert() {
    local script_id="$1"
    local level="$2"
    local message="$3"
    local alert_file="${ALERTS_DIR}/${script_id}.alert"
    
    # Generate alert entry
    {
        echo "TIMESTAMP=$(date -u +%Y%m%d%H%M%S)"
        echo "LEVEL=${level}"
        echo "MESSAGE=${message}"
    } > "$alert_file"
    
    # Log alert
    log_alert "$script_id" "$level" "$message"
    
    # Process alert based on level
    case "$level" in
        "$ALERT_CRITICAL")
            handle_critical_alert "$script_id" "$message"
            ;;
        "$ALERT_ERROR")
            handle_error_alert "$script_id" "$message"
            ;;
        "$ALERT_WARNING")
            handle_warning_alert "$script_id" "$message"
            ;;
        "$ALERT_INFO")
            handle_info_alert "$script_id" "$message"
            ;;
    esac
}

# Log alert to the alert log
log_alert() {
    local script_id="$1"
    local level="$2"
    local message="$3"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Format the alert message
    local formatted_message
    formatted_message="[${timestamp}] ${script_id}: [${level}] ${message}"
    
    # Log to alert log file
    echo "$formatted_message" >> "$ALERT_LOG"
    
    # Display colored output to terminal if it's interactive
    if [ -t 1 ]; then
        local color
        case "$level" in
            "$ALERT_CRITICAL") color="$COLOR_CRITICAL" ;;
            "$ALERT_ERROR") color="$COLOR_ERROR" ;;
            "$ALERT_WARNING") color="$COLOR_WARNING" ;;
            "$ALERT_INFO") color="$COLOR_INFO" ;;
            *) color="$COLOR_RESET" ;;
        esac
        echo -e "${color}${formatted_message}${COLOR_RESET}"
    fi
}

# Handle different alert levels
handle_critical_alert() {
    local script_id="$1"
    local message="$2"
    
    # Log to system log
    logger -p user.crit -t "lfs-wrapper" "CRITICAL ALERT - ${script_id}: ${message}"
    
    # Send email notification if configured
    if [ -x "$(command -v mail)" ] && [ -n "${ADMIN_EMAIL:-}" ]; then
        echo "Critical Alert - ${script_id}: ${message}" | \
            mail -s "CRITICAL: LFS Build Alert" "$ADMIN_EMAIL"
    fi
    
    # Create status file for monitoring
    echo "CRITICAL" > "${ALERTS_DIR}/${script_id}.status"
}

handle_error_alert() {
    local script_id="$1"
    local message="$2"
    
    # Log to system log
    logger -p user.err -t "lfs-wrapper" "ERROR ALERT - ${script_id}: ${message}"
    
    # Create status file for monitoring
    echo "ERROR" > "${ALERTS_DIR}/${script_id}.status"
}

handle_warning_alert() {
    local script_id="$1"
    local message="$2"
    
    # Log to system log
    logger -p user.warning -t "lfs-wrapper" "WARNING ALERT - ${script_id}: ${message}"
    
    # Create status file for monitoring
    echo "WARNING" > "${ALERTS_DIR}/${script_id}.status"
}

handle_info_alert() {
    local script_id="$1"
    local message="$2"
    
    # Log to system log
    logger -p user.info -t "lfs-wrapper" "INFO ALERT - ${script_id}: ${message}"
    
    # Create status file for monitoring
    echo "INFO" > "${ALERTS_DIR}/${script_id}.status"
}

# Clear alerts for a script
clear_alerts() {
    local script_id="$1"
    rm -f "${ALERTS_DIR}/${script_id}."*
}

# Get current alert status
get_alert_status() {
    local script_id="$1"
    local status_file="${ALERTS_DIR}/${script_id}.status"
    
    if [ -f "$status_file" ]; then
        cat "$status_file"
    else
        echo "NO_ALERTS"
    fi
}

# Main entry point
main() {
    if [ "$#" -lt 3 ]; then
        log_error "Usage: $0 <script_id> <level> <message>"
        exit 1
    fi
    
    create_alert "$@"
}

# Execute main function if not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

