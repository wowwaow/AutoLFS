SYSTEM_DIR = /mnt/host/WARP_CURRENT

# Warp Agent Session Instructions - Enhanced Edition with Task Detection & Auto-Promotion

This system uses a **single consolidated rule set**, a shared template library, and a series of persistent local files + system commands to coordinate multi-agent operations with intelligent task detection and automatic objective promotion.

You must follow these rules **exactly** for every session.

## 📁 **Directory Structure & File Hierarchy**

### Primary System Directories
- **Core system** → `/mnt/host/WARP_CURRENT/`
  - `System Commands/` → Command definitions and executables
  - `Work Logs/` → Active session logs and archives
  - `System Logs/` → System maintenance and operational logs
  - `Warp Rules/` → Governance and operational procedures
  - `Current Objective/` → Active project phase data
  - `Future Objectives/` → Queued project phases
  - `Past Objectives/` → Completed project archives
  - `Agent Status/` → Per-agent heartbeat and status files
  - `Task Pool/` → Active and pending task definitions
  - `Dependencies/` → Cross-task and cross-objective dependency mapping
  - `**Missing Tasks/`** → **Detected missing tasks awaiting addition**
  - `**Promotion Queue/`** → **Objectives ready for promotion tracking**

### Secondary Directories
- **General projects** → `/mnt/host/`
- **Templates** → `/mnt/host/Templates/`
- **Archived (obsolete) files** → `/mnt/host/Archive/`
- **Masterlog archive** → `/mnt/host/WARP_CURRENT/Work Logs/Archive/`
- **Emergency backups** → `/mnt/host/WARP_CURRENT/Backups/`
- **Cloud sync staging** → `/mnt/host/WARP_CURRENT/Cloud_Sync/`
- **Simulation workspace** → `/mnt/host/WARP_CURRENT/Simulation/`
- **Remote backup cache** → `/mnt/host/WARP_CURRENT/Remote_Cache/`

### Critical System Files
- **Main ruleset** → `/mnt/host/WARP_CURRENT/Warp Rules/README.md`
- **System documentation** → `/mnt/host/WARP_CURRENT/Warp Rules/DOCUMENTATION.md`
- **Path registry** → `/mnt/host/WARP_CURRENT/System Logs/PATHS.md`
- **Tidy log** → `/mnt/host/WARP_CURRENT/System Logs/TIDY_LOG.md`
- **Organize log** → `/mnt/host/WARP_CURRENT/System Logs/ORGANIZE_LOG.md`
- **System status** → `/mnt/host/WARP_CURRENT/System Logs/SYSTEM_STATUS.md`
- **Anomaly detection log** → `/mnt/host/WARP_CURRENT/System Logs/ANOMALY_LOG.md`
- **Supervisor alerts** → `/mnt/host/WARP_CURRENT/System Logs/SUPERVISOR_ALERTS.md`
- **Agent registry** → `/mnt/host/WARP_CURRENT/Agent Status/AGENT_REGISTRY.csv`
- **🆕 Missing task log** → `/mnt/host/WARP_CURRENT/System Logs/MISSING_TASKS_LOG.md`
- **🆕 Objective promotion log** → `/mnt/host/WARP_CURRENT/System Logs/OBJECTIVE_PROMOTION_LOG.md`
- **🆕 Agent timeout log** → `/mnt/host/WARP_CURRENT/System Logs/AGENT_TIMEOUT_LOG.md`
- **🆕 Task reassignment log** → `/mnt/host/WARP_CURRENT/System Logs/TASK_REASSIGNMENT_LOG.md`
- **🆕 Agent heartbeat monitor** → `/mnt/host/WARP_CURRENT/Agent Status/HEARTBEAT_MONITOR.json`

---

## 1️⃣ **General Instructions & Session Initialization**

### Enhanced Session Startup Protocol

✅ **Mandatory Startup Sequence (Execute in Order):**

1. **Identity Verification**
   - Confirm agent identity and session timestamp
   - Log session start in `AGENT_REGISTRY.csv`
   - Check for existing agent conflicts or overlapping sessions

2. **Rule Set Validation**
   - Read primary ruleset from `README.md`
   - Cross-reference with `DOCUMENTATION.md` for system architecture
   - Verify rule version compatibility and last update timestamp

3. **System Health Check**
   - Validate directory structure integrity
   - Check file permissions and access rights
   - Verify template availability and version consistency

