#!/bin/bash
#===============================================================================
# LFS/BLFS Build Scripts Wrapper System - Core Configuration
# Version: 0.1.0
# Description: Core configuration settings for the wrapper system
#===============================================================================

#===============================================================================
# System-wide Configuration
#===============================================================================

# System version and identification
readonly SYSTEM_VERSION="0.1.0"
readonly SYSTEM_NAME="LFS/BLFS Build Scripts Wrapper"
readonly SYSTEM_ID="lfs-wrapper"

# Base directories (can be overridden by environment variables)
export WRAPPER_BASE_DIR="${WRAPPER_BASE_DIR:-/mnt/host/WARP_CURRENT}"
readonly WRAPPER_BASE_DIR
export BASE_DIR="${WRAPPER_BASE_DIR}"
readonly BASE_DIR

# Critical system directories
export LOGS_DIR="${BASE_DIR}/logs"
export ARTIFACTS_DIR="${BASE_DIR}/artifacts"
export TEMP_DIR="${BASE_DIR}/temp"
export CONFIG_DIR="${BASE_DIR}/config"
export SCRIPTS_DIR="${BASE_DIR}/scripts"
readonly LOGS_DIR ARTIFACTS_DIR TEMP_DIR CONFIG_DIR SCRIPTS_DIR

# Script directories
export LFS_SCRIPTS_DIR="${SCRIPTS_DIR}/lfs"
export BLFS_SCRIPTS_DIR="${SCRIPTS_DIR}/blfs"
readonly LFS_SCRIPTS_DIR BLFS_SCRIPTS_DIR

# Build configuration
export MAX_JOBS="$(nproc)"
readonly MAX_JOBS
export DEFAULT_MAKEFLAGS="-j${MAX_JOBS}"
readonly DEFAULT_MAKEFLAGS

# Default timeout values (in seconds)
export DEFAULT_COMMAND_TIMEOUT=3600
export DEFAULT_BUILD_TIMEOUT=7200
export DEFAULT_SCRIPT_TIMEOUT=1800
readonly DEFAULT_COMMAND_TIMEOUT DEFAULT_BUILD_TIMEOUT DEFAULT_SCRIPT_TIMEOUT

#===============================================================================
# Logging Configuration
#===============================================================================

# Log levels (0=DEBUG, 1=INFO, 2=WARN, 3=ERROR)
export DEFAULT_LOG_LEVEL=1
readonly DEFAULT_LOG_LEVEL

# Log rotation settings
export LOG_MAX_SIZE=100M
export LOG_KEEP_DAYS=30
export LOG_COMPRESS=true
readonly LOG_MAX_SIZE LOG_KEEP_DAYS LOG_COMPRESS

# Build verification settings
export VERIFY_CHECKSUMS=true
export VERIFY_SIGNATURES=true
export VERIFY_DEPENDENCIES=true
readonly VERIFY_CHECKSUMS VERIFY_SIGNATURES VERIFY_DEPENDENCIES

# Log file paths (relative to LOGS_DIR)
readonly LOG_PATHS=(
    "system/wrapper.log"
    "system/discovery.log"
    "build/current.log"
    "build/history.log"
    "error/wrapper.log"
    "error/build.log"
)

# Log format templates
readonly LOG_FORMAT_SYSTEM="[%datetime%] %level%: %message%"
readonly LOG_FORMAT_BUILD="[%datetime%] [%phase%] %level%: %message%"
readonly LOG_FORMAT_ERROR="[%datetime%] %level% (%errno%): %message%"

#===============================================================================
# Build Environment Settings
#===============================================================================

# Build environment variables
export LFS="/mnt/lfs"
export LFS_TGT="$(uname -m)-lfs-linux-gnu"
export PATH="/tools/bin:/bin:/usr/bin"
export LC_ALL=POSIX
export LFS_TEST_SUITE=1

# Build flags and settings
export DEFAULT_CFLAGS="-O2 -pipe"
export DEFAULT_CXXFLAGS="-O2 -pipe"
readonly DEFAULT_CFLAGS DEFAULT_CXXFLAGS

