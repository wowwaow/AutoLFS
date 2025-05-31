"""
Core state management implementation for the LFS/BLFS Build Scripts Wrapper System.
"""
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import uuid

from .persistence import StatePersistence
from test_runner.core import TestRunner
from test_runner.exceptions import TestRunnerError

class BuildPhase(Enum):
    """Build process phases."""
    INIT = auto()
    SETUP = auto()
    BUILD = auto()
    TEST = auto()
    CLEANUP = auto()
    COMPLETE = auto()
    ERROR = auto()

class BuildStatus(Enum):
    """Build status indicators."""
    PENDING = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    RECOVERING = auto()

class ValidationResult:
    """Result of state validation."""
    def __init__(self, valid: bool, errors: List[str] = None):
        self.valid = valid
        self.errors = errors or []

class BuildState:
    """Represents the current state of a build process."""
    
    def __init__(
        self,
        phase: BuildPhase,
        status: BuildStatus,
        resources: Dict[str, Any] = None,
        artifacts: List[str] = None,
        dependencies: Dict = None,
        metadata: Dict[str, Any] = None
    ):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self.phase = phase
        self.status = status
        self.resources = resources or {}
        self.artifacts = artifacts or []
        self.dependencies = dependencies or {}
        self.checkpoints = []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for persistence."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase.name,
            "status": self.status.name,
            "resources": self.resources,
            "artifacts": self.artifacts,
            "dependencies": self.dependencies,
            "checkpoints": self.checkpoints,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BuildState':
        """Create state instance from dictionary."""
        state = cls(
            phase=BuildPhase[data["phase"]],
            status=BuildStatus[data["status"]],
            resources=data["resources"],
            artifacts=data["artifacts"],
            dependencies=data["dependencies"],
            metadata=data["metadata"]
        )
        state.id = data["id"]
        state.timestamp = datetime.fromisoformat(data["timestamp"])
        state.checkpoints = data["checkpoints"]
        return state

class StateValidator:
    """Validates build states and transitions."""

    VALID_TRANSITIONS = {
        BuildPhase.INIT: [BuildPhase.SETUP, BuildPhase.ERROR],
        BuildPhase.SETUP: [BuildPhase.BUILD, BuildPhase.ERROR],
        BuildPhase.BUILD: [BuildPhase.TEST, BuildPhase.ERROR],
        BuildPhase.TEST: [BuildPhase.CLEANUP, BuildPhase.ERROR],
        BuildPhase.CLEANUP: [BuildPhase.COMPLETE, BuildPhase.ERROR],
        BuildPhase.ERROR: [BuildPhase.INIT, BuildPhase.CLEANUP],
        BuildPhase.COMPLETE: []
    }

    def validate_state(self, state: BuildState) -> ValidationResult:
        """Validate state structure and contents."""
        errors = []

        # Validate required fields
        if not state.id or not isinstance(state.id, str):
            errors.append("Invalid state ID")
        if not state.timestamp or not isinstance(state.timestamp, datetime):
            errors.append("Invalid timestamp")
        if not isinstance(state.phase, BuildPhase):
            errors.append("Invalid build phase")
        if not isinstance(state.status, BuildStatus):
            errors.append("Invalid build status")

        # Validate resources
        for resource, value in state.resources.items():
            if not self._validate_resource(resource, value):
                errors.append(f"Invalid resource: {resource}")

        # Validate artifacts
        for artifact in state.artifacts:
            if not Path(artifact).exists():
                errors.append(f"Missing artifact: {artifact}")

        # Validate checkpoints
        for checkpoint in state.checkpoints:
            if not self._validate_checkpoint(checkpoint):
                errors.append(f"Invalid checkpoint: {checkpoint}")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_transition(self, from_state: BuildState, to_state: BuildState) -> ValidationResult:
        """Validate state transition."""
        errors = []

        # Check if transition is allowed
        if to_state.phase not in self.VALID_TRANSITIONS[from_state.phase]:
            errors.append(f"Invalid transition: {from_state.phase} -> {to_state.phase}")

        # Validate resource changes
        if not self._validate_resource_transition(from_state, to_state):
            errors.append("Invalid resource transition")

        # Validate artifact preservation
        if not self._validate_artifact_transition(from_state, to_state):
            errors.append("Invalid artifact transition")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _validate_resource(self, resource: str, value: Any) -> bool:
        """Validate individual resource configuration."""
        try:
            if resource == "memory":
                return isinstance(value, (int, float)) and value > 0
            elif resource == "cpu":
                return isinstance(value, int) and value > 0
            elif resource == "disk":
                return isinstance(value, (int, float)) and value > 0
            return True
        except Exception:
            return False

    def _validate_checkpoint(self, checkpoint: str) -> bool:
        """Validate checkpoint identifier."""
        try:
            return bool(uuid.UUID(checkpoint, version=4))
        except ValueError:
            return False

    def _validate_resource_transition(self, from_state: BuildState, to_state: BuildState) -> bool:
        """Validate resource state changes."""
        if from_state.phase == BuildPhase.CLEANUP:
            return len(to_state.resources) == 0
        return True

    def _validate_artifact_transition(self, from_state: BuildState, to_state: BuildState) -> bool:
        """Validate artifact preservation rules."""
        if from_state.phase in [BuildPhase.BUILD, BuildPhase.TEST]:
            return set(from_state.artifacts).issubset(set(to_state.artifacts))
        return True

