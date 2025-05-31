"""
Example system test demonstrating framework capabilities.

This test simulates a data processing pipeline that:
1. Allocates disk space for input/output data
2. Generates test data with configurable size
3. Processes data through multiple stages
4. Tracks resource usage and performance metrics
5. Cleans up resources properly
"""

import asyncio
import os
import random
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from ...framework.test_runners.performance_runner import PerformanceRunner, PerformanceThresholds
from ...core.base_test import SystemTest
from ...core.exceptions import (
    ResourceAllocationError,
    TestSetupError,
    CleanupError
)

# Configure logging
logger = logging.getLogger(__name__)

class DataProcessingTest(SystemTest):
    """
    Example system test that demonstrates disk space allocation,
    resource tracking, and proper test lifecycle management.
    """
    
    def __init__(
        self,
        input_size_mb: int = 100,
        chunk_size_kb: int = 64,
        processing_delay_ms: int = 10,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize test parameters.
        
        Args:
            input_size_mb: Size of input test data in MB
            chunk_size_kb: Processing chunk size in KB
            processing_delay_ms: Simulated processing delay per chunk
            output_dir: Custom output directory (uses temp dir if None)
        """
        super().__init__()
        
        # Validate input parameters
        if input_size_mb <= 0:
            raise ValueError("input_size_mb must be positive")
        if chunk_size_kb <= 0:
            raise ValueError("chunk_size_kb must be positive")
        if processing_delay_ms < 0:
            raise ValueError("processing_delay_ms cannot be negative")
            
        self.input_size_mb = input_size_mb
        self.chunk_size_kb = chunk_size_kb
        self.processing_delay_ms = processing_delay_ms
        
        # Default to system temporary directory with unique test ID
        if output_dir is None:
            test_id = int(time.time() * 1000)
            output_dir = Path(f"/tmp/test_data_{test_id}")
        self.output_dir = output_dir
        
        # Runtime properties
        self.input_file: Optional[Path] = None
        self.stage1_file: Optional[Path] = None
        self.stage2_file: Optional[Path] = None
        self.output_file: Optional[Path] = None
        
        # Performance metrics
        self.chunks_processed = 0
        self.bytes_processed = 0
        self.processing_time = 0.0
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def register_custom_metrics(self, collector) -> None:
        """Register test-specific metrics with the collector."""
        await collector.register_metric(
            "throughput_mbps",
            "Data processing throughput in MB/s",
            unit="MB/s",
            type="gauge"
        )
        await collector.register_metric(
            "chunks_per_second",
            "Number of chunks processed per second",
            unit="chunks/s",
            type="gauge"
        )
        await collector.register_metric(
            "disk_usage_mb",
            "Total disk space used by test files",
            unit="MB",
            type="gauge"
        )
    
    async def setup(self) -> None:
        """Set up test environment and allocate resources."""
        try:
            # Create test directories with proper permissions
            os.makedirs(self.output_dir, mode=0o755, exist_ok=True)
            
            # Allocate disk space for test files
            total_size = self.input_size_mb * 1024 * 1024  # Convert to bytes
            self.input_file = self.output_dir / "input.dat"
            self.stage1_file = self.output_dir / "stage1.dat"
            self.stage2_file = self.output_dir / "stage2.dat"
            self.output_file = self.output_dir / "output.dat"
            
            # Generate input test data
            logger.info(f"Generating {self.input_size_mb}MB of test data...")
            await self._generate_test_data(self.input_file, total_size)
            
            # Verify disk space allocation
            if not await self._verify_disk_space():
                raise ResourceAllocationError(
                    f"Failed to allocate {self.input_size_mb}MB for test data"
                )
            
            # Set proper file permissions
            for file in [self.input_file, self.stage1_file, self.stage2_file, self.output_file]:
                if file and file.exists():
                    os.chmod(file, 0o644)
            
        except Exception as e:
            await self.cleanup()  # Clean up on setup failure
            raise TestSetupError(f"Setup failed: {str(e)}") from e
    
    async def run(self) -> None:
        """Execute the test scenario."""
        start_time = time.time()
        
        try:
            # Process data through pipeline stages
            await self._process_stage1()
            await self._process_stage2()
            await self._verify_output()
            
            # Record final metrics
            total_time = time.time() - start_time
            throughput = (self.bytes_processed / 1024 / 1024) / total_time
            chunks_per_sec = self.chunks_processed / total_time
            
            logger.info("Test execution completed successfully:")
            logger.info(f"- Total time: {total_time:.2f}s")
            logger.info(f"- Throughput: {throughput:.2f} MB/s")
            logger.info(f"- Chunks/sec: {chunks_per_sec:.2f}")
            
        except Exception as e:
            logger.error(f"Test execution failed: {str(e)}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up test resources."""
        try:
            # Shut down thread pool
            self.executor.shutdown(wait=True)
            
            # Remove test files with proper error handling
            for file in [
                self.input_file,
                self.stage1_file,
                self.stage2_file,
                self.output_file
            ]:
                if file and file.exists():
                    try:
                        file.unlink()
                    except OSError as e:
                        logger.warning(f"Failed to remove file {file}: {e}")
            
            # Remove test directory if empty
            try:
                if self.output_dir.exists():
                    if not any(self.output_dir.iterdir()):
                        self.output_dir.rmdir()
                    else:
                        logger.warning(f"Directory not empty: {self.output_dir}")
            except OSError as e:
                logger.warning(f"Failed to remove directory {self.output_dir}: {e}")
                
        except Exception as e:
            raise CleanupError(f"Cleanup failed: {str(e)}") from e
    
    async def _generate_test_data(self, file_path: Path, size_bytes: int) -> None:
        """Generate test data file of specified size."""
        chunk_size = self.chunk_size_kb * 1024
        remaining = size_bytes
        
        async def write_chunk(chunk_size: int) -> int:
            chunk = random.randbytes(chunk_size)
            with open(file_path, "ab") as f:
                f.write(chunk)
            return len(chunk)
        
        # Create empty file with proper permissions
        with open(file_path, "wb") as _:
            pass
        os.chmod(file_path, 0o644)
        
        while remaining > 0:
            write_size = min(chunk_size, remaining)
            bytes_written = await write_chunk(write_size)
            remaining -= bytes_written
            
            # Allow other tasks to run periodically
            if remaining % (10 * chunk_size) == 0:
                await asyncio.sleep(0)
    
    async def _verify_disk_space(self) -> bool:
        """Verify that required disk space was allocated."""
        if not self.input_file or not self.input_file.exists():
            return False
        
        try:
            # Check actual file size
            actual_size = os.path.getsize(self.input_file)
            expected_size = self.input_size_mb * 1024 * 1024
            
            # Allow 1KB tolerance
            return abs(actual_size - expected_size) < 1024
            
        except OSError as e:
            logger.error(f"Failed to verify disk space: {e}")
            return False
    
    async def _process_stage1(self) -> None:
        """First stage of data processing pipeline."""
        logger.info("Starting processing stage 1...")
        start_time = time.time()
        
        try:
            with open(self.input_file, "rb") as input_file, \
                 open(self.stage1_file, "wb") as output_file:
                
                while True:
                    chunk = input_file.read(self.chunk_size_kb * 1024)
                    if not chunk:
                        break
                    
                    # Simulate CPU-intensive processing
                    processed = await self.executor.submit(
                        lambda: bytes([b ^ 0xFF for b in chunk])
                    )
                    output_file.write(processed)
                    
                    # Update metrics
                    self.chunks_processed += 1
                    self.bytes_processed += len(chunk)
                    
                    # Simulate processing delay
                    await asyncio.sleep(self.processing_delay_ms / 1000)
            
            # Set proper permissions on output file
            os.chmod(self.stage1_file, 0o644)
            
        finally:
            self.processing_time += time.time() - start_time
    
    async def _process_stage2(self) -> None:
        """Second stage of data processing pipeline."""
        logger.info("Starting processing stage 2...")
        start_time = time.time()
        
        try:
            with open(self.stage1_file, "rb") as input_file, \
                 open(self.stage2_file, "wb") as output_file:
                
                while True:
                    chunk = input_file.read(self.chunk_size_kb * 1024)
                    if not chunk:
                        break
                    
                    # Simulate different CPU-intensive processing
                    processed = await self.executor.submit(
                        lambda: bytes(sorted(chunk))
                    )
                    output_file.write(processed)
                    
                    # Update metrics
                    self.chunks_processed += 1
                    self.bytes_processed += len(chunk)
                    
                    # Simulate processing delay
                    await asyncio.sleep(self.processing_delay_ms / 1000)
            
            # Set proper permissions on output file
            os.chmod(self.stage2_file, 0o644)
            
        finally:
            self.processing_time += time.time() - start_time
            
            # Calculate and log performance metrics
            throughput = (self.bytes_processed / 1024 / 1024) / self.processing_time
            chunks_per_sec = self.chunks_processed / self.processing_time
            
            logger.info("Processing complete:")
            logger.info(f"- Throughput: {throughput:.2f} MB/s")
            logger.info(f"- Chunks/sec: {chunks_per_sec:.2f}")
    
    async def _verify_output(self) -> None:
        """Verify processing results."""
        if not self.stage2_file.exists():
            raise ValueError("Processing output file not found")
        
        try:
            # Verify file size hasn't changed
            input_size = os.path.getsize(self.input_file)
            output_size = os.path.getsize(self.stage2_file)
            
            if abs(input_size - output_size) > 1024:  # Allow 1KB tolerance
                raise ValueError(
                    f"Output size mismatch: {output_size} != {input_size} bytes"
                )
                
        except OSError as e:
            raise ValueError(f"Failed to verify output: {e}")

# Example usage with proper error handling
async def run_example_test():
    """Run example test with performance monitoring."""
    test = None
    runner = None
    
    try:
        # Configure test parameters
        test = DataProcessingTest(
            input_size_mb=100,  # 100MB test data
            chunk_size_kb=64,   # 64KB chunks
            processing_delay_ms=10  # 10ms processing delay
        )
        
        # Configure performance thresholds
        thresholds = PerformanceThresholds(
            max_cpu_percent=90.0,
            max_memory_percent=80.0,
            max_execution_time=300.0,  # 5 minutes
            custom_thresholds={
                "throughput_mbps": 50.0,  # Minimum 50 MB/s
                "chunks_per_second": 100.0  # Minimum 100 chunks/s
            }
        )
        
        # Create performance runner with proper directory permissions
        output_dir = Path("/tmp/test_results")
        os.makedirs(output_dir, mode=0o755, exist_ok=True)
        
        runner = PerformanceRunner(
            output_dir=output_dir,
            thresholds=thresholds,
            collection_interval=0.1  # 100ms collection interval
        )
        
        # Execute test with performance monitoring
        result = await runner.execute_test(test)
        
        # Log results
        if result.passed:
            print("Test passed successfully!")
        else:
            print("Test failed:")
            for failure in result.failures:
                print(f"- {failure}")
        
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"- {warning}")
        
        # Ensure performance report has proper permissions
        report_path = result.artifacts['performance_report']
        if os.path.exists(report_path):
            os.chmod(report_path, 0o644)
        
        print(f"\nPerformance report: {report_path}")
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        raise
        
    finally:
        # Ensure cleanup runs even if test fails
        if test:
            await test.cleanup()
        if runner:
            await runner.cleanup()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    asyncio.run(run_example_test())

