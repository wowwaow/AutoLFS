"""
Unit tests for the CheckpointManager class.

Tests checkpoint creation, restoration, verification, and
maintenance functionality.
"""

import json
import os
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lfs_wrapper.build_manager import BuildPhase, BuildState, BuildStatus
from lfs_wrapper.checkpoint_manager import (
    BuildSnapshot,
    CheckpointManager,
    CheckpointMetadata,
    CheckpointType
)
from lfs_wrapper.exceptions import (
    CheckpointError,
    RestorationError,
    ValidationError
)


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        'checkpoints': {
            'directory': 'checkpoints',
            'max_checkpoints': 3,
            'critical_paths': [
                '/test/path1',
                '/test/path2'
            ]
        },
        'logging': {
            'directory': 'logs'
        }
    }


@pytest.fixture
def test_build_state():
    """Provide test build state."""
    return BuildState(
        phase=BuildPhase.TOOLCHAIN,
        status=BuildStatus.IN_PROGRESS,
        current_script="current.sh",
        completed_scripts=["script1.sh", "script2.sh"],
        failed_scripts=[],
        start_time=time.time(),
        last_checkpoint=time.time(),
        error_count=0
    )


@pytest.fixture
def checkpoint_manager(tmp_path, test_config):
    """Provide CheckpointManager instance."""
    config = test_config.copy()
    config['checkpoints']['directory'] = str(tmp_path / "checkpoints")
    config['logging']['directory'] = str(tmp_path / "logs")
    
    # Create log directory
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "build.log").write_text("test log")
    
    return CheckpointManager(config)


def test_create_checkpoint(checkpoint_manager, test_build_state):
    """Test checkpoint creation."""
    checkpoint_id = checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.LFS,
        "Test checkpoint",
        {"test"}
    )
    
    checkpoint_path = Path(checkpoint_manager.checkpoint_dir) / checkpoint_id
    assert checkpoint_path.exists()
    assert (checkpoint_path / "snapshot.json").exists()
    assert (checkpoint_path / "metadata.json").exists()


def test_create_checkpoint_with_env_vars(checkpoint_manager, test_build_state):
    """Test checkpoint creation with environment variables."""
    os.environ['TEST_VAR'] = 'test_value'
    
    checkpoint_id = checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.LFS,
        "Test checkpoint"
    )
    
    snapshot = checkpoint_manager._load_snapshot(
        checkpoint_manager.checkpoint_dir / checkpoint_id
    )
    assert snapshot.environment_vars['TEST_VAR'] == 'test_value'


def test_restore_checkpoint(checkpoint_manager, test_build_state):
    """Test checkpoint restoration."""
    checkpoint_id = checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.LFS,
        "Test checkpoint"
    )
    
    restored = checkpoint_manager.restore_checkpoint(checkpoint_id)
    assert restored.build_state.phase == test_build_state.phase
    assert restored.build_state.status == test_build_state.status
    assert restored.build_state.current_script == test_build_state.current_script


def test_restore_nonexistent_checkpoint(checkpoint_manager):
    """Test restoration of non-existent checkpoint."""
    with pytest.raises(RestorationError):
        checkpoint_manager.restore_checkpoint("nonexistent")


def test_verify_checkpoint(checkpoint_manager, test_build_state):
    """Test checkpoint verification."""
    checkpoint_id = checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.LFS,
        "Test checkpoint"
    )
    
    assert checkpoint_manager.verify_checkpoint(checkpoint_id)


def test_verify_corrupted_checkpoint(checkpoint_manager, test_build_state):
    """Test verification of corrupted checkpoint."""
    checkpoint_id = checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.LFS,
        "Test checkpoint"
    )
    
    # Corrupt metadata file
    metadata_file = checkpoint_manager.checkpoint_dir / checkpoint_id / "metadata.json"
    metadata_file.write_text("corrupted")
    
    assert not checkpoint_manager.verify_checkpoint(checkpoint_id)


def test_list_checkpoints(checkpoint_manager, test_build_state):
    """Test checkpoint listing."""
    # Create multiple checkpoints
    checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.LFS,
        "LFS checkpoint",
        {"lfs"}
    )
    checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.BLFS,
        "BLFS checkpoint",
        {"blfs"}
    )
    
    # List all checkpoints
    checkpoints = checkpoint_manager.list_checkpoints()
    assert len(checkpoints) == 2
    
    # Filter by type
    lfs_checkpoints = checkpoint_manager.list_checkpoints(CheckpointType.LFS)
    assert len(lfs_checkpoints) == 1
    assert lfs_checkpoints[0].checkpoint_type == CheckpointType.LFS
    
    # Filter by tags
    tagged_checkpoints = checkpoint_manager.list_checkpoints(tags={"lfs"})
    assert len(tagged_checkpoints) == 1


def test_delete_checkpoint(checkpoint_manager, test_build_state):
    """Test checkpoint deletion."""
    checkpoint_id = checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.LFS,
        "Test checkpoint"
    )
    
    checkpoint_manager.delete_checkpoint(checkpoint_id)
    assert not (checkpoint_manager.checkpoint_dir / checkpoint_id).exists()


def test_cleanup_old_checkpoints(checkpoint_manager, test_build_state):
    """Test automatic cleanup of old checkpoints."""
    # Create more checkpoints than max_checkpoints
    for i in range(5):
        checkpoint_manager.create_checkpoint(
            test_build_state,
            CheckpointType.LFS,
            f"Checkpoint {i}"
        )
        time.sleep(0.1)  # Ensure different timestamps
    
    checkpoints = checkpoint_manager.list_checkpoints()
    assert len(checkpoints) == 3  # max_checkpoints
    
    # Verify we kept the newest ones
    timestamps = [c.timestamp for c in checkpoints]
    assert sorted(timestamps, reverse=True) == timestamps


@patch('lfs_wrapper.checkpoint_manager.CheckpointManager._compute_checksums')
def test_checksum_verification(mock_compute, checkpoint_manager, test_build_state):
    """Test file checksum verification."""
    checksums = {'/test/path1': 'abc123', '/test/path2': 'def456'}
    mock_compute.return_value = checksums
    
    checkpoint_id = checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.LFS,
        "Test checkpoint"
    )
    
    # Verify with matching checksums
    mock_compute.return_value = checksums
    assert checkpoint_manager._verify_checksums(checksums)
    
    # Verify with mismatched checksums
    mock_compute.return_value = {'/test/path1': 'changed'}
    assert not checkpoint_manager._verify_checksums(checksums)


def test_build_log_collection(checkpoint_manager, test_build_state):
    """Test build log collection."""
    checkpoint_id = checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.LFS,
        "Test checkpoint"
    )
    
    snapshot = checkpoint_manager._load_snapshot(
        checkpoint_manager.checkpoint_dir / checkpoint_id
    )
    assert "build.log" in snapshot.build_logs
    assert snapshot.build_logs["build.log"] == "test log"


def test_checkpoint_metadata_serialization(checkpoint_manager, test_build_state):
    """Test checkpoint metadata serialization."""
    checkpoint_id = checkpoint_manager.create_checkpoint(
        test_build_state,
        CheckpointType.LFS,
        "Test checkpoint",
        {"tag1", "tag2"}
    )
    
    metadata = checkpoint_manager._load_metadata(
        checkpoint_manager.checkpoint_dir / checkpoint_id
    )
    assert metadata.checkpoint_id == checkpoint_id
    assert metadata.checkpoint_type == CheckpointType.LFS
    assert metadata.build_phase == BuildPhase.TOOLCHAIN
    assert metadata.tags == {"tag1", "tag2"}

