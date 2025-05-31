#!/usr/bin/env python3
"""
Test Runner Script for LFS Wrapper System

This script manages the complete test execution process, including environment
setup, dependency installation, test execution, and report generation.

Author: WARP System
Created: 2025-05-31
"""

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from loguru import logger

from qa_framework import QAFramework
from qa_framework.test_suite import TestCategory


class TestRunner:
    """
    Manages the complete test execution process.

    This class is responsible for:
    - Setting up the test environment
    - Installing dependencies
    - Initializing the QA framework
    - Running tests
    - Generating reports
    """

    def __init__(self):
        """Initialize the TestRunner."""
        self.base_dir = Path(__file__).parent
        self.test_dir = self.base_dir / "tests"
        self.report_dir = self.base_dir / "test-reports"
        self.temp_dir = Path("/tmp/lfs_test")
        
        # Configure logging
        logger.add(
            self.report_dir / "test_runner.log",
            rotation="100 MB",
            retention="1 week"
        )

    async def setup_environment(self) -> None:
        """Set up the test execution environment."""
        logger.info("Setting up test environment")
        
        # Create required directories
        for path in [
            self.temp_dir,
            self.temp_dir / "build",
            self.temp_dir / "sources",
            self.temp_dir / "logs",
            self.report_dir,
            self.report_dir / "coverage",
            self.report_dir / "allure"
        ]:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {path}")

        # Set up environment variables
        os.environ["LFS_TEST_ROOT"] = str(self.temp_dir)
        os.environ["PYTHONPATH"] = str(self.base_dir)
        
        logger.info("Test environment setup complete")

    def install_dependencies(self) -> None:
        """Install required test dependencies."""
        logger.info("Installing test dependencies")
        
        # Read dependencies from pytest.ini
        pytest_ini = self.base_dir / "pytest.ini"
        if not pytest_ini.exists():
            raise FileNotFoundError("pytest.ini not found")

        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(pytest_ini)
            
            # Get dependencies from pytest.ini
            dependencies = []
            
            # Core dependencies
            dependencies.extend([
                "pytest",
                "pytest-asyncio",
                "pytest-cov",
                "pytest-html",
                "pytest-xdist",
                "pytest-timeout",
                "loguru",
                "pyyaml",
                "psutil"
            ])
            
            # Additional plugin dependencies from pytest.ini
            if config.has_section('dependencies') and config.has_option('dependencies', 'dependency_plugins'):
                plugin_deps = config.get('dependencies', 'dependency_plugins').strip().split('\n')
                dependencies.extend([dep.strip() for dep in plugin_deps if dep.strip()])
            
            logger.info(f"Installing dependencies: {dependencies}")
            
            # Install dependencies in batches to handle any failures
            failed_deps = []
            for dep in dependencies:
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", dep],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    logger.debug(f"Successfully installed {dep}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to install {dep}: {e.stderr}")
                    failed_deps.append(dep)
            
            if failed_deps:
                raise RuntimeError(f"Failed to install dependencies: {failed_deps}")
            
            logger.info("All dependencies installed successfully")
            
        except Exception as e:
            logger.error(f"Dependency installation failed: {str(e)}")
            raise

    async def run_tests(
        self,
        categories: Optional[List[TestCategory]] = None,
        parallel: bool = True
    ) -> None:
        """
        Run the test suite using the QA framework.

        Args:
            categories: Optional list of test categories to run
            parallel: Whether to run tests in parallel
        """
        logger.info("Initializing QA framework")
        framework = QAFramework(base_test_path=str(self.test_dir))
        await framework.initialize()

        logger.info("Starting test execution")
        try:
            # Run tests through QA framework
            results = await framework.run_tests(categories, parallel)
            
            # Process results
            failed_tests = []
            for category, category_results in results.items():
                for test_id, result in category_results.items():
                    if result.status != "SUCCESS":
                        failed_tests.append(f"{category.name}: {test_id}")
            
            if failed_tests:
                logger.error(f"Failed tests: {failed_tests}")
                raise RuntimeError("Test execution failed")
            
            logger.info("Test execution completed successfully")
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            raise
        finally:
            # Generate test summary
            summary = framework.get_test_summary()
            self._save_summary(summary)

    def _save_summary(self, summary: Dict) -> None:
        """
        Save test execution summary.

        Args:
            summary: Test execution summary data
        """
        summary_file = self.report_dir / "test_summary.yaml"
        import yaml
        
        with open(summary_file, 'w') as f:
            yaml.dump(summary, f)
        
        logger.info(f"Test summary saved to {summary_file}")

    def cleanup(self) -> None:
        """Clean up test environment."""
        logger.info("Cleaning up test environment")
        
        # Preserve logs if specified in pytest.ini
        if not self._should_preserve_logs():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        logger.info("Cleanup complete")

    def _should_preserve_logs(self) -> bool:
        """Check if logs should be preserved based on config."""
        import configparser
        config = configparser.ConfigParser()
        config.read(self.base_dir / "pytest.ini")
        
        return (
            config.has_section("resource-management") and
            config.getboolean("resource-management", "preserve_logs", fallback=False)
        )


async def main() -> None:
    """Main test execution function."""
    parser = argparse.ArgumentParser(description="LFS Wrapper Test Runner")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=[cat.name for cat in TestCategory],
        help="Test categories to run"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel test execution"
    )
    parser.add_argument(
        "--keep-logs",
        action="store_true",
        help="Preserve test logs after execution"
    )
    
    args = parser.parse_args()
    
    # Convert category names to enums
    categories = None
    if args.categories:
        categories = [TestCategory[cat] for cat in args.categories]
    
    # Initialize runner
    runner = TestRunner()
    
    try:
        # Setup and run tests
        await runner.setup_environment()
        runner.install_dependencies()
        await runner.run_tests(categories, not args.no_parallel)
        
        logger.info("Test execution completed successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)
    finally:
        if not args.keep_logs:
            runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

