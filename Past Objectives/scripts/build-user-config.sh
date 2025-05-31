#!/bin/bash
#
# build-user-config.sh - LFS Build User Configuration Management
# LFS Chapter 4 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Manages and validates the LFS build user configuration
# including startup files and permissions.

set -e

# Source build environment configuration
source "$(dirname "$0")/../config/build-environment.conf"

# Color output setup
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

validate_user_exists() {
    if ! id -u "$LFS_USER" >/dev/null 2>&1; then
        log_error "LFS user $LFS_USER does not exist"
        return 1
    fi
    log_info "LFS user exists: $LFS_USER"
}

validate_environment_vars() {
    local required_vars=(
        "LFS"
        "LFS_TGT"
        "PATH"
        "CONFIG_SITE"
        "LC_ALL"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required environment variable $var is not set"
            return 1
        fi
    done
    log_info "All required environment variables are set"
}

create_bash_profile() {
    local profile_content='exec env -i HOME=$HOME TERM=$TERM PS1='\''[\u@\h \W]\$ '\'' /bin/bash'
    
    echo "$profile_content" > "$LFS_HOME/.bash_profile"
    chown "$LFS_USER:$LFS_GROUP" "$LFS_HOME/.bash_profile"
    chmod 644 "$LFS_HOME/.bash_profile"
    log_info "Created .bash_profile"
}

create_bashrc() {
    cat > "$LFS_HOME/.bashrc" << 'EOF'
set +h
umask 022
LFS=/mnt/lfs
LC_ALL=POSIX
LFS_TGT=$(uname -m)-lfs-linux-gnu
PATH=/usr/bin
if [ ! -L /bin ]; then PATH=/bin:$PATH; fi
PATH=$LFS/tools/bin:$PATH
CONFIG_SITE=$LFS/usr/share/config.site
export LFS LC_ALL LFS_TGT PATH CONFIG_SITE
EOF
    
    chown "$LFS_USER:$LFS_GROUP" "$LFS_HOME/.bashrc"
    chmod 644 "$LFS_HOME/.bashrc"
    log_info "Created .bashrc"
}

validate_startup_files() {
    local files=(".bash_profile" ".bashrc")
    local errors=0
    
    for file in "${files[@]}"; do
        local full_path="$LFS_HOME/$file"
        
        # Check file exists
        if [ ! -f "$full_path" ]; then
            log_error "Startup file missing: $file"
            ((errors++))
            continue
        }
        
        # Check permissions
        local perms=$(stat -c %a "$full_path")
        if [ "$perms" != "644" ]; then
            log_error "Incorrect permissions on $file: $perms (should be 644)"
            ((errors++))
        fi
        
        # Check ownership
        local owner=$(stat -c %U:%G "$full_path")
        if [ "$owner" != "$LFS_USER:$LFS_GROUP" ]; then
            log_error "Incorrect ownership on $file: $owner (should be $LFS_USER:$LFS_GROUP)"
            ((errors++))
        fi
    done
    
    if [ "$errors" -eq 0 ]; then
        log_info "All startup files validated successfully"
        return 0
    fi
    return 1
}

validate_home_permissions() {
    local home_perms=$(stat -c %a "$LFS_HOME")
    if [ "$home_perms" != "755" ]; then
        log_error "Incorrect home directory permissions: $home_perms (should be 755)"
        return 1
    fi
    
    local home_owner=$(stat -c %U:%G "$LFS_HOME")
    if [ "$home_owner" != "$LFS_USER:$LFS_GROUP" ]; then
        log_error "Incorrect home directory ownership: $home_owner"
        return 1
    }
    
    log_info "Home directory permissions validated"
    return 0
}

test_user_environment() {
    log_info "Testing user environment..."
    
    # Test environment as LFS user
    su - "$LFS_USER" -c 'env | grep -q "^LFS=" && \
                         env | grep -q "^LFS_TGT=" && \
                         env | grep -q "^PATH=" && \
                         echo "Environment test successful"' || {
        log_error "Environment test failed"
        return 1
    }
    
    log_info "User environment tested successfully"
}

main() {
    log_info "Starting build user configuration validation..."
    
    if [ "$(id -u)" != "0" ]; then
        log_error "This script must be run as root"
        exit 1
    }
    
    local errors=0
    
    # Run all validation steps
    validate_user_exists || ((errors++))
    validate_environment_vars || ((errors++))
    
    # Create/update configuration files
    create_bash_profile
    create_bashrc
    
    # Validate configuration
    validate_startup_files || ((errors++))
    validate_home_permissions || ((errors++))
    test_user_environment || ((errors++))
    
    if [ "$errors" -eq 0 ]; then
        log_info "Build user configuration completed successfully"
        return 0
    else
        log_error "Build user configuration failed with $errors errors"
        return 1
    fi
}

main "$@"

