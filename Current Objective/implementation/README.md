# LFS Wrapper

A Python-based wrapper system for managing Linux From Scratch (LFS) build processes and scripts.

## Features

- **Automated Build Management**
  - Parallel build process orchestration
  - Build script execution and monitoring
  - Dependency tracking and validation
  - Build environment management

- **Process Control**
  - Resource usage monitoring
  - Process isolation and cleanup
  - Build environment validation
  - Error recovery and retry mechanisms

- **Build Metrics**
  - Build time tracking
  - Resource utilization metrics
  - Success/failure statistics
  - Performance monitoring

- **Error Handling**
  - Intelligent error detection
  - Automatic recovery procedures
  - Build state preservation
  - Detailed error logging

## Installation

```bash
# Basic installation
pip install lfs-wrapper

# Install with all extras (recommended for development)
pip install "lfs-wrapper[test,qa,docs]"
```

## Quick Start

```python
from lfs_wrapper import LFSWrapper
from lfs_wrapper.core.config import WrapperConfig

# Initialize with custom configuration
config = WrapperConfig(
    build_dir="/path/to/lfs/build",
    source_dir="/path/to/lfs/sources",
    parallel_jobs=4
)

# Create wrapper instance
wrapper = LFSWrapper(config)

# Initialize build environment
await wrapper.initialize()

# Build a package
success = await wrapper.build_package("gcc-12.2.0")

# Check build metrics
metrics = await wrapper.get_build_metrics("gcc-12.2.0")
```

CLI Usage:

```bash
# Initialize build environment
lfs-wrapper init --build-dir /path/to/lfs/build

# Build a package
lfs-wrapper build gcc-12.2.0

# Check build status
lfs-wrapper status gcc-12.2.0

# View build metrics
lfs-wrapper metrics gcc-12.2.0
```

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/warp/lfs-wrapper.git
   cd lfs-wrapper
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Testing

Run the test suite using pytest:

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_build_process.py

# Run tests with specific marker
pytest -m "integration"
```

Coverage reports are generated in HTML format in the `htmlcov` directory.

## Code Quality

Maintain high code quality standards using the provided tools:

```bash
# Run all QA checks
tox

# Run specific checks
black .              # Code formatting
isort .             # Import sorting
flake8 .            # Style guide enforcement
mypy .              # Type checking
pylint lfs_wrapper  # Code analysis
```

## Project Structure

```
lfs_wrapper/
├── core/           # Core build system functionality
├── process/        # Process management and monitoring
├── build/          # Build script execution
├── utils/          # Utility functions
├── errors/         # Error definitions and handling
├── metrics/        # Build metrics collection
└── cli.py         # Command-line interface
```

## Build Process Overview

1. **Initialization**
   - Environment validation
   - Directory structure setup
   - Resource limit configuration
   - Build toolchain verification

2. **Package Building**
   - Source verification
   - Build script validation
   - Environment preparation
   - Process monitoring
   - Resource management
   - Error handling

3. **Metrics Collection**
   - Build timing
   - Resource usage tracking
   - Error rate monitoring
   - Performance analysis

## Error Recovery

The system includes sophisticated error recovery mechanisms:

- Automatic retry for transient failures
- Build state preservation
- Environment cleanup and reset
- Detailed error logging and analysis
- Customizable recovery strategies

## License

This project is licensed under the MIT License - see the LICENSE file for details.

