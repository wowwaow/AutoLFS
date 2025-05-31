#!/usr/bin/env python3
"""
Test Runner Implementation for LFS/BLFS Build Scripts Wrapper System.
Handles test execution, resource management, and result collection.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import yaml
from psutil import Process, cpu_percent, virtual_memory

# Configuration and logging setup
CONFIG_PATH = Path(__file__).parent / "config.yaml"
LOG_DIR = Path("/mnt/host/WARP_CURRENT/Work Logs")
RESULTS_DIR = Path("/mnt/host/WARP_CURRENT/Current Objective/integration/testing/results")

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "test_runner.log"),
        logging.StreamHandler()
    ]
)

class TestStatus(Enum):
    """Test execution status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class TestResult:
    """Test execution result container."""
    test_id: str
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime]
    execution_time: float
    output: str
    error: Optional[str]
    resources: Dict[str, float]

class ResourceManager:
    """Manages system resources for test execution."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.resources = config['resource_allocation']
        self._active_tests: Set[str] = set()
        self._resource_locks: Dict[str, asyncio.Lock] = {}
    
    async def allocate(self, test_id: str) -> bool:
        """Allocate resources for a test."""
        if not self._check_available_resources():
            return False
        
        async with self._get_lock():
            if self._can_allocate():
                self._active_tests.add(test_id)
                return True
        return False
    
    async def release(self, test_id: str) -> None:
        """Release resources allocated to a test."""
        async with self._get_lock():
            self._active_tests.remove(test_id)
    
    def _check_available_resources(self) -> bool:
        """Check if required resources are available."""
        cpu = cpu_percent(interval=1)
        mem = virtual_memory().percent
        
        return (cpu < self.resources['computation']['cpu']['warning_threshold'] and
                mem < self.resources['computation']['memory']['warning_threshold'])
    
    def _can_allocate(self) -> bool:
        """Check if new test can be allocated resources."""
        return len(self._active_tests) < self.resources['computation']['max_concurrent_tests']
    
    def _get_lock(self) -> asyncio.Lock:
        """Get or create resource lock."""
        if 'resource_lock' not in self._resource_locks:
            self._resource_locks['resource_lock'] = asyncio.Lock()
        return self._resource_locks['resource_lock']

class ResultCollector:
    """Collects and manages test results."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.results_dir = RESULTS_DIR
        self._results: Dict[str, TestResult] = {}
    
    def add_result(self, result: TestResult) -> None:
        """Add a test result."""
        self._results[result.test_id] = result
        self._save_result(result)
    
    def get_result(self, test_id: str) -> Optional[TestResult]:
        """Get a specific test result."""
        return self._results.get(test_id)
    
    def _save_result(self, result: TestResult) -> None:
        """Save test result to file."""
        result_file = self.results_dir / f"{result.test_id}_{result.end_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w') as f:
            json.dump({
                'test_id': result.test_id,
                'status': result.status.value,
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat() if result.end_time else None,
                'execution_time': result.execution_time,
                'output': result.output,
                'error': result.error,
                'resources': result.resources
            }, f, indent=2)

class TestRunner:
    """Main test runner implementation."""
    
    def __init__(self):
        with open(CONFIG_PATH) as f:
            self.config = yaml.safe_load(f)
        
        self.resource_manager = ResourceManager(self.config)
        self.result_collector = ResultCollector(self.config)
        self._active_tests: Dict[str, asyncio.Task] = {}
    
    async def execute_test(self, test_spec: Dict) -> TestResult:
        """Execute a single test."""
        test_id = test_spec['id']
        start_time = datetime.now()
        
        # Try to allocate resources
        if not await self.resource_manager.allocate(test_id):
            return TestResult(
                test_id=test_id,
                status=TestStatus.SKIPPED,
                start_time=start_time,
                end_time=datetime.now(),
                execution_time=0.0,
                output="",
                error="Resource allocation failed",
                resources={}
            )
        
        try:
            # Execute test
            proc = await asyncio.create_subprocess_exec(
                *test_spec['command'],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            result = TestResult(
                test_id=test_id,
                status=TestStatus.COMPLETED if proc.returncode == 0 else TestStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                execution_time=execution_time,
                output=stdout.decode(),
                error=stderr.decode() if stderr else None,
                resources=self._collect_resource_metrics()
            )
            
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            result = TestResult(
                test_id=test_id,
                status=TestStatus.ERROR,
                start_time=start_time,
                end_time=end_time,
                execution_time=execution_time,
                output="",
                error=str(e),
                resources=self._collect_resource_metrics()
            )
            
        finally:
            await self.resource_manager.release(test_id)
            self.result_collector.add_result(result)
        
        return result
    
    async def schedule_tests(self, test_suite: List[Dict]) -> None:
        """Schedule a suite of tests for execution."""
        for test_spec in test_suite:
            task = asyncio.create_task(self.execute_test(test_spec))
            self._active_tests[test_spec['id']] = task
        
        await asyncio.gather(*self._active_tests.values())
    
    def _collect_resource_metrics(self) -> Dict[str, float]:
        """Collect current resource usage metrics."""
        process = Process()
        return {
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'num_threads': process.num_threads(),
            'io_counters': process.io_counters()._asdict() if process.io_counters() else {}
        }

async def main():
    """Main entry point for test runner."""
    runner = TestRunner()
    # Example test suite
    test_suite = [
        {
            'id': 'test_001',
            'command': ['pytest', 'test_basic.py'],
            'priority': 'high'
        },
        {
            'id': 'test_002',
            'command': ['pytest', 'test_advanced.py'],
            'priority': 'normal'
        }
    ]
    
    await runner.schedule_tests(test_suite)

if __name__ == '__main__':
    asyncio.run(main())

