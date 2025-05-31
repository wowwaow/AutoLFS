"""
Command line interface for LFS build script wrapper.

Provides commands for managing LFS build process, including build phase
execution, status monitoring, and error handling.

Dependencies:
    - click>=8.0
    - PyYAML>=6.0
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click
import yaml

from .build_manager import BuildManager, BuildPhase, BuildStatus
from .exceptions import BuildError, ConfigurationError, ValidationError


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_config(config_file: Path) -> dict:
    """
    Load configuration from YAML file.

    Args:
        config_file: Path to configuration file

    Returns:
        dict: Configuration dictionary

    Raises:
        click.FileError: If config file cannot be read
        click.UsageError: If config file is invalid
    """
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise click.FileError(
            str(config_file),
            hint="Configuration file not found"
        )
    except yaml.YAMLError as e:
        raise click.UsageError(f"Invalid configuration file: {e}")


@click.group()
@click.option(
    '--config',
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default='config.yaml',
    help='Path to configuration file'
)
@click.option(
    '--verbose/--quiet',
    default=False,
    help='Enable verbose output'
)
@click.pass_context
def cli(ctx: click.Context, config: Path, verbose: bool) -> None:
    """LFS build script wrapper command line interface."""
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(config)
    ctx.obj['verbose'] = verbose


@cli.command()
@click.argument(
    'build_root',
    type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.pass_context
def setup(ctx: click.Context, build_root: Path) -> None:
    """Initialize build environment and prepare for build process."""
    try:
        manager = BuildManager(build_root, ctx.obj['config'])
        click.echo("Setting up build environment...")
        
        # Execute setup phase scripts
        manager.execute_phase(BuildPhase.TOOLCHAIN)
        click.echo("Build environment setup completed successfully")
        
    except (ConfigurationError, ValidationError) as e:
        click.echo(f"Setup failed: {str(e)}", err=True)
        sys.exit(1)
    except BuildError as e:
        click.echo(f"Build setup failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument(
    'build_root',
    type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    '--phase',
    type=click.Choice([p.name.lower() for p in BuildPhase]),
    help='Specific build phase to execute'
)
@click.pass_context
def build(ctx: click.Context, build_root: Path, phase: Optional[str]) -> None:
    """Execute the build process or a specific build phase."""
    try:
        manager = BuildManager(build_root, ctx.obj['config'])
        
        if phase:
            # Execute specific phase
            build_phase = BuildPhase[phase.upper()]
            click.echo(f"Executing build phase: {phase}")
            manager.execute_phase(build_phase)
            click.echo(f"Phase {phase} completed successfully")
        else:
            # Execute all phases in sequence
            for build_phase in BuildPhase:
                if build_phase != BuildPhase.CONFIGURATION:  # Configuration handled separately
                    click.echo(f"Executing build phase: {build_phase.name}")
                    manager.execute_phase(build_phase)
            click.echo("Build process completed successfully")
        
    except BuildError as e:
        click.echo(f"Build failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument(
    'build_root',
    type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.pass_context
def configure(ctx: click.Context, build_root: Path) -> None:
    """Configure the built system."""
    try:
        manager = BuildManager(build_root, ctx.obj['config'])
        click.echo("Configuring system...")
        manager.execute_phase(BuildPhase.CONFIGURATION)
        click.echo("System configuration completed successfully")
        
    except BuildError as e:
        click.echo(f"Configuration failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument(
    'build_root',
    type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.pass_context
def status(ctx: click.Context, build_root: Path) -> None:
    """Show current build status and progress."""
    try:
        manager = BuildManager(build_root, ctx.obj['config'])
        progress = manager.get_build_progress()
        
        click.echo("Build Status:")
        click.echo(f"  Phase: {progress['phase']}")
        click.echo(f"  Status: {progress['status']}")
        click.echo(f"  Current Script: {progress['current_script'] or 'None'}")
        click.echo(f"  Completed Scripts: {progress['completed_scripts']}")
        click.echo(f"  Failed Scripts: {progress['failed_scripts']}")
        click.echo(f"  Error Count: {progress['error_count']}")
        click.echo(f"  Runtime: {progress['runtime']:.2f} seconds")
        
    except (ConfigurationError, ValidationError) as e:
        click.echo(f"Failed to get status: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument(
    'build_root',
    type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.pass_context
def cleanup(ctx: click.Context, build_root: Path) -> None:
    """Clean up build artifacts and temporary files."""
    try:
        manager = BuildManager(build_root, ctx.obj['config'])
        click.echo("Cleaning up build artifacts...")
        manager.cleanup()
        click.echo("Cleanup completed successfully")
        
    except Exception as e:
        click.echo(f"Cleanup failed: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli(obj={})

#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional
import click
import yaml

# Add lib directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "lib"))
from lfs_core import LFSCore, LFSError, BuildEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('lfs_wrapper.log')
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise click.ClickException(f"Configuration error: {e}")

class LFSWrapper:
    """Main wrapper class for LFS build system."""
    
    def __init__(self, config_path: str):
        """Initialize wrapper with configuration."""
        self.config = load_config(config_path)
        self.core = LFSCore(self.config)
        
    def setup_environment(self) -> None:
        """Set up the LFS build environment."""
        try:
            self.core.env.setup()
            self.core.validate_environment()
        except LFSError as e:
            logger.error(f"Environment setup failed: {e}")
            raise click.ClickException(str(e))
    
    def execute_script(self, script_name: str, args: Optional[List[str]] = None) -> None:
        """Execute an LFS build script."""
        try:
            self.core.execute_script(script_name, args)
        except LFSError as e:
            logger.error(f"Script execution failed: {e}")
            raise click.ClickException(str(e))
    
    def get_status(self) -> Dict:
        """Get current build environment status."""
        return self.core.env.get_status()

@click.group()
@click.option('--config', default='../config/config.yaml', help='Path to configuration file')
@click.pass_context
def cli(ctx, config):
    """LFS Build Script Wrapper System"""
    try:
        ctx.obj = LFSWrapper(config)
    except Exception as e:
        logger.error(f"Failed to initialize wrapper: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.pass_obj
def setup(wrapper: LFSWrapper):
    """Set up the LFS build environment."""
    wrapper.setup_environment()
    click.echo("Environment setup complete")

@cli.command()
@click.argument('script')
@click.argument('args', nargs=-1)
@click.pass_obj
def run(wrapper: LFSWrapper, script: str, args: tuple):
    """Execute an LFS build script."""
    wrapper.execute_script(script, list(args))
    click.echo(f"Successfully executed {script}")

@cli.command()
@click.pass_obj
def status(wrapper: LFSWrapper):
    """Show current build status and environment information."""
    status_info = wrapper.get_status()
    for key, value in status_info.items():
        click.echo(f"{key}: {value}")

if __name__ == '__main__':
    cli(obj=None)

