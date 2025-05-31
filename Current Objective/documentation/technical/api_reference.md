# API Reference

## Core API

### System Management API

#### `init(config_path: str = None) -> Result<Config, Error>`
Initializes the wrapper system with optional configuration path.
```rust
// Example usage
let config = init("/etc/lfs-wrapper/config.yaml")?;
```

#### `status() -> Result<SystemStatus, Error>`
Returns current system status including build progress and health metrics.
```rust
// Example usage
let status = status()?;
println!("Build progress: {}%", status.progress);
```

#### `health_check() -> Result<HealthStatus, Error>`
Performs comprehensive system health check.
```rust
// Example usage
let health = health_check()?;
assert!(health.is_healthy());
```

### Build Management API

#### `build_start(options: BuildOptions) -> Result<BuildProcess, Error>`
Starts the build process with specified options.
```rust
// Example usage
let options = BuildOptions {
    parallel_jobs: 4,
    memory_limit: "8G",
    package_set: "desktop",
};
let process = build_start(options)?;
```

#### `build_pause() -> Result<(), Error>`
Pauses current build process.
```rust
// Example usage
build_pause()?;
```

#### `build_resume() -> Result<(), Error>`
Resumes paused build process.
```rust
// Example usage
build_resume()?;
```

### Checkpoint Management API

#### `checkpoint_create(name: str) -> Result<Checkpoint, Error>`
Creates new build checkpoint.
```rust
// Example usage
let checkpoint = checkpoint_create("pre_desktop")?;
```

#### `checkpoint_list() -> Result<Vec<Checkpoint>, Error>`
Lists available checkpoints.
```rust
// Example usage
let checkpoints = checkpoint_list()?;
```

#### `checkpoint_restore(id: str) -> Result<(), Error>`
Restores system to specified checkpoint.
```rust
// Example usage
checkpoint_restore("checkpoint_123")?;
```

### Package Management API

#### `package_list() -> Result<Vec<Package>, Error>`
Lists available packages.
```rust
// Example usage
let packages = package_list()?;
```

#### `package_info(name: str) -> Result<PackageInfo, Error>`
Returns detailed package information.
```rust
// Example usage
let info = package_info("gcc")?;
```

### Monitoring API

#### `monitor_start() -> Result<Monitor, Error>`
Starts system monitoring.
```rust
// Example usage
let monitor = monitor_start()?;
```

#### `monitor_stats() -> Result<Stats, Error>`
Returns current monitoring statistics.
```rust
// Example usage
let stats = monitor_stats()?;
```

### Configuration API

#### `config_get(key: str) -> Result<Value, Error>`
Retrieves configuration value.
```rust
// Example usage
let value = config_get("build.parallel_jobs")?;
```

#### `config_set(key: str, value: Value) -> Result<(), Error>`
Sets configuration value.
```rust
// Example usage
config_set("build.memory_limit", "16G")?;
```

## Data Types

### SystemStatus
```rust
struct SystemStatus {
    state: State,
    progress: f32,
    current_phase: String,
    errors: Vec<Error>,
    warnings: Vec<Warning>,
}
```

### BuildOptions
```rust
struct BuildOptions {
    parallel_jobs: u32,
    memory_limit: String,
    disk_threshold: String,
    package_set: String,
}
```

### Checkpoint
```rust
struct Checkpoint {
    id: String,
    timestamp: DateTime,
    description: String,
    size: u64,
    state: CheckpointState,
}
```

### Package
```rust
struct Package {
    name: String,
    version: String,
    dependencies: Vec<String>,
    status: PackageStatus,
}
```

### Monitor
```rust
struct Monitor {
    metrics: Vec<Metric>,
    alerts: Vec<Alert>,
    thresholds: HashMap<String, f64>,
}
```

## Error Handling

All API functions return a Result type that can contain the following errors:

### SystemError
- INIT_FAILED
- CONFIG_INVALID
- PERMISSION_DENIED
- RESOURCE_UNAVAILABLE

### BuildError
- BUILD_FAILED
- DEPENDENCY_MISSING
- CHECKSUM_MISMATCH
- TIMEOUT

### CheckpointError
- CHECKPOINT_CREATION_FAILED
- CHECKPOINT_NOT_FOUND
- RESTORE_FAILED

## Events and Callbacks

### BuildEvents
```rust
enum BuildEvent {
    Started { timestamp: DateTime },
    Progress { percent: f32 },
    Paused { reason: String },
    Resumed { timestamp: DateTime },
    Completed { success: bool },
    Failed { error: BuildError },
}
```

### Callback Registration
```rust
fn register_callback(event: BuildEvent, callback: fn(BuildEvent)) -> Result<(), Error>
```

## Resource Management

### Resource Limits
```rust
struct ResourceLimits {
    cpu_cores: u32,
    memory_gb: u32,
    disk_space_gb: u32,
    build_timeout: Duration,
}
```

### Resource Monitoring
```rust
fn monitor_resources() -> Result<ResourceUsage, Error>
```

