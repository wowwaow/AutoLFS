"""
Test suite for state persistence functionality.
"""
import pytest
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid

from ..persistence import StatePersistence, StateFilter
from ..state_manager import BuildState, BuildPhase, BuildStatus

@pytest.fixture
def test_storage_path(tmp_path: Path) -> Path:
    """Create temporary storage directory."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    yield storage_dir
    shutil.rmtree(storage_dir)

@pytest.fixture
def persistence(test_storage_path: Path) -> StatePersistence:
    """Create persistence instance for testing."""
    return StatePersistence(str(test_storage_path))

@pytest.fixture
def test_state() -> BuildState:
    """Create test build state."""
    return BuildState(
        phase=BuildPhase.INIT,
        status=BuildStatus.PENDING,
        resources={"memory": 1024, "cpu": 1},
        artifacts=["/tmp/test.log"],
        dependencies={"lib1": "1.0.0"},
        metadata={"version": "1.0.0"}
    )

class TestStatePersistence:
    """Test cases for state persistence functionality."""

    def test_initialization(self, persistence: StatePersistence, test_storage_path: Path):
        """Test persistence system initialization."""
        assert persistence.storage_path == test_storage_path
        assert persistence.active_path.exists()
        assert persistence.archived_path.exists()
        assert persistence.backup_path.exists()
        assert (persistence.active_path / "index.json").exists()

    def test_save_state(self, persistence: StatePersistence, test_state: BuildState):
        """Test state saving functionality."""
        # Save state
        success = persistence.save_state(test_state)
        assert success
        
        # Verify file creation
        state_dir = persistence.active_path / test_state.id
        state_file = state_dir / "current_state.json"
        assert state_file.exists()
        
        # Verify content
        with open(state_file) as f:
            saved_data = json.load(f)
        assert saved_data["id"] == test_state.id
        assert saved_data["phase"] == test_state.phase.name
        assert saved_data["status"] == test_state.status.name

    def test_load_state(self, persistence: StatePersistence, test_state: BuildState):
        """Test state loading functionality."""
        # Save and load state
        persistence.save_state(test_state)
        loaded_state = persistence.load_state(test_state.id)
        
        # Verify loaded data
        assert loaded_state["id"] == test_state.id
        assert loaded_state["phase"] == test_state.phase.name
        assert loaded_state["resources"] == test_state.resources
        assert loaded_state["artifacts"] == test_state.artifacts

    def test_state_filtering(self, persistence: StatePersistence):
        """Test state filtering functionality."""
        # Create multiple states
        states = []
        for i in range(3):
            state = BuildState(
                phase=BuildPhase.INIT if i < 2 else BuildPhase.SETUP,
                status=BuildStatus.PENDING,
                metadata={"index": i}
            )
            persistence.save_state(state)
            states.append(state)
        
        # Test filtering
        filter_criteria = {"phase": "INIT"}
        filtered_states = persistence.list_states(filter_criteria)
        assert len(filtered_states) == 2
        assert all(s["phase"] == "INIT" for s in filtered_states)

    def test_checkpointing(self, persistence: StatePersistence, test_state: BuildState):
        """Test checkpoint creation and loading."""
        # Create checkpoint
        checkpoint_id = str(uuid.uuid4())
        success = persistence.save_checkpoint(checkpoint_id, test_state)
        assert success
        
        # Verify checkpoint file
        checkpoint_dir = persistence.active_path / test_state.id / "checkpoints"
        checkpoint_file = checkpoint_dir / f"{checkpoint_id}.json"
        assert checkpoint_file.exists()
        
        # Load checkpoint
        loaded_checkpoint = persistence.load_checkpoint(checkpoint_id)
        assert loaded_checkpoint["id"] == test_state.id
        assert loaded_checkpoint["phase"] == test_state.phase.name

    def test_state_archiving(self, persistence: StatePersistence, test_state: BuildState):
        """Test state archiving functionality."""
        # Save state
        persistence.save_state(test_state)
        
        # Archive state
        success = persistence.archive_state(test_state.id)
        assert success
        
        # Verify archival
        original_dir = persistence.active_path / test_state.id
        assert not original_dir.exists()
        
        archived_states = list(persistence.archived_path.glob(f"{test_state.id}_*"))
        assert len(archived_states) == 1

    def test_backup_creation(self, persistence: StatePersistence, test_state: BuildState):
        """Test backup creation functionality."""
        # Save state
        persistence.save_state(test_state)
        
        # Verify backup
        backups = list(persistence.backup_path.glob(f"{test_state.id}_*"))
        assert len(backups) == 1
        
        # Verify backup content
        backup_state_file = next(backups[0].glob("current_state.json"))
        with open(backup_state_file) as f:
            backup_data = json.load(f)
        assert backup_data["id"] == test_state.id

    def test_concurrent_access(self, test_storage_path: Path):
        """Test concurrent access handling."""
        persistence1 = StatePersistence(str(test_storage_path))
        persistence2 = StatePersistence(str(test_storage_path))
        
        # Create test states
        state1 = BuildState(phase=BuildPhase.INIT, status=BuildStatus.PENDING)
        state2 = BuildState(phase=BuildPhase.INIT, status=BuildStatus.PENDING)
        
        # Concurrent saves
        persistence1.save_state(state1)
        persistence2.save_state(state2)
        
        # Verify both states saved
        assert (persistence1.active_path / state1.id).exists()
        assert (persistence2.active_path / state2.id).exists()

    def test_index_management(self, persistence: StatePersistence, test_state: BuildState):
        """Test state index management."""
        # Save state
        persistence.save_state(test_state)
        
        # Verify index update
        index_file = persistence.active_path / "index.json"
        with open(index_file) as f:
            index = json.load(f)
        
        assert test_state.id in index["states"]
        assert index["states"][test_state.id]["phase"] == test_state.phase.name
        
        # Test index cleanup after archival
        persistence.archive_state(test_state.id)
        with open(index_file) as f:
            updated_index = json.load(f)
        assert test_state.id not in updated_index["states"]

    def test_error_handling(self, persistence: StatePersistence):
        """Test error handling in persistence operations."""
        # Test loading non-existent state
        with pytest.raises(FileNotFoundError):
            persistence.load_state("non_existent_id")
        
        # Test loading non-existent checkpoint
        with pytest.raises(FileNotFoundError):
            persistence.load_checkpoint("non_existent_checkpoint")
        
        # Test archiving non-existent state
        with pytest.raises(FileNotFoundError):
            persistence.archive_state("non_existent_id")

    def test_state_cleanup(self, persistence: StatePersistence, test_state: BuildState):
        """Test state cleanup and resource management."""
        # Save state with temporary resources
        test_state.resources["temp_file"] = "/tmp/temp.dat"
        persistence.save_state(test_state)
        
        # Archive state
        persistence.archive_state(test_state.id)
        
        # Verify cleanup
        assert not (persistence.active_path / test_state.id).exists()
        assert len(list(persistence.active_path.glob(f"{test_state.id}*"))) == 0