"""
Example system test demonstrating framework capabilities.

Tests disk space allocation and cleanup while showcasing:
1. SystemTestCase usage
2. Configuration management  
3. Resource handling
4. Environment setup/teardown
5. State validation
6. Error handling
7. Logging
8. Metrics tracking
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Optional

from ..base import SystemTestCase
from ..configs.base_config import SystemTestConfig 
from ....core.metrics import MetricsCollector
from ....core.exceptions import (
    ResourceAllocationError,
    ValidationError,
    CleanupError
)

logger = logging.getLogger(__name__)

class TestDiskSpaceAllocation(SystemTestCase):
    """
    Example system test that verifies disk space allocation and cleanup.
    
    Demonstrates proper usage of the testing framework including:
    - Resource management
    - Configuration handling
    - State validation
    - Error handling
    - Metrics tracking
    """

    async def setup_test(self) -> None:
        """Configure test environment and allocate resources."""
        logger.info("Setting up disk space allocation test")
        
        # Load test configuration
        self.config = SystemTestConfig(
            resource_requirements={
                "disk_space_gb": 5,  # Request 5GB for test
                "memory_mb": 512,    # Request 512MB RAM
                "cpu_cores": 1       # Request 1 CPU core
            },
            timeout_seconds=300,     # 5 minute timeout
            cleanup_policy="always"  # Always run cleanup
        )

        # Initialize metrics collector
        self.metrics = MetricsCollector(
            collection_interval_seconds=1,
            metrics_to_track=[
                "disk_usage_bytes",
                "disk_free_bytes",
                "disk_write_speed_bps",
                "disk_read_speed_bps"
            ]
        )

        # Create test directory with proper permissions
        self.test_dir = Path("/mnt/host/WARP_CURRENT/test_workspace/disk_test")
        os.makedirs(self.test_dir, exist_ok=True)
        os.chmod(self.test_dir, 0o755)

        # Verify initial state
        try:
            await self._verify_initial_state()
        except ValidationError as e:
            logger.error(f"Initial state validation failed: {e}")
            await self.cleanup_test()
            raise

        logger.info("Test setup completed successfully")

    async def _verify_initial_state(self) -> None:
        """Verify system is in proper initial state."""
        # Check available disk space
        free_space = shutil.disk_usage(self.test_dir).free
        required_space = self.config.resource_requirements["disk_space_gb"] * 1024**3

        if free_space < required_space:
            raise ValidationError(
                f"Insufficient disk space. Need {required_space} bytes, "
                f"have {free_space} bytes"
            )

        # Verify directory is empty
        if any(self.test_dir.iterdir()):
            raise ValidationError(f"Test directory {self.test_dir} is not empty")

        logger.info("Initial state validation passed")

    async def run_test(self) -> None:
        """Execute disk space allocation test."""
        logger.info("Starting disk space allocation test")

        try:
            # Start metrics collection
            await self.metrics.start_collection()

            # Test file creation and space allocation
            await self._test_file_operations()

            # Verify metrics are within expected ranges
            await self._verify_metrics()

            logger.info("Disk space allocation test completed successfully")

        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            raise
        finally:
            # Always stop metrics collection
            await self.metrics.stop_collection()

    async def _test_file_operations(self) -> None:
        """Test file creation and space allocation."""
        file_sizes = [100, 500, 1000]  # MB
        files: Dict[Path, int] = {}

        # Create test files
        for size in file_sizes:
            size_bytes = size * 1024 * 1024
            file_path = self.test_dir / f"test_file_{size}mb"
            
            logger.info(f"Creating {size}MB test file at {file_path}")
            
            try:
                # Create file with specified size
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(size_bytes))
                files[file_path] = size_bytes
            except OSError as e:
                logger.error(f"Failed to create test file: {e}")
                raise ResourceAllocationError(f"File creation failed: {e}")

            # Verify file size
            actual_size = file_path.stat().st_size
            if actual_size != size_bytes:
                raise ValidationError(
                    f"File size mismatch. Expected {size_bytes}, got {actual_size}"
                )

        # Read files to generate metrics
        for file_path in files:
            logger.debug(f"Reading test file {file_path}")
            with open(file_path, 'rb') as f:
                while f.read(1024 * 1024):  # Read 1MB at a time
                    await asyncio.sleep(0.1)  # Prevent CPU overload

    async def _verify_metrics(self) -> None:
        """Verify collected metrics meet requirements."""
        metrics_data = await self.metrics.get_metrics()

        # Verify disk usage increased as expected
        initial_usage = metrics_data["disk_usage_bytes"][0]
        final_usage = metrics_data["disk_usage_bytes"][-1]
        expected_increase = sum([
            100 * 1024 * 1024,
            500 * 1024 * 1024,
            1000 * 1024 * 1024
        ])

        usage_diff = final_usage - initial_usage
        if abs(usage_diff - expected_increase) > 1024 * 1024:  # 1MB tolerance
            raise ValidationError(
                f"Unexpected disk usage change. Expected ~{expected_increase} bytes, "
                f"got {usage_diff} bytes"
            )

        # Verify write speed meets minimum requirement (10MB/s)
        min_write_speed = 10 * 1024 * 1024  # 10MB/s
        avg_write_speed = sum(metrics_data["disk_write_speed_bps"]) / len(
            metrics_data["disk_write_speed_bps"]
        )

        if avg_write_speed < min_write_speed:
            raise ValidationError(
                f"Disk write speed below requirement. Need {min_write_speed} B/s, "
                f"got {avg_write_speed} B/s"
            )

        logger.info("All metrics validated successfully")

    async def cleanup_test(self) -> None:
        """Clean up test environment and free resources."""
        logger.info("Starting test cleanup")

        try:
            # Remove test files
            if self.test_dir.exists():
                shutil.rmtree(self.test_dir)

            # Verify cleanup
            if self.test_dir.exists():
                raise CleanupError(f"Failed to remove test directory {self.test_dir}")

            # Stop metrics collection if still running
            if self.metrics.is_collecting():
                await self.metrics.stop_collection()

            logger.info("Test cleanup completed successfully")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise CleanupError(f"Test cleanup failed: {e}")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    asyncio.run(TestDiskSpaceAllocation().run())

