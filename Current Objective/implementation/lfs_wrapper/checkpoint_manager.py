"""
Checkpoint management system for LFS and BLFS builds.

Provides functionality for preserving, validating, and restoring
build state across build processes.

Dependencies:
    - packaging>=21.0
"""

import json
import logging
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

from .blfs_manager import BLFSPackage, PackageStatus
from .build_manager import BuildPhase, BuildState, BuildStatus
from .exceptions import (
    CheckpointError,
    RestorationError,
    ValidationError
)


class CheckpointType(Enum):
    """Types of checkpoints."""
    LFS = auto()
    BLFS = auto()
    SYSTEM = auto()


@dataclass
class CheckpointMetadata:
    """Checkpoint metadata information."""
    checkpoint_id: str
    timestamp: float
    checkpoint_type: CheckpointType
    build_phase: BuildPhase
    description: str
    tags: Set[str]
    verified: bool = False


@dataclass
class BuildSnapshot:
    """Represents a snapshot of build state."""
    build_state: BuildState
    environment_vars: Dict[str, str]
    file_checksums: Dict[str, str]
    installed_packages: Dict[str, str]
    build_logs: Dict[str, str]
    timestamp: float


class CheckpointManager:
    """
    Manages build state checkpoints.

    Handles creation, validation, and restoration of build state
    checkpoints for both LFS and BLFS builds.

    Attributes:
        config (Dict): Checkpoint configuration
        checkpoint_dir (Path): Directory for checkpoint storage
        max_checkpoints (int): Maximum number of checkpoints to keep
        logger (logging.Logger): Logger instance
    """

    def __init__(self, config: Dict):
        """Initialize the checkpoint manager."""
        self.config = config
        self.checkpoint_dir = Path(config['checkpoints']['directory'])
        self.max_checkpoints = config['checkpoints'].get('max_checkpoints', 10)
        self.logger = logging.getLogger(__name__)

        self._ensure_checkpoint_dir()

    def _ensure_checkpoint_dir(self) -> None:
        """Ensure checkpoint directory exists."""
        try:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise CheckpointError(f"Failed to create checkpoint directory: {e}")

    def create_checkpoint(
        self,
        build_state: BuildState,
        checkpoint_type: CheckpointType,
        description: str,
        tags: Optional[Set[str]] = None
    ) -> str:
        """
        Create a new checkpoint.

        Args:
            build_state: Current build state
            checkpoint_type: Type of checkpoint
            description: Checkpoint description
            tags: Optional tags for organization

        Returns:
            str: Checkpoint ID

        Raises:
            CheckpointError: If checkpoint creation fails
        """
        try:
            # Generate checkpoint ID
            timestamp = time.time()
            checkpoint_id = f"{checkpoint_type.name}_{int(timestamp)}"
            
            # Create checkpoint directory
            checkpoint_path = self.checkpoint_dir / checkpoint_id
            checkpoint_path.mkdir()
            
            # Create snapshot
            snapshot = BuildSnapshot(
                build_state=build_state,
                environment_vars=dict(os.environ),
                file_checksums=self._compute_checksums(),
                installed_packages=self._get_installed_packages(),
                build_logs=self._collect_build_logs(),
                timestamp=timestamp
            )
            
            # Save snapshot
            self._save_snapshot(checkpoint_path, snapshot)
            
            # Create and save metadata
            metadata = CheckpointMetadata(
                checkpoint_id=checkpoint_id,
                timestamp=timestamp,
                checkpoint_type=checkpoint_type,
                build_phase=build_state.phase,
                description=description,
                tags=tags or set()
            )
            self._save_metadata(checkpoint_path, metadata)
            
            # Clean up old checkpoints
            self._cleanup_old_checkpoints()
            
            return checkpoint_id
            
        except Exception as e:
            raise CheckpointError(f"Failed to create checkpoint: {e}")

    def restore_checkpoint(self, checkpoint_id: str) -> BuildSnapshot:
        """
        Restore system state from a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to restore

        Returns:
            BuildSnapshot: Restored build state

        Raises:
            RestorationError: If restoration fails
        """
        try:
            checkpoint_path = self.checkpoint_dir / checkpoint_id
            if not checkpoint_path.exists():
                raise RestorationError(f"Checkpoint not found: {checkpoint_id}")
            
            # Verify checkpoint
            if not self.verify_checkpoint(checkpoint_id):
                raise RestorationError(
                    f"Checkpoint verification failed: {checkpoint_id}"
                )
            
            # Load snapshot
            snapshot = self._load_snapshot(checkpoint_path)
            
            # Restore environment
            os.environ.update(snapshot.environment_vars)
            
            # Verify file integrity
            if not self._verify_checksums(snapshot.file_checksums):
                raise RestorationError("File integrity check failed")
            
            return snapshot
            
        except Exception as e:
            raise RestorationError(f"Failed to restore checkpoint: {e}")

    def verify_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Verify a checkpoint's integrity.

        Args:
            checkpoint_id: ID of checkpoint to verify

        Returns:
            bool: True if checkpoint is valid
        """
        try:
            checkpoint_path = self.checkpoint_dir / checkpoint_id
            if not checkpoint_path.exists():
                return False
            
            # Load and verify metadata
            metadata = self._load_metadata(checkpoint_path)
            if not metadata:
                return False
            
            # Load and verify snapshot
            snapshot = self._load_snapshot(checkpoint_path)
            if not snapshot:
                return False
            
            # Update metadata verification status
            metadata.verified = True
            self._save_metadata(checkpoint_path, metadata)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Checkpoint verification failed: {e}")
            return False

    def list_checkpoints(
        self,
        checkpoint_type: Optional[CheckpointType] = None,
        tags: Optional[Set[str]] = None
    ) -> List[CheckpointMetadata]:
        """
        List available checkpoints.

        Args:
            checkpoint_type: Optional type filter
            tags: Optional tag filter

        Returns:
            List[CheckpointMetadata]: List of checkpoint metadata
        """
        checkpoints = []
        
        for path in self.checkpoint_dir.iterdir():
            if not path.is_dir():
                continue
                
            try:
                metadata = self._load_metadata(path)
                if not metadata:
                    continue
                
                # Apply filters
                if checkpoint_type and metadata.checkpoint_type != checkpoint_type:
                    continue
                if tags and not tags.issubset(metadata.tags):
                    continue
                
                checkpoints.append(metadata)
                
            except Exception as e:
                self.logger.error(f"Failed to load checkpoint {path}: {e}")
        
        return sorted(checkpoints, key=lambda x: x.timestamp, reverse=True)

    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """
        Delete a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to delete

        Raises:
            CheckpointError: If deletion fails
        """
        try:
            checkpoint_path = self.checkpoint_dir / checkpoint_id
            if checkpoint_path.exists():
                shutil.rmtree(checkpoint_path)
        except Exception as e:
            raise CheckpointError(f"Failed to delete checkpoint: {e}")

    def _compute_checksums(self) -> Dict[str, str]:
        """Compute checksums for critical files."""
        import hashlib
        
        checksums = {}
        critical_paths = self.config['checkpoints'].get('critical_paths', [])
        
        for path in critical_paths:
            if not Path(path).exists():
                continue
                
            try:
                with open(path, 'rb') as f:
                    checksums[path] = hashlib.sha256(f.read()).hexdigest()
            except Exception as e:
                self.logger.error(f"Failed to compute checksum for {path}: {e}")
        
        return checksums

    def _verify_checksums(self, saved_checksums: Dict[str, str]) -> bool:
        """Verify file checksums match saved values."""
        current_checksums = self._compute_checksums()
        return all(
            current_checksums.get(path) == checksum
            for path, checksum in saved_checksums.items()
        )

    def _get_installed_packages(self) -> Dict[str, str]:
        """Get list of installed packages and versions."""
        # Implementation depends on package management system
        return {}

    def _collect_build_logs(self) -> Dict[str, str]:
        """Collect relevant build logs."""
        logs = {}
        log_dir = Path(self.config['logging']['directory'])
        
        try:
            for log_file in log_dir.glob('*.log'):
                with open(log_file, 'r') as f:
                    logs[log_file.name] = f.read()
        except Exception as e:
            self.logger.error(f"Failed to collect build logs: {e}")
        
        return logs

    def _save_snapshot(self, path: Path, snapshot: BuildSnapshot) -> None:
        """Save build snapshot to disk."""
        snapshot_file = path / "snapshot.json"
        
        try:
            # Convert BuildState to dict for serialization
            state_dict = {
                'phase': snapshot.build_state.phase.name,
                'status': snapshot.build_state.status.name,
                'current_script': snapshot.build_state.current_script,
                'completed_scripts': snapshot.build_state.completed_scripts,
                'failed_scripts': snapshot.build_state.failed_scripts,
                'start_time': snapshot.build_state.start_time,
                'last_checkpoint': snapshot.build_state.last_checkpoint,
                'error_count': snapshot.build_state.error_count
            }
            
            data = {
                'build_state': state_dict,
                'environment_vars': snapshot.environment_vars,
                'file_checksums': snapshot.file_checksums,
                'installed_packages': snapshot.installed_packages,
                'build_logs': snapshot.build_logs,
                'timestamp': snapshot.timestamp
            }
            
            with open(snapshot_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            raise CheckpointError(f"Failed to save snapshot: {e}")

    def _load_snapshot(self, path: Path) -> BuildSnapshot:
        """Load build snapshot from disk."""
        snapshot_file = path / "snapshot.json"
        
        try:
            with open(snapshot_file, 'r') as f:
                data = json.load(f)
            
            # Convert dict back to BuildState
            state_dict = data['build_state']
            build_state = BuildState(
                phase=BuildPhase[state_dict['phase']],
                status=BuildStatus[state_dict['status']],
                current_script=state_dict['current_script'],
                completed_scripts=state_dict['completed_scripts'],
                failed_scripts=state_dict['failed_scripts'],
                start_time=state_dict['start_time'],
                last_checkpoint=state_dict['last_checkpoint'],
                error_count=state_dict['error_count']
            )
            
            return BuildSnapshot(
                build_state=build_state,
                environment_vars=data['environment_vars'],
                file_checksums=data['file_checksums'],
                installed_packages=data['installed_packages'],
                build_logs=data['build_logs'],
                timestamp=data['timestamp']
            )
            
        except Exception as e:
            raise CheckpointError(f"Failed to load snapshot: {e}")

    def _save_metadata(self, path: Path, metadata: CheckpointMetadata) -> None:
        """Save checkpoint metadata to disk."""
        metadata_file = path / "metadata.json"
        
        try:
            data = {
                'checkpoint_id': metadata.checkpoint_id,
                'timestamp': metadata.timestamp,
                'checkpoint_type': metadata.checkpoint_type.name,
                'build_phase': metadata.build_phase.name,
                'description': metadata.description,
                'tags': list(metadata.tags),
                'verified': metadata.verified
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            raise CheckpointError(f"Failed to save metadata: {e}")

    def _load_metadata(self, path: Path) -> Optional[CheckpointMetadata]:
        """Load checkpoint metadata from disk."""
        metadata_file = path / "metadata.json"
        
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
            
            return CheckpointMetadata(
                checkpoint_id=data['checkpoint_id'],
                timestamp=data['timestamp'],
                checkpoint_type=CheckpointType[data['checkpoint_type']],
                build_phase=BuildPhase[data['build_phase']],
                description=data['description'],
                tags=set(data['tags']),
                verified=data['verified']
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")
            return None

    def _cleanup_old_checkpoints(self) -> None:
        """Clean up old checkpoints exceeding max limit."""
        checkpoints = self.list_checkpoints()
        
        if len(checkpoints) > self.max_checkpoints:
            # Sort by timestamp and remove oldest
            to_remove = sorted(
                checkpoints,
                key=lambda x: x.timestamp
            )[:-self.max_checkpoints]
            
            for checkpoint in to_remove:
                try:
                    self.delete_checkpoint(checkpoint.checkpoint_id)
                except Exception as e:
                    self.logger.error(
                        f"Failed to delete checkpoint {checkpoint.checkpoint_id}: {e}"
                    )

