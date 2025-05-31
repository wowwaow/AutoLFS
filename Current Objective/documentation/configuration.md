# Configuration Reference

## Configuration Files

### 1. Main Configuration
```yaml
# /etc/lfs-wrapper/config.yaml
system:
  build_dir: /var/lfs/build
  log_dir: /var/log/lfs-wrapper
  temp_dir: /var/tmp/lfs-wrapper
  checkpoint_dir: /var/lib/lfs-wrapper/checkpoints

logging:
  level: INFO
  format: detailed
  rotation: daily
  retention: 30d

monitoring:
  enabled: true
  interval: 5m
  metrics_retention: 7d

build:
  parallel_jobs: 4
  memory_limit: 8G
  disk_threshold: 90%
  timeout: 12h
```

### 2. Build Configuration
```yaml
# /etc/lfs-wrapper/build.yaml
lfs:
  version: 11.3
  scripts_dir: /usr/local/lfs/scripts
  patches_dir: /usr/local/lfs/patches
  
blfs:
  enabled: true
  package_selection: minimal
  graphics: true
  gaming: false
```

### 3. Package Configuration
```yaml
# /etc/lfs-wrapper/packages.yaml
selections:
  minimal: [base, core, network]
  desktop: [minimal, x11, gtk, qt]
  gaming: [desktop, vulkan, steam]
```

## Environment Variables

### System Variables
```bash
LFS_WRAPPER_HOME=/opt/lfs-wrapper
LFS_BUILD_DIR=/var/lfs/build
LFS_LOG_DIR=/var/log/lfs-wrapper
LFS_CHECKPOINT_DIR=/var/lib/lfs-wrapper/checkpoints
```

### Build Variables
```bash
LFS_PARALLEL_JOBS=4
LFS_MEMORY_LIMIT=8G
LFS_DISK_THRESHOLD=90
LFS_BUILD_TIMEOUT=12h
```

### Debug Variables
```bash
LFS_DEBUG=0
LFS_VERBOSE=1
LFS_TRACE=0
```

## Command-line Options

### Global Options
```bash
--config-file PATH    Alternative config file
--log-level LEVEL    Logging level
--verbose           Verbose output
--debug            Debug mode
--quiet            Minimal output
```

### Build Options
```bash
--jobs N           Number of parallel jobs
--memory-limit N   Memory limit per job
--disk-threshold N Disk usage threshold
--timeout N        Build timeout
```

### Monitoring Options
```bash
--monitor          Enable monitoring
--metrics          Enable metrics collection
--dashboard        Enable dashboard
```

## Configuration Guidelines

### 1. System Resources
- Set parallel jobs based on CPU cores
- Allocate memory based on system RAM
- Monitor disk usage thresholds
- Configure timeout values

### 2. Logging Setup
- Choose appropriate log levels
- Configure log rotation
- Set retention periods
- Enable required metrics

### 3. Build Options
- Select package sets
- Configure optimization flags
- Set resource limits
- Enable required features

### 4. Security Settings
- Configure permissions
- Set resource isolation
- Enable security features
- Configure access controls

## Configuration Examples

### Minimal System
```yaml
system:
  build_dir: /var/lfs/build
  parallel_jobs: 2
  memory_limit: 4G

build:
  package_selection: minimal
  graphics: false
  gaming: false
```

### Desktop System
```yaml
system:
  build_dir: /var/lfs/build
  parallel_jobs: 4
  memory_limit: 8G

build:
  package_selection: desktop
  graphics: true
  gaming: false
```

### Gaming System
```yaml
system:
  build_dir: /var/lfs/build
  parallel_jobs: 8
  memory_limit: 16G

build:
  package_selection: gaming
  graphics: true
  gaming: true
```

## Troubleshooting

### Common Issues
1. Resource Limits
   - Adjust parallel jobs
   - Check memory limits
   - Monitor disk space

2. Build Failures
   - Check log levels
   - Enable debugging
   - Review timeouts

3. Performance Issues
   - Optimize resource allocation
   - Review monitoring settings
   - Check system load

