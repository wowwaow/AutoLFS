"""
State persistence implementation for the state management system.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import fcntl

class StateFilter:
    """Filter criteria for state queries."""
    def __init__(self, criteria: Dict[str, Any]):
        self.criteria = criteria

    def matches(self, state: Dict[str, Any]) -> bool:
        """Check if state matches filter criteria."""
        for key, value in self.criteria.items():
            if key not in state or state[key] != value:
                return False
        return True

class StatePersistence:
    """Handles state storage and retrieval."""

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.active_path = self.storage_path / "active"
        self.archived_path = self.storage_path / "archived"
        self.backup_path = self.storage_path / "backups"
        self.logger = logging.getLogger(__name__)

        # Ensure directory structure exists
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize storage directory structure."""
        for path in [self.active_path, self.archived_path, self.backup_path]:
            path.mkdir(parents=True, exist_ok=True)

        # Create index file if it doesn't exist
        index_file = self.active_path / "index.json"
        if not index_file.exists():
            self._write_json(index_file, {"states": {}})

    def save_state(self, state: Any) -> bool:
        """Save state to storage."""
        try:
            # Convert state to dictionary
            state_data = state.to_dict()
            
            # Create state directory
            state_dir = self.active_path / state.id
            state_dir.mkdir(exist_ok=True)
            
            # Create temporary file
            state_file = state_dir / "current_state.json"
            temp_file = state_file.with_suffix(".tmp")
            
            # Write state to temporary file
            self._write_json(temp_file, state_data)
            
            # Atomic rename
            temp_file.rename(state_file)
            
            # Update index
            self._update_index(state.id, state_data)
            
            # Create backup
            self._create_backup(state.id)
            
            self.logger.info(f"Saved state {state.id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            raise

    def load_state(self, state_id: str) -> Any:
        """Load state from storage."""
        try:
            state_file = self.active_path / state_id / "current_state.json"
            if not state_file.exists():
                raise FileNotFoundError(f"State {state_id} not found")
            
            state_data = self._read_json(state_file)
            return state_data
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            raise

    def list_states(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List all states matching filter criteria."""
        try:
            index = self._read_json(self.active_path / "index.json")
            states = index.get("states", {}).values()
            
            if filter_criteria:
                state_filter = StateFilter(filter_criteria)
                states = [s for s in states if state_filter.matches(s)]
            
            return list(states)
        except Exception as e:
            self.logger.error(f"Failed to list states: {e}")
            raise

    def archive_state(self, state_id: str) -> bool:
        """Move state to archive."""
        try:
            source_dir = self.active_path / state_id
            if not source_dir.exists():
                raise FileNotFoundError(f"State {state_id} not found")
            
            # Create archive directory with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_dir = self.archived_path / f"{state_id}_{timestamp}"
            
            # Move state to archive
            shutil.move(str(source_dir), str(archive_dir))
            
            # Update index
            self._remove_from_index(state_id)
            
            self.logger.info(f"Archived state {state_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to archive state: {e}")
            raise

    def save_checkpoint(self, checkpoint_id: str, state: Any) -> bool:
        """Save state checkpoint."""
        try:
            # Convert state to dictionary
            state_data = state.to_dict()
            
            # Create checkpoint directory
            checkpoint_dir = self.active_path / state.id / "checkpoints"
            checkpoint_dir.mkdir(exist_ok=True)
            
            # Save checkpoint
            checkpoint_file = checkpoint_dir / f"{checkpoint_id}.json"
            self._write_json(checkpoint_file, state_data)
            
            self.logger.info(f"Created checkpoint {checkpoint_id} for state {state.id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            raise

    def load_checkpoint(self, checkpoint_id: str) -> Any:
        """Load state from checkpoint."""
        try:
            # Find checkpoint file
            for state_dir in self.active_path.iterdir():
                if state_dir.is_dir():
                    checkpoint_file = state_dir / "checkpoints" / f"{checkpoint_id}.json"
                    if checkpoint_file.exists():
                        return self._read_json(checkpoint_file)
            
            raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            raise

    def _write_json(self, file_path: Path, data: Dict) -> None:
        """Write JSON data with file locking."""
        with open(file_path, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(data, f, indent=2)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _read_json(self, file_path: Path) -> Dict:
        """Read JSON data with file locking."""
        with open(file_path, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return data

    def _update_index(self, state_id: str, state_data: Dict) -> None:
        """Update state index."""
        index_file = self.active_path / "index.json"
        index = self._read_json(index_file)
        index["states"][state_id] = {
            "id": state_id,
            "phase": state_data["phase"],
            "status": state_data["status"],
            "timestamp": state_data["timestamp"]
        }
        self._write_json(index_file, index)

    def _remove_from_index(self, state_id: str) -> None:
        """Remove state from index."""
        index_file = self.active_path / "index.json"
        index = self._read_json(index_file)
        if state_id in index["states"]:
            del index["states"][state_id]
        self._write_json(index_file, index)

    def _create_backup(self, state_id: str) -> None:
        """Create state backup."""
        source_dir = self.active_path / state_id
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_path / f"{state_id}_{timestamp}"
        
        # Create backup
        shutil.copytree(str(source_dir), str(backup_dir))