4. **🆕 Missing Task Detection & Resolution**
   - **Scan Current Objective** for incomplete or missing tasks
   - **Analyze task dependencies** to identify gaps
   - **Check against known patterns** for standard task types
   - **Auto-generate missing tasks** and add to Current Objective
   - **Log all detected missing tasks** to `MISSING_TASKS_LOG.md`
   - **Update task pool** with newly identified tasks

5. **🆕 Objective Completion Check & Auto-Promotion**
   - **Evaluate current objective status** for completion
   - **If all tasks complete**: Execute automatic promotion sequence
   - **Promotion Sequence**:
     1. Archive completed objective to `Past Objectives/`
     2. Scan `Future Objectives/` for highest priority objective
     3. **Move selected objective files** to `Current Objective/`
     4. Parse new objective and **atomize into executable tasks**
     5. Update `Task Pool/` with new work items
     6. Log promotion to `OBJECTIVE_PROMOTION_LOG.md`
     7. Notify all agents of new objective availability

6. **Maintenance Status Verification**
   - Check `TIDY_LOG.md` for last maintenance timestamp
   - Check `ORGANIZE_LOG.md` for last organization timestamp
   - If >24 hours since last tidy, **mandatory TIDY execution**
   - If >24 hours since last organize, **mandatory ORGANIZE execution**
   - Log maintenance requirements in agent status file

7. **Work Queue Analysis**
   - Scan available tasks in current objective
   - Identify parallel-executable tasks across phases
   - Check for timeout takeovers or abandoned tasks

8. **🆕 Agent Timeout Detection & Task Reassignment**
   - **Scan agent heartbeats** for timeout detection
   - **Identify stalled or abandoned tasks** from timed-out agents
   - **Execute automatic task reassignment** to available agents
   - **Log timeout events** and reassignment actions
   - **Update task ownership** and agent workload tracking
   - **Preserve task progress** and state for seamless handoff

9. **Anomaly Detection Scan**
   - Run AI-driven anomaly detection on system metrics
   - Check for abnormal error rates, performance degradation, or resource spikes
   - Generate alerts if thresholds exceeded
   - Log anomalies to `ANOMALY_LOG.md`

9. **Supervisor Alert Assessment**
   - Review pending supervisor alerts in queue
   - Evaluate alert priority and escalation requirements
   - Update supervisor dashboard with critical issues

---

## 📂 **Enhanced System Command Reference**

### Core Command Definitions

#### **🆕 DETECT_MISSING_TASKS**
- **Purpose:** AI-driven detection and addition of missing tasks to current objective
- **Syntax:** `DETECT_MISSING_TASKS [objective_name] [scan_depth] [auto_add]`
- **Enhanced Behavior:**
  - **Pattern Analysis:** Compare current objective against standard project patterns
  - **Dependency Gap Detection:** Identify missing prerequisite or follow-up tasks
  - **Best Practice Scanning:** Check for commonly forgotten task types
  - **Stakeholder Review Tasks:** Ensure approval and review tasks exist
  - **Quality Assurance Tasks:** Verify testing and validation tasks present
  - **Documentation Tasks:** Confirm knowledge transfer and documentation tasks
  - **Auto-Addition:** Automatically add detected missing tasks to Current Objective
  - **Priority Assignment:** Smart priority assignment based on dependencies
- **Output:** List of detected and added tasks with reasoning
- **Auto-Execution:** Runs during session startup if enabled

#### **🆕 MONITOR_AGENTS**
- **Purpose:** Continuous agent heartbeat monitoring with automatic timeout detection
- **Syntax:** `MONITOR_AGENTS [scan_interval] [timeout_threshold] [auto_reassign]`
- **Enhanced Behavior:**
  - **Heartbeat Scanning:** Check all agent heartbeats against timeout thresholds
  - **Timeout Detection:** Identify agents that have missed heartbeat intervals
  - **Task State Analysis:** Determine status of tasks assigned to timed-out agents
  - **Automatic Reassignment:** Transfer abandoned tasks to available agents
  - **Progress Preservation:** Maintain task progress and state during handoff
  - **Agent Notification:** Alert remaining agents of reassigned tasks
  - **Logging:** Record all timeout events and reassignments
- **Auto-Execution:** Runs continuously in background every 30 seconds
- **Output:** Timeout detection results and reassignment actions taken

