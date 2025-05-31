# LFS Build Script Wrapper System

## Overview
This system provides a comprehensive wrapper for managing and executing LFS (Linux From Scratch) build scripts with enhanced logging, error handling, and build state management.

## System Requirements

### Base System Requirements
- Python 3.9 or higher
- POSIX-compliant shell
- Standard Unix tools (df, which, etc.)
- Sufficient disk space (default: 30GB)

### Python Dependencies
```
pytest>=7.0.0
pytest-cov>=3.0.0
click>=8.0.0
PyYAML>=6.0.0
```

## Installation

### System Prerequisites

1. Install Python 3 and pip:
   ```bash
   # For Ubuntu/Debian:
   sudo apt-get update
   sudo apt-get install python3 python3-pip python3-venv

   # For CentOS/RHEL:
   sudo yum install python3 python3-pip python3-virtualenv
   ```

### Development Setup

1. Clone the repository and navigate to the implementation directory:
   ```bash
   cd implementation/
   ```

2. Run the development environment setup script:
   ```bash
   ./setup_dev_env.sh
   ```

   This script will:
   - Create a Python virtual environment
   - Install all development dependencies
   - Set up the necessary directory structure
   - Copy the default configuration

3. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

### Manual Installation

If you prefer to set up manually:

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install the package in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

## Configuration

The system uses a YAML configuration file (config.yaml) with the following structure:

```yaml
environment:
  LFS: /mnt/lfs
  LFS_TGT: x86_64-lfs-linux-gnu
  PATH: /tools/bin:/bin:/usr/bin

paths:
  sources: /mnt/lfs/sources
  tools: /tools
  scripts: /mnt/lfs/scripts
  logs: /mnt/lfs/logs

logging:
  directory: logs
  level: INFO

requirements:
  disk_space_gb: 30
```

## Usage

### Basic Commands

1. Setup build environment:
   ```bash
   ./lfs_wrapper.py setup
   ```

2. Run a build script:
   ```bash
   ./lfs_wrapper.py run script_name [args...]
   ```

3. Check system status:
   ```bash
   ./lfs_wrapper.py status
   ```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest --cov=. tests/
```

## Package Structure

```
implementation/
├── lfs_wrapper/          # Main package directory
│   ├── __init__.py      # Package initialization
│   ├── cli.py           # Command-line interface
│   └── lfs_core.py      # Core functionality
├── tests/               # Test suite
│   └── test_lfs_wrapper.py
├── config/              # Configuration files
│   └── config.yaml
├── logs/               # Log files
├── setup.py            # Package setup configuration
├── setup_dev_env.sh    # Development environment setup
└── README.md           # This documentation
```

## Error Handling

The system provides comprehensive error handling for:
- Configuration issues
- Environment setup problems
- Script execution failures
- Resource constraints
- Permission issues

## Logging

Logs are stored in the configured log directory with:
- Timestamps for all events
- Log rotation support
- Multiple log levels (INFO, DEBUG, ERROR)
- Structured logging format

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit pull request

## Maintainers
- WARP System Development Team

## License
[License details to be added]

