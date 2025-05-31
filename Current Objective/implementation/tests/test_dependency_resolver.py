"""
Unit tests for the DependencyResolver class.

Tests dependency resolution, cycle detection, version constraints,
and conflict resolution functionality.
"""

import pytest
from packaging.version import Version

from lfs_wrapper.dependency_resolver import (
    Dependency,
    DependencyResolver,
    DependencyType,
    VersionConstraint
)
from lfs_wrapper.exceptions import (
    CircularDependencyError,
    ConflictError,
    DependencyError,
    VersionError
)


@pytest.fixture
def resolver():
    """Provide a fresh DependencyResolver instance."""
    return DependencyResolver()


def test_version_constraint_validation():
    """Test version constraint validation."""
    # Valid constraints
    assert VersionConstraint(">=1.0.0", "test")
    assert VersionConstraint("~=2.0", "test")
    
    # Invalid constraints
    with pytest.raises(VersionError):
        VersionConstraint("invalid", "test")


def test_version_constraint_matching():
    """Test version constraint matching."""
    constraint = VersionConstraint(">=1.0.0", "test")
    
    assert constraint.matches("1.0.0")
    assert constraint.matches("1.1.0")
    assert not constraint.matches("0.9.0")
    
    with pytest.raises(VersionError):
        constraint.matches("invalid")


def test_add_package(resolver):
    """Test adding a package with dependencies."""
    deps = [
        Dependency("dep1", VersionConstraint(">=1.0.0", "dep1")),
        Dependency("dep2", dependency_type=DependencyType.OPTIONAL)
    ]
    
    resolver.add_package("test", "1.0.0", deps)
    assert "test" in resolver.packages
    assert resolver.packages["test"]["version"] == "1.0.0"
    assert len(resolver.packages["test"]["dependencies"]) == 2


def test_add_package_invalid_version(resolver):
    """Test adding a package with invalid version."""
    with pytest.raises(VersionError):
        resolver.add_package("test", "invalid", [])


def test_circular_dependency_detection(resolver):
    """Test circular dependency detection."""
    # Add packages that would create a cycle
    resolver.add_package("pkg1", "1.0.0", [
        Dependency("pkg2")
    ])
    resolver.add_package("pkg2", "1.0.0", [
        Dependency("pkg3")
    ])
    
    # This would create a cycle
    with pytest.raises(CircularDependencyError):
        resolver.add_package("pkg3", "1.0.0", [
            Dependency("pkg1")
        ])


def test_resolve_dependencies(resolver):
    """Test dependency resolution."""
    # Create a simple dependency chain
    resolver.add_package("pkg3", "1.0.0", [])
    resolver.add_package("pkg2", "1.0.0", [
        Dependency("pkg3")
    ])
    resolver.add_package("pkg1", "1.0.0", [
        Dependency("pkg2")
    ])
    
    build_order = resolver.resolve_dependencies("pkg1")
    assert build_order == ["pkg3", "pkg2", "pkg1"]


def test_resolve_dependencies_missing_package(resolver):
    """Test resolving dependencies for non-existent package."""
    with pytest.raises(DependencyError):
        resolver.resolve_dependencies("nonexistent")


def test_verify_constraints(resolver):
    """Test version constraint verification."""
    # Add packages with version constraints
    resolver.add_package("dep", "2.0.0", [])
    resolver.add_package("test", "1.0.0", [
        Dependency("dep", VersionConstraint(">=2.0.0", "dep"))
    ])
    
    assert resolver.verify_constraints("test")


def test_verify_constraints_failure(resolver):
    """Test version constraint verification failure."""
    # Add packages with incompatible versions
    resolver.add_package("dep", "1.0.0", [])
    resolver.add_package("test", "1.0.0", [
        Dependency("dep", VersionConstraint(">=2.0.0", "dep"))
    ])
    
    with pytest.raises(VersionError):
        resolver.verify_constraints("test")


def test_find_conflicts(resolver):
    """Test finding dependency conflicts."""
    # Create conflicting dependencies
    resolver.add_package("dep", "1.0.0", [])
    resolver.add_package("test", "1.0.0", [
        Dependency("dep", VersionConstraint(">=2.0.0", "dep"))
    ])
    
    conflicts = resolver.find_conflicts("test")
    assert len(conflicts) == 1
    assert conflicts[0][0] == "test"
    assert conflicts[0][1] == "dep"


def test_resolve_conflict_with_alternative(resolver):
    """Test conflict resolution using alternatives."""
    # Add packages with alternative versions
    resolver.add_package("dep-alt", "2.0.0", [])
    resolver.add_package("dep", "1.0.0", [])
    resolver.add_package("test", "1.0.0", [
        Dependency(
            "dep",
            VersionConstraint(">=2.0.0", "dep"),
            alternatives=["dep-alt"]
        )
    ])
    
    conflicts = resolver.find_conflicts("test")
    resolution = resolver.resolve_conflict("test", conflicts[0])
    assert resolution == "Use alternative: dep-alt"


def test_resolve_conflict_unresolvable(resolver):
    """Test handling of unresolvable conflicts."""
    # Create conflict with no alternatives
    resolver.add_package("dep", "1.0.0", [])
    resolver.add_package("test", "1.0.0", [
        Dependency("dep", VersionConstraint(">=2.0.0", "dep"))
    ])
    
    conflicts = resolver.find_conflicts("test")
    with pytest.raises(ConflictError):
        resolver.resolve_conflict("test", conflicts[0])


def test_get_build_order_multiple_packages(resolver):
    """Test getting build order for multiple packages."""
    # Create dependency network
    resolver.add_package("base", "1.0.0", [])
    resolver.add_package("lib1", "1.0.0", [
        Dependency("base")
    ])
    resolver.add_package("lib2", "1.0.0", [
        Dependency("base")
    ])
    resolver.add_package("app", "1.0.0", [
        Dependency("lib1"),
        Dependency("lib2")
    ])
    
    build_order = resolver.get_build_order(["app", "lib1"])
    assert build_order.index("base") < build_order.index("lib1")
    assert build_order.index("lib1") < build_order.index("app")


def test_get_build_order_impossible(resolver):
    """Test handling of impossible build orders."""
    # Create conflicting requirements
    resolver.add_package("pkg1", "1.0.0", [
        Dependency("pkg2")
    ])
    resolver.add_package("pkg2", "1.0.0", [
        Dependency("pkg1")
    ])
    
    with pytest.raises(DependencyError):
        resolver.get_build_order(["pkg1", "pkg2"])


def test_dependency_type_handling(resolver):
    """Test handling of different dependency types."""
    resolver.add_package("test", "1.0.0", [
        Dependency("required", dependency_type=DependencyType.REQUIRED),
        Dependency("optional", dependency_type=DependencyType.OPTIONAL),
        Dependency("build", dependency_type=DependencyType.BUILD),
        Dependency("test", dependency_type=DependencyType.TEST)
    ])
    
    assert len(resolver.packages["test"]["dependencies"]) == 4
    deps = resolver.packages["test"]["dependencies"]
    assert any(d.dependency_type == DependencyType.REQUIRED for d in deps)
    assert any(d.dependency_type == DependencyType.OPTIONAL for d in deps)
    assert any(d.dependency_type == DependencyType.BUILD for d in deps)
    assert any(d.dependency_type == DependencyType.TEST for d in deps)