#### **🆕 REASSIGN_TASK**
- **Purpose:** Intelligent task reassignment with state preservation
- **Syntax:** `REASSIGN_TASK [task_id] [from_agent] [to_agent] [preserve_state]`
- **Enhanced Behavior:**
  - **Agent Capability Matching:** Select best replacement agent based on skills
  - **State Transfer:** Preserve task progress, notes, and intermediate results
  - **Dependency Validation:** Ensure reassignment doesn't break dependencies
  - **Priority Adjustment:** Update task priority based on delay impact
  - **Handoff Documentation:** Create detailed handoff notes for new agent
  - **Timeline Recalculation:** Update project timelines based on reassignment
- **Automatic Mode:** Can be triggered by MONITOR_AGENTS for seamless operation
- **Manual Mode:** Supervisor-initiated reassignment with custom parameters

#### **🆕 HEARTBEAT**
- **Purpose:** Agent lifecycle and health monitoring
- **Syntax:** `HEARTBEAT [agent_id] [status] [current_task] [progress]`
- **Enhanced Behavior:**
  - **Health Status Update:** Report agent health and resource utilization
  - **Task Progress Reporting:** Update task completion percentage and status
  - **Capability Advertisement:** Report current agent capabilities and availability
  - **Resource Usage Tracking:** Monitor CPU, memory, and I/O usage
  - **Error State Reporting:** Report any errors or issues encountered
  - **Next Heartbeat Scheduling:** Set next expected heartbeat timestamp
- **Mandatory Frequency:** Every 2 minutes for active agents
- **Timeout Thresholds:** 
  - **Soft Timeout:** 5 minutes (warning)
  - **Hard Timeout:** 10 minutes (reassignment trigger)
  - **Critical Timeout:** 15 minutes (agent marked as failed)
- **Purpose:** Intelligent objective promotion with complete file migration
- **Syntax:** `PROMOTE_OBJECTIVE [source_objective] [target_location] [archive_current]`
- **Enhanced Behavior:**
  - **Completion Verification:** Validate all current objective tasks are complete
  - **Priority Assessment:** Select highest priority objective from Future Objectives
  - **File Migration:** Move all objective files from Future to Current directory
  - **Task Atomization:** Break down objective into executable tasks
  - **Dependency Mapping:** Update cross-objective dependencies
  - **Agent Notification:** Alert all agents to new objective availability
  - **Archive Management:** Safely archive completed objective with metadata
- **Auto-Execution:** Triggered when current objective completion detected
- **Logging:** All promotion activities logged to `OBJECTIVE_PROMOTION_LOG.md`

#### **WORK** (Enhanced)
- **Purpose:** Intelligent task allocation with missing task detection and objective promotion
- **Syntax:** `WORK [agent_id] [task_filter] [parallel_mode]`
- **🆕 Enhanced Behavior:**
  - **Pre-work missing task detection** (scan and add missing tasks first)
  - **Objective completion check** with auto-promotion if complete
  - **Cross-phase parallel task identification**
  - **Agent capacity and capability matching**
  - **Dependency resolution and task ordering**
  - **Real-time conflict detection and resolution**
- **🆕 Enhanced Flow:**
  1. **Check for missing tasks** in current objective
  2. **Add any detected missing tasks** to task pool
  3. **Evaluate objective completion status**
  4. **If complete**: Execute automatic objective promotion
  5. **If incomplete**: Assign available tasks to agent
  6. **Log all actions** and reasoning
- **Output:** Task assignment with completion timeline and any auto-actions taken

#### **STATUS** (Enhanced)
- **Purpose:** Comprehensive system state reporting with task detection status
- **Syntax:** `STATUS [detail_level] [scope] [format]`
- **🆕 Enhanced Reporting:**
  - **Current objective progress** with missing task analysis
  - **Recent missing task detections** and additions
  - **Objective promotion history** and triggers
  - **Task completion velocity** with projection accuracy
  - **Auto-promotion readiness** assessment
  - **Missing task detection patterns** and frequency
  - **Future objective readiness** evaluation
- **🆕 New Status Categories:**
  - `TASK_DETECTION_STATUS`: Missing task scan results
  - `PROMOTION_READINESS`: Objective completion analysis
  - `AUTO_ACTION_HISTORY`: Recent automated system actions

---

## 📐 **Enhanced Rule System with Task Detection & Auto-Promotion**

### 🆕 Rule 11 — Intelligent Missing Task Detection & Auto-Addition