class RecoveryHandler:
    """Handles state recovery and checkpoints."""

    def __init__(self, persistence: StatePersistence):
        self.persistence = persistence
        self.logger = logging.getLogger(__name__)

    def create_checkpoint(self, state: BuildState) -> str:
        """Create a new checkpoint for the current state."""
        checkpoint_id = str(uuid.uuid4())
        
        try:
            # Store checkpoint
            self.persistence.save_checkpoint(checkpoint_id, state)
            
            # Update state
            state.checkpoints.append(checkpoint_id)
            
            self.logger.info(f"Created checkpoint {checkpoint_id} for state {state.id}")
            return checkpoint_id
        except Exception as e:
            self.logger.error(f"Failed to create checkpoint: {e}")
            raise

    def restore_checkpoint(self, checkpoint_id: str) -> BuildState:
        """Restore state from a checkpoint."""
        try:
            # Load checkpoint
            state = self.persistence.load_checkpoint(checkpoint_id)
            
            # Validate restored state
            validator = StateValidator()
            result = validator.validate_state(state)
            
            if not result.valid:
                raise ValueError(f"Invalid checkpoint state: {result.errors}")
            
            self.logger.info(f"Restored checkpoint {checkpoint_id} for state {state.id}")
            return state
        except Exception as e:
            self.logger.error(f"Failed to restore checkpoint: {e}")
            raise

class StateManager:
    """Core state management system."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.persistence = StatePersistence(config["storage_path"])
        self.validator = StateValidator()
        self.recovery_handler = RecoveryHandler(self.persistence)
        self.logger = logging.getLogger(__name__)
        self.current_state: Optional[BuildState] = None

    def initialize_state(self) -> BuildState:
        """Initialize a new build state."""
        state = BuildState(
            phase=BuildPhase.INIT,
            status=BuildStatus.PENDING
        )
        
        validation = self.validator.validate_state(state)
        if not validation.valid:
            raise ValueError(f"Invalid initial state: {validation.errors}")
            
        self.current_state = state
        self.persistence.save_state(state)
        
        # Create initial checkpoint
        self.recovery_handler.create_checkpoint(state)
        
        return state

    def transition_state(self, target_phase: BuildPhase) -> BuildState:
        """Transition to a new state phase."""
        if not self.current_state:
            raise ValueError("No current state")

        # Create new state
        new_state = BuildState(
            phase=target_phase,
            status=BuildStatus.PENDING,
            resources=self.current_state.resources.copy(),
            artifacts=self.current_state.artifacts.copy(),
            dependencies=self.current_state.dependencies.copy(),
            metadata=self.current_state.metadata.copy()
        )

        # Validate transition
        validation = self.validator.validate_transition(self.current_state, new_state)
        if not validation.valid:
            raise ValueError(f"Invalid state transition: {validation.errors}")

        # Create checkpoint before transition
        self.recovery_handler.create_checkpoint(self.current_state)

        # Update state
        self.current_state = new_state
        self.persistence.save_state(new_state)

        return new_state

    def update_state(self, updates: Dict[str, Any]) -> BuildState:
        """Update current state with new information."""
        if not self.current_state:
            raise ValueError("No current state")

        # Apply updates
        for key, value in updates.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)

        # Validate updated state
        validation = self.validator.validate_state(self.current_state)
        if not validation.valid:
            raise ValueError(f"Invalid state update: {validation.errors}")

        # Save updated state
        self.persistence.save_state(self.current_state)

        return self.current_state

    def handle_error(self, error: Exception) -> BuildState:
        """Handle error by transitioning to error state."""
        if not self.current_state:
            raise ValueError("No current state")

        # Create error state
        error_state = BuildState(
            phase=BuildPhase.ERROR,
            status=BuildStatus.FAILED,
            resources=self.current_state.resources.copy(),
            artifacts=self.current_state.artifacts.copy(),
            dependencies=self.current_state.dependencies.copy(),
            metadata={
                **self.current_state.metadata,
                "error": str(error),
                "error_time": datetime.utcnow().isoformat()
            }
        )

        # Validate error state
        validation = self.validator.validate_state(error_state)
        if not validation.valid:
            self.logger.error(f"Invalid error state: {validation.errors}")
            raise ValueError(f"Invalid error state: {validation.errors}")

        # Update state
        self.current_state = error_state
        self.persistence.save_state(error_state)

        return error_state

    def load_state(self, state_id: str) -> BuildState:
        """Load existing state."""
        state = self.persistence.load_state(state_id)
        
        # Validate loaded state
        validation = self.validator.validate_state(state)
        if not validation.valid:
            raise ValueError(f"Invalid loaded state: {validation.errors}")
            
        self.current_state = state
        return state

    def list_states(self, filter_criteria: Dict[str, Any] = None) -> List[BuildState]:
        """List all states matching filter criteria."""
        return self.persistence.list_states(filter_criteria)

    def archive_state(self, state_id: str) -> bool:
        """Archive a completed state."""
        return self.persistence.archive_state(state_id)

