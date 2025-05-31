-- Package Management System Views
-- Version: 1.0.0
-- Created: 2025-05-31

-- Current Package Status View
CREATE VIEW IF NOT EXISTS v_package_status AS
SELECT 
    p.package_id,
    p.name,
    p.status AS package_status,
    pv.version,
    pv.status AS version_status,
    pv.created_at AS version_created,
    br.status AS build_status,
    br.started_at AS build_started,
    br.completed_at AS build_completed
FROM packages p
LEFT JOIN package_versions pv ON p.package_id = pv.package_id
LEFT JOIN build_records br ON pv.version_id = br.version_id
WHERE pv.version_id = (
    SELECT version_id 
    FROM package_versions 
    WHERE package_id = p.package_id 
    ORDER BY created_at DESC 
    LIMIT 1
);

-- Package Dependencies View
CREATE VIEW IF NOT EXISTS v_package_dependencies AS
SELECT 
    p.name AS package_name,
    pv.version,
    dep_p.name AS dependency_name,
    d.version_constraint,
    d.dependency_type,
    d.optional_features_json
FROM dependencies d
JOIN package_versions pv ON d.package_version_id = pv.version_id
JOIN packages p ON pv.package_id = p.package_id
JOIN packages dep_p ON d.required_package_id = dep_p.package_id;

-- Complete Build History View
CREATE VIEW IF NOT EXISTS v_build_history AS
SELECT 
    p.name AS package_name,
    pv.version,
    br.status AS build_status,
    br.started_at,
    br.completed_at,
    br.error_message,
    br.performance_metrics_json,
    CASE 
        WHEN br.completed_at IS NOT NULL 
        THEN round((julianday(br.completed_at) - julianday(br.started_at)) * 86400)
        ELSE NULL 
    END as build_duration_seconds
FROM build_records br
JOIN package_versions pv ON br.version_id = pv.version_id
JOIN packages p ON br.package_id = p.package_id
ORDER BY br.started_at DESC;

-- Performance Metrics Summary View
CREATE VIEW IF NOT EXISTS v_performance_summary AS
SELECT 
    metric_type,
    COUNT(*) as measurement_count,
    MIN(value) as min_value,
    MAX(value) as max_value,
    AVG(value) as avg_value,
    strftime('%Y-%m-%d', timestamp) as measurement_date
FROM performance_metrics
GROUP BY metric_type, measurement_date
ORDER BY measurement_date DESC;

-- Package Build Success Rate View
CREATE VIEW IF NOT EXISTS v_build_success_rate AS
SELECT 
    p.name AS package_name,
    COUNT(*) as total_builds,
    SUM(CASE WHEN br.status = 'built' THEN 1 ELSE 0 END) as successful_builds,
    ROUND(CAST(SUM(CASE WHEN br.status = 'built' THEN 1 ELSE 0 END) AS FLOAT) / 
          COUNT(*) * 100, 2) as success_rate_percent,
    AVG(CASE 
        WHEN br.completed_at IS NOT NULL 
        THEN (julianday(br.completed_at) - julianday(br.started_at)) * 86400
        ELSE NULL 
    END) as avg_build_duration_seconds
FROM packages p
JOIN build_records br ON p.package_id = br.package_id
GROUP BY p.name
ORDER BY success_rate_percent DESC;

-- Recent Build Status View
CREATE VIEW IF NOT EXISTS v_recent_builds AS
SELECT 
    p.name AS package_name,
    pv.version,
    br.status AS build_status,
    br.started_at,
    br.completed_at,
    br.error_message,
    CASE 
        WHEN br.completed_at IS NOT NULL 
        THEN round((julianday(br.completed_at) - julianday(br.started_at)) * 86400)
        ELSE NULL 
    END as build_duration_seconds
FROM build_records br
JOIN package_versions pv ON br.version_id = pv.version_id
JOIN packages p ON br.package_id = p.package_id
WHERE br.started_at >= datetime('now', '-7 days')
ORDER BY br.started_at DESC;

-- Dependency Chain View
CREATE VIEW IF NOT EXISTS v_dependency_chain AS
WITH RECURSIVE dep_chain AS (
    -- Base case: direct dependencies
    SELECT 
        d.package_version_id,
        d.required_package_id,
        d.dependency_type,
        1 as depth,
        d.required_package_id as path
    FROM dependencies d
    
    UNION ALL
    
    -- Recursive case: indirect dependencies
    SELECT 
        dc.package_version_id,
        d.required_package_id,
        d.dependency_type,
        dc.depth + 1,
        dc.path || ',' || d.required_package_id
    FROM dependencies d
    JOIN dep_chain dc ON d.package_version_id = dc.required_package_id
    WHERE dc.depth < 10  -- Prevent infinite recursion
)
SELECT 
    pv.package_id as source_package_id,
    p_src.name as source_package_name,
    pv.version as source_version,
    p_dep.name as dependency_name,
    dc.dependency_type,
    dc.depth as dependency_depth,
    dc.path as dependency_path
FROM dep_chain dc
JOIN package_versions pv ON dc.package_version_id = pv.version_id
JOIN packages p_src ON pv.package_id = p_src.package_id
JOIN packages p_dep ON dc.required_package_id = p_dep.package_id;

-- State Transition History View
CREATE VIEW IF NOT EXISTS v_state_transitions AS
SELECT 
    sr.record_id,
    sr.state_type,
    sr.timestamp,
    prev.state_type as previous_state_type,
    prev.timestamp as previous_timestamp,
    CASE 
        WHEN prev.timestamp IS NOT NULL 
        THEN round((julianday(sr.timestamp) - julianday(prev.timestamp)) * 86400)
        ELSE NULL 
    END as transition_duration_seconds
FROM state_records sr
LEFT JOIN state_records prev ON sr.previous_state_id = prev.record_id
ORDER BY sr.timestamp DESC;

