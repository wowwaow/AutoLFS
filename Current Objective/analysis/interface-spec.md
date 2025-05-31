# Build Wrapper Interface Specification
Version: 1.0
Last Updated: 2025-05-31T15:03:28Z

## Command Line Interface

### Primary Command Structure
```bash
build-wrapper <command> [options] <target>
```

### Commands
1. **build**
   - Purpose: Execute build script
   - Usage: `build-wrapper build [options] <package>`
   - Options:
     * `--parallel=<n>` - Set parallel jobs
     * `--test` - Run test suite
     * `--no-verify` - Skip verification
     * `--force` - Force rebuild

2. **status**
   - Purpose: Check build status
   - Usage: `build-wrapper status [package]`
   - Output: Current build state
   - Options:
     * `--json` - JSON output
     * `--verbose` - Detailed status

3. **clean**
   - Purpose: Clean build artifacts
   - Usage: `build-wrapper clean [package]`
   - Options:
     * `--all` - Clean all packages
     * `--dry-run` - Show what would be cleaned

4. **resume**
   - Purpose: Resume interrupted build
   - Usage: `build-wrapper resume [package]`
   - Options:
     * `--from=<step>` - Resume from step
     * `--verify` - Verify before resume

5. **validate**
   - Purpose: Verify build environment
   - Usage: `build-wrapper validate [checks]`
   - Options:
     * `--fix` - Attempt to fix issues
     * `--report` - Generate report

## Configuration Interface

### Configuration File Format
```yaml
build_wrapper:
  # Global Settings
  global:
    parallel_jobs: 4
    log_level: info
    work_dir: /mnt/lfs
    
  # Build Settings
  build:
    test_suite: enabled
    verification: enabled
    keep_work: false
    
  # Environment Settings
  environment:
    build_root: /mnt/lfs
    tools_dir: /tools
    sources_dir: /sources
    
  # Logging Settings
  logging:
    file: build.log
    format: detailed
    rotate: true
    max_size: 100M
    
  # Validation Settings
  validation:
    check_space: true
    verify_checksums: true
    run_tests: true
```

### Environment Variables
```bash
# Core Variables
LFS=/mnt/lfs
LFS_TGT=$(uname -m)-lfs-linux-gnu
BUILD_WRAPPER_CONFIG=/etc/build-wrapper/config.yaml

# Build Control
BUILD_WRAPPER_JOBS=4
BUILD_WRAPPER_VERBOSE=0
BUILD_WRAPPER_DEBUG=0

# Logging Control
BUILD_WRAPPER_LOG_LEVEL=info
BUILD_WRAPPER_LOG_FILE=build.log
```

## API Interface

### Core Functions
```bash
# Build Management
start_build() {
    # Initialize build process
}

stop_build() {
    # Stop build process
}

resume_build() {
    # Resume build process
}

# Status Management
get_status() {
    # Return build status
}

update_status() {
    # Update build status
}

# Error Handling
handle_error() {
    # Process error condition
}

# Logging
log_message() {
    # Log message
}
```

### Hook Points
```bash
# Pre-build hooks
pre_build() {
    # Pre-build actions
}

# Post-build hooks
post_build() {
    # Post-build actions
}

# Error hooks
on_error() {
    # Error handling actions
}

# Validation hooks
validate_step() {
    # Validation actions
}
```

## Progress Interface

### Progress Reporting
```bash
# Progress update format
{
    "package": "binutils",
    "phase": "configure",
    "progress": 45,
    "status": "running",
    "time_elapsed": "00:05:23",
    "time_remaining": "00:06:40"
}
```

### Status Codes
1. **Build Status**
   - 0: Success
   - 1: Error
   - 2: Warning
   - 3: Skipped
   - 4: Pending

2. **Phase Status**
   - PREP: Preparation
   - CONF: Configuration
   - BUILD: Building
   - TEST: Testing
   - INST: Installation
   - CLEAN: Cleanup

## Error Interface

### Error Categories
1. **Environment Errors**
   - ENV_001: Invalid directory
   - ENV_002: Missing tool
   - ENV_003: Permission denied

2. **Build Errors**
   - BUILD_001: Configure failed
   - BUILD_002: Compilation failed
   - BUILD_003: Test failed

3. **System Errors**
   - SYS_001: Out of space
   - SYS_002: Out of memory
   - SYS_003: Process killed

### Error Response Format
```json
{
    "error": {
        "code": "BUILD_001",
        "message": "Configuration failed",
        "details": "Error in config.guess",
        "location": "binutils/configure",
        "timestamp": "2025-05-31T15:03:28Z",
        "recovery": {
            "possible": true,
            "action": "Retry configuration",
            "command": "build-wrapper resume binutils --from=configure"
        }
    }
}
```

## Integration Requirements

### Script Integration
1. **Required Functions**
   - initialize()
   - configure()
   - build()
   - test()
   - install()
   - cleanup()

2. **Required Variables**
   - PACKAGE_NAME
   - PACKAGE_VERSION
   - BUILD_REQUIREMENTS
   - TEST_SUITE

### System Integration
1. **File System**
   - Build directory structure
   - Log file locations
   - Temporary storage

2. **Process Management**
   - Job control
   - Resource limits
   - Signal handling

## Notes
- All interfaces must be backward compatible
- Error handling must be comprehensive
- Logging should be configurable
- Progress reporting must be real-time
- Integration points must be well-defined