✅ **Missing Task Detection Algorithm:**
```
FUNCTION detect_missing_tasks(objective):
    missing_tasks = []
    
    // Standard Project Pattern Analysis
    FOR each standard_pattern IN project_patterns:
        IF objective.type MATCHES standard_pattern.type:
            required_tasks = standard_pattern.required_tasks
            FOR each required_task IN required_tasks:
                IF required_task NOT IN objective.tasks:
                    missing_tasks.append(required_task)
    
    // Dependency Gap Analysis
    FOR each existing_task IN objective.tasks:
        prerequisites = analyze_prerequisites(existing_task)
        follow_ups = analyze_follow_ups(existing_task)
        
        FOR each prerequisite IN prerequisites:
            IF prerequisite NOT IN objective.tasks:
                missing_tasks.append(prerequisite)
        
        FOR each follow_up IN follow_ups:
            IF follow_up NOT IN objective.tasks:
                missing_tasks.append(follow_up)
    
    // Quality Assurance Check
    qa_tasks = ["Testing", "Review", "Approval", "Documentation"]
    FOR each qa_task IN qa_tasks:
        IF qa_task NOT IN objective.tasks AND objective.requires_qa:
            missing_tasks.append(qa_task)
    
    RETURN deduplicate(missing_tasks)
```

✅ **Auto-Addition Process:**
1. **Detection Trigger:** 
   - During session startup
   - Before work assignment
   - After task completion
   - On-demand via DETECT_MISSING_TASKS command

2. **Addition Workflow:**
   - Generate missing task with appropriate details
   - Assign priority based on dependencies and criticality
   - Add to Current Objective task list
   - Update Task Pool with new work items
   - Log addition with reasoning to `MISSING_TASKS_LOG.md`
   - Notify agents of new tasks available

3. **Quality Controls:**
   - Prevent duplicate task creation
   - Validate task relevance and necessity
   - Ensure proper dependency linking
   - Maintain task priority consistency

### 🆕 Rule 12 — Automatic Objective Promotion & File Migration

✅ **Objective Completion Detection:**
```
FUNCTION check_objective_completion(current_objective):
    all_tasks = load_tasks(current_objective)
    
    FOR each task IN all_tasks:
        IF task.status != "COMPLETED":
            RETURN false
    
    // Additional completion checks
    IF missing_required_deliverables(current_objective):
        RETURN false
    
    IF outstanding_dependencies(current_objective):
        RETURN false
    
    RETURN true
```

✅ **Automatic Promotion Process:**
```
FUNCTION auto_promote_objective():
    IF check_objective_completion(current_objective):
        // 1. Archive Current Objective
        archive_path = create_archive_entry(current_objective)
        move_files(current_objective_path, archive_path)
        
        // 2. Select Next Objective
        future_objectives = scan_directory("Future Objectives/")
        next_objective = select_highest_priority(future_objectives)
        
        // 3. Migrate Files
        source_path = "Future Objectives/" + next_objective
        target_path = "Current Objective/"
        move_files(source_path, target_path)
        
        // 4. Atomize Objective
        tasks = parse_objective_tasks(next_objective)
        atomized_tasks = atomize_tasks(tasks)
        update_task_pool(atomized_tasks)
        
        // 5. Update System State
        log_promotion(current_objective, next_objective)
        notify_all_agents("NEW_OBJECTIVE_PROMOTED")
        update_system_status()
        
        RETURN next_objective
    
    RETURN null
```

✅ **File Migration Standards:**
- **Complete Directory Transfer:** Move entire objective folder structure
- **Preserve File Relationships:** Maintain internal links and dependencies
- **Update Path References:** Automatically update any absolute path references
- **Metadata Preservation:** Keep creation dates, permissions, and attributes
- **Backup Creation:** Create backup before migration for rollback capability

### 🆕 Rule 14 — Agent Timeout Detection & Automatic Task Reassignment

✅ **Heartbeat Monitoring System:**
```
FUNCTION monitor_agent_heartbeats():
    current_time = get_current_timestamp()
    active_agents = load_agent_registry()
    timeout_events = []
    
    FOR each agent IN active_agents:
        last_heartbeat = agent.last_heartbeat_timestamp
        time_since_heartbeat = current_time - last_heartbeat
        
        // Timeout Detection Logic
        IF time_since_heartbeat > SOFT_TIMEOUT (5 minutes):
            log_warning("Agent soft timeout", agent.id)
            send_ping_request(agent.id)
        
        IF time_since_heartbeat > HARD_TIMEOUT (10 minutes):
            timeout_events.append({
                agent_id: agent.id,
                timeout_duration: time_since_heartbeat,
                assigned_tasks: get_agent_tasks(agent.id),
                last_known_status: agent.last_status,
                timeout_type: "HARD_TIMEOUT"
            })
        
        IF time_since_heartbeat > CRITICAL_TIMEOUT (15 minutes):
            mark_agent_as_failed(agent.id)
            escalate_to_supervisor(agent.id, "CRITICAL_TIMEOUT")
    
    // Process timeout events
    FOR each timeout_event IN timeout_events:
        process_agent_timeout(timeout_event)
    
    RETURN timeout_events
```

