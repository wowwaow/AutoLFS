"""
BLFS package analysis and dependency management system.

Analyzes BLFS package dependencies, relationships, and build order
requirements. Handles validation, configuration, and maintenance.

Dependencies:
    - networkx>=2.6
    - tqdm>=4.65
"""

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx
import yaml

from .exceptions import (
    BLFSAnalysisError,
    BLFSConfigError,
    BLFSValidationError
)


class DependencyType(Enum):
    """Types of BLFS package dependencies."""
    REQUIRED = auto()      # Must be installed
    RECOMMENDED = auto()   # Should be installed
    OPTIONAL = auto()      # May be installed
    TEST = auto()         # Required for testing
    RUNTIME = auto()      # Required at runtime
    BUILD = auto()        # Required for building


@dataclass
class DependencyInfo:
    """Information about a package dependency."""
    name: str
    type: DependencyType
    version: Optional[str]
    build_order: Optional[int]
    description: str
    alternatives: List[str]


@dataclass
class PackageInfo:
    """Comprehensive BLFS package information."""
    name: str
    version: str
    description: str
    dependencies: List[DependencyInfo]
    build_commands: List[str]
    test_commands: List[str]
    post_install: List[str]
    configuration: Dict[str, str]
    validated: bool = False


class BLFSAnalyzer:
    """
    Analyzes BLFS packages and their relationships.

    Provides package analysis, dependency resolution, validation,
    and maintenance capabilities.

    Attributes:
        config (Dict): Analysis configuration
        package_db (Dict): Package information database
        dependency_graph (nx.DiGraph): Package dependency graph
        logger (logging.Logger): Logger instance
    """

    def __init__(self, config: Dict):
        """Initialize BLFS analyzer."""
        self.config = config
        self.package_db = {}
        self.dependency_graph = nx.DiGraph()
        self.logger = logging.getLogger(__name__)

    def analyze_package(self, package_name: str) -> PackageInfo:
        """
        Analyze a BLFS package and its dependencies.

        Args:
            package_name: Name of package to analyze

        Returns:
            PackageInfo: Package information

        Raises:
            BLFSAnalysisError: If analysis fails
        """
        try:
            # Load package information
            pkg_info = self._load_package_info(package_name)
            
            # Analyze dependencies
            deps = self._analyze_dependencies(pkg_info)
            
            # Create package info
            package = PackageInfo(
                name=package_name,
                version=pkg_info['version'],
                description=pkg_info['description'],
                dependencies=deps,
                build_commands=pkg_info['build_commands'],
                test_commands=pkg_info.get('test_commands', []),
                post_install=pkg_info.get('post_install', []),
                configuration=pkg_info.get('configuration', {})
            )
            
            # Add to database
            self.package_db[package_name] = package
            
            # Update dependency graph
            self._update_dependency_graph(package)
            
            return package
            
        except Exception as e:
            raise BLFSAnalysisError(f"Failed to analyze {package_name}: {e}")

    def optimize_build_order(self, packages: List[str]) -> List[str]:
        """
        Optimize build order for a set of packages.

        Args:
            packages: List of packages to optimize

        Returns:
            List[str]: Optimized build order

        Raises:
            BLFSAnalysisError: If optimization fails
        """
        try:
            # Ensure all packages are analyzed
            for pkg in packages:
                if pkg not in self.package_db:
                    self.analyze_package(pkg)
            
            # Create subgraph of required packages
            pkgs = set(packages)
            for pkg in packages:
                deps = self._get_all_dependencies(pkg)
                pkgs.update(deps)
            
            subgraph = self.dependency_graph.subgraph(pkgs)
            
            # Get build order (reverse topological sort)
            try:
                build_order = list(reversed(list(nx.topological_sort(subgraph))))
                return build_order
            except nx.NetworkXUnfeasible:
                raise BLFSAnalysisError("Circular dependency detected")
            
        except Exception as e:
            raise BLFSAnalysisError(f"Failed to optimize build order: {e}")

    def validate_package(self, package_name: str) -> bool:
        """
        Validate a BLFS package installation.

        Args:
            package_name: Package to validate

        Returns:
            bool: True if validation passes

        Raises:
            BLFSValidationError: If validation fails
        """
        try:
            pkg = self.package_db.get(package_name)
            if not pkg:
                pkg = self.analyze_package(package_name)
            
            # Run validation checks
            self._validate_installation(pkg)
            self._validate_configuration(pkg)
            self._validate_dependencies(pkg)
            
            # Run test commands
            if pkg.test_commands:
                self._run_test_commands(pkg)
            
            pkg.validated = True
            return True
            
        except Exception as e:
            raise BLFSValidationError(f"Validation failed for {package_name}: {e}")

    def manage_configuration(
        self,
        package_name: str,
        config: Dict[str, str]
    ) -> None:
        """
        Manage package configuration.

        Args:
            package_name: Package to configure
            config: Configuration settings

        Raises:
            BLFSConfigError: If configuration fails
        """
        try:
            pkg = self.package_db.get(package_name)
            if not pkg:
                pkg = self.analyze_package(package_name)
            
            # Validate configuration
            self._validate_config_settings(pkg, config)
            
            # Update configuration
            pkg.configuration.update(config)
            
            # Apply configuration
            self._apply_configuration(pkg)
            
        except Exception as e:
            raise BLFSConfigError(f"Configuration failed for {package_name}: {e}")

    def check_updates(self) -> Dict[str, Tuple[str, str]]:
        """
        Check for package updates.

        Returns:
            Dict[str, Tuple[str, str]]: Package update info (current, available)
        """
        updates = {}
        
        for pkg_name, pkg in self.package_db.items():
            try:
                available = self._check_available_version(pkg_name)
                if available and available != pkg.version:
                    updates[pkg_name] = (pkg.version, available)
            except Exception as e:
                self.logger.error(f"Failed to check updates for {pkg_name}: {e}")
        
        return updates

    def _load_package_info(self, package_name: str) -> Dict:
        """Load package information from BLFS database."""
        db_path = Path(self.config['blfs']['package_db'])
        if not db_path.exists():
            raise BLFSAnalysisError("Package database not found")
        
        try:
            with open(db_path) as f:
                data = yaml.safe_load(f)
                if package_name not in data['packages']:
                    raise BLFSAnalysisError(f"Package not found: {package_name}")
                return data['packages'][package_name]
        except Exception as e:
            raise BLFSAnalysisError(f"Failed to load package info: {e}")

    def _analyze_dependencies(self, pkg_info: Dict) -> List[DependencyInfo]:
        """Analyze package dependencies."""
        deps = []
        
        # Process each dependency type
        for dep_type in DependencyType:
            type_deps = pkg_info.get(f"{dep_type.name.lower()}_dependencies", [])
            for dep in type_deps:
                # Parse dependency string (name[>=version])
                match = re.match(r"([^[]+)(?:\[([^\]]+)\])?", dep)
                if match:
                    name, version = match.groups()
                    deps.append(DependencyInfo(
                        name=name.strip(),
                        type=dep_type,
                        version=version,
                        build_order=None,
                        description=self._get_dep_description(name),
                        alternatives=self._get_dep_alternatives(name)
                    ))
        
        return deps

    def _get_dep_description(self, dep_name: str) -> str:
        """Get dependency description."""
        try:
            if dep_name in self.package_db:
                return self.package_db[dep_name].description
            info = self._load_package_info(dep_name)
            return info['description']
        except Exception:
            return "No description available"

    def _get_dep_alternatives(self, dep_name: str) -> List[str]:
        """Get alternative packages for a dependency."""
        try:
            if dep_name in self.package_db:
                return []  # No alternatives for known packages
            info = self._load_package_info(dep_name)
            return info.get('alternatives', [])
        except Exception:
            return []

    def _update_dependency_graph(self, package: PackageInfo) -> None:
        """Update dependency graph with package information."""
        # Add package node
        self.dependency_graph.add_node(
            package.name,
            version=package.version,
            info=package
        )
        
        # Add dependency edges
        for dep in package.dependencies:
            self.dependency_graph.add_edge(
                package.name,
                dep.name,
                type=dep.type,
                version=dep.version
            )

    def _get_all_dependencies(self, package_name: str) -> Set[str]:
        """Get all dependencies for a package."""
        deps = set()
        for dep in self.package_db[package_name].dependencies:
            deps.add(dep.name)
            if dep.name in self.package_db:
                deps.update(self._get_all_dependencies(dep.name))
        return deps

    def _validate_installation(self, package: PackageInfo) -> None:
        """Validate package installation."""
        # Check package files
        self._check_package_files(package)
        
        # Verify version
        installed_version = self._get_installed_version(package.name)
        if not installed_version:
            raise BLFSValidationError(f"Package {package.name} not installed")
        if installed_version != package.version:
            raise BLFSValidationError(
                f"Version mismatch: expected {package.version}, "
                f"found {installed_version}"
            )

    def _validate_configuration(self, package: PackageInfo) -> None:
        """Validate package configuration."""
        for key, value in package.configuration.items():
            if not self._check_config_value(package.name, key, value):
                raise BLFSValidationError(
                    f"Invalid configuration: {key}={value}"
                )

    def _validate_dependencies(self, package: PackageInfo) -> None:
        """Validate package dependencies."""
        for dep in package.dependencies:
            if dep.type == DependencyType.REQUIRED:
                if not self._check_dependency_installed(dep):
                    raise BLFSValidationError(
                        f"Required dependency not installed: {dep.name}"
                    )

    def _run_test_commands(self, package: PackageInfo) -> None:
        """Run package test commands."""
        for cmd in package.test_commands:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise BLFSValidationError(
                    f"Test failed: {cmd}\n{result.stderr}"
                )

    def _validate_config_settings(
        self,
        package: PackageInfo,
        config: Dict[str, str]
    ) -> None:
        """Validate configuration settings."""
        # Load config schema
        schema = self._load_config_schema(package.name)
        
        # Validate against schema
        for key, value in config.items():
            if key not in schema:
                raise BLFSConfigError(f"Unknown config option: {key}")
            if not self._validate_config_value(value, schema[key]):
                raise BLFSConfigError(
                    f"Invalid value for {key}: {value}"
                )

    def _apply_configuration(self, package: PackageInfo) -> None:
        """Apply package configuration."""
        for key, value in package.configuration.items():
            try:
                self._set_config_value(package.name, key, value)
            except Exception as e:
                raise BLFSConfigError(
                    f"Failed to set {key}={value}: {e}"
                )

    def _check_package_files(self, package: PackageInfo) -> None:
        """Check package file installation."""
        # Get file list
        file_list = self._get_package_files(package.name)
        
        # Check each file
        for file_path in file_list:
            if not Path(file_path).exists():
                raise BLFSValidationError(f"Missing file: {file_path}")

    def _get_installed_version(self, package_name: str) -> Optional[str]:
        """Get installed package version."""
        try:
            result = subprocess.run(
                ['pkg-config', '--modversion', package_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _check_dependency_installed(self, dependency: DependencyInfo) -> bool:
        """Check if a dependency is installed."""
        version = self._get_installed_version(dependency.name)
        if not version:
            return False
        
        if dependency.version:
            # Check version constraint
            constraint = dependency.version.split()[0]
            version_num = dependency.version.split()[1]
            
            if constraint == '>=':
                return version >= version_num
            elif constraint == '<=':
                return version <= version_num
            elif constraint == '==':
                return version == version_num
            
        return True

    def _load_config_schema(self, package_name: str) -> Dict:
        """Load package configuration schema."""
        try:
            with open(self.config['blfs']['schema_db']) as f:
                data = yaml.safe_load(f)
                return data['packages'].get(package_name, {}).get('config', {})
        except Exception as e:
            raise BLFSConfigError(f"Failed to load config schema: {e}")

    def _validate_config_value(self, value: str, schema: Dict) -> bool:
        """Validate a configuration value against schema."""
        try:
            value_type = schema['type']
            if value_type == 'string':
                pattern = schema.get('pattern')
                if pattern and not re.match(pattern, value):
                    return False
            elif value_type == 'integer':
                value = int(value)
                min_val = schema.get('minimum')
                max_val = schema.get('maximum')
                if min_val is not None and value < min_val:
                    return False
                if max_val is not None and value > max_val:
                    return False
            elif value_type == 'boolean':
                value = value.lower()
                if value not in ['true', 'false', '1', '0']:
                    return False
            return True
        except Exception:
            return False

    def _set_config_value(
        self,
        package_name: str,
        key: str,
        value: str
    ) -> None:
        """Set a configuration value."""
        try:
            # Get config file path
            config_file = self._get_config_file(package_name, key)
            if not config_file:
                raise BLFSConfigError(f"No config file for {key}")
            
            # Read current config
            with open(config_file) as f:
                content = f.read()
            
            # Update config
            if not self._update_config_file(config_file, key, value):
                raise BLFSConfigError(f"Failed to update {key}")
            
        except Exception as e:
            raise BLFSConfigError(f"Failed to set config: {e}")

    def _get_config_file(self, package_name: str, key: str) -> Optional[Path]:
        """Get configuration file path for a setting."""
        try:
            with open(self.config['blfs']['config_map']) as f:
                data = yaml.safe_load(f)
                return Path(
                    data['packages'][package_name]['config_files'][key]
                )
        except Exception:
            return None

    def _update_config_file(
        self,
        file_path: Path,
        key: str,
        value: str
    ) -> bool:
        """Update a configuration file."""
        try:
            with open(file_path) as f:
                lines = f.readlines()
            
            # Find and update key
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    break
            else:
                lines.append(f"{key}={value}\n")
            
            # Write back
            with open(file_path, 'w') as f:
                f.writelines(lines)
            
            return True
        except Exception:
            return False

    def _check_available_version(self, package_name: str) -> Optional[str]:
        """Check available package version."""
        try:
            info = self._load_package_info(package_name)
            return info['version']
        except Exception:
            return None

