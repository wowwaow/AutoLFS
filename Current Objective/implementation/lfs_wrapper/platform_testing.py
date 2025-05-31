"""
Cross-platform testing framework for LFS/BLFS builds.

Provides functionality for managing distribution-specific requirements
and compatibility validation.

Dependencies:
    - distro>=1.7
"""

import logging
import os
import platform
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import distro
import yaml

from .exceptions import PlatformError


class PlatformType(Enum):
    """Supported platform types."""
    DEBIAN = auto()  # Debian-based: Debian, Ubuntu, etc.
    RHEL = auto()    # Red Hat-based: RHEL, CentOS, Fedora, etc.
    SUSE = auto()    # SUSE-based: openSUSE, SLES, etc.
    ARCH = auto()    # Arch Linux-based: Arch, Manjaro, etc.
    OTHER = auto()   # Other Linux distributions


@dataclass
class PlatformInfo:
    """System platform information."""
    platform_type: PlatformType
    distribution: str
    version: str
    architecture: str
    package_manager: str
    build_tools: Dict[str, str]
    system_libraries: Dict[str, str]


@dataclass
class CompatibilityReport:
    """Platform compatibility analysis report."""
    platform_info: PlatformInfo
    missing_dependencies: List[str]
    incompatible_packages: List[str]
    required_fixes: List[str]
    recommendations: List[str]
    validation_results: Dict[str, bool]