✅ **Automatic Task Reassignment Algorithm:**
```
FUNCTION process_agent_timeout(timeout_event):
    timed_out_agent = timeout_event.agent_id
    abandoned_tasks = timeout_event.assigned_tasks
    
    FOR each task IN abandoned_tasks:
        // Preserve task state
        task_state = save_task_state(task)
        task_progress = get_task_progress(task)
        
        // Find suitable replacement agent
        available_agents = get_available_agents()
        suitable_agents = filter_by_capability(available_agents, task.required_skills)
        
        IF suitable_agents.count > 0:
            // Select best agent based on workload and capability
            replacement_agent = select_optimal_agent(suitable_agents, task)
            
            // Execute reassignment
            reassign_result = execute_task_reassignment(
                task_id = task.id,
                from_agent = timed_out_agent,
                to_agent = replacement_agent,
                preserved_state = task_state,
                progress_data = task_progress
            )
            
            // Log reassignment
            log_task_reassignment(reassign_result)
            
            // Notify new agent
            notify_agent_new_assignment(replacement_agent, task, task_state)
            
        ELSE:
            // No suitable agents available
            mark_task_as_queued(task)
            alert_supervisor("No available agents for reassignment", task)
            log_reassignment_failure(task, "NO_SUITABLE_AGENTS")
```

✅ **Agent Selection Criteria for Reassignment:**
```
FUNCTION select_optimal_agent(candidate_agents, task):
    scored_agents = []
    
    FOR each agent IN candidate_agents:
        score = 0
        
        // Capability matching (40% weight)
        capability_match = calculate_skill_match(agent.skills, task.required_skills)
        score += capability_match * 0.4
        
        // Current workload (30% weight)
        workload_factor = 1.0 - (agent.current_tasks / agent.max_capacity)
        score += workload_factor * 0.3
        
        // Agent reliability (20% weight)
        reliability_score = agent.completion_rate * agent.uptime_percentage
        score += reliability_score * 0.2
        
        // Task similarity experience (10% weight)
        similarity_score = calculate_task_similarity(agent.completed_tasks, task)
        score += similarity_score * 0.1
        
        scored_agents.append({agent: agent, score: score})
    
    // Return highest scoring agent
    best_agent = max(scored_agents, key=lambda x: x.score)
    RETURN best_agent.agent
```

✅ **State Preservation During Reassignment:**
```
FUNCTION execute_task_reassignment(task_id, from_agent, to_agent, preserved_state, progress_data):
    // Create handoff package
    handoff_package = {
        task_id: task_id,
        original_agent: from_agent,
        new_agent: to_agent,
        task_state: preserved_state,
        progress_percentage: progress_data.completion_percent,
        work_completed: progress_data.completed_items,
        notes: progress_data.agent_notes,
        files_created: progress_data.output_files,
        next_steps: progress_data.planned_actions,
        estimated_remaining_time: recalculate_time_estimate(progress_data),
        reassignment_timestamp: get_current_timestamp(),
        reassignment_reason: "AGENT_TIMEOUT"
    }
    
    // Update task ownership
    update_task_assignment(task_id, to_agent)
    
    // Update agent workloads
    remove_task_from_agent(from_agent, task_id)
    add_task_to_agent(to_agent, task_id)
    
    // Preserve work artifacts
    transfer_work_files(from_agent, to_agent, task_id)
    
    // Update project timeline
    adjust_timeline_for_reassignment(task_id, handoff_package)
    
    // Log complete reassignment
    log_detailed_reassignment(handoff_package)
    
    RETURN handoff_package
```

### 🆕 Rule 15 — Continuous Background Monitoring

✅ **Background Agent Monitor (Always Running):**
```
BACKGROUND_PROCESS monitor_system():
    WHILE system_active:
        // Run every 30 seconds
        sleep(30)
        
        // Check agent heartbeats
        timeout_events = monitor_agent_heartbeats()
        
        // Process any timeouts found
        IF timeout_events.count > 0:
            FOR each event IN timeout_events:
                process_agent_timeout(event)
        
        // Update system health metrics
        update_system_health_dashboard()
        
        // Check for system-wide issues
        detect_system_anomalies()
        
        // Cleanup old heartbeat data
        cleanup_expired_heartbeat_records()
```

