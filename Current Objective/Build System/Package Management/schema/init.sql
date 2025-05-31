-- Package Management System Schema Initialization
-- Version: 1.0.0
-- Created: 2025-05-31

-- Enable foreign key support and WAL mode
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -2000;  -- 2MB cache

-- Create packages table
CREATE TABLE IF NOT EXISTS packages (
    package_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    maintainer TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('draft', 'pending', 'building', 'built', 'failed', 'archived', 'deprecated')
    ),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT CHECK (json_valid(metadata_json)),
    CONSTRAINT valid_name CHECK (name REGEXP '^[a-zA-Z0-9][a-zA-Z0-9_.-]*$')
);

-- Create package versions table
CREATE TABLE IF NOT EXISTS package_versions (
    version_id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('draft', 'testing', 'stable', 'deprecated', 'archived')
    ),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    build_requirements_json TEXT CHECK (json_valid(build_requirements_json)),
    metadata_json TEXT CHECK (json_valid(metadata_json)),
    FOREIGN KEY (package_id) REFERENCES packages(package_id) ON DELETE CASCADE,
    CONSTRAINT valid_version CHECK (
        version REGEXP '^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?(?:\+[a-zA-Z0-9]+)?$'
    ),
    UNIQUE (package_id, version)
);

-- Create dependencies table
CREATE TABLE IF NOT EXISTS dependencies (
    dependency_id TEXT PRIMARY KEY,
    package_version_id TEXT NOT NULL,
    required_package_id TEXT NOT NULL,
    version_constraint TEXT NOT NULL,
    dependency_type TEXT NOT NULL DEFAULT 'required'
        CHECK (dependency_type IN ('required', 'optional', 'build_time', 'dev_only')),
    optional_features_json TEXT CHECK (json_valid(optional_features_json)),
    FOREIGN KEY (package_version_id) 
        REFERENCES package_versions(version_id) ON DELETE CASCADE,
    FOREIGN KEY (required_package_id) 
        REFERENCES packages(package_id) ON DELETE RESTRICT
);

-- Create build records table
CREATE TABLE IF NOT EXISTS build_records (
    build_id TEXT PRIMARY KEY,
    package_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('draft', 'pending', 'building', 'built', 'failed', 'archived', 'deprecated')
    ),
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error_message TEXT,
    performance_metrics_json TEXT CHECK (json_valid(performance_metrics_json)),
    FOREIGN KEY (package_id) REFERENCES packages(package_id),
    FOREIGN KEY (version_id) REFERENCES package_versions(version_id),
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

-- Create state records table
CREATE TABLE IF NOT EXISTS state_records (
    record_id TEXT PRIMARY KEY,
    state_type TEXT NOT NULL CHECK (
        state_type IN ('build', 'test', 'deploy', 'rollback', 'cleanup')
    ),
    state_data_json TEXT NOT NULL CHECK (json_valid(state_data_json)),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    previous_state_id TEXT,
    FOREIGN KEY (previous_state_id) REFERENCES state_records(record_id)
);

-- Create performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    metric_id TEXT PRIMARY KEY,
    metric_type TEXT NOT NULL CHECK (
        metric_type IN ('build_time', 'memory_usage', 'cpu_usage', 'disk_usage', 'network_usage')
    ),
    value REAL NOT NULL CHECK (value >= 0),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    context_json TEXT CHECK (json_valid(context_json))
);

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    record_id TEXT NOT NULL,
    old_values_json TEXT,
    new_values_json TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT NOT NULL
);

-- Create indices for performance optimization

-- Packages indices
CREATE INDEX IF NOT EXISTS idx_packages_name ON packages(name);
CREATE INDEX IF NOT EXISTS idx_packages_status ON packages(status);
CREATE INDEX IF NOT EXISTS idx_packages_maintainer ON packages(maintainer);

-- Package versions indices
CREATE INDEX IF NOT EXISTS idx_versions_package ON package_versions(package_id);
CREATE INDEX IF NOT EXISTS idx_versions_status ON package_versions(status);

-- Dependencies indices
CREATE INDEX IF NOT EXISTS idx_deps_package_version ON dependencies(package_version_id);
CREATE INDEX IF NOT EXISTS idx_deps_required_package ON dependencies(required_package_id);

-- Build records indices
CREATE INDEX IF NOT EXISTS idx_builds_package ON build_records(package_id);
CREATE INDEX IF NOT EXISTS idx_builds_version ON build_records(version_id);
CREATE INDEX IF NOT EXISTS idx_builds_status ON build_records(status);
CREATE INDEX IF NOT EXISTS idx_builds_dates ON build_records(started_at, completed_at);

-- State records indices
CREATE INDEX IF NOT EXISTS idx_states_type ON state_records(state_type);
CREATE INDEX IF NOT EXISTS idx_states_timestamp ON state_records(timestamp);

-- Performance metrics indices
CREATE INDEX IF NOT EXISTS idx_metrics_type ON performance_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp);

-- Audit log indices
CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);

