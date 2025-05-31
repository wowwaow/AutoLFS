#!/bin/bash
#
# LFS Environment Setup Script
# Sets up the basic environment for LFS building

# LFS environment variables
export LFS=/mnt/lfs
export LFS_TGT=$(uname -m)-lfs-linux-gnu
export PATH=/tools/bin:/bin:/usr/bin

# Script metadata
SCRIPT_VERSION="1.0"
SCRIPT_PHASE="configuration"
SCRIPT_DEPENDENCIES=""

# Error handling
set -e
trap 'echo "Error on line $LINENO"' ERR

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Create LFS directory structure
create_directories() {
    log "Creating LFS directory structure"
    mkdir -p $LFS/{sources,tools,build-logs}
    mkdir -p $LFS/tools/{bin,lib,include}
}

# Set up permissions
setup_permissions() {
    log "Setting up directory permissions"
    chown -R root:root $LFS/tools
    chmod -R u+w $LFS/tools
}

# Create lfs user
create_lfs_user() {
    log "Creating lfs user"
    groupadd lfs || true
    useradd -s /bin/bash -g lfs -m -k /dev/null lfs || true
    chown -R lfs:lfs $LFS
}

# Configure environment
configure_environment() {
    log "Configuring build environment"
    cat > /home/lfs/.bash_profile << "EOF"
exec env -i HOME=/home/lfs TERM=$TERM PS1='\u:\w\$ ' /bin/bash
EOF

    cat > /home/lfs/.bashrc << "EOF"
set +h
umask 022
LFS=/mnt/lfs
LC_ALL=POSIX
LFS_TGT=$(uname -m)-lfs-linux-gnu
PATH=/tools/bin:/bin:/usr/bin
export LFS LC_ALL LFS_TGT PATH
EOF
}

# Verify setup
verify_setup() {
    log "Verifying environment setup"
    if [ ! -d "$LFS" ]; then
        log "ERROR: LFS directory not created"
        exit 1
    fi
    if ! id -u lfs >/dev/null 2>&1; then
        log "ERROR: lfs user not created"
        exit 1
    fi
}

# Main function
main() {
    log "Starting LFS environment setup"
    create_directories
    setup_permissions
    create_lfs_user
    configure_environment
    verify_setup
    log "LFS environment setup completed"
}

# Execute main function
main "$@"

