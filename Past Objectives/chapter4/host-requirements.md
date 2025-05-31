# LFS Chapter 4: Host System Requirements
Version: LFS 12.3
Last Updated: 2025-05-31T15:03:28Z

## Overview
This document outlines the host system requirements for building Linux From Scratch 12.3. These requirements must be met to ensure a successful build process.

## System Requirements

### Hardware Requirements
- **CPU:** x86_64 architecture
- **Memory:** 
  - Minimum: 4GB RAM
  - Recommended: 8GB RAM or more
- **Storage:**
  - Minimum free space: 8GB
  - Recommended free space: 12GB
  - Build partition type: ext4/xfs recommended
  - Required mount options: acl,user_xattr

### Operating System Requirements
- **Linux Distribution:** Any recent Linux distribution
- **Kernel Version:** 4.14 or newer
- **System Architecture:** x86_64 (64-bit)
- **File System:** Supporting symbolic links and device files

## Required Tools and Versions

### Core Build Tools
| Package    | Minimum Version | Verification Command | Common Issues/Solutions |
|------------|----------------|---------------------|------------------------|
| bash       | 3.2           | `bash --version`    | Shell compatibility issues - use `/bin/bash` explicitly |
| binutils   | 2.13.1        | `ld --version`      | Version mismatch - install development version |
| coreutils  | 6.9           | `chown --version`   | GNU version required - avoid BSD variants |
| gcc        | 5.1           | `gcc --version`     | C++11 support needed - upgrade if older |
| glibc      | 2.17          | `ldd --version`     | ABI compatibility - check host headers |
| grep       | 2.5.1a        | `grep --version`    | PCRE support recommended |
| make       | 4.0           | `make --version`    | GNU Make required |
| sed        | 4.1.5         | `sed --version`     | GNU sed required |

### Development Tools
| Package    | Minimum Version | Purpose |
|------------|----------------|----------|
| m4         | 1.4.10        | Macro processor for build scripts |
| perl       | 5.8.8         | Build scripts and configurations |
| python     | 3.4           | Build scripts and utilities |
| texinfo    | 4.7           | Documentation generation |

### System Utilities
| Package    | Minimum Version | Purpose |
|------------|----------------|----------|
| bison      | 2.7           | Parser generation |
| diffutils  | 2.8.1         | Source comparisons |
| findutils  | 4.2.31        | File operations |
| gawk       | 4.0.1         | Text processing |
| patch      | 2.5.4         | Source modifications |
| tar        | 1.22          | Archive management |

### Version Control
| Package    | Minimum Version | Purpose |
|------------|----------------|----------|
| git        | 2.14.1        | Source management |
| wget/curl  | Latest        | Source downloads |

## File System Requirements

### Mount Points
```
/dev       - Device files (devtmpfs recommended)
/proc      - Process information
/sys       - System information
/run       - Runtime data
```

### Permissions
- Build directory: owner read/write/execute
- Source directories: owner read/write
- Tools directories: owner read/write/execute

## Resource Requirements

### Disk Space Allocation
- **Source Code:** ~400MB
- **Build Tools:** ~4GB
- **Final System:** ~3GB
- **Temporary Space:** ~1GB

### Memory Usage
- **Minimal Build:** 4GB RAM
- **Parallel Build:** 1GB + 2GB per job
- **Swap Space:** 2GB minimum

## Build Environment Variables
```bash
export LFS=/mnt/lfs
export LFS_TGT=$(uname -m)-lfs-linux-gnu
export PATH=/tools/bin:/bin:/usr/bin
```

## Common Issues and Solutions

### Version Conflicts
- **Issue:** Multiple tool versions installed
- **Solution:** Use PATH to prioritize correct versions

### Permission Problems
- **Issue:** Unable to write to build directory
- **Solution:** Check ownership and mount options

### Resource Constraints
- **Issue:** Out of memory during build
- **Solution:** Reduce parallel jobs or increase swap

## Additional Notes
- Regular backups recommended during build
- Keep detailed build logs
- Verify checksum of all downloaded sources
- Follow LFS book instructions precisely

