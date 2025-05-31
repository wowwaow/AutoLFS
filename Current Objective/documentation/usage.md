# Usage Guide

## Basic Commands

### System Management
```bash
# Initialize system
lfs-wrapper init

# Check system status
lfs-wrapper status

# Verify system health
lfs-wrapper health

# Show system information
lfs-wrapper info
```

### Build Management
```bash
# Start build process
lfs-wrapper build start

# Pause build
lfs-wrapper build pause

# Resume build
lfs-wrapper build resume

# Show build status
lfs-wrapper build status
```

### Checkpoint Management
```bash
# Create checkpoint
lfs-wrapper checkpoint create

# List checkpoints
lfs-wrapper checkpoint list

# Restore checkpoint
lfs-wrapper checkpoint restore [ID]

# Remove checkpoint
lfs-wrapper checkpoint remove [ID]
```

### Package Management
```bash
# List available packages
lfs-wrapper package list

# Show package details
lfs-wrapper package info [NAME]

# Check package status
lfs-wrapper package status [NAME]
```

## Common Use Cases

### 1. Complete System Build
```bash
# Initialize system
lfs-wrapper init

# Configure build
lfs-wrapper config set build.type full

# Start build
lfs-wrapper build start

# Monitor progress
lfs-wrapper monitor
```

### 2. Incremental Build
```bash
# List checkpoints
lfs-wrapper checkpoint list

# Restore checkpoint
lfs-wrapper checkpoint restore last

# Resume build
lfs-wrapper build resume
```

### 3. Custom Package Selection
```bash
# Select packages
lfs-wrapper package select desktop gaming

# Verify selection
lfs-wrapper package list selected

# Start build
lfs-wrapper build start
```

### 4. System Maintenance
```bash
# Check system health
lfs-wrapper health check

# Clean build directory
lfs-wrapper clean build

# Update system
lfs-wrapper update

# Verify system
lfs-wrapper verify
```

## Best Practices

### 1. Regular Checkpoints
- Create checkpoints before major steps
- Maintain multiple checkpoint versions
- Verify checkpoint integrity
- Clean old checkpoints regularly

### 2. Resource Management
- Monitor system resources
- Adjust parallel jobs as needed
- Watch disk space usage
- Monitor memory consumption

### 3. Error Handling
- Check error logs regularly
- Address warnings promptly
- Maintain clean build environment
- Follow recovery procedures

### 4. Performance Optimization
- Use appropriate parallel jobs
- Monitor system load
- Optimize disk usage
- Manage memory allocation

## Examples

### Basic Build Process
```bash
# Initial setup
lfs-wrapper init
lfs-wrapper config verify

# Start build
lfs-wrapper build start

# Monitor progress
lfs-wrapper monitor
```

### Advanced Usage
```bash
# Custom configuration
lfs-wrapper config set build.jobs 4
lfs-wrapper config set build.memory 8G

# Start build with monitoring
lfs-wrapper build start --monitor
```

### Maintenance Tasks
```bash
# System cleanup
lfs-wrapper clean all

# Update system
lfs-wrapper update --force

# Verify system
lfs-wrapper verify --thorough
```

## Troubleshooting

### Common Issues
1. Build Failures
   - Check error logs
   - Verify resources
   - Check dependencies

2. Performance Issues
   - Monitor system load
   - Check resource usage
   - Verify configuration

3. System Problems
   - Check disk space
   - Verify permissions
   - Check dependencies

## Advanced Features

### 1. Custom Scripts
```bash
# Register custom script
lfs-wrapper script register ./custom.sh

# Run custom script
lfs-wrapper script run custom
```

### 2. Performance Monitoring
```bash
# Enable monitoring
lfs-wrapper monitor start

# Show metrics
lfs-wrapper monitor stats

# Generate report
lfs-wrapper monitor report
```

### 3. System Integration
```bash
# Enable service
lfs-wrapper service enable

# Start service
lfs-wrapper service start

# Check status
lfs-wrapper service status
```

