"""
LFS build script management module.

Provides functionality for discovering, validating, and executing LFS build scripts.
Handles script environment setup, execution tracking, and cleanup operations.

Dependencies:
    - PyYAML>=6.0
    - click>=8.0
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from .exceptions import (
    ScriptNotFoundError,
    EnvironmentError,
    ValidationError,
    ExecutionError
)


class ScriptManager:
    """
    Manages LFS build script discovery and execution.

    Handles script discovery, environment validation, execution sequencing,
    and state management for LFS build scripts.

    Attributes:
        script_root (Path): Root directory containing build scripts
        config (Dict): Configuration settings for script execution
        env (Dict[str, str]): Environment variables for script execution
    """

    def __init__(self, script_root: Path, config: Dict) -> None:
        """
        Initialize the script manager.

        Args:
            script_root: Root directory containing build scripts
            config: Configuration dictionary for script execution

        Raises:
            EnvironmentError: If script_root doesn't exist or isn't readable
            ValidationError: If config is missing required fields
        """
        self.script_root = script_root
        self.config = config
        self.env = self._prepare_environment()
        self.logger = logging.getLogger(__name__)

        if not self.script_root.exists():
            raise EnvironmentError(f"Script root directory not found: {script_root}")
        if not self.script_root.is_dir():
            raise EnvironmentError(f"Script root is not a directory: {script_root}")

        self._validate_config()

    def _validate_config(self) -> None:
        """
        Validate the configuration dictionary.

        Raises:
            ValidationError: If required configuration fields are missing
        """
        required_fields = ['environment', 'paths', 'logging']
        missing = [f for f in required_fields if f not in self.config]
        if missing:
            raise ValidationError(f"Missing required config fields: {', '.join(missing)}")

        required_paths = ['sources', 'tools', 'scripts', 'logs']
        missing_paths = [p for p in required_paths if p not in self.config['paths']]
        if missing_paths:
            raise ValidationError(f"Missing required path configs: {', '.join(missing_paths)}")

    def _prepare_environment(self) -> Dict[str, str]:
        """
        Prepare the environment variables for script execution.

        Returns:
            Dict[str, str]: Environment variables dictionary

        Raises:
            EnvironmentError: If required environment variables can't be set
        """
        env = os.environ.copy()
        
        # Add LFS environment variables
        env.update(self.config['environment'])
        
        # Ensure critical variables are set
        required_vars = ['LFS', 'LFS_TGT', 'PATH']
        missing = [v for v in required_vars if not env.get(v)]
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
        
        return env

    def discover_scripts(self) -> List[Path]:
        """
        Discover available build scripts in the script root directory.

        Returns:
            List[Path]: List of discovered script paths
        """
        scripts = []
        for item in self.script_root.glob('*.sh'):
            if item.is_file() and os.access(item, os.X_OK):
                scripts.append(item)
        return sorted(scripts)

    def validate_script(self, script_path: Path) -> bool:
        """
        Validate a build script file.

        Args:
            script_path: Path to the script to validate

        Returns:
            bool: True if script is valid, False otherwise

        Raises:
            ScriptNotFoundError: If script doesn't exist
            ValidationError: If script fails validation checks
        """
        if not script_path.exists():
            raise ScriptNotFoundError(f"Script not found: {script_path}")
        
        if not script_path.is_file():
            raise ValidationError(f"Not a regular file: {script_path}")
        
        if not os.access(script_path, os.X_OK):
            raise ValidationError(f"Script not executable: {script_path}")
        
        # Basic script content validation
        try:
            with open(script_path, 'r') as f:
                first_line = f.readline().strip()
                if not first_line.startswith('#!'):
                    raise ValidationError(f"Missing shebang in script: {script_path}")
        except Exception as e:
            raise ValidationError(f"Failed to validate script {script_path}: {str(e)}")
        
        return True

    def execute_script(
        self,
        script_path: Path,
        args: Optional[List[str]] = None,
        timeout: Optional[int] = None
    ) -> Tuple[int, str, str]:
        """
        Execute a build script with the configured environment.

        Args:
            script_path: Path to the script to execute
            args: Optional list of arguments to pass to the script
            timeout: Optional timeout in seconds

        Returns:
            Tuple[int, str, str]: (return_code, stdout, stderr)

        Raises:
            ScriptNotFoundError: If script doesn't exist
            ExecutionError: If script execution fails
        """
        self.validate_script(script_path)
        
        cmd = [str(script_path)]
        if args:
            cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        
        except subprocess.TimeoutExpired as e:
            raise ExecutionError(f"Script execution timed out: {script_path}")
        except subprocess.SubprocessError as e:
            raise ExecutionError(f"Script execution failed: {str(e)}")
        except Exception as e:
            raise ExecutionError(f"Unexpected error executing script: {str(e)}")

    def get_script_metadata(self, script_path: Path) -> Dict:
        """
        Extract metadata from a build script.

        Args:
            script_path: Path to the script

        Returns:
            Dict: Script metadata dictionary

        Raises:
            ScriptNotFoundError: If script doesn't exist
            ValidationError: If metadata extraction fails
        """
        if not script_path.exists():
            raise ScriptNotFoundError(f"Script not found: {script_path}")
        
        metadata = {
            'name': script_path.name,
            'path': str(script_path),
            'size': script_path.stat().st_size,
            'executable': os.access(script_path, os.X_OK),
        }
        
        try:
            with open(script_path, 'r') as f:
                # Extract metadata from script comments
                for i, line in enumerate(f):
                    if i > 10:  # Only check first 10 lines
                        break
                    if line.startswith('# DESCRIPTION:'):
                        metadata['description'] = line.replace('# DESCRIPTION:', '').strip()
                    elif line.startswith('# DEPENDENCIES:'):
                        metadata['dependencies'] = [
                            d.strip() for d in
                            line.replace('# DEPENDENCIES:', '').strip().split(',')
                        ]
        except Exception as e:
            raise ValidationError(f"Failed to extract metadata from {script_path}: {str(e)}")
        
        return metadata

