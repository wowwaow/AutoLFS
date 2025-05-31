SYSTEM_DIR = /mnt/host/WARP_CURRENT

# Warp Agent Session Instructions - Enhanced Edition with Targeted Permission Management, Task Detection, Auto-Promotion & Tool Installation

This system uses a **single consolidated rule set**, a shared template library, and a series of persistent local files + system commands to coordinate multi-agent operations with intelligent task detection, automatic objective promotion, **targeted permission management**, and autonomous tool installation capabilities.

You must follow these rules **exactly** for every session.

## 📁 **Directory Structure & File Hierarchy**

### Primary System Directories
- **Core system** → /mnt/host/WARP_CURRENT/
  - System Commands/ → Command definitions and executables
  - Work Logs/ → Active session logs and archives
  - System Logs/ → System maintenance and operational logs
  - Warp Rules/ → Governance and operational procedures
  - Current Objective/ → Active project phase data
  - Future Objectives/ → Queued project phases
  - Past Objectives/ → Completed project archives
  - Agent Status/ → Per-agent heartbeat and status files
  - Task Pool/ → Active and pending task definitions
  - Dependencies/ → Cross-task and cross-objective dependency mapping
  - **Missing Tasks/** → **Detected missing tasks awaiting addition**
  - **Promotion Queue/** → **Objectives ready for promotion tracking**
  - **🆕 Installed Tools/** → **Registry of agent-installed tools and packages**

### Secondary Directories
- **General projects** → /mnt/host/
- **Templates** → /mnt/host/Templates/
- **Archived (obsolete) files** → /mnt/host/Archive/
- **Masterlog archive** → /mnt/host/WARP_CURRENT/Work Logs/Archive/
- **Emergency backups** → /mnt/host/WARP_CURRENT/Backups/
- **Cloud sync staging** → /mnt/host/WARP_CURRENT/Cloud_Sync/
- **Simulation workspace** → /mnt/host/WARP_CURRENT/Simulation/
- **Remote backup cache** → /mnt/host/WARP_CURRENT/Remote_Cache/

### Critical System Files
- **Main ruleset** → /mnt/host/WARP_CURRENT/Warp Rules/README.md
- **System documentation** → /mnt/host/WARP_CURRENT/Warp Rules/DOCUMENTATION.md
- **Path registry** → /mnt/host/WARP_CURRENT/System Logs/PATHS.md
- **Tidy log** → /mnt/host/WARP_CURRENT/System Logs/TIDY_LOG.md
- **Organize log** → /mnt/host/WARP_CURRENT/System Logs/ORGANIZE_LOG.md
- **System status** → /mnt/host/WARP_CURRENT/System Logs/SYSTEM_STATUS.md
- **Anomaly detection log** → /mnt/host/WARP_CURRENT/System Logs/ANOMALY_LOG.md
- **Supervisor alerts** → /mnt/host/WARP_CURRENT/System Logs/SUPERVISOR_ALERTS.md
- **Agent registry** → /mnt/host/WARP_CURRENT/Agent Status/AGENT_REGISTRY.csv
- **🆕 Missing task log** → /mnt/host/WARP_CURRENT/System Logs/MISSING_TASKS_LOG.md
- **🆕 Objective promotion log** → /mnt/host/WARP_CURRENT/System Logs/OBJECTIVE_PROMOTION_LOG.md
- **🆕 Agent timeout log** → /mnt/host/WARP_CURRENT/System Logs/AGENT_TIMEOUT_LOG.md
- **🆕 Task reassignment log** → /mnt/host/WARP_CURRENT/System Logs/TASK_REASSIGNMENT_LOG.md
- **🆕 Agent heartbeat monitor** → /mnt/host/WARP_CURRENT/Agent Status/HEARTBEAT_MONITOR.json
- **🆕 Permission audit log** → /mnt/host/WARP_CURRENT/System Logs/PERMISSION_AUDIT_LOG.md
- **🆕 Tool installation log** → /mnt/host/WARP_CURRENT/System Logs/TOOL_INSTALLATION_LOG.md
- **🆕 Installed tools registry** → /mnt/host/WARP_CURRENT/Installed Tools/TOOLS_REGISTRY.json

---

## 🔐 **Targeted Permission Management & Security Protocol**

### 🆕 Rule 0 — Just-In-Time Permission Management

✅ **MANDATORY: Agents MUST ensure proper permissions ONLY on files/directories they are about to use**

**Targeted Permission Functions:**

```bash
# Set permissions on specific file before use
FUNCTION ensure_file_permissions(file_path):
    IF file_exists(file_path):
        sudo chown ubuntu:ubuntu "$file_path"
        sudo chmod 644 "$file_path"
        log_permission_action("FILE", file_path, "permissions_set")
    RETURN verify_file_access(file_path)

# Set permissions on specific directory before use  
FUNCTION ensure_directory_permissions(dir_path):
    IF directory_exists(dir_path):
        sudo chown ubuntu:ubuntu "$dir_path"
        sudo chmod 755 "$dir_path"
        log_permission_action("DIRECTORY", dir_path, "permissions_set")
    ELSE:
        sudo mkdir -p "$dir_path"
        sudo chown ubuntu:ubuntu "$dir_path"
        sudo chmod 755 "$dir_path"
        log_permission_action("DIRECTORY", dir_path, "created_with_permissions")
    RETURN verify_directory_access(dir_path)

# Targeted permission check before any operation
FUNCTION verify_and_fix_access(target_path):
    IF is_file(target_path):
        RETURN ensure_file_permissions(target_path)
    ELIF is_directory(target_path):
        RETURN ensure_directory_permissions(target_path)
    ELSE:
        parent_dir = get_parent_directory(target_path)
        ensure_directory_permissions(parent_dir)
        RETURN TRUE
```

**Pre-Operation Permission Protocol:**

```bash
# Before reading any file
FUNCTION safe_file_read(file_path):
    ensure_file_permissions(file_path)
    content = read_file(file_path)
    RETURN content

# Before writing any file
FUNCTION safe_file_write(file_path, content):
    parent_dir = get_parent_directory(file_path)
    ensure_directory_permissions(parent_dir)
    
    IF file_exists(file_path):
        ensure_file_permissions(file_path)
    
    write_file(file_path, content)
    ensure_file_permissions(file_path)  # Fix permissions after write
    
    RETURN verify_file_written(file_path)

# Before directory operations
FUNCTION safe_directory_operation(dir_path, operation):
    ensure_directory_permissions(dir_path)
    result = execute_operation(dir_path, operation)
    ensure_directory_permissions(dir_path)  # Fix permissions after operation
    RETURN result
```

**Mandatory Targeted Permission Checks:**

1. **Before reading ANY specific file:** `ensure_file_permissions(file_path)`
2. **Before writing ANY specific file:** `ensure_directory_permissions(parent_dir)` + `ensure_file_permissions(file_path)`
3. **Before creating ANY directory:** `ensure_directory_permissions(dir_path)`
4. **Before moving/copying files:** `ensure_file_permissions(source)` + `ensure_directory_permissions(destination_dir)`
5. **🆕 Before tool installation:** `ensure_directory_permissions("/mnt/host/WARP_CURRENT/Installed Tools/")`

**Permission Audit Function:**

```bash
FUNCTION audit_specific_permissions(path_list):
    issues_found = []
    
    FOR each path IN path_list:
        ownership = get_ownership(path)
        permissions = get_permissions(path)
        
        IF ownership != "ubuntu:ubuntu":
            issues_found.append({path: path, issue: "wrong_ownership", current: ownership})
        
        IF path_type == "file" AND permissions != "644":
            issues_found.append({path: path, issue: "wrong_file_permissions", current: permissions})
        
        IF path_type == "directory" AND permissions != "755":
            issues_found.append({path: path, issue: "wrong_dir_permissions", current: permissions})
    
    RETURN issues_found
```

---

## 🛠️ **Tool Installation & Dependency Management**

### 🆕 Rule 0.3 — Autonomous Tool Installation with Targeted Permissions

✅ **AGENTS HAVE FULL AUTHORITY TO INSTALL ANY REQUIRED TOOLS OR DEPENDENCIES**

**Tool Installation Protocol with Targeted Permissions:**

```bash
FUNCTION install_tool(tool_name, installation_method, justification):
    # Ensure permissions on tool directory before starting
    ensure_directory_permissions("/mnt/host/WARP_CURRENT/Installed Tools/")
    
    # Ensure permissions on log file before writing
    log_file = "/mnt/host/WARP_CURRENT/System Logs/TOOL_INSTALLATION_LOG.md"
    ensure_file_permissions(log_file)
    
    # Pre-installation logging
    log_tool_installation_request(tool_name, justification)
    
    # Execute installation with full sudo privileges
    installation_result = execute_installation(tool_name, installation_method)
    
    # Post-installation verification
    verify_tool_installation(tool_name)
    
    # Ensure permissions on registry before updating
    registry_file = "/mnt/host/WARP_CURRENT/Installed Tools/TOOLS_REGISTRY.json"
    ensure_file_permissions(registry_file)
    
    # Update tool registry
    update_tools_registry(tool_name, installation_result)
    
    # Fix permissions on modified files only
    ensure_file_permissions(log_file)
    ensure_file_permissions(registry_file)
    
    # Log completion
    log_tool_installation_complete(tool_name, installation_result)
    
    RETURN installation_result
```

**Supported Installation Methods:**
1. **Package Managers:** `apt`, `pip`, `npm`, `cargo`, `go install`
2. **Direct Downloads:** `wget`, `curl` with verification
3. **Source Compilation:** `make`, `cmake`, custom build scripts
4. **Container Images:** `docker pull`, `podman pull`
5. **Language-Specific:** `gem install`, `composer install`, etc.

**Installation Examples with Targeted Permissions:**

```bash
# System packages
sudo apt update && sudo apt install -y [package_name]

# Python packages (user-local, no system permissions needed)
pip install [package_name] --user

# Node.js packages
npm install -g [package_name]

# Rust packages
cargo install [package_name]

# Go packages
go install [package_url]

# Custom installations with targeted permission management
tool_dir="/mnt/host/WARP_CURRENT/Installed Tools/"
ensure_directory_permissions("$tool_dir")
wget [download_url] -O "$tool_dir/installer.sh"
ensure_file_permissions("$tool_dir/installer.sh")
chmod +x "$tool_dir/installer.sh"
sudo "$tool_dir/installer.sh"
```

### 🆕 Tool Installation Command Set

#### **INSTALL_TOOL**
- **Purpose:** Install any required tool or dependency with targeted permission management
- **Syntax:** INSTALL_TOOL [tool_name] [method] [justification] [version]
- **Enhanced Behavior:**

```bash
FUNCTION install_tool(tool_name, method="auto", justification="required", version="latest"):
    # Target permission setup for tool installation
    tool_log = "/mnt/host/WARP_CURRENT/System Logs/TOOL_INSTALLATION_LOG.md"
    tool_registry = "/mnt/host/WARP_CURRENT/Installed Tools/TOOLS_REGISTRY.json"
    
    ensure_file_permissions(tool_log)
    ensure_file_permissions(tool_registry)
    
    # Log installation request
    log_installation_request(tool_name, justification)
    
    # Determine installation method
    IF method == "auto":
        method = detect_best_installation_method(tool_name)
    
    # Execute installation
    CASE method:
        "apt": sudo apt update && sudo apt install -y $tool_name
        "pip": pip install $tool_name --user
        "npm": npm install -g $tool_name
        "cargo": cargo install $tool_name
        "wget": download_and_install_from_url(tool_name)
        "compile": compile_from_source(tool_name)
    
    # Verify installation
    verification = verify_tool_available(tool_name)
    
    # Update registry with targeted permissions
    ensure_file_permissions(tool_registry)
    update_tools_registry(tool_name, method, version, verification)
    ensure_file_permissions(tool_registry)
    
    # Log completion with targeted permissions
    ensure_file_permissions(tool_log)
    log_installation_complete(tool_name, verification)
    ensure_file_permissions(tool_log)
    
    RETURN verification
```

#### **CHECK_DEPENDENCIES**
- **Purpose:** Scan current objective for missing dependencies and auto-install
- **Syntax:** CHECK_DEPENDENCIES [objective_path] [auto_install] [scan_depth]
- **Enhanced Behavior:**

```bash
FUNCTION check_dependencies(objective_path):
    # Ensure permissions on objective directory before scanning
    ensure_directory_permissions(objective_path)
    
    # Scan for dependency requirements
    dependencies = scan_for_dependencies(objective_path)
    missing_deps = []
    
    FOR each dependency IN dependencies:
        IF NOT tool_available(dependency.name):
            missing_deps.append(dependency)
    
    # Auto-install missing dependencies
    FOR each missing_dep IN missing_deps:
        install_result = INSTALL_TOOL(missing_dep.name, missing_dep.method, "objective_requirement")
        
        # Log with targeted permissions
        dep_log = "/mnt/host/WARP_CURRENT/System Logs/TOOL_INSTALLATION_LOG.md"
        ensure_file_permissions(dep_log)
        log_dependency_installation(missing_dep, install_result)
        ensure_file_permissions(dep_log)
    
    RETURN missing_deps
```

---

## 1️⃣ **General Instructions & Session Initialization**

### Enhanced Session Startup Protocol with Targeted Permissions

✅ **Mandatory Startup Sequence (Execute in Order):**

1. **🆕 TARGETED: Essential Directory Access Verification**

```bash
# Only set permissions on directories we need to access immediately
essential_dirs = [
    "/mnt/host/WARP_CURRENT/Agent Status/",
    "/mnt/host/WARP_CURRENT/Warp Rules/",
    "/mnt/host/WARP_CURRENT/System Logs/"
]

FOR each dir IN essential_dirs:
    ensure_directory_permissions(dir)

# Verify success for essential directories only
audit_result = audit_specific_permissions(essential_dirs)

IF audit_result.has_issues:
    log_critical_error("Essential directory access failed")
    halt_session_startup()
```

2. **🆕 Tool Registry Initialization with Targeted Permissions**

```bash
# Target tool directory and registry file specifically
tool_dir = "/mnt/host/WARP_CURRENT/Installed Tools/"
tool_registry = "/mnt/host/WARP_CURRENT/Installed Tools/TOOLS_REGISTRY.json"

ensure_directory_permissions(tool_dir)
ensure_file_permissions(tool_registry)

# Verify all previously installed tools are still functional
tools = load_tools_registry()
FOR each tool IN tools:
    tool_status = verify_tool_status(tool.name)
    update_tool_status(tool.name, tool_status)

# Update registry with targeted permissions
ensure_file_permissions(tool_registry)
save_tools_registry(tools)
ensure_file_permissions(tool_registry)
```

3. **Identity Verification with Targeted File Access**

```bash
# Target specific agent registry file
agent_registry = "/mnt/host/WARP_CURRENT/Agent Status/AGENT_REGISTRY.csv"
ensure_file_permissions(agent_registry)

# Confirm agent identity and session timestamp
log_session_start_in_registry(agent_registry)

# Fix permissions after write
ensure_file_permissions(agent_registry)

# Check for existing agent conflicts
check_agent_conflicts(agent_registry)
```

4. **Rule Set Validation with Targeted File Access**

```bash
# Target specific rule files
rule_files = [
    "/mnt/host/WARP_CURRENT/Warp Rules/README.md",
    "/mnt/host/WARP_CURRENT/Warp Rules/DOCUMENTATION.md"
]

FOR each rule_file IN rule_files:
    ensure_file_permissions(rule_file)
    content = safe_file_read(rule_file)
    validate_rule_content(content)
```

5. **System Health Check with Targeted Directory Scanning**

```bash
# Target critical system directories for health check
critical_dirs = [
    "/mnt/host/WARP_CURRENT/Current Objective/",
    "/mnt/host/WARP_CURRENT/Future Objectives/",
    "/mnt/host/WARP_CURRENT/Past Objectives/",
    "/mnt/host/WARP_CURRENT/Task Pool/"
]

FOR each dir IN critical_dirs:
    ensure_directory_permissions(dir)
    health_status = check_directory_health(dir)
    log_health_status(dir, health_status)
```

6. **🆕 Dependency Scan & Auto-Installation with Targeted Access**

```bash
# Target current objective directory
current_obj_dir = "/mnt/host/WARP_CURRENT/Current Objective/"
ensure_directory_permissions(current_obj_dir)

# Execute dependency check with targeted permissions
missing_deps = CHECK_DEPENDENCIES(current_obj_dir)

# Log results with targeted file access
dep_log = "/mnt/host/WARP_CURRENT/System Logs/TOOL_INSTALLATION_LOG.md"
ensure_file_permissions(dep_log)
log_dependency_scan_results(missing_deps)
ensure_file_permissions(dep_log)
```

7. **🆕 Missing Task Detection with Targeted Directory Access**

```bash
# Target specific directories for task detection
objective_dirs = [
    "/mnt/host/WARP_CURRENT/Current Objective/",
    "/mnt/host/WARP_CURRENT/Task Pool/"
]

FOR each dir IN objective_dirs:
    ensure_directory_permissions(dir)

# Scan and detect missing tasks
missing_tasks = scan_for_missing_tasks(objective_dirs)

# Log with targeted file access
missing_task_log = "/mnt/host/WARP_CURRENT/System Logs/MISSING_TASKS_LOG.md"
ensure_file_permissions(missing_task_log)
log_missing_tasks(missing_tasks)
ensure_file_permissions(missing_task_log)

# Update task pool with targeted permissions
task_pool_dir = "/mnt/host/WARP_CURRENT/Task Pool/"
ensure_directory_permissions(task_pool_dir)
update_task_pool_with_missing_tasks(missing_tasks)
```

8. **🆕 Objective Completion Check & Auto-Promotion with Targeted File Operations**

```bash
# Target objective directories for completion check
obj_dirs = [
    "/mnt/host/WARP_CURRENT/Current Objective/",
    "/mnt/host/WARP_CURRENT/Future Objectives/",
    "/mnt/host/WARP_CURRENT/Past Objectives/"
]

FOR each dir IN obj_dirs:
    ensure_directory_permissions(dir)

# Evaluate current objective status
current_obj_status = evaluate_objective_completion("/mnt/host/WARP_CURRENT/Current Objective/")

IF current_obj_status == "COMPLETE":
    # Execute targeted promotion sequence
    execute_objective_promotion_with_targeted_permissions()

FUNCTION execute_objective_promotion_with_targeted_permissions():
    # Target each directory individually for moves
    current_dir = "/mnt/host/WARP_CURRENT/Current Objective/"
    past_dir = "/mnt/host/WARP_CURRENT/Past Objectives/"
    future_dir = "/mnt/host/WARP_CURRENT/Future Objectives/"
    
    ensure_directory_permissions(current_dir)
    ensure_directory_permissions(past_dir)
    ensure_directory_permissions(future_dir)
    
    # Move completed objective with targeted permissions
    timestamp = get_timestamp()
    archive_name = "completed_objective_" + timestamp
    
    move_directory_contents(current_dir, past_dir + archive_name + "/")
    ensure_directory_permissions(past_dir + archive_name + "/")
    
    # Select and promote next objective
    next_objective = select_highest_priority_objective(future_dir)
    move_directory_contents(future_dir + next_objective + "/", current_dir)
    ensure_directory_permissions(current_dir)
    
    # Log promotion with targeted file access
    promotion_log = "/mnt/host/WARP_CURRENT/System Logs/OBJECTIVE_PROMOTION_LOG.md"
    ensure_file_permissions(promotion_log)
    log_objective_promotion(next_objective, archive_name)
    ensure_file_permissions(promotion_log)
```

9. **Maintenance Status Verification with Targeted Log Access**

```bash
# Target specific maintenance log files
maintenance_logs = [
    "/mnt/host/WARP_CURRENT/System Logs/TIDY_LOG.md",
    "/mnt/host/WARP_CURRENT/System Logs/ORGANIZE_LOG.md"
]

FOR each log_file IN maintenance_logs:
    ensure_file_permissions(log_file)
    last_maintenance = get_last_maintenance_timestamp(log_file)
    
    IF time_since(last_maintenance) > 24_hours:
        IF log_file.contains("TIDY"):
            execute_mandatory_tidy_with_targeted_permissions()
        ELIF log_file.contains("ORGANIZE"):
            execute_mandatory_organize_with_targeted_permissions()
```

10. **🆕 Agent Timeout Detection with Targeted Heartbeat Access**

```bash
# Target agent heartbeat directory
heartbeat_dir = "/mnt/host/WARP_CURRENT/Agent Status/"
ensure_directory_permissions(heartbeat_dir)

# Scan individual heartbeat files
heartbeat_files = list_files_in_directory(heartbeat_dir)
timed_out_agents = []

FOR each heartbeat_file IN heartbeat_files:
    ensure_file_permissions(heartbeat_file)
    last_heartbeat = read_last_heartbeat(heartbeat_file)
    
    IF is_timed_out(last_heartbeat):
        timed_out_agents.append(extract_agent_id(heartbeat_file))

# Handle timeout reassignments with targeted access
IF timed_out_agents.length > 0:
    timeout_log = "/mnt/host/WARP_CURRENT/System Logs/AGENT_TIMEOUT_LOG.md"
    ensure_file_permissions(timeout_log)
    
    reassign_tasks_from_timed_out_agents(timed_out_agents)
    
    log_timeout_reassignments(timed_out_agents, timeout_log)
    ensure_file_permissions(timeout_log)
```

11. **🆕 Final Targeted Permission Verification**

```bash
# Audit only the files and directories we've actually accessed
accessed_paths = get_session_accessed_paths()
final_audit = audit_specific_permissions(accessed_paths)

IF final_audit.has_issues:
    FOR each issue IN final_audit.issues:
        IF issue.type == "file":
            ensure_file_permissions(issue.path)
        ELIF issue.type == "directory":
            ensure_directory_permissions(issue.path)
    
    # Log only the specific permission fixes applied
    permission_log = "/mnt/host/WARP_CURRENT/System Logs/PERMISSION_AUDIT_LOG.md"
    ensure_file_permissions(permission_log)
    log_targeted_permission_fixes(final_audit.issues)
    ensure_file_permissions(permission_log)

# Log successful startup
startup_log = "/mnt/host/WARP_CURRENT/System Logs/SYSTEM_STATUS.md"
ensure_file_permissions(startup_log)
log_session_startup_complete()
ensure_file_permissions(startup_log)
```

---

✅ **Enhanced System Summary:**

This enhanced Warp Agent system now implements **targeted permission management** that only sets permissions on specific files and directories immediately before they are accessed, rather than applying broad permissions across the entire directory structure.

**Key Targeted Permission Management Features:**

- **🆕 Just-in-time permission setting** - permissions applied only when needed
- **🆕 File-specific permission management** - individual files targeted before access
- **🆕 Directory-specific permission management** - directories targeted before operations
- **🆕 Minimal permission scope** - no unnecessary broad permission changes
- **🆕 Operation-specific permission functions** - tailored permission management for different operations
- **🆕 Permission audit trails** - logging of specific permission actions taken
- **🆕 Targeted startup sequence** - only essential directories accessed during initialization
- **🆕 Secure tool installation** - targeted permissions for tool directories only

**Security Benefits:**

- **Reduced attack surface** - minimal permission modifications
- **Principle of least privilege** - only necessary permissions granted
- **Audit compliance** - detailed logging of permission changes
- **System integrity** - unchanged permissions on unused files/directories
- **Performance improvement** - faster startup without broad permission operations

**Tool Installation Integration:**

- All tool installations use targeted permission management
- Tool registry and log files have permissions set only when accessed
- Installation directories are secured individually as needed
- Permission fixes applied only to modified tool-related files

The system maintains all previous functionality while implementing secure, targeted permission management that respects the principle of least privilege and minimizes unnecessary system-wide permission changes.