✅ **Enhanced Agent Lifecycle Management:**
```
// Agent startup procedure
FUNCTION agent_startup(agent_id):
    register_agent(agent_id)
    initialize_heartbeat_schedule(agent_id)
    send_initial_heartbeat(agent_id)
    request_work_assignment(agent_id)

// Agent shutdown procedure  
FUNCTION agent_shutdown(agent_id):
    save_current_task_state(agent_id)
    mark_tasks_for_reassignment(agent_id)
    deregister_agent(agent_id)
    cleanup_agent_resources(agent_id)

// Heartbeat update procedure
FUNCTION send_heartbeat(agent_id, status, current_task, progress):
    heartbeat_data = {
        agent_id: agent_id,
        timestamp: get_current_timestamp(),
        status: status,
        current_task: current_task,
        progress_percent: progress,
        memory_usage: get_memory_usage(),
        cpu_usage: get_cpu_usage(),
        error_count: get_recent_error_count(),
        next_heartbeat_due: get_current_timestamp() + 120 // 2 minutes
    }
    
    update_heartbeat_monitor(heartbeat_data)
    update_agent_registry(heartbeat_data)
```

✅ **Agent Startup Enhancement:**
Every agent session MUST execute this enhanced startup sequence:

1. **Initialize Agent Session**
2. **🆕 Run Missing Task Detection:**
   ```
   missing_tasks = DETECT_MISSING_TASKS(current_objective)
   IF missing_tasks.count > 0:
       log_missing_tasks(missing_tasks)
       add_tasks_to_objective(missing_tasks)
   ```

3. **🆕 Check Objective Completion:**
   ```
   IF check_objective_completion(current_objective):
       promoted_objective = auto_promote_objective()
       IF promoted_objective:
           log_promotion_success(promoted_objective)
       ELSE:
           log_promotion_failure()
   ```

4. **Continue Standard Startup Sequence** (maintenance, work assignment, etc.)

✅ **Enhanced Work Assignment Logic:**
```
FUNCTION enhanced_work_assignment(agent_id):
    // Pre-work checks
    detect_and_add_missing_tasks()
    
    IF objective_completion_detected():
        auto_promote_objective()
    
    // Standard work assignment
    available_tasks = get_available_tasks()
    IF available_tasks.count == 0:
        RETURN "NO_WORK_AVAILABLE"
    
    assigned_task = select_best_task(agent_id, available_tasks)
    RETURN assigned_task
```

---

## 📄 **Enhanced Logging & Documentation**

### 🆕 AGENT_TIMEOUT_LOG.md Structure
```markdown
# Agent Timeout Detection Log

## Timeout Event: [Timestamp]
- **Agent ID:** [Timed-out agent identifier]
- **Timeout Duration:** [Minutes since last heartbeat]
- **Timeout Type:** [SOFT/HARD/CRITICAL]
- **Last Known Status:** [Agent's last reported status]
- **Detection Method:** [Heartbeat/Manual/System]

### Agent State at Timeout:
- **Assigned Tasks:** [List of tasks agent was working on]
- **Task Progress:** [Completion percentages for each task]
- **Last Activity:** [Timestamp of last recorded activity]
- **Resource Usage:** [CPU/Memory at last heartbeat]
- **Error History:** [Recent errors or issues]

### Timeout Response Actions:
- **Immediate Actions:** [Ping attempts, status checks]
- **Reassignment Triggered:** [Yes/No]
- **Tasks Affected:** [Count and list]
- **Agents Notified:** [List of agents alerted]
- **Supervisor Escalation:** [Yes/No - for critical timeouts]

### Recovery Attempts:
- **Ping Results:** [Response/No Response]
- **Agent Recovery:** [Agent came back online: Yes/No]
- **Recovery Timestamp:** [If agent recovered]
- **Tasks Resumed:** [Count of tasks returned to original agent]
```

