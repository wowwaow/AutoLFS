-- Package Management System Triggers
-- Version: 1.0.0
-- Created: 2025-05-31

-- Package update timestamp trigger
CREATE TRIGGER IF NOT EXISTS trg_packages_update_timestamp
AFTER UPDATE ON packages
BEGIN
    UPDATE packages 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE package_id = NEW.package_id;
END;

-- Build record completion trigger
CREATE TRIGGER IF NOT EXISTS trg_build_completion
AFTER UPDATE OF status ON build_records
WHEN NEW.status IN ('built', 'failed')
BEGIN
    UPDATE build_records
    SET completed_at = CURRENT_TIMESTAMP
    WHERE build_id = NEW.build_id 
    AND completed_at IS NULL;
END;

-- Version status change trigger
CREATE TRIGGER IF NOT EXISTS trg_version_status_change
AFTER UPDATE OF status ON package_versions
BEGIN
    INSERT INTO state_records (
        record_id,
        state_type,
        state_data_json
    ) VALUES (
        hex(randomblob(16)),
        'build',
        json_object(
            'version_id', NEW.version_id,
            'old_status', OLD.status,
            'new_status', NEW.status,
            'timestamp', CURRENT_TIMESTAMP
        )
    );
END;

-- Package status validation trigger
CREATE TRIGGER IF NOT EXISTS trg_package_status_validation
BEFORE UPDATE OF status ON packages
BEGIN
    SELECT CASE
        WHEN NEW.status = 'built' 
             AND NOT EXISTS (
                 SELECT 1 FROM build_records 
                 WHERE package_id = NEW.package_id 
                 AND status = 'built'
             )
        THEN RAISE(ABORT, 'Cannot mark package as built without successful build record')
        WHEN NEW.status = 'deprecated' 
             AND EXISTS (
                 SELECT 1 FROM package_versions 
                 WHERE package_id = NEW.package_id 
                 AND status = 'stable'
             )
        THEN RAISE(ABORT, 'Cannot deprecate package with stable versions')
    END;
END;

-- Audit logging triggers
CREATE TRIGGER IF NOT EXISTS trg_audit_packages_insert
AFTER INSERT ON packages
BEGIN
    INSERT INTO audit_log (
        audit_id,
        table_name,
        operation,
        record_id,
        new_values_json,
        user_id
    ) VALUES (
        hex(randomblob(16)),
        'packages',
        'INSERT',
        NEW.package_id,
        json_object(
            'name', NEW.name,
            'status', NEW.status,
            'maintainer', NEW.maintainer
        ),
        COALESCE((SELECT user_id FROM sqlite_master LIMIT 1), 'system')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_packages_update
AFTER UPDATE ON packages
BEGIN
    INSERT INTO audit_log (
        audit_id,
        table_name,
        operation,
        record_id,
        old_values_json,
        new_values_json,
        user_id
    ) VALUES (
        hex(randomblob(16)),
        'packages',
        'UPDATE',
        NEW.package_id,
        json_object(
            'status', OLD.status,
            'maintainer', OLD.maintainer
        ),
        json_object(
            'status', NEW.status,
            'maintainer', NEW.maintainer
        ),
        COALESCE((SELECT user_id FROM sqlite_master LIMIT 1), 'system')
    );
END;

-- Performance metrics trigger
CREATE TRIGGER IF NOT EXISTS trg_build_performance_metrics
AFTER UPDATE OF status ON build_records
WHEN NEW.status = 'built'
BEGIN
    -- Record build time
    INSERT INTO performance_metrics (
        metric_id,
        metric_type,
        value,
        context_json
    ) 
    SELECT
        hex(randomblob(16)),
        'build_time',
        (julianday(NEW.completed_at) - julianday(NEW.started_at)) * 86400,
        json_object(
            'package_id', NEW.package_id,
            'version_id', NEW.version_id,
            'build_id', NEW.build_id
        );
        
    -- Parse and record other metrics from performance_metrics_json
    INSERT INTO performance_metrics (
        metric_id,
        metric_type,
        value,
        context_json
    )
    SELECT
        hex(randomblob(16)),
        json_each.key,
        CAST(json_each.value AS REAL),
        json_object(
            'package_id', NEW.package_id,
            'version_id', NEW.version_id,
            'build_id', NEW.build_id
        )
    FROM json_each(NEW.performance_metrics_json)
    WHERE json_each.key IN ('memory_usage', 'cpu_usage', 'disk_usage', 'network_usage');
END;

-- Dependency cycle prevention trigger
CREATE TRIGGER IF NOT EXISTS trg_prevent_dependency_cycles
BEFORE INSERT ON dependencies
BEGIN
    WITH RECURSIVE dep_check(required_id, depth) AS (
        -- Base case: direct dependency
        SELECT NEW.required_package_id, 1
        UNION ALL
        -- Recursive case: follow chain
        SELECT d.required_package_id, dc.depth + 1
        FROM dependencies d
        JOIN dep_check dc ON d.package_version_id IN (
            SELECT version_id 
            FROM package_versions 
            WHERE package_id = dc.required_id
        )
        WHERE dc.depth < 50  -- Prevent infinite recursion
    )
    SELECT CASE
        WHEN EXISTS (
            SELECT 1 FROM package_versions
            WHERE version_id = NEW.package_version_id
            AND package_id IN (SELECT required_id FROM dep_check)
        )
        THEN RAISE(ABORT, 'Dependency cycle detected')
    END;
END;

-- Version constraint validation trigger
CREATE TRIGGER IF NOT EXISTS trg_version_constraint_validation
BEFORE INSERT ON dependencies
BEGIN
    SELECT CASE
        WHEN NEW.version_constraint NOT REGEXP '^([<>=~^]+)?[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'
        THEN RAISE(ABORT, 'Invalid version constraint format')
    END;
END;

