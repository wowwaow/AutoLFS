"""
Gaming support framework for LFS/BLFS builds.

Provides gaming-specific package management, optimization, and
integration capabilities.

Dependencies:
    - vulkan-tools>=1.3
    - steam-devices>=1.0
"""

import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

from .blfs_analyzer import BLFSAnalyzer, PackageInfo
from .exceptions import (
    GamingError,
    GamingDriverError,
    GamingOptimizationError,
    GamingValidationError
)


class DriverType(Enum):
    """Types of graphics drivers."""
    NVIDIA = auto()
    AMD = auto()
    INTEL = auto()
    VULKAN = auto()


class OptimizationType(Enum):
    """Types of gaming optimizations."""
    CPU = auto()
    GPU = auto()
    MEMORY = auto()
    STORAGE = auto()
    NETWORK = auto()


@dataclass
class GamingProfile:
    """Gaming optimization profile."""
    name: str
    optimizations: Dict[OptimizationType, Dict[str, str]]
    requirements: Dict[str, str]
    environment: Dict[str, str]
    libraries: List[str]
    tools: List[str]


@dataclass
class SteamConfig:
    """Steam/Proton configuration."""
    proton_version: str
    steam_runtime: bool
    environment: Dict[str, str]
    libraries: Set[str]
    launch_options: Dict[str, str]