### 🆕 TASK_REASSIGNMENT_LOG.md Structure
```markdown
# Task Reassignment Log

## Reassignment Event: [Timestamp]
- **Trigger:** [Agent timeout/Manual/Emergency]
- **Original Agent:** [Agent that was originally assigned]
- **New Agent:** [Agent receiving the reassignment]
- **Task ID:** [Unique task identifier]
- **Task Name:** [Human-readable task name]

### Task State Transfer:
- **Progress Completed:** [Percentage]
- **Work Items Done:** [List of completed subtasks]
- **Files Created:** [List of output files/artifacts]
- **Agent Notes:** [Previous agent's notes and observations]
- **Estimated Remaining Time:** [Recalculated estimate]

### Reassignment Process:
- **State Preservation:** [Successful/Partial/Failed]
- **File Transfer:** [List of files moved to new agent]
- **Dependencies Updated:** [Yes/No]
- **Timeline Adjusted:** [New completion estimate]
- **Agent Capability Match:** [Compatibility score]

### Agent Selection Criteria:
- **Available Agents Considered:** [Count]
- **Selection Factors:**
  - **Skill Match:** [Score/10]
  - **Current Workload:** [Tasks assigned]
  - **Reliability Score:** [Historical performance]
  - **Task Similarity:** [Experience with similar tasks]
- **Selected Agent Justification:** [Why this agent was chosen]

### Post-Reassignment Status:
- **Handoff Successful:** [Yes/No]
- **New Agent Started:** [Timestamp]
- **Issues Encountered:** [Any problems during transition]
- **Timeline Impact:** [Delay estimate]
- **Quality Impact:** [Potential quality concerns]

### Follow-up Actions:
- **Monitoring Schedule:** [Increased monitoring for reassigned task]
- **Original Agent Status:** [Recovery/Replacement/Investigation]
- **Lessons Learned:** [Process improvements identified]
```

### 🆕 HEARTBEAT_MONITOR.json Structure
```json
{
  "monitoring_config": {
    "scan_interval_seconds": 30,
    "soft_timeout_minutes": 5,
    "hard_timeout_minutes": 10,
    "critical_timeout_minutes": 15,
    "max_missed_heartbeats": 5,
    "auto_reassignment_enabled": true
  },
  "active_agents": {
    "agent_001": {
      "agent_id": "agent_001",
      "status": "ACTIVE",
      "last_heartbeat": "2025-05-31T10:30:00Z",
      "next_heartbeat_due": "2025-05-31T10:32:00Z",
      "current_task": "task_456",
      "task_progress": 65,
      "consecutive_missed_heartbeats": 0,
      "health_status": "HEALTHY",
      "resource_usage": {
        "cpu_percent": 45,
        "memory_mb": 256,
        "disk_io_rate": "low"
      },
      "capability_tags": ["analysis", "documentation", "testing"],
      "max_concurrent_tasks": 3,
      "current_task_count": 1
    }
  },
  "timeout_history": [
    {
      "timestamp": "2025-05-31T09:15:00Z",
      "agent_id": "agent_002",
      "timeout_type": "HARD_TIMEOUT",
      "duration_minutes": 12,
      "reassignment_successful": true,
      "tasks_affected": ["task_123", "task_124"]
    }
  ],
  "system_health": {
    "total_active_agents": 3,
    "agents_in_timeout": 0,
    "successful_reassignments_today": 2,
    "failed_reassignments_today": 0,
    "average_agent_uptime_percent": 97.5
  }
}
```
```markdown
# Missing Tasks Detection Log

## Detection Entry: [Timestamp]
- **Agent ID:** [Agent performing detection]
- **Objective:** [Target objective name]
- **Detection Trigger:** [Startup/Manual/Scheduled]
- **Scan Scope:** [Full objective/Specific area]

### Detected Missing Tasks:
1. **Task Name:** [Generated task name]
   - **Type:** [Task category]
   - **Priority:** [Assigned priority level]
   - **Dependencies:** [Required prerequisites]
   - **Reasoning:** [Why this task was identified as missing]
   - **Auto-Added:** [Yes/No]

### Summary:
- **Total Missing Tasks Detected:** [Count]
- **Tasks Auto-Added:** [Count]
- **Tasks Requiring Manual Review:** [Count]
- **Detection Accuracy:** [Confidence score]
- **Next Scheduled Detection:** [Timestamp]
```

