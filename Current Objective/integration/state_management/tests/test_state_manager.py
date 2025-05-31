"""
Test suite for the state management system core functionality.
"""
import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import uuid

from ..state_manager import (
    StateManager,
    BuildState,
    BuildPhase,
    BuildStatus,
    ValidationResult
)
from ..persistence import StatePersistence
from test_runner.core import TestRunner
from test_runner.exceptions import TestRunnerError

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration."""
    return {
        "storage_path": "/tmp/test_state_storage",
        "build": {
            "parallel_jobs": 2,
            "timeout": 1800,
            "retry_count": 2
        },
        "resources": {
            "memory_limit": "2G",
            "cpu_limit": 1,
            "disk_space": "5G"
        }
    }

@pytest.fixture
def state_manager(test_config: Dict[str, Any]) -> StateManager:
    """Create state manager instance for testing."""
    return StateManager(test_config)

class TestStateManager:
    """Test cases for StateManager functionality."""

    def test_initialization(self, state_manager: StateManager):
        """Test state manager initialization."""
        assert state_manager is not None
        assert isinstance(state_manager.persistence, StatePersistence)
        assert state_manager.current_state is None

    def test_initialize_state(self, state_manager: StateManager):
        """Test new state initialization."""
        state = state_manager.initialize_state()
        
        assert state is not None
        assert state.phase == BuildPhase.INIT
        assert state.status == BuildStatus.PENDING
        assert isinstance(state.id, str)
        assert isinstance(state.timestamp, datetime)
        assert len(state.checkpoints) == 1  # Initial checkpoint

    def test_state_transitions(self, state_manager: StateManager):
        """Test valid state transitions."""
        state_manager.initialize_state()
        
        # Test INIT -> SETUP transition
        state = state_manager.transition_state(BuildPhase.SETUP)
        assert state.phase == BuildPhase.SETUP
        
        # Test SETUP -> BUILD transition
        state = state_manager.transition_state(BuildPhase.BUILD)
        assert state.phase == BuildPhase.BUILD
        
        # Verify checkpoint creation
        assert len(state.checkpoints) > 0

    def test_invalid_transition(self, state_manager: StateManager):
        """Test invalid state transitions are rejected."""
        state_manager.initialize_state()
        
        with pytest.raises(ValueError) as exc:
            state_manager.transition_state(BuildPhase.COMPLETE)
        assert "Invalid state transition" in str(exc.value)

    def test_state_updates(self, state_manager: StateManager):
        """Test state update functionality."""
        state = state_manager.initialize_state()
        
        updates = {
            "status": BuildStatus.RUNNING,
            "resources": {"memory": 1024, "cpu": 1},
            "artifacts": ["/tmp/test.log"],
            "metadata": {"version": "1.0.0"}
        }
        
        updated_state = state_manager.update_state(updates)
        assert updated_state.status == BuildStatus.RUNNING
        assert updated_state.resources == updates["resources"]
        assert updated_state.artifacts == updates["artifacts"]
        assert updated_state.metadata == updates["metadata"]

    def test_error_handling(self, state_manager: StateManager):
        """Test error state handling."""
        state_manager.initialize_state()
        
        test_error = TestRunnerError("Test failure")
        error_state = state_manager.handle_error(test_error)
        
        assert error_state.phase == BuildPhase.ERROR
        assert error_state.status == BuildStatus.FAILED
        assert "Test failure" in error_state.metadata["error"]
        assert "error_time" in error_state.metadata

    def test_state_recovery(self, state_manager: StateManager):
        """Test state recovery from checkpoint."""
        initial_state = state_manager.initialize_state()
        checkpoint_id = initial_state.checkpoints[0]
        
        # Transition to new state
        state_manager.transition_state(BuildPhase.SETUP)
        
        # Recover from checkpoint
        recovered_state = state_manager.recovery_handler.restore_checkpoint(checkpoint_id)
        assert recovered_state.phase == BuildPhase.INIT
        assert recovered_state.id == initial_state.id

    def test_resource_validation(self, state_manager: StateManager):
        """Test resource validation rules."""
        state = state_manager.initialize_state()
        
        # Test valid resources
        valid_updates = {
            "resources": {
                "memory": 1024,
                "cpu": 2,
                "disk": 5000
            }
        }
        updated_state = state_manager.update_state(valid_updates)
        assert updated_state.resources == valid_updates["resources"]
        
        # Test invalid resources
        invalid_updates = {
            "resources": {
                "memory": -1,
                "cpu": 0,
                "disk": "invalid"
            }
        }
        with pytest.raises(ValueError):
            state_manager.update_state(invalid_updates)

    def test_artifact_preservation(self, state_manager: StateManager):
        """Test artifact preservation during transitions."""
        state_manager.initialize_state()
        
        # Add artifacts in BUILD phase
        state_manager.transition_state(BuildPhase.SETUP)
        state_manager.transition_state(BuildPhase.BUILD)
        state_manager.update_state({"artifacts": ["/tmp/build.log", "/tmp/output.bin"]})
        
        # Verify artifacts are preserved in TEST phase
        test_state = state_manager.transition_state(BuildPhase.TEST)
        assert len(test_state.artifacts) == 2
        assert "/tmp/build.log" in test_state.artifacts
        assert "/tmp/output.bin" in test_state.artifacts

    def test_metadata_management(self, state_manager: StateManager):
        """Test metadata handling."""
        state = state_manager.initialize_state()
        
        # Add metadata
        metadata = {
            "build_id": "test-123",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }
        state_manager.update_state({"metadata": metadata})
        
        # Verify metadata persistence
        loaded_state = state_manager.load_state(state.id)
        assert loaded_state.metadata == metadata

    def test_test_runner_integration(self, state_manager: StateManager, test_config: Dict[str, Any]):
        """Test integration with test runner."""
        test_runner = TestRunner(test_config)
        state = state_manager.initialize_state()
        
        # Simulate test execution
        state_manager.transition_state(BuildPhase.TEST)
        state_manager.update_state({
            "status": BuildStatus.RUNNING,
            "metadata": {"test_suite": "integration_tests"}
        })
        
        # Verify test runner state tracking
        assert state_manager.current_state.phase == BuildPhase.TEST
        assert state_manager.current_state.status == BuildStatus.RUNNING

    def test_concurrent_operations(self, test_config: Dict[str, Any]):
        """Test concurrent state operations."""
        manager1 = StateManager(test_config)
        manager2 = StateManager(test_config)
        
        # Initialize states
        state1 = manager1.initialize_state()
        state2 = manager2.initialize_state()
        
        # Verify unique states
        assert state1.id != state2.id
        
        # Test concurrent updates
        manager1.update_state({"metadata": {"instance": "1"}})
        manager2.update_state({"metadata": {"instance": "2"}})
        
        # Verify state isolation
        assert manager1.current_state.metadata["instance"] == "1"
        assert manager2.current_state.metadata["instance"] == "2"

