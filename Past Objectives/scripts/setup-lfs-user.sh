#!/bin/bash
#
# setup-lfs-user.sh - LFS Build User Setup
# LFS Chapter 4 Implementation
# Version: 1.0
# Date: 2025-05-31
#
# Description: Creates and configures the LFS build user account
# with proper permissions and environment settings.

set -e

# Configuration
LFS_USER="lfs"
LFS_GROUP="lfs"
LFS_HOME="/home/$LFS_USER"
LFS_BASHRC="$LFS_HOME/.bashrc"
LFS_PROFILE="$LFS_HOME/.bash_profile"

# Color output setup
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

create_lfs_user() {
    if ! getent group $LFS_GROUP >/dev/null; then
        groupadd $LFS_GROUP
        log_info "Created group: $LFS_GROUP"
    fi
    
    if ! id -u $LFS_USER >/dev/null 2>&1; then
        useradd -s /bin/bash -g $LFS_GROUP -m -k /dev/null $LFS_USER
        log_info "Created user: $LFS_USER"
    fi
}

setup_environment() {
    # Create .bash_profile
    cat > "$LFS_PROFILE" << "EOF"
exec env -i HOME=$HOME TERM=$TERM PS1='\u:\w\$ ' /bin/bash
EOF
    
    # Create .bashrc
    cat > "$LFS_BASHRC" << "EOF"
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
    
    # Set ownership
    chown $LFS_USER:$LFS_GROUP "$LFS_PROFILE" "$LFS_BASHRC"
    log_info "Environment files created and configured"
}

verify_setup() {
    # Verify user exists
    if ! id -u $LFS_USER >/dev/null 2>&1; then
        log_error "User $LFS_USER was not created successfully"
        return 1
    fi
    
    # Verify group exists
    if ! getent group $LFS_GROUP >/dev/null; then
        log_error "Group $LFS_GROUP was not created successfully"
        return 1
    fi
    
    # Verify environment files
    for file in "$LFS_PROFILE" "$LFS_BASHRC"; do
        if [ ! -f "$file" ]; then
            log_error "Environment file $file is missing"
            return 1
        fi
    done
    
    log_info "User setup verification completed successfully"
    return 0
}

main() {
    log_info "Starting LFS user setup..."
    
    if [ "$(id -u)" != "0" ]; then
        log_error "This script must be run as root"
        exit 1
    fi
    
    create_lfs_user
    setup_environment
    verify_setup
    
    log_info "LFS user setup completed successfully"
}

main "$@"