### 🆕 OBJECTIVE_PROMOTION_LOG.md Structure
```markdown
# Objective Promotion Log

## Promotion Entry: [Timestamp]
- **Trigger Agent:** [Agent that triggered promotion]
- **Completed Objective:** [Name of completed objective]
- **Promoted Objective:** [Name of newly promoted objective]
- **Promotion Trigger:** [Auto/Manual]

### Completion Verification:
- **Total Tasks in Completed Objective:** [Count]
- **Completed Tasks:** [Count]
- **Remaining Tasks:** [Count] (Should be 0)
- **Outstanding Dependencies:** [List any remaining]
- **Completion Verification:** [PASSED/FAILED]

### Promotion Process:
- **Archive Location:** [Path to archived objective]
- **Source Location:** [Original path in Future Objectives]
- **Target Location:** [New path in Current Objective]
- **Files Migrated:** [Count and list]
- **Atomized Tasks Created:** [Count]
- **Task Pool Updated:** [Yes/No]

### Post-Promotion Status:
- **New Objective Status:** [Active/Pending/Error]
- **Agent Notifications Sent:** [Count]
- **System Status Updated:** [Yes/No]
- **Next Promotion Eligibility:** [Estimated date]

### Issues/Warnings:
- **Migration Errors:** [Any file migration issues]
- **Dependency Conflicts:** [Cross-objective dependency issues]
- **Agent Conflicts:** [Any agent assignment conflicts]
```

---

## 🔧 **Implementation Guidelines**

### Missing Task Detection Triggers
1. **Automatic Triggers:**
   - Agent session startup (mandatory)
   - Before work assignment
   - After task completion
   - Weekly comprehensive scan

2. **Manual Triggers:**
   - DETECT_MISSING_TASKS command
   - Supervisor-initiated scan
   - Post-objective modification

3. **Smart Triggers:**
   - When task dependencies change
   - When objective scope expands
   - When similar objectives complete elsewhere

### Objective Promotion Triggers
1. **Automatic Triggers:**
   - All current objective tasks marked complete
   - No remaining work items in task pool
   - All dependencies satisfied

2. **Manual Triggers:**
   - PROMOTE_OBJECTIVE command
   - Supervisor-initiated promotion
   - Emergency objective change

3. **Validation Checks:**
   - Complete deliverable verification
   - Stakeholder approval confirmation
   - Quality assurance completion

---

## 🚨 **Error Handling & Recovery**

### Missing Task Detection Errors
- **Detection Failure:** Log error, continue with existing tasks
- **Invalid Task Generation:** Mark for manual review
- **Duplicate Task Creation:** Merge with existing task
- **Priority Conflict:** Use conservative priority assignment

### Objective Promotion Errors
- **Incomplete Objective:** Halt promotion, log incomplete items
- **File Migration Failure:** Rollback changes, alert supervisor
- **No Future Objectives:** Create placeholder objective, alert supervisor
- **Dependency Conflicts:** Resolve dependencies, retry promotion
- **Heartbeat Detection Failure:** Continue monitoring, log anomaly
- **Task State Preservation Failure:** Create manual recovery task, alert supervisor
- **No Suitable Replacement Agent:** Queue task for later assignment, escalate
- **Reassignment Process Failure:** Rollback assignment, mark task as urgent
- **State Transfer Corruption:** Restore from last checkpoint, document data loss

### Enhanced Error Recovery Procedures
- **Timeout False Positives:** Implement agent verification ping before reassignment
- **Cascading Agent Failures:** Emergency scaling protocol with supervisor notification
- **Task State Corruption:** Automated backup restoration with integrity verification
- **Critical Task Abandonment:** Immediate supervisor escalation with priority override
- **System-Wide Agent Failure:** Disaster recovery activation with external notification

---

✅ **Enhanced System Summary:**

This enhanced Warp Agent system now provides intelligent missing task detection with automatic addition to current objectives, seamless automatic objective promotion with complete file migration from Future Objectives to Current Objective directory, and robust agent timeout detection with automatic task reassignment. The system continuously monitors for task gaps, ensures project completeness, automatically advances workflow, and maintains operational continuity even when agents fail or become unresponsive, all while maintaining full audit trails and error recovery capabilities.

Key enhancements include:
- **🆕 AI-driven missing task detection** with auto-addition
- **🆕 Automatic objective promotion** with file migration
- **🆕 Agent timeout detection** with automatic task reassignment
- **🆕 Continuous background monitoring** of agent health and heartbeats
- **🆕 Intelligent task reassignment** with state preservation and capability matching
- **🆕 Enhanced logging** for all automated actions including timeouts and reassignments
- **🆕 Comprehensive error handling** and recovery for all failure scenarios
- **🆕 Background resilience** ensuring system operation continues despite individual agent failures
- **🆕 Integration** with existing workflow and maintenance systems
