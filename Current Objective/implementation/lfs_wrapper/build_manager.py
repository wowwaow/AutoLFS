"""
LFS build process management module.

Coordinates the execution of LFS build scripts, manages build state,
and provides checkpoint/resume functionality with error recovery.

Dependencies:
    - PyYAML>=6.0
    - click>=8.0
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from .exceptions import (
    BuildError,
    ConfigurationError,
    ExecutionError,
    ValidationError
)
from .script_manager import ScriptManager


class BuildPhase(Enum):
    """Enumeration of LFS build phases."""
    TOOLCHAIN = auto()
    TEMP_SYSTEM = auto()
    SYSTEM = auto()
    CONFIGURATION = auto()
    BOOTLOADER = auto()


class BuildStatus(Enum):
    """Build status indicators."""
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    RECOVERING = auto()


@dataclass
class BuildState:
    """Represents the current state of the build process."""
    phase: BuildPhase
    status: BuildStatus
    current_script: Optional[str]
    completed_scripts: List[str]
    failed_scripts: List[str]
    start_time: float
    last_checkpoint: float
    error_count: int


class BuildManager:
    """
    Manages the LFS build process.

    Coordinates script execution, tracks build progress, handles
    checkpointing, and provides error recovery mechanisms.

    Attributes:
        build_root (Path): Root directory for the build
        config (Dict): Build configuration
        script_manager (ScriptManager): Script execution manager
        state (BuildState): Current build state
    """

    def __init__(self, build_root: Path, config: Dict) -> None:
        """
        Initialize the build manager.

        Args:
            build_root: Root directory for the build
            config: Build configuration dictionary

        Raises:
            ConfigurationError: If configuration is invalid
            ValidationError: If build root is invalid
        """
        self.build_root = build_root
        self.config = config
        self.logger = logging.getLogger(__name__)

        if not self.build_root.exists():
            raise ValidationError(f"Build root does not exist: {build_root}")

        self._validate_config()
        self.script_manager = ScriptManager(
            self.build_root / "scripts",
            self.config
        )
        
        # Initialize or load build state
        self.state = self._load_state() or BuildState(
            phase=BuildPhase.TOOLCHAIN,
            status=BuildStatus.NOT_STARTED,
            current_script=None,
            completed_scripts=[],
            failed_scripts=[],
            start_time=time.time(),
            last_checkpoint=time.time(),
            error_count=0
        )

    def _validate_config(self) -> None:
        """
        Validate build configuration.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        required_sections = ['build', 'phases', 'checkpoints']
        missing = [s for s in required_sections if s not in self.config]
        if missing:
            raise ConfigurationError(f"Missing config sections: {', '.join(missing)}")

        if 'recovery' not in self.config:
            self.logger.warning("No recovery configuration found, using defaults")

    def _load_state(self) -> Optional[BuildState]:
        """
        Load build state from checkpoint file.

        Returns:
            Optional[BuildState]: Loaded state or None if no checkpoint exists
        """
        state_file = self.build_root / "build_state.json"
        if not state_file.exists():
            return None

        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
                return BuildState(
                    phase=BuildPhase[data['phase']],
                    status=BuildStatus[data['status']],
                    current_script=data['current_script'],
                    completed_scripts=data['completed_scripts'],
                    failed_scripts=data['failed_scripts'],
                    start_time=data['start_time'],
                    last_checkpoint=data['last_checkpoint'],
                    error_count=data['error_count']
                )
        except Exception as e:
            self.logger.error(f"Failed to load build state: {e}")
            return None

    def _save_state(self) -> None:
        """Save current build state to checkpoint file."""
        state_file = self.build_root / "build_state.json"
        state_data = {
            'phase': self.state.phase.name,
            'status': self.state.status.name,
            'current_script': self.state.current_script,
            'completed_scripts': self.state.completed_scripts,
            'failed_scripts': self.state.failed_scripts,
            'start_time': self.state.start_time,
            'last_checkpoint': time.time(),
            'error_count': self.state.error_count
        }

        try:
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save build state: {e}")

    def get_build_scripts(self, phase: BuildPhase) -> List[Path]:
        """
        Get list of build scripts for a specific phase.

        Args:
            phase: Build phase to get scripts for

        Returns:
            List[Path]: List of script paths in execution order
        """
        phase_config = self.config['phases'][phase.name.lower()]
        script_dir = self.build_root / "scripts" / phase.name.lower()
        
        if not script_dir.exists():
            raise ValidationError(f"Script directory not found: {script_dir}")

        scripts = []
        for script_pattern in phase_config['scripts']:
            matched = list(script_dir.glob(script_pattern))
            if not matched:
                self.logger.warning(f"No scripts matched pattern: {script_pattern}")
            scripts.extend(matched)

        return sorted(scripts)

    def execute_phase(self, phase: BuildPhase) -> bool:
        """
        Execute all scripts in a build phase.

        Args:
            phase: Build phase to execute

        Returns:
            bool: True if phase completed successfully

        Raises:
            BuildError: If phase execution fails
        """
        self.state.phase = phase
        self.state.status = BuildStatus.IN_PROGRESS
        self._save_state()

        try:
            scripts = self.get_build_scripts(phase)
            for script in scripts:
                if str(script) in self.state.completed_scripts:
                    self.logger.info(f"Skipping completed script: {script}")
                    continue

                self.state.current_script = str(script)
                self._save_state()

                try:
                    returncode, stdout, stderr = self.script_manager.execute_script(
                        script,
                        timeout=self.config['build'].get('script_timeout', 3600)
                    )
                    
                    if returncode != 0:
                        raise ExecutionError(
                            f"Script failed with code {returncode}: {stderr}"
                        )

                    self.state.completed_scripts.append(str(script))
                    self._save_state()

                except ExecutionError as e:
                    self.state.failed_scripts.append(str(script))
                    self.state.error_count += 1
                    self._save_state()
                    
                    if not self._handle_error(e):
                        raise BuildError(f"Phase {phase.name} failed: {str(e)}")

            self.state.status = BuildStatus.COMPLETED
            self._save_state()
            return True

        except Exception as e:
            self.state.status = BuildStatus.FAILED
            self._save_state()
            raise BuildError(f"Phase {phase.name} failed: {str(e)}")

    def _handle_error(self, error: Exception) -> bool:
        """
        Handle build errors and attempt recovery.

        Args:
            error: The error that occurred

        Returns:
            bool: True if recovery was successful
        """
        self.state.status = BuildStatus.RECOVERING
        self._save_state()

        recovery_config = self.config.get('recovery', {})
        max_retries = recovery_config.get('max_retries', 3)
        retry_delay = recovery_config.get('retry_delay', 60)

        if self.state.error_count > max_retries:
            self.logger.error("Maximum retry attempts exceeded")
            return False

        self.logger.info(f"Attempting recovery, retry {self.state.error_count}")
        time.sleep(retry_delay)

        try:
            # Attempt to clean up failed script artifacts
            cleanup_script = self.build_root / "scripts" / "cleanup.sh"
            if cleanup_script.exists():
                self.script_manager.execute_script(cleanup_script)

            return True

        except Exception as e:
            self.logger.error(f"Recovery failed: {e}")
            return False

    def get_build_progress(self) -> Dict:
        """
        Get current build progress information.

        Returns:
            Dict: Build progress information
        """
        return {
            'phase': self.state.phase.name,
            'status': self.state.status.name,
            'current_script': self.state.current_script,
            'completed_scripts': len(self.state.completed_scripts),
            'failed_scripts': len(self.state.failed_scripts),
            'error_count': self.state.error_count,
            'runtime': time.time() - self.state.start_time,
            'last_checkpoint': time.time() - self.state.last_checkpoint
        }

    def cleanup(self) -> None:
        """Clean up build artifacts and temporary files."""
        try:
            cleanup_script = self.build_root / "scripts" / "cleanup.sh"
            if cleanup_script.exists():
                self.script_manager.execute_script(cleanup_script)
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")