class GamingManager:
    """
    Manages gaming support and optimization.

    Handles gaming package installation, driver management,
    and performance optimization.

    Attributes:
        config (Dict): Gaming configuration
        blfs_analyzer (BLFSAnalyzer): Package analyzer
        profiles (Dict[str, GamingProfile]): Gaming profiles
        logger (logging.Logger): Logger instance
    """

    def __init__(self, config: Dict, blfs_analyzer: BLFSAnalyzer):
        """Initialize gaming manager."""
        self.config = config
        self.blfs_analyzer = blfs_analyzer
        self.profiles = {}
        self.logger = logging.getLogger(__name__)
        
        # Load gaming profiles
        self._load_profiles()

    def setup_gaming_environment(self, profile_name: str) -> None:
        """
        Set up gaming environment with specified profile.

        Args:
            profile_name: Gaming profile to use

        Raises:
            GamingError: If setup fails
        """
        try:
            profile = self.profiles[profile_name]
            
            # Install required packages
            self._install_gaming_packages(profile)
            
            # Set up drivers
            self._setup_drivers(profile)
            
            # Apply optimizations
            self._apply_optimizations(profile)
            
            # Configure environment
            self._configure_environment(profile)
            
        except Exception as e:
            raise GamingError(f"Failed to set up gaming environment: {e}")

    def manage_drivers(self, driver_type: DriverType) -> None:
        """
        Manage graphics drivers.

        Args:
            driver_type: Type of driver to manage

        Raises:
            GamingDriverError: If driver management fails
        """
        try:
            # Get driver info
            driver_info = self._get_driver_info(driver_type)
            
            # Install/update driver
            if not self._check_driver_installed(driver_type):
                self._install_driver(driver_type, driver_info)
            elif self._check_driver_update(driver_type, driver_info):
                self._update_driver(driver_type, driver_info)
            
            # Configure driver
            self._configure_driver(driver_type, driver_info)
            
        except Exception as e:
            raise GamingDriverError(f"Driver management failed: {e}")

    def apply_optimizations(
        self,
        optimization_types: List[OptimizationType]
    ) -> None:
        """
        Apply gaming optimizations.

        Args:
            optimization_types: Types of optimizations to apply

        Raises:
            GamingOptimizationError: If optimization fails
        """
        try:
            for opt_type in optimization_types:
                if opt_type == OptimizationType.CPU:
                    self._optimize_cpu()
                elif opt_type == OptimizationType.GPU:
                    self._optimize_gpu()
                elif opt_type == OptimizationType.MEMORY:
                    self._optimize_memory()
                elif opt_type == OptimizationType.STORAGE:
                    self._optimize_storage()
                elif opt_type == OptimizationType.NETWORK:
                    self._optimize_network()
            
        except Exception as e:
            raise GamingOptimizationError(f"Optimization failed: {e}")

    def setup_steam_proton(self, config: SteamConfig) -> None:
        """
        Set up Steam and Proton.

        Args:
            config: Steam/Proton configuration

        Raises:
            GamingError: If setup fails
        """
        try:
            # Install Steam
            if not self._check_steam_installed():
                self._install_steam()
            
            # Configure Steam
            self._configure_steam(config)
            
            # Set up Proton
            self._setup_proton(config)
            
            # Configure runtime
            if config.steam_runtime:
                self._enable_steam_runtime()
            else:
                self._disable_steam_runtime()
            
        except Exception as e:
            raise GamingError(f"Steam/Proton setup failed: {e}")

    def validate_gaming_setup(self) -> bool:
        """
        Validate gaming environment setup.

        Returns:
            bool: True if validation passes

        Raises:
            GamingValidationError: If validation fails
        """
        try:
            # Validate drivers
            self._validate_drivers()
            
            # Validate libraries
            self._validate_libraries()
            
            # Validate Steam/Proton
            self._validate_steam_proton()
            
            # Validate performance
            self._validate_performance()
            
            return True
            
        except Exception as e:
            raise GamingValidationError(f"Validation failed: {e}")

    def backup_gaming_config(self, backup_path: Path) -> None:
        """
        Back up gaming configuration.

        Args:
            backup_path: Backup destination path

        Raises:
            GamingError: If backup fails
        """
        try:
            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Back up Steam config
            self._backup_steam_config(backup_path)
            
            # Back up driver config
            self._backup_driver_config(backup_path)
            
            # Back up optimization settings
            self._backup_optimization_config(backup_path)
            
        except Exception as e:
            raise GamingError(f"Backup failed: {e}")

    def restore_gaming_config(self, backup_path: Path) -> None:
        """
        Restore gaming configuration.

        Args:
            backup_path: Backup source path

        Raises:
            GamingError: If restoration fails
        """
        try:
            # Verify backup
            if not self._verify_backup(backup_path):
                raise GamingError("Invalid backup")
            
            # Restore Steam config
            self._restore_steam_config(backup_path)
            
            # Restore driver config
            self._restore_driver_config(backup_path)
            
            # Restore optimization settings
            self._restore_optimization_config(backup_path)
            
        except Exception as e:
            raise GamingError(f"Restoration failed: {e}")

    def _load_profiles(self) -> None:
        """Load gaming optimization profiles."""
        profile_path = Path(self.config['gaming']['profiles'])
        if not profile_path.exists():
            raise GamingError("Gaming profiles not found")
        
        try:
            with open(profile_path) as f:
                data = yaml.safe_load(f)
                
            for name, profile_data in data['profiles'].items():
                self.profiles[name] = GamingProfile(
                    name=name,
                    optimizations=profile_data['optimizations'],
                    requirements=profile_data['requirements'],
                    environment=profile_data['environment'],
                    libraries=profile_data['libraries'],
                    tools=profile_data['tools']
                )
                
        except Exception as e:
            raise GamingError(f"Failed to load profiles: {e}")

    def _install_gaming_packages(self, profile: GamingProfile) -> None:
        """Install required gaming packages."""
        packages = (
            profile.requirements.keys() |
            profile.libraries |
            profile.tools
        )
        
        for package in packages:
            try:
                pkg_info = self.blfs_analyzer.analyze_package(package)
                if not self.blfs_analyzer.validate_package(package):
                    self.blfs_analyzer.manage_configuration(
                        package,
                        profile.requirements.get(package, {})
                    )
            except Exception as e:
                raise GamingError(f"Failed to install {package}: {e}")

    def _setup_drivers(self, profile: GamingProfile) -> None:
        """Set up required drivers."""
        # Detect GPU
        gpu_type = self._detect_gpu_type()
        
        # Install appropriate driver
        if gpu_type == DriverType.NVIDIA:
            self.manage_drivers(DriverType.NVIDIA)
        elif gpu_type == DriverType.AMD:
            self.manage_drivers(DriverType.AMD)
        elif gpu_type == DriverType.INTEL:
            self.manage_drivers(DriverType.INTEL)
        
        # Always set up Vulkan
        self.manage_drivers(DriverType.VULKAN)

    def _detect_gpu_type(self) -> DriverType:
        """Detect GPU type."""
        try:
            # Check lspci output
            result = subprocess.run(
                ['lspci'],
                capture_output=True,
                text=True
            )
            
            output = result.stdout.lower()
            if 'nvidia' in output:
                return DriverType.NVIDIA
            elif 'amd' in output or 'radeon' in output:
                return DriverType.AMD
            elif 'intel' in output:
                return DriverType.INTEL
            
            raise GamingDriverError("GPU not detected")
            
        except Exception as e:
            raise GamingDriverError(f"Failed to detect GPU: {e}")

    def _get_driver_info(self, driver_type: DriverType) -> Dict:
        """Get driver information."""
        try:
            return self.config['gaming']['drivers'][driver_type.name.lower()]
        except KeyError:
            raise GamingDriverError(f"No configuration for {driver_type.name}")

    def _check_driver_installed(self, driver_type: DriverType) -> bool:
        """Check if driver is installed."""
        driver_info = self._get_driver_info(driver_type)
        
        # Check kernel module
        if driver_info.get('module'):
            result = subprocess.run(
                ['lsmod'],
                capture_output=True,
                text=True
            )
            if driver_info['module'] not in result.stdout:
                return False
        
        # Check libraries
        for lib in driver_info.get('libraries', []):
            if not Path(lib).exists():
                return False
        
        return True

    def _check_driver_update(
        self,
        driver_type: DriverType,
        driver_info: Dict
    ) -> bool:
        """Check if driver update is available."""
        try:
            current = self._get_driver_version(driver_type)
            if not current:
                return True
            
            available = driver_info['version']
            return available > current
            
        except Exception:
            return False

    def _get_driver_version(self, driver_type: DriverType) -> Optional[str]:
        """Get installed driver version."""
        try:
            driver_info = self._get_driver_info(driver_type)
            version_cmd = driver_info['version_command']
            
            result = subprocess.run(
                version_cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                match = re.search(
                    driver_info['version_pattern'],
                    result.stdout
                )
                if match:
                    return match.group(1)
            
        except Exception:
            pass
        
        return None

    def _install_driver(
        self,
        driver_type: DriverType,
        driver_info: Dict
    ) -> None:
        """Install graphics driver."""
        try:
            install_cmd = driver_info['install_command']
            result = subprocess.run(
                install_cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise GamingDriverError(
                    f"Driver installation failed: {result.stderr}"
                )
            
        except Exception as e:
            raise GamingDriverError(f"Failed to install driver: {e}")

    def _update_driver(
        self,
        driver_type: DriverType,
        driver_info: Dict
    ) -> None:
        """Update graphics driver."""
        try:
            update_cmd = driver_info['update_command']
            result = subprocess.run(
                update_cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise GamingDriverError(
                    f"Driver update failed: {result.stderr}"
                )
            
        except Exception as e:
            raise GamingDriverError(f"Failed to update driver: {e}")

    def _configure_driver(
        self,
        driver_type: DriverType,
        driver_info: Dict
    ) -> None:
        """Configure graphics driver."""
        try:
            # Apply configuration
            config_file = Path(driver_info['config_file'])
            config_template = Path(driver_info['config_template'])
            
            if config_template.exists():
                shutil.copy2(config_template, config_file)
            
            # Update configuration
            if 'config_options' in driver_info:
                self._update_driver_config(
                    config_file,
                    driver_info['config_options']
                )
            
        except Exception as e:
            raise GamingDriverError(f"Failed to configure driver: {e}")

    def _update_driver_config(self, config_file: Path, options: Dict) -> None:
        """Update driver configuration file."""
        try:
            content = []
            if config_file.exists():
                with open(config_file) as f:
                    content = f.readlines()
            
            # Update options
            for key, value in options.items():
                line = f"{key}={value}\n"
                for i, existing in enumerate(content):
                    if existing.startswith(f"{key}="):
                        content[i] = line
                        break
                else:
                    content.append(line)
            
            # Write back
            with open(config_file, 'w') as f:
                f.writelines(content)
                
        except Exception as e:
            raise GamingDriverError(f"Failed to update config: {e}")

    def _optimize_cpu(self) -> None:
        """Apply CPU optimizations."""
        try:
            # Set CPU governor
            subprocess.run(
                ['cpupower', 'frequency-set', '-g', 'performance'],
                check=True
            )
            
            # Set process priorities
            subprocess.run(
                ['renice', '-n', '-5', '-p', str(os.getpid())],
                check=True
            )
            
        except Exception as e:
            raise GamingOptimizationError(f"CPU optimization failed: {e}")

    def _optimize_gpu(self) -> None:
        """Apply GPU optimizations."""
        try:
            gpu_type = self._detect_gpu_type()
            
            if gpu_type == DriverType.NVIDIA:
                # Set power mode
                subprocess.run(
                    ['nvidia-settings', '-a', 'GPUPowerMizerMode=1'],
                    check=True
                )
            elif gpu_type == DriverType.AMD:
                # Set performance mode
                with open('/sys/class/drm/card0/device/power_dpm_force_performance_level', 'w') as f:
                    f.write('high\n')
                    
        except Exception as e:
            raise GamingOptimizationError(f"GPU optimization failed: {e}")

    def _optimize_memory(self) -> None:
        """Apply memory optimizations."""
        try:
            # Set swappiness
            with open('/proc/sys/vm/swappiness', 'w') as f:
                f.write('10\n')
            
            # Set cache pressure
            with open('/proc/sys/vm/vfs_cache_pressure', 'w') as f:
                f.write('50\n')
                
        except Exception as e:
            raise GamingOptimizationError(f"Memory optimization failed: {e}")

    def _optimize_storage(self) -> None:
        """Apply storage optimizations."""
        try:
            # Set I/O scheduler
            for device in Path('/sys/block').glob('sd*'):
                scheduler = device / 'queue/scheduler'
                if scheduler.exists():
                    with open(scheduler, 'w') as f:
                        f.write('deadline\n')
                        
        except Exception as e:
            raise GamingOptimizationError(f"Storage optimization failed: {e}")

    def _optimize_network(self) -> None:
        """Apply network optimizations."""
        try:
            # Enable TCP BBR
            subprocess.run(
                ['sysctl', '-w', 'net.ipv4.tcp_congestion_control=bbr'],
                check=True
            )
            
            # Increase buffer sizes
            subprocess.run(
                ['sysctl', '-w', 'net.core.rmem_max=16777216'],
                check=True
            )
            subprocess.run(
                ['sysctl', '-w', 'net.core.wmem_max=16777216'],
                check=True
            )
            
        except Exception as e:
            raise GamingOptimizationError(f"Network optimization failed: {e}")

    def _validate_drivers(self) -> None:
        """Validate graphics drivers."""
        gpu_type = self._detect_gpu_type()
        
        # Check driver installation
        if not self._check_driver_installed(gpu_type):
            raise GamingValidationError(f"{gpu_type.name} driver not installed")
        
        # Check Vulkan support
        result = subprocess.run(
            ['vulkaninfo'],
            capture_output=True
        )
        if result.returncode != 0:
            raise GamingValidationError("Vulkan support not available")

    def _validate_libraries(self) -> None:
        """Validate gaming libraries."""
        for profile in self.profiles.values():
            for library in profile.libraries:
                if not self._check_library_installed(library):
                    raise GamingValidationError(f"Missing library: {library}")

    def _check_library_installed(self, library: str) -> bool:
        """Check if a library is installed."""
        try:
            result = subprocess.run(
                ['ldconfig', '-p'],
                capture_output=True,
                text=True
            )
            return library in result.stdout
        except Exception:
            return False

    def _validate_steam_proton(self) -> None:
        """Validate Steam and Proton setup."""
        if not self._check_steam_installed():
            raise GamingValidationError("Steam not installed")
        
        if not self._check_proton_setup():
            raise GamingValidationError("Proton not properly configured")

    def _check_steam_installed(self) -> bool:
        """Check if Steam is installed."""
        steam_path = Path.home() / ".steam"
        return steam_path.exists()

    def _check_proton_setup(self) -> bool:
        """Check Proton configuration."""
        try:
            steam_path = Path.home() / ".steam/root"
            compattools = steam_path / "compatibilitytools.d"
            return compattools.exists() and any(compattools.iterdir())
        except Exception:
            return False

    def _validate_performance(self) -> None:
        """Validate gaming performance."""
        try:
            # Check CPU governor
            with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor') as f:
                if f.read().strip() != 'performance':
                    raise GamingValidationError("CPU not in performance mode")
            
            # Check GPU settings
            gpu_type = self._detect_gpu_type()
            if gpu_type == DriverType.NVIDIA:
                result = subprocess.run(
                    ['nvidia-settings', '-q', 'GPUPowerMizerMode'],
                    capture_output=True,
                    text=True
                )
                if 'performance' not in result.stdout.lower():
                    raise GamingValidationError("GPU not in performance mode")
            
        except Exception as e:
            raise GamingValidationError(f"Performance validation failed: {e}")

    def _backup_steam_config(self, backup_path: Path) -> None:
        """Back up Steam configuration."""
        steam_path = Path.home() / ".steam"
        if steam_path.exists():
            dest = backup_path / "steam"
            shutil.copytree(steam_path, dest)

    def _backup_driver_config(self, backup_path: Path) -> None:
        """Back up driver configuration."""
        gpu_type = self._detect_gpu_type()
        driver_info = self._get_driver_info(gpu_type)
        
        config_file = Path(driver_info['config_file'])
        if config_file.exists():
            dest = backup_path / "drivers" / config_file.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(config_file, dest)

    def _backup_optimization_config(self, backup_path: Path) -> None:
        """Back up optimization settings."""
        settings = {
            'cpu_governor': self._get_cpu_governor(),
            'gpu_settings': self._get_gpu_settings(),
            'memory_settings': self._get_memory_settings(),
            'network_settings': self._get_network_settings()
        }
        
        settings_file = backup_path / "optimization_settings.json"
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

    def _verify_backup(self, backup_path: Path) -> bool:
        """Verify backup integrity."""
        try:
            # Check structure
            required = ['steam', 'drivers', 'optimization_settings.json']
            for item in required:
                if not (backup_path / item).exists():
                    return False
            
            # Check settings file
            with open(backup_path / "optimization_settings.json") as f:
                settings = json.load(f)
                if not all(k in settings for k in [
                    'cpu_governor',
                    'gpu_settings',
                    'memory_settings',
                    'network_settings'
                ]):
                    return False
            
            return True
            
        except Exception:
            return False

    def _restore_steam_config(self, backup_path: Path) -> None:
        """Restore Steam configuration."""
        steam_backup = backup_path / "steam"
        if steam_backup.exists():
            steam_path = Path.home() / ".steam"
            if steam_path.exists():
                shutil.rmtree(steam_path)
            shutil.copytree(steam_backup, steam_path)

    def _restore_driver_config(self, backup_path: Path) -> None:
        """Restore driver configuration."""
        gpu_type = self._detect_gpu_type()
        driver_info = self._get_driver_info(gpu_type)
        
        config_backup = backup_path / "drivers" / Path(
            driver_info['config_file']
        ).name
        if config_backup.exists():
            shutil.copy2(config_backup, driver_info['config_file'])

    def _restore_optimization_config(self, backup_path: Path) -> None:
        """Restore optimization settings."""
        settings_file = backup_path / "optimization_settings.json"
        if not settings_file.exists():
            return
        
        with open(settings_file) as f:
            settings = json.load(f)
        
        # Restore settings
        self._set_cpu_governor(settings['cpu_governor'])
        self._set_gpu_settings(settings['gpu_settings'])
        self._set_memory_settings(settings['memory_settings'])
        self._set_network_settings(settings['network_settings'])

    def _get_cpu_governor(self) -> str:
        """Get current CPU governor."""
        with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor') as f:
            return f.read().strip()

    def _get_gpu_settings(self) -> Dict:
        """Get current GPU settings."""
        gpu_type = self._detect_gpu_type()
        if gpu_type == DriverType.NVIDIA:
            result = subprocess.run(
                ['nvidia-settings', '-q', 'all'],
                capture_output=True,
                text=True
            )
            return self._parse_nvidia_settings(result.stdout)
        return {}

    def _get_memory_settings(self) -> Dict:
        """Get current memory settings."""
        settings = {}
        with open('/proc/sys/vm/swappiness') as f:
            settings['swappiness'] = f.read().strip()
        with open('/proc/sys/vm/vfs_cache_pressure') as f:
            settings['cache_pressure'] = f.read().strip()
        return settings

    def _get_network_settings(self) -> Dict:
        """Get current network settings."""
        settings = {}
        result = subprocess.run(
            ['sysctl', '-a'],
            capture_output=True,
            text=True
        )
        for line in result.stdout.splitlines():
            if any(k in line for k in [
                'tcp_congestion_control',
                'rmem_max',
                'wmem_max'
            ]):
                key, value = line.split('=', 1)
                settings[key.strip()] = value.strip()
        return settings

    def _set_cpu_governor(self, governor: str) -> None:
        """Set CPU governor."""
        subprocess.run(
            ['cpupower', 'frequency-set', '-g', governor],
            check=True
        )

    def _set_gpu_settings(self, settings: Dict) -> None:
        """Set GPU settings."""
        gpu_type = self._detect_gpu_type()
        if gpu_type == DriverType.NVIDIA:
            for key, value in settings.items():
                subprocess.run(
                    ['nvidia-settings', '-a', f'{key}={value}'],
                    check=True
                )

    def _set_memory_settings(self, settings: Dict) -> None:
        """Set memory settings."""
        with open('/proc/sys/vm/swappiness', 'w') as f:
            f.write(f"{settings['swappiness']}\n")
        with open('/proc/sys/vm/vfs_cache_pressure', 'w') as f:
            f.write(f"{settings['cache_pressure']}\n")

    def _set_network_settings(self, settings: Dict) -> None:
        """Set network settings."""
        for key, value in settings.items():
            subprocess.run(
                ['sysctl', '-w', f'{key}={value}'],
                check=True
            )

    def _parse_nvidia_settings(self, output: str) -> Dict[str, str]:
        """Parse nvidia-settings output."""
        settings = {}
        for line in output.splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                settings[key.strip()] = value.strip()
        return settings

