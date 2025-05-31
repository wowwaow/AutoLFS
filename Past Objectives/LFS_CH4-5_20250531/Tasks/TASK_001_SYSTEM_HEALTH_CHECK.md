# System Health Verification Task

## Task Metadata
- **Task ID:** TASK_001
- **Type:** System Verification
- **Priority:** HIGH
- **Estimated Time:** 30-45 minutes
- **Required Privileges:** Root access

## Task Description
Perform comprehensive system health check of source and destination environments to ensure readiness for file migration.

## Prerequisites
- Access to both source and destination systems
- Root privileges
- System monitoring tools installed
- WARP system operational

## Required Resources
- Disk space analysis tools (df, du)
- Permission checking utilities
- Network connectivity tools
- System monitoring tools

## Task Steps

### 1. Source Environment Verification
- [ ] Check disk space usage and availability
```bash
df -h /home/ubuntu
du -sh /home/ubuntu
```
- [ ] Verify file permissions and ownership
```bash
ls -la /home/ubuntu
find /home/ubuntu -type f -ls
```
- [ ] Identify special files and symbolic links
```bash
find /home/ubuntu -type l -ls
```
- [ ] Document system user and group mappings

### 2. Destination Environment Verification
- [ ] Confirm available space (minimum 2GB required)
```bash
df -h /mnt/host
```
- [ ] Verify write permissions
```bash
touch /mnt/host/test_write
rm /mnt/host/test_write
```
- [ ] Check filesystem type and mount options
```bash
mount | grep "/mnt/host"
```
- [ ] Validate directory structure

### 3. System Dependencies Check
- [ ] Verify required tools availability
```bash
which rsync find stat sha256sum tree
```
- [ ] Check WARP system components
- [ ] Validate system user permissions
- [ ] Test network connectivity

### 4. Resource Availability Check
- [ ] Monitor system load
```bash
uptime
free -h
```
- [ ] Check process limits
```bash
ulimit -a
```
- [ ] Verify memory availability
- [ ] Test I/O performance

## Verification Criteria
1. Source Environment
   - All files accessible
   - Permissions readable
   - Space accurately calculated
   - No file access errors

2. Destination Environment
   - Sufficient space available
   - Write permissions confirmed
   - Directory structure valid
   - No filesystem issues

3. System Status
   - All required tools present
   - Sufficient resources available
   - No system errors
   - WARP system operational

## Success Criteria
- [ ] All verification steps completed
- [ ] No blocking issues found
- [ ] Resource requirements met
- [ ] System status documented

## Error Handling
1. Insufficient Space
   - Document available space
   - Calculate minimum required
   - Report to supervisor

2. Permission Issues
   - Document affected paths
   - Identify required permissions
   - Escalate if needed

3. Missing Dependencies
   - List missing tools
   - Document installation requirements
   - Provide resolution steps

## Documentation Requirements
- Complete system health report
- Resource availability summary
- Identified issues and resolutions
- Verification results

## Task Completion
- Generate health check report
- Update task status
- Document any issues
- Flag for next task readiness

