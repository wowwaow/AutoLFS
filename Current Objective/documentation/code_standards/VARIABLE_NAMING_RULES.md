# Variable Naming Rules
Created: 2025-05-31T16:20:01Z
Status: ACTIVE
Category: Coding Standards

## Overview
This document defines the variable naming rules for the LFS/BLFS Build Scripts Wrapper System, ensuring consistency across Python, Shell, and configuration files.

## General Principles
```yaml
naming_principles:
  clarity: names should be descriptive and unambiguous
  consistency: follow established patterns
  length: balance between clarity and brevity
  context: names should reflect scope and purpose
  language_specific: follow language idioms
```

## Python Variable Naming

### 1. Case Conventions
```python
# Module-level constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
CONFIG_PATH = "/etc/lfs-wrapper"

# Class-level constants
class BuildManager:
    DEFAULT_WORKERS = 4
    MAX_QUEUE_SIZE = 100

# Instance variables
self.build_status = "pending"
self.current_phase = None

# Local variables
package_name = "gcc"
build_options = {"optimize": True}

# Private variables (module or class)
_internal_cache = {}
_cleanup_scheduled = False
```

### 2. Type-Specific Rules
```yaml
type_rules:
  boolean:
    prefix: is_, has_, should_, can_
    examples:
      - is_complete
      - has_dependencies
      - should_rebuild
      - can_proceed
  
  collections:
    suffix: _list, _dict, _set, _queue
    examples:
      - package_list
      - config_dict
      - dependency_set
      - build_queue
  
  callables:
    suffix: _fn, _cb, _handler
    examples:
      - validation_fn
      - error_cb
      - event_handler
```

### 3. Scope-Based Rules
```yaml
scope_rules:
  module_level:
    constants: UPPERCASE_WITH_UNDERSCORES
    variables: lowercase_with_underscores
    private: _lowercase_with_underscores
  
  class_level:
    constants: UPPERCASE_WITH_UNDERSCORES
    attributes: lowercase_with_underscores
    private: _lowercase_with_underscores
  
  function_level:
    parameters: lowercase_with_underscores
    locals: lowercase_with_underscores
```

## Shell Script Variables

### 1. Environment Variables
```bash
# System configuration
export LFS_ROOT="/mnt/lfs"
export LFS_TGT="x86_64-lfs-linux-gnu"
export LFS_BUILD_THREADS=4

# Path configuration
export LFS_TOOLS="/tools"
export LFS_SOURCES="/sources"
```

### 2. Script-Local Variables
```bash
# Constants (readonly)
readonly SCRIPT_VERSION="1.0.0"
readonly MAX_RETRIES=3
readonly DEFAULT_TIMEOUT=30

# Working variables
build_status="pending"
current_phase=""
error_count=0
```

### 3. Special Purpose Variables
```yaml
special_variables:
  loop_counters:
    pattern: i, j, k or idx, jdx, kdx
    example: for i in "${packages[@]}"
  
  temporary:
    prefix: tmp_
    example: tmp_output=$(mktemp)
  
  flags:
    prefix: flag_
    example: flag_verbose=false
```

## Configuration Variables

### 1. YAML Configuration
```yaml
build_config:
  # System settings
  system:
    root_path: /mnt/lfs
    build_path: /var/build
    log_path: /var/log/lfs

  # Resource limits
  resources:
    max_threads: 4
    max_memory_gb: 8
    disk_space_gb: 50
```

### 2. Environment Files
```bash
# Build environment
BUILD_USER=lfs
BUILD_GROUP=lfs
BUILD_MODE=normal

# Resource configuration
MEMORY_LIMIT=8G
DISK_QUOTA=50G
```

## Validation Rules

### 1. Automated Validation
```yaml
validation:
  tools:
    python:
      - pylint
      - pep8-naming
    shell:
      - shellcheck
      - bashate
  
  rules:
    python:
      constant_pattern: ^[A-Z][A-Z0-9_]*$
      variable_pattern: ^[a-z][a-z0-9_]*$
      private_pattern: ^_[a-z][a-z0-9_]*$
    
    shell:
      constant_pattern: ^[A-Z][A-Z0-9_]*$
      variable_pattern: ^[a-z][a-z0-9_]*$
```

### 2. Pre-commit Hooks
```yaml
pre_commit:
  - id: check-python-variable-names
    name: Python variable naming
    entry: python-name-checker
    types: [python]
  
  - id: check-shell-variable-names
    name: Shell variable naming
    entry: shell-name-checker
    types: [shell]
```

## Examples

### 1. Python Examples
```python
# Good examples
MAX_ATTEMPTS = 3
current_status = "building"
_internal_cache = {}
is_complete = False
package_list = []
error_handler = lambda x: None

# Bad examples
maxAttempts = 3  # Wrong: not snake_case
CURRENT_STATUS = "building"  # Wrong: not a constant
internal_cache = {}  # Wrong: should be private
```

### 2. Shell Examples
```bash
# Good examples
readonly MAX_RETRIES=3
build_status="pending"
_cleanup_temp_files() { ... }

# Bad examples
maxRetries=3  # Wrong: not shell style
BUILD_status="pending"  # Wrong: inconsistent
```

## Integration Requirements
1. Code style checkers
2. Pre-commit hooks
3. CI pipeline validation
4. Documentation tools

## Success Criteria
1. All variables follow naming conventions
2. Automated validation passes
3. Documentation complete
4. Examples provided
5. Integration verified