class PlatformManager:
    """
    Manages cross-platform compatibility.

    Handles platform detection, configuration, and compatibility
    validation for different Linux distributions.

    Attributes:
        config (Dict): Platform configuration
        platform_info (PlatformInfo): Current platform information
        logger (logging.Logger): Logger instance
    """

    def __init__(self, config: Dict):
        """Initialize platform manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.platform_info = self._detect_platform()

    def validate_platform(self) -> CompatibilityReport:
        """
        Validate platform compatibility.

        Returns:
            CompatibilityReport: Platform compatibility report

        Raises:
            PlatformError: If validation fails
        """
        try:
            # Check platform dependencies
            missing_deps = self._check_dependencies()
            
            # Check package compatibility
            incompatible = self._check_package_compatibility()
            
            # Generate fixes and recommendations
            fixes = self._generate_fixes(missing_deps, incompatible)
            recommendations = self._generate_recommendations()
            
            # Run platform-specific validation
            validation_results = self._run_platform_validation()
            
            return CompatibilityReport(
                platform_info=self.platform_info,
                missing_dependencies=missing_deps,
                incompatible_packages=incompatible,
                required_fixes=fixes,
                recommendations=recommendations,
                validation_results=validation_results
            )
            
        except Exception as e:
            raise PlatformError(f"Platform validation failed: {e}")

    def get_platform_config(self) -> Dict:
        """
        Get platform-specific configuration.

        Returns:
            Dict: Platform configuration
        """
        try:
            # Load base configuration
            base_config = self.config['platform']['base_config']
            
            # Load platform-specific overrides
            platform_config = self.config['platform']['platforms'].get(
                self.platform_info.platform_type.name.lower(),
                {}
            )
            
            # Merge configurations
            config = base_config.copy()
            config.update(platform_config)
            
            return config
            
        except Exception as e:
            raise PlatformError(f"Failed to get platform config: {e}")

    def install_platform_dependencies(self) -> None:
        """
        Install required platform dependencies.

        Raises:
            PlatformError: If dependency installation fails
        """
        try:
            missing = self._check_dependencies()
            if not missing:
                return
            
            # Get package manager commands
            install_cmd = self._get_package_manager_command('install')
            if not install_cmd:
                raise PlatformError(
                    f"Package manager not supported: {self.platform_info.package_manager}"
                )
            
            # Install missing dependencies
            for package in missing:
                try:
                    subprocess.run(
                        [*install_cmd.split(), package],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                except subprocess.CalledProcessError as e:
                    raise PlatformError(
                        f"Failed to install {package}: {e.stderr}"
                    )
            
        except Exception as e:
            raise PlatformError(f"Failed to install dependencies: {e}")

    def get_build_requirements(self) -> Dict[str, str]:
        """
        Get platform-specific build requirements.

        Returns:
            Dict[str, str]: Build requirements
        """
        try:
            # Get base requirements
            requirements = self.config['platform']['build_requirements']['base'].copy()
            
            # Add platform-specific requirements
            platform_reqs = self.config['platform']['build_requirements'].get(
                self.platform_info.platform_type.name.lower(),
                {}
            )
            requirements.update(platform_reqs)
            
            return requirements
            
        except Exception as e:
            raise PlatformError(f"Failed to get build requirements: {e}")

    def _detect_platform(self) -> PlatformInfo:
        """Detect current platform information."""
        try:
            # Get distribution info
            dist_id = distro.id()
            platform_type = self._get_platform_type(dist_id)
            
            # Get package manager
            pkg_manager = self._detect_package_manager()
            
            # Get build tools versions
            build_tools = self._detect_build_tools()
            
            # Get system libraries
            system_libs = self._detect_system_libraries()
            
            return PlatformInfo(
                platform_type=platform_type,
                distribution=dist_id,
                version=distro.version(),
                architecture=platform.machine(),
                package_manager=pkg_manager,
                build_tools=build_tools,
                system_libraries=system_libs
            )
            
        except Exception as e:
            raise PlatformError(f"Platform detection failed: {e}")

    def _get_platform_type(self, dist_id: str) -> PlatformType:
        """Determine platform type from distribution ID."""
        dist_id = dist_id.lower()
        
        if dist_id in ['debian', 'ubuntu', 'linuxmint']:
            return PlatformType.DEBIAN
        elif dist_id in ['rhel', 'centos', 'fedora']:
            return PlatformType.RHEL
        elif dist_id in ['suse', 'opensuse']:
            return PlatformType.SUSE
        elif dist_id in ['arch', 'manjaro']:
            return PlatformType.ARCH
        else:
            return PlatformType.OTHER

    def _detect_package_manager(self) -> str:
        """Detect system package manager."""
        package_managers = {
            'apt': PlatformType.DEBIAN,
            'dnf': PlatformType.RHEL,
            'yum': PlatformType.RHEL,
            'zypper': PlatformType.SUSE,
            'pacman': PlatformType.ARCH
        }
        
        for pkg_mgr in package_managers:
            result = subprocess.run(
                ['which', pkg_mgr],
                capture_output=True
            )
            if result.returncode == 0:
                return pkg_mgr
        
        return 'unknown'

    def _detect_build_tools(self) -> Dict[str, str]:
        """Detect installed build tools and versions."""
        tools = {}
        
        for tool in ['gcc', 'make', 'ld', 'python3']:
            try:
                result = subprocess.run(
                    [tool, '--version'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    version = re.search(r'\d+\.\d+\.\d+', result.stdout)
                    if version:
                        tools[tool] = version.group(0)
            except Exception:
                continue
        
        return tools

    def _detect_system_libraries(self) -> Dict[str, str]:
        """Detect installed system libraries."""
        libraries = {}
        
        # Common library paths
        lib_paths = ['/lib', '/lib64', '/usr/lib', '/usr/lib64']
        
        for path in lib_paths:
            if not os.path.exists(path):
                continue
            
            for lib in Path(path).glob('*.so*'):
                match = re.match(r'lib([^.]+)\.so\.(\d+\.\d+\.\d+)', lib.name)
                if match:
                    libraries[match.group(1)] = match.group(2)
        
        return libraries

    def _check_dependencies(self) -> List[str]:
        """Check for missing platform dependencies."""
        missing = []
        platform_deps = self.config['platform']['dependencies'].get(
            self.platform_info.platform_type.name.lower(),
            []
        )
        
        for dep in platform_deps:
            if not self._check_package_installed(dep):
                missing.append(dep)
        
        return missing

    def _check_package_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        try:
            cmd = self._get_package_manager_command('query')
            if not cmd:
                return False
            
            result = subprocess.run(
                [*cmd.split(), package],
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_package_manager_command(self, action: str) -> Optional[str]:
        """Get package manager command for action."""
        commands = {
            'apt': {
                'install': 'apt-get install -y',
                'query': 'dpkg -l'
            },
            'dnf': {
                'install': 'dnf install -y',
                'query': 'rpm -q'
            },
            'yum': {
                'install': 'yum install -y',
                'query': 'rpm -q'
            },
            'zypper': {
                'install': 'zypper install -y',
                'query': 'rpm -q'
            },
            'pacman': {
                'install': 'pacman -S --noconfirm',
                'query': 'pacman -Q'
            }
        }
        
        return commands.get(self.platform_info.package_manager, {}).get(action)

    def _check_package_compatibility(self) -> List[str]:
        """Check for incompatible packages."""
        incompatible = []
        platform_type = self.platform_info.platform_type.name.lower()
        
        # Check package compatibility rules
        compatibility_rules = self.config['platform']['compatibility'].get(
            platform_type,
            {}
        )
        
        for package, rules in compatibility_rules.items():
            if not self._check_compatibility_rules(package, rules):
                incompatible.append(package)
        
        return incompatible

    def _check_compatibility_rules(
        self,
        package: str,
        rules: Dict
    ) -> bool:
        """Check package compatibility rules."""
        try:
            # Check version constraints
            if 'min_version' in rules:
                current = self._get_package_version(package)
                if not current or not self._version_meets_constraint(
                    current,
                    rules['min_version'],
                    '>='
                ):
                    return False
            
            # Check dependencies
            if 'requires' in rules:
                for dep in rules['requires']:
                    if not self._check_package_installed(dep):
                        return False
            
            # Check conflicts
            if 'conflicts' in rules:
                for conflict in rules['conflicts']:
                    if self._check_package_installed(conflict):
                        return False
            
            return True
            
        except Exception:
            return False

    def _get_package_version(self, package: str) -> Optional[str]:
        """Get installed package version."""
        try:
            cmd = self._get_package_manager_command('query')
            if not cmd:
                return None
            
            result = subprocess.run(
                [*cmd.split(), package],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                version = re.search(r'\d+\.\d+\.\d+', result.stdout)
                return version.group(0) if version else None
        except Exception:
            pass
        return None

    def _version_meets_constraint(
        self,
        version: str,
        constraint_version: str,
        operator: str
    ) -> bool:
        """Check if version meets constraint."""
        try:
            v1 = tuple(map(int, version.split('.')))
            v2 = tuple(map(int, constraint_version.split('.')))
            
            if operator == '>=':
                return v1 >= v2
            elif operator == '>':
                return v1 > v2
            elif operator == '<=':
                return v1 <= v2
            elif operator == '<':
                return v1 < v2
            elif operator == '==':
                return v1 == v2
            return False
            
        except Exception:
            return False

    def _generate_fixes(
        self,
        missing_deps: List[str],
        incompatible: List[str]
    ) -> List[str]:
        """Generate required fixes."""
        fixes = []
        
        # Add dependency installation commands
        if missing_deps:
            install_cmd = self._get_package_manager_command('install')
            if install_cmd:
                fixes.append(
                    f"Install missing dependencies: {install_cmd} "
                    f"{' '.join(missing_deps)}"
                )
        
        # Add incompatible package fixes
        for package in incompatible:
            rules = self.config['platform']['compatibility'].get(
                self.platform_info.platform_type.name.lower(),
                {}
            ).get(package, {})
            
            if 'fix' in rules:
                fixes.append(f"Fix {package}: {rules['fix']}")
        
        return fixes

    def _generate_recommendations(self) -> List[str]:
        """Generate platform-specific recommendations."""
        recommendations = []
        platform_type = self.platform_info.platform_type.name.lower()
        
        # Add platform-specific recommendations
        platform_recs = self.config['platform']['recommendations'].get(
            platform_type,
            []
        )
        recommendations.extend(platform_recs)
        
        # Add build tool recommendations
        for tool, version in self.platform_info.build_tools.items():
            recommended = self.config['platform']['recommended_versions'].get(
                tool
            )
            if recommended and version != recommended:
                recommendations.append(
                    f"Update {tool} to recommended version {recommended}"
                )
        
        return recommendations

    def _run_platform_validation(self) -> Dict[str, bool]:
        """Run platform-specific validation checks."""
        results = {}
        platform_type = self.platform_info.platform_type.name.lower()
        
        # Run validation checks
        validation_checks = self.config['platform']['validation'].get(
            platform_type,
            {}
        )
        
        for check_name, check_cmd in validation_checks.items():
            try:
                result = subprocess.run(
                    check_cmd,
                    shell=True,
                    capture_output=True
                )
                results[check_name] = result.returncode == 0
            except Exception:
                results[check_name] = False
        
        return results

