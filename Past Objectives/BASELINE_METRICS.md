# System Performance Baseline Metrics

## Overview
This document establishes baseline performance metrics and acceptable ranges for system operations based on initial system data collected during the initialization phase. These baselines will be used to configure monitoring thresholds and detect anomalies.

## System Maintenance Operations

### TIDY Operation Baselines
- **Files Processed**
  - Baseline: 356 files
  - Acceptable Range: 200-500 files
  - Alert Threshold: <200 or >500 files
  
- **Memory Usage**
  - Baseline: 29GB
  - Acceptable Range: 25GB-35GB
  - Alert Threshold: >35GB or <25GB

- **Operation Duration**
  - Baseline: 24 seconds
  - Acceptable Range: 15-45 seconds
  - Alert Threshold: >60 seconds or <10 seconds

### ORGANIZE Operation Baselines
- **Files Categorized**
  - Baseline: 667 files
  - Acceptable Range: 400-800 files
  - Alert Threshold: <400 or >800 files

- **Memory Usage**
  - Baseline: 28GB
  - Acceptable Range: 24GB-32GB
  - Alert Threshold: >32GB or <24GB

- **Operation Duration**
  - Baseline: < 5 seconds
  - Acceptable Range: 0-30 seconds
  - Alert Threshold: >45 seconds

## Resource Utilization Baselines

## System Resource Utilization

### CPU Usage Baselines
- **User Processing**
  - Baseline: 8.2%
  - Normal Range: 5-15%
  - Warning Threshold: >25%
  - Critical Threshold: >40%

- **System Processing**
  - Baseline: 1.9%
  - Normal Range: 1-5%
  - Warning Threshold: >10%
  - Critical Threshold: >20%

- **Idle Time**
  - Baseline: 89%
  - Minimum Expected: 70%
  - Warning Threshold: <60%
  - Critical Threshold: <40%

- **I/O Wait**
  - Baseline: 1.0%
  - Normal Range: 0-3%
  - Warning Threshold: >5%
  - Critical Threshold: >10%

### Memory Usage
- **Total System Memory**
  - Available: 31.5GB
  - Reserved for System: 2GB
  - Available for Applications: 29.5GB

- **Normal Operation**
  - Used Memory Baseline: 29GB
  - Buffer/Cache Usage: 18GB
  - Available Memory: 2.4GB
  - Normal Range: 25-30GB used
  - Warning Threshold: <2GB available
  - Critical Threshold: <1GB available

- **Buffer/Cache**
  - Baseline: 17-18GB
  - Normal Range: 15-20GB
  - Warning Threshold: <10GB or >25GB

### Disk Usage Baselines
- **System Partition (/mnt/host)**
  - Total Size: 849GB
  - Current Usage: 18GB (2.1%)
  - Normal Range: 0-50% used
  - Warning Threshold: >70% used
  - Critical Threshold: >85% used

- **Temp Directories**
  - /tmp Usage: Normal Range 0-25%
  - Warning Threshold: >50%
  - Critical Threshold: >75%

### Storage Usage
- **Log Growth Rate**
  - Expected: 50MB/day
  - Alert Threshold: >100MB/day

- **Backup Size**
  - Expected Range: 1-2GB
  - Alert Threshold: >3GB

## Task Execution Metrics

### Agent Response Times
- **Command Processing**
  - Expected: <500ms
  - Alert Threshold: >2000ms

- **Task Completion**
  - Small Tasks: <5 minutes
  - Medium Tasks: 5-15 minutes
  - Large Tasks: 15-60 minutes
  - Alert Threshold: >150% of expected duration

### System Health Indicators
- **Error Rate**
  - Normal Range: 0-2% of operations
  - Warning Threshold: >5%
  - Critical Threshold: >10%

- **Task Queue Length**
  - Normal Range: 0-10 tasks
  - Warning Threshold: >20 tasks
  - Critical Threshold: >50 tasks

## Adjustment Protocol
These baselines should be reviewed and adjusted:
1. After first 24 hours of operation
2. Weekly for the first month
3. Monthly thereafter
4. Immediately following any significant system changes

## Monitoring Implementation
- All metrics should be logged at 5-minute intervals
- Rolling 24-hour averages should be maintained
- Weekly trend analysis should be performed
- Monthly baseline reviews should be conducted

## Notes
- Initial baselines are derived from system initialization data
- Ranges account for expected variation in normal operation
- Thresholds are conservative to minimize false positives
- Adjustments should be based on actual operational patterns

## Change Log
- 2025-05-31 14:54: Initial baseline metrics established
- 2025-05-31 14:56: Added comprehensive system resource utilization baselines