# Build validation settings
export BUILD_VALIDATION=true
export CHECKSUM_VALIDATION=true
export SIGNATURE_VALIDATION=true
readonly BUILD_VALIDATION CHECKSUM_VALIDATION SIGNATURE_VALIDATION

#===============================================================================
# Script Discovery Settings
#===============================================================================

# Script search paths (relative to BASE_DIR)
readonly SCRIPT_SEARCH_PATHS=(
    "scripts/lfs"
    "scripts/blfs"
    "scripts/custom"
    "scripts/templates"
)

# Script pattern matching
readonly SCRIPT_PATTERNS=(
    "*.sh"
    "*.bash"
    "build-*.sh"
    "install-*.sh"
)

# Script metadata parsing
readonly METADATA_REQUIRED=(
    "NAME"
    "VERSION"
    "DESCRIPTION"
)

# Script categorization
readonly SCRIPT_CATEGORIES=(
    "core"
    "system"
    "network"
    "xorg"
    "desktop"
    "development"
    "utilities"
)

#===============================================================================
# Default Build Options
#===============================================================================

# Build modes
readonly BUILD_MODE_NORMAL="normal"
readonly BUILD_MODE_QUICK="quick"
readonly BUILD_MODE_VERBOSE="verbose"
readonly BUILD_MODE_TEST="test"
readonly DEFAULT_BUILD_MODE="${BUILD_MODE_NORMAL}"

# Build phases
readonly BUILD_PHASES=(
    "prepare"
    "configure"
    "build"
    "test"
    "install"
    "post-install"
    "cleanup"
)

# Default build options
declare -a DEFAULT_BUILD_OPTS
DEFAULT_BUILD_OPTS=(
    "--enable-shared"
    "--prefix=/usr"
    "--sysconfdir=/etc"
    "--localstatedir=/var"
)
export DEFAULT_BUILD_OPTS
readonly DEFAULT_BUILD_OPTS

# Test suite settings
declare -a DEFAULT_TEST_OPTS
DEFAULT_TEST_OPTS=(
    "--enable-tests"
    "--enable-checking"
    "test_suite=full"
)
export DEFAULT_TEST_OPTS
readonly DEFAULT_TEST_OPTS

#===============================================================================
# Error Handling Settings
#===============================================================================

# Error recovery options
readonly MAX_RETRIES=3
readonly RETRY_DELAY=5
readonly AUTO_RECOVERY=true

# Error notification settings
readonly NOTIFY_ON_ERROR=true
readonly NOTIFY_ON_COMPLETION=true
readonly NOTIFICATION_METHOD="log"  # Options: log, email, webhook

#===============================================================================
# Resource Management
#===============================================================================

# Disk space requirements (in GB)
readonly MIN_DISK_SPACE=50
readonly MIN_TEMP_SPACE=10
readonly MIN_BUILD_SPACE=30

# Memory requirements (in GB)
readonly MIN_MEMORY=4
readonly MIN_SWAP=8

# Process limits
readonly MAX_PROCESSES=10000
readonly MAX_OPEN_FILES=4096
readonly MAX_FILE_SIZE=10G

#===============================================================================
# Security Settings
#===============================================================================

# Permission defaults
declare -r DEFAULT_DIR_MODE=0755
declare -r DEFAULT_FILE_MODE=0644
declare -r DEFAULT_SCRIPT_MODE=0755
export DEFAULT_DIR_MODE DEFAULT_FILE_MODE DEFAULT_SCRIPT_MODE

# User and group settings
declare -r BUILD_USER="lfs"
declare -r BUILD_GROUP="lfs"
export BUILD_USER BUILD_GROUP

# Validation settings
declare -r VALIDATE_SCRIPTS=true
declare -r VALIDATE_CONFIGS=true
declare -r VALIDATE_CHECKSUMS=true
export VALIDATE_SCRIPTS VALIDATE_CONFIGS VALIDATE_CHECKSUMS

