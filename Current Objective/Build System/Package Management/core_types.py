"""
Core type definitions for the build system package management.

This module defines the fundamental data types and validation logic used
throughout the build system. It includes status enumerations, data classes
for packages, versions, dependencies, and various records.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Union, Any
import re
import json
import uuid

# Custom exceptions
class ValidationError(Exception):
    """Raised when data validation fails."""
    pass

class SerializationError(Exception):
    """Raised when object serialization/deserialization fails."""
    pass

# Status enumerations
class PackageStatus(Enum):
    """Represents the current status of a package."""
    DRAFT = "draft"
    PENDING = "pending"
    BUILDING = "building"
    BUILT = "built"
    FAILED = "failed"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"

class VersionStatus(Enum):
    """Represents the current status of a package version."""
    DRAFT = "draft"
    TESTING = "testing"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

class DependencyType(Enum):
    """Represents the type of dependency relationship."""
    REQUIRED = "required"
    OPTIONAL = "optional"
    BUILD_TIME = "build_time"
    DEV_ONLY = "dev_only"

class StateType(Enum):
    """Represents different types of state records."""
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"
    CLEANUP = "cleanup"

class MetricType(Enum):
    """Represents different types of performance metrics."""
    BUILD_TIME = "build_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_USAGE = "network_usage"

# Validation utilities
def validate_package_name(name: str) -> bool:
    """Validate package name format."""
    if not name:
        raise ValidationError("Package name cannot be empty")
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', name):
        raise ValidationError("Invalid package name format")
    return True

def validate_version_string(version: str) -> bool:
    """Validate semantic version format."""
    if not version:
        raise ValidationError("Version string cannot be empty")
    if not re.match(r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?(?:\+[a-zA-Z0-9]+)?$', version):
        raise ValidationError("Invalid version format")
    return True

def validate_timestamp(timestamp: datetime) -> bool:
    """Validate timestamp is not in the future."""
    if timestamp > datetime.utcnow():
        raise ValidationError("Timestamp cannot be in the future")
    return True

# Core data classes
@dataclass
class Package:
    """
    Represents a package in the build system.
    
    Contains metadata about the package including its name, description,
    maintainer information, and current status.
    """
    name: str
    description: str
    maintainer: str
    status: PackageStatus = PackageStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    package_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate package data after initialization."""
        validate_package_name(self.name)
        validate_timestamp(self.created_at)
        validate_timestamp(self.updated_at)
        
        if self.created_at > self.updated_at:
            raise ValidationError("created_at cannot be after updated_at")
        
        if not self.description:
            raise ValidationError("Description cannot be empty")
        
        if not self.maintainer:
            raise ValidationError("Maintainer cannot be empty")

@dataclass
class PackageVersion:
    """
    Represents a specific version of a package.
    
    Contains version-specific information including build requirements,
    dependencies, and status.
    """
    package_id: str
    version: str
    status: VersionStatus = VersionStatus.DRAFT
    build_requirements: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate version data after initialization."""
        validate_version_string(self.version)
        validate_timestamp(self.created_at)

@dataclass
class Dependency:
    """
    Represents a dependency relationship between packages.
    
    Specifies version constraints and the type of dependency.
    """
    package_name: str
    version_constraint: str
    dependency_type: DependencyType = DependencyType.REQUIRED
    optional_features: List[str] = field(default_factory=list)
    dependency_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Validate dependency data after initialization."""
        validate_package_name(self.package_name)
        if not self.version_constraint:
            raise ValidationError("Version constraint cannot be empty")

@dataclass
class BuildRecord:
    """
    Represents a record of a build operation.
    
    Contains build status, timestamps, and performance metrics.
    """
    package_id: str
    version_id: str
    status: PackageStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    build_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_message: Optional[str] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Validate build record data after initialization."""
        validate_timestamp(self.started_at)
        if self.completed_at:
            validate_timestamp(self.completed_at)
            if self.completed_at < self.started_at:
                raise ValidationError("completed_at cannot be before started_at")

@dataclass
class StateRecord:
    """
    Represents a record of system state.
    
    Tracks state changes and transitions during build operations.
    """
    state_type: StateType
    state_data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    previous_state_id: Optional[str] = None

    def __post_init__(self):
        """Validate state record data after initialization."""
        validate_timestamp(self.timestamp)
        if not self.state_data:
            raise ValidationError("state_data cannot be empty")

@dataclass
class PerformanceMetric:
    """
    Represents a performance metric measurement.
    
    Records performance data with timestamps for analysis.
    """
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metric_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate performance metric data after initialization."""
        validate_timestamp(self.timestamp)
        if self.value < 0:
            raise ValidationError("Metric value cannot be negative")

# JSON serialization support
class CoreTypesEncoder(json.JSONEncoder):
    """Custom JSON encoder for core types."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, '__dataclass_fields__'):
            return asdict(obj)
        return super().default(obj)

def serialize_to_json(obj: Any) -> str:
    """Serialize object to JSON string."""
    try:
        return json.dumps(obj, cls=CoreTypesEncoder)
    except Exception as e:
        raise SerializationError(f"Failed to serialize object: {e}")

def deserialize_from_json(json_str: str, target_class: type) -> Any:
    """Deserialize JSON string to object."""
    try:
        data = json.loads(json_str)
        if issubclass(target_class, Enum):
            return target_class(data)
        
        # Convert string timestamps to datetime objects
        if hasattr(target_class, '__dataclass_fields__'):
            for field_name, field_type in target_class.__annotations__.items():
                if field_type == datetime and field_name in data:
                    data[field_name] = datetime.fromisoformat(data[field_name])
        
        return target_class(**data)
    except Exception as e:
        raise SerializationError(f"Failed to deserialize object: {e}")

