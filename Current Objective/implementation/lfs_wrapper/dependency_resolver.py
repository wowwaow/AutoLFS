"""
Dependency resolution system for LFS build scripts.

Provides functionality for managing build dependencies, detecting
circular dependencies, and resolving version constraints.

Dependencies:
    - networkx>=2.6
    - packaging>=21.0
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx
from packaging.specifiers import SpecifierSet
from packaging.version import Version, parse

from .exceptions import (
    CircularDependencyError,
    ConflictError,
    DependencyError,
    VersionError
)


class DependencyType(Enum):
    """Types of package dependencies."""
    REQUIRED = auto()
    OPTIONAL = auto()
    BUILD = auto()
    TEST = auto()


@dataclass
class VersionConstraint:
    """Represents a version constraint for a package."""
    specifier: str
    package: str

    def __post_init__(self):
        """Validate the version specifier."""
        try:
            SpecifierSet(self.specifier)
        except Exception as e:
            raise VersionError(f"Invalid version specifier '{self.specifier}': {e}")

    def matches(self, version: str) -> bool:
        """Check if a version matches this constraint."""
        try:
            return Version(version) in SpecifierSet(self.specifier)
        except Exception as e:
            raise VersionError(f"Invalid version format '{version}': {e}")


@dataclass
class Dependency:
    """Represents a package dependency."""
    name: str
    version_constraint: Optional[VersionConstraint] = None
    dependency_type: DependencyType = DependencyType.REQUIRED
    alternatives: List[str] = None

    def __post_init__(self):
        """Initialize alternatives list if None."""
        if self.alternatives is None:
            self.alternatives = []


class DependencyResolver:
    """
    Manages package dependencies and their resolution.

    Handles dependency graph construction, cycle detection,
    version constraints, and dependency resolution.

    Attributes:
        graph (nx.DiGraph): Dependency graph
        packages (Dict): Package information dictionary
        logger (logging.Logger): Logger instance
    """

    def __init__(self):
        """Initialize the dependency resolver."""
        self.graph = nx.DiGraph()
        self.packages: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)

    def add_package(
        self,
        name: str,
        version: str,
        dependencies: List[Dependency]
    ) -> None:
        """
        Add a package and its dependencies to the graph.

        Args:
            name: Package name
            version: Package version
            dependencies: List of package dependencies

        Raises:
            VersionError: If version format is invalid
            DependencyError: If dependency specification is invalid
        """
        try:
            parse(version)  # Validate version format
        except Exception as e:
            raise VersionError(f"Invalid version format for {name}: {e}")

        self.packages[name] = {
            'version': version,
            'dependencies': dependencies
        }

        # Add nodes and edges to the graph
        self.graph.add_node(name, version=version)
        for dep in dependencies:
            self.graph.add_edge(name, dep.name, constraint=dep.version_constraint)

        # Verify no cycles were introduced
        try:
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                cycle = ' -> '.join(cycles[0])
                raise CircularDependencyError(
                    f"Circular dependency detected: {cycle}"
                )
        except CircularDependencyError:
            # Remove the added nodes/edges
            self.graph.remove_node(name)
            del self.packages[name]
            raise

    def resolve_dependencies(self, package: str) -> List[str]:
        """
        Resolve dependencies for a package in build order.

        Args:
            package: Name of the package to resolve dependencies for

        Returns:
            List[str]: List of packages in build order

        Raises:
            DependencyError: If dependencies cannot be resolved
        """
        if package not in self.packages:
            raise DependencyError(f"Package not found: {package}")

        try:
            # Get all dependencies (direct and transitive)
            deps = nx.descendants(self.graph, package)
            # Add the package itself
            deps.add(package)
            
            # Create subgraph of relevant dependencies
            subgraph = self.graph.subgraph(deps)
            
            # Get topological sort (build order)
            build_order = list(reversed(list(nx.topological_sort(subgraph))))
            
            return build_order
        
        except nx.NetworkXUnfeasible:
            raise DependencyError(f"Cannot resolve dependencies for {package}")

    def verify_constraints(self, package: str) -> bool:
        """
        Verify version constraints for a package and its dependencies.

        Args:
            package: Name of the package to verify

        Returns:
            bool: True if all constraints are satisfied

        Raises:
            VersionError: If version constraints are not satisfied
        """
        if package not in self.packages:
            raise DependencyError(f"Package not found: {package}")

        pkg_info = self.packages[package]
        deps = self.packages[package]['dependencies']

        for dep in deps:
            if dep.name not in self.packages:
                raise DependencyError(f"Dependency not found: {dep.name}")

            if dep.version_constraint:
                dep_version = self.packages[dep.name]['version']
                if not dep.version_constraint.matches(dep_version):
                    raise VersionError(
                        f"Version constraint not satisfied for {dep.name}: "
                        f"required {dep.version_constraint.specifier}, "
                        f"found {dep_version}"
                    )

        return True

    def find_conflicts(self, package: str) -> List[Tuple[str, str, str]]:
        """
        Find version conflicts in package dependencies.

        Args:
            package: Name of the package to check for conflicts

        Returns:
            List[Tuple[str, str, str]]: List of conflicts (package, dep, reason)
        """
        conflicts = []
        deps = self.resolve_dependencies(package)

        for dep in deps:
            try:
                self.verify_constraints(dep)
            except VersionError as e:
                conflicts.append((package, dep, str(e)))

        return conflicts

    def resolve_conflict(
        self,
        package: str,
        conflict: Tuple[str, str, str]
    ) -> Optional[str]:
        """
        Attempt to resolve a dependency conflict.

        Args:
            package: Name of the package with conflict
            conflict: Conflict tuple (package, dep, reason)

        Returns:
            Optional[str]: Resolution strategy or None if unresolvable

        Raises:
            ConflictError: If conflict cannot be resolved
        """
        conflicting_pkg, dep, reason = conflict
        pkg_info = self.packages[conflicting_pkg]
        
        # Check for alternative versions
        for dep_info in pkg_info['dependencies']:
            if dep_info.name == dep and dep_info.alternatives:
                for alt in dep_info.alternatives:
                    try:
                        if self.verify_constraints(alt):
                            return f"Use alternative: {alt}"
                    except (VersionError, DependencyError):
                        continue

        raise ConflictError(
            f"Unable to resolve conflict in {package}: {reason}"
        )

    def get_build_order(self, packages: List[str]) -> List[str]:
        """
        Get optimal build order for multiple packages.

        Args:
            packages: List of package names to build

        Returns:
            List[str]: Packages in optimal build order

        Raises:
            DependencyError: If build order cannot be determined
        """
        try:
            # Create set of all packages and their dependencies
            all_pkgs = set()
            for pkg in packages:
                deps = set(self.resolve_dependencies(pkg))
                all_pkgs.update(deps)
            
            # Create subgraph and get topological sort
            subgraph = self.graph.subgraph(all_pkgs)
            return list(reversed(list(nx.topological_sort(subgraph))))
        
        except nx.NetworkXUnfeasible as e:
            raise DependencyError(f"Cannot determine build order: {e}")

