"""
BLFS package management and integration module.

Manages BLFS package selection, configuration, building, and maintenance
using the core build infrastructure.

Dependencies:
    - networkx>=2.6
    - packaging>=21.0
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml
from packaging.version import Version, parse

from .build_manager import BuildManager, BuildPhase
from .build_scheduler import BuildPriority, BuildScheduler
from .dependency_resolver import DependencyResolver, VersionConstraint
from .exceptions import (
    BLFSError,
    ConfigurationError,
    ValidationError,
    VersionError
)


class PackageStatus(Enum):
    """BLFS package status indicators."""
    NOT_INSTALLED = auto()
    INSTALLED = auto()
    NEEDS_UPDATE = auto()
    FAILED = auto()


@dataclass
class BLFSPackage:
    """Represents a BLFS package configuration."""
    name: str
    version: str
    source_url: str
    dependencies: List[str]
    optional_dependencies: List[str]
    configure_options: List[str]
    build_options: Dict[str, str]
    install_options: Dict[str, str]
    post_install_commands: List[str]
    test_commands: List[str]
    status: PackageStatus = PackageStatus.NOT_INSTALLED


class BLFSManager:
    """
    Manages BLFS package operations.

    Handles package selection, configuration, building, and maintenance
    using the core build infrastructure.

    Attributes:
        build_manager (BuildManager): Core build process manager
        dependency_resolver (DependencyResolver): Dependency resolution
        build_scheduler (BuildScheduler): Build scheduling
        config (Dict): BLFS configuration
        packages (Dict[str, BLFSPackage]): Known packages
    """

    def __init__(
        self,
        build_manager: BuildManager,
        dependency_resolver: DependencyResolver,
        build_scheduler: BuildScheduler,
        config: Dict
    ):
        """Initialize the BLFS manager."""
        self.build_manager = build_manager
        self.dependency_resolver = dependency_resolver
        self.build_scheduler = build_scheduler
        self.config = config
        self.packages: Dict[str, BLFSPackage] = {}
        self.logger = logging.getLogger(__name__)
        
        self._load_package_database()
        self._validate_config()

    def _load_package_database(self) -> None:
        """Load BLFS package database."""
        db_path = Path(self.config['blfs']['package_db'])
        if not db_path.exists():
            raise ConfigurationError(f"Package database not found: {db_path}")

        try:
            with open(db_path, 'r') as f:
                data = yaml.safe_load(f)
                
            for pkg_data in data['packages']:
                pkg = BLFSPackage(
                    name=pkg_data['name'],
                    version=pkg_data['version'],
                    source_url=pkg_data['source_url'],
                    dependencies=pkg_data.get('dependencies', []),
                    optional_dependencies=pkg_data.get('optional_dependencies', []),
                    configure_options=pkg_data.get('configure_options', []),
                    build_options=pkg_data.get('build_options', {}),
                    install_options=pkg_data.get('install_options', {}),
                    post_install_commands=pkg_data.get('post_install', []),
                    test_commands=pkg_data.get('tests', [])
                )
                self.packages[pkg.name] = pkg
                
        except Exception as e:
            raise ConfigurationError(f"Failed to load package database: {e}")

    def _validate_config(self) -> None:
        """Validate BLFS configuration."""
        required = ['package_db', 'build_dir', 'install_dir', 'source_cache']
        missing = [k for k in required if k not in self.config.get('blfs', {})]
        if missing:
            raise ConfigurationError(
                f"Missing BLFS configuration keys: {', '.join(missing)}"
            )

    def select_package(
        self,
        package: str,
        version: Optional[str] = None
    ) -> BLFSPackage:
        """
        Select a BLFS package for installation.

        Args:
            package: Package name
            version: Optional specific version

        Returns:
            BLFSPackage: Selected package

        Raises:
            BLFSError: If package selection fails
        """
        if package not in self.packages:
            raise BLFSError(f"Package not found: {package}")
        
        pkg = self.packages[package]
        if version and pkg.version != version:
            raise VersionError(
                f"Version mismatch for {package}: "
                f"requested {version}, found {pkg.version}"
            )
        
        return pkg

    def resolve_dependencies(
        self,
        package: str,
        include_optional: bool = False
    ) -> List[str]:
        """
        Resolve all dependencies for a BLFS package.

        Args:
            package: Package name
            include_optional: Whether to include optional dependencies

        Returns:
            List[str]: Resolved dependency list

        Raises:
            BLFSError: If dependency resolution fails
        """
        try:
            pkg = self.select_package(package)
            deps = set(pkg.dependencies)
            if include_optional:
                deps.update(pkg.optional_dependencies)
            
            return self.dependency_resolver.resolve_dependencies(package)
            
        except Exception as e:
            raise BLFSError(f"Failed to resolve dependencies for {package}: {e}")

    def configure_package(
        self,
        package: str,
        options: Optional[Dict] = None
    ) -> None:
        """
        Configure a BLFS package.

        Args:
            package: Package name
            options: Optional configuration options

        Raises:
            BLFSError: If configuration fails
        """
        try:
            pkg = self.select_package(package)
            
            # Update package configuration
            if options:
                pkg.configure_options.extend(
                    [f"--{k}={v}" for k, v in options.items()]
                )
            
            # Write updated configuration
            self._save_package_config(pkg)
            
        except Exception as e:
            raise BLFSError(f"Failed to configure {package}: {e}")

    def build_package(
        self,
        package: str,
        priority: BuildPriority = BuildPriority.NORMAL
    ) -> None:
        """
        Build a BLFS package.

        Args:
            package: Package name
            priority: Build priority level

        Raises:
            BLFSError: If build fails
        """
        try:
            pkg = self.select_package(package)
            
            # Schedule package and dependencies for building
            deps = self.resolve_dependencies(package)
            for dep in deps:
                self.build_scheduler.schedule_build(dep, priority)
            
            # Schedule the package itself
            self.build_scheduler.schedule_build(
                package,
                priority,
                resource_requirements=pkg.build_options.get('resources', {})
            )
            
        except Exception as e:
            raise BLFSError(f"Failed to build {package}: {e}")

    def test_package(self, package: str) -> bool:
        """
        Run post-installation tests for a package.

        Args:
            package: Package name

        Returns:
            bool: True if tests pass

        Raises:
            BLFSError: If testing fails
        """
        try:
            pkg = self.select_package(package)
            
            for test_cmd in pkg.test_commands:
                result = subprocess.run(
                    test_cmd,
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    self.logger.error(
                        f"Test failed for {package}: {result.stderr}"
                    )
                    return False
            
            return True
            
        except Exception as e:
            raise BLFSError(f"Failed to test {package}: {e}")

    def get_package_status(self, package: str) -> PackageStatus:
        """
        Get current status of a package.

        Args:
            package: Package name

        Returns:
            PackageStatus: Current package status
        """
        try:
            pkg = self.select_package(package)
            return pkg.status
        except Exception:
            return PackageStatus.NOT_INSTALLED

    def update_package(self, package: str) -> None:
        """
        Update a package to the latest version.

        Args:
            package: Package name

        Raises:
            BLFSError: If update fails
        """
        try:
            pkg = self.select_package(package)
            current_version = self._get_installed_version(package)
            
            if not current_version:
                raise BLFSError(f"Package not installed: {package}")
            
            if parse(pkg.version) > parse(current_version):
                self.build_package(package, BuildPriority.HIGH)
            
        except Exception as e:
            raise BLFSError(f"Failed to update {package}: {e}")

    def _get_installed_version(self, package: str) -> Optional[str]:
        """Get installed version of a package."""
        try:
            result = subprocess.run(
                f"pkg-config --modversion {package}",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _save_package_config(self, package: BLFSPackage) -> None:
        """Save package configuration to disk."""
        config_dir = Path(self.config['blfs']['config_dir'])
        config_file = config_dir / f"{package.name}.yaml"
        
        config_data = {
            'name': package.name,
            'version': package.version,
            'configure_options': package.configure_options,
            'build_options': package.build_options,
            'install_options': package.install_options
        }
        
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
        except Exception as e:
            self.logger.error(f"Failed to save config for {package.name}: {e}")

    def perform_maintenance(self) -> Dict[str, List[str]]:
        """
        Perform system maintenance checks.

        Returns:
            Dict[str, List[str]]: Maintenance report
        """
        report = {
            'needs_update': [],
            'broken_packages': [],
            'missing_dependencies': []
        }
        
        for name, pkg in self.packages.items():
            try:
                # Check for updates
                current_version = self._get_installed_version(name)
                if current_version and parse(pkg.version) > parse(current_version):
                    report['needs_update'].append(name)
                
                # Verify package health
                if not self.test_package(name):
                    report['broken_packages'].append(name)
                
                # Check dependencies
                deps = self.resolve_dependencies(name)
                for dep in deps:
                    if not self._get_installed_version(dep):
                        report['missing_dependencies'].append(
                            f"{name} missing {dep}"
                        )
                        
            except Exception as e:
                self.logger.error(f"Maintenance check failed for {name}: {e}")
        
        return report

