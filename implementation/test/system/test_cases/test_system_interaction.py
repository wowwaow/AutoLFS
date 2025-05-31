"""
Example system test case implementation.

This module provides an example implementation of a system test case
that tests producer-consumer interaction patterns.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from ..base import SystemTestCase
from ...core.exceptions import TestSetupError, TestExecutionError, TestCleanupError
from ..configs import SystemTestConfig, ResourceLimits

class ProducerConsumerTest(SystemTestCase):
    """
    Test case for producer-consumer interaction patterns.
    
    This test verifies the correct interaction between producer and consumer
    processes in a system environment, including resource allocation,
    IPC mechanisms, and cleanup.
    """
    
    def __init__(self, queue_size: int = 100, num_producers: int = 2, num_consumers: int = 2):
        """
        Initialize test case.
        
        Args:
            queue_size: Maximum size of the message queue
            num_producers: Number of producer processes
            num_consumers: Number of consumer processes
        """
        super().__init__()
        
        self.queue_size = queue_size
        self.num_producers = num_producers
        self.num_consumers = num_consumers
        
        # Runtime state
        self.message_queue: Optional[asyncio.Queue] = None
        self.producer_tasks: List[asyncio.Task] = []
        self.consumer_tasks: List[asyncio.Task] = []
        self.messages_produced = 0
        self.messages_consumed = 0
    
    async def setup_test(self) -> None:
        """Set up test environment."""
        try:
            # Configure test environment
            self.config = SystemTestConfig(
                base_dir=Path("/tmp/producer_consumer_test"),
                resources=ResourceLimits(
                    cpu_cores=max(self.num_producers + self.num_consumers, 2),
                    memory_mb=4096,
                    network_ports=list(range(8000, 8010))
                )
            )
            
            # Initialize message queue
            self.message_queue = asyncio.Queue(maxsize=self.queue_size)
            
            # Set up metrics collection
            await self.start_metrics()
            
            self.logger.info(
                "Test setup complete - Producers: %d, Consumers: %d, Queue Size: %d",
                self.num_producers,
                self.num_consumers,
                self.queue_size
            )
            
        except Exception as e:
            raise TestSetupError(f"Failed to set up test environment: {e}")
    
    async def producer(self, producer_id: int) -> None:
        """
        Producer coroutine.
        
        Args:
            producer_id: Unique producer identifier
        """
        try:
            for i in range(50):  # Produce 50 messages per producer
                message = f"Message {i} from Producer {producer_id}"
                await self.message_queue.put(message)
                self.messages_produced += 1
                
                # Simulate processing time
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error("Producer %d failed: %s", producer_id, e)
            raise
    
    async def consumer(self, consumer_id: int) -> None:
        """
        Consumer coroutine.
        
        Args:
            consumer_id: Unique consumer identifier
        """
        try:
            while True:
                # Get message from queue
                message = await self.message_queue.get()
                self.messages_consumed += 1
                
                # Simulate processing time
                await asyncio.sleep(0.2)
                
                # Mark task as done
                self.message_queue.task_done()
                
        except Exception as e:
            self.logger.error("Consumer %d failed: %s", consumer_id, e)
            raise
    
    async def run_test(self) -> None:
        """Execute the test scenario."""
        try:
            # Start producers
            for i in range(self.num_producers):
                task = asyncio.create_task(self.producer(i))
                self.producer_tasks.append(task)
            
            # Start consumers
            for i in range(self.num_consumers):
                task = asyncio.create_task(self.consumer(i))
                self.consumer_tasks.append(task)
            
            # Wait for producers to finish
            await asyncio.gather(*self.producer_tasks)
            
            # Wait for queue to be empty
            await self.message_queue.join()
            
            # Cancel consumer tasks
            for task in self.consumer_tasks:
                task.cancel()
            
            # Wait for consumers to finish
            await asyncio.gather(*self.consumer_tasks, return_exceptions=True)
            
            # Verify results
            if self.messages_produced != self.messages_consumed:
                raise TestExecutionError(
                    f"Message count mismatch - Produced: {self.messages_produced}, "
                    f"Consumed: {self.messages_consumed}"
                )
            
            self.logger.info(
                "Test completed successfully - Messages Processed: %d",
                self.messages_produced
            )
            
        except Exception as e:
            raise TestExecutionError(f"Test execution failed: {e}")
    
    async def cleanup_test(self) -> None:
        """Clean up test resources."""
        try:
            # Stop metrics collection
            await self.stop_metrics()
            
            # Cancel any remaining tasks
            for task in self.producer_tasks + self.consumer_tasks:
                if not task.done():
                    task.cancel()
            
            # Clear queues
            self.message_queue = None
            self.producer_tasks.clear()
            self.consumer_tasks.clear()
            
            self.logger.info("Test cleanup completed successfully")
            
        except Exception as e:
            raise TestCleanupError(f"Failed to clean up test resources: {e}")
    
    async def start_metrics(self) -> None:
        """Start metrics collection."""
        if not self.metrics:
            self.metrics = MetricsCollector(
                collection_interval_seconds=1.0,
                metrics_to_track=[
                    "cpu_percent",
                    "memory_percent",
                    "queue_size"
                ]
            )
        await self.metrics.start_collection()
    
    async def stop_metrics(self) -> None:
        """Stop metrics collection."""
        if self.metrics and self.metrics.is_collecting():
            await self.metrics.stop_collection()

"""
System interaction test case demonstrating producer-consumer pattern.

This test validates the interaction between multiple system components using
a producer-consumer scenario with shared resources and concurrent operations.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set

from ...core.exceptions import (
    ResourceAllocationError,
    ValidationError,
    CleanupError
)
from ...core.metrics import MetricsCollector
from ..base import SystemTestCase
from ..configs.base_config import SystemTestConfig

class SystemInteractionConfig(SystemTestConfig):
    """Configuration for system interaction test."""
    
    def __init__(
        self,
        data_dir: str,
        num_items: int = 100,
        item_size_bytes: int = 1024,
        producer_delay: float = 0.1,
        consumer_delay: float = 0.2,
        max_queue_size: int = 50
    ):
        """
        Initialize test configuration.
        
        Args:
            data_dir: Directory for shared data
            num_items: Number of items to produce/consume
            item_size_bytes: Size of each data item
            producer_delay: Delay between producing items
            consumer_delay: Delay between consuming items
            max_queue_size: Maximum items in queue
        """
        self.data_dir = data_dir
        self.num_items = num_items
        self.item_size_bytes = item_size_bytes
        self.producer_delay = producer_delay
        self.consumer_delay = consumer_delay
        self.max_queue_size = max_queue_size
        
        # Derived paths
        self.queue_dir = os.path.join(data_dir, "queue")
        self.processed_dir = os.path.join(data_dir, "processed")
        self.failed_dir = os.path.join(data_dir, "failed")

class ProducerConsumerTest(SystemTestCase):
    """
    Test case for producer-consumer interaction.
    
    Validates system behavior when multiple components interact through
    shared resources while under resource constraints.
    """
    
    def __init__(self):
        """Initialize test case."""
        super().__init__()
        self.metrics: Optional[MetricsCollector] = None
        self.producer_task: Optional[asyncio.Task] = None
        self.consumer_task: Optional[asyncio.Task] = None
        self.produced_items: Set[str] = set()
        self.consumed_items: Set[str] = set()
        self.failed_items: Set[str] = set()

    async def setup_test(self) -> None:
        """Set up test environment and resources."""
        # Create test configuration
        self.config = SystemInteractionConfig(
            data_dir=tempfile.mkdtemp(prefix="system_test_")
        )
        
        # Create required directories
        os.makedirs(self.config.queue_dir, mode=0o755)
        os.makedirs(self.config.processed_dir, mode=0o755)
        os.makedirs(self.config.failed_dir, mode=0o755)
        
        # Initialize metrics collection
        self.metrics = MetricsCollector(
            collection_interval_seconds=1.0,
            metrics_to_track=[
                "cpu_percent",
                "memory_percent",
                "disk_write_bytes",
                "disk_read_bytes"
            ]
        )
        await self.metrics.start_collection()
        
        # Update test state
        self.update_state(
            setup_complete=True,
            producer_running=False,
            consumer_running=False,
            items_produced=0,
            items_consumed=0,
            items_failed=0
        )
        
        self.logger.info(
            "Test setup complete. Using directories: %s", self.config.data_dir
        )

    async def run_test(self) -> None:
        """Execute the producer-consumer test scenario."""
        try:
            # Start producer and consumer tasks
            self.producer_task = asyncio.create_task(self._run_producer())
            self.consumer_task = asyncio.create_task(self._run_consumer())
            
            # Update state
            self.update_state(
                producer_running=True,
                consumer_running=True
            )
            
            # Wait for completion
            await asyncio.gather(self.producer_task, self.consumer_task)
            
            # Validate results
            await self._validate_results()
            
        except Exception as e:
            self.logger.error("Test execution failed: %s", e)
            raise

    async def cleanup_test(self) -> None:
        """Clean up test resources and restore system state."""
        try:
            # Stop metrics collection
            if self.metrics:
                await self.metrics.stop_collection()
            
            # Cancel any running tasks
            if self.producer_task and not self.producer_task.done():
                self.producer_task.cancel()
            if self.consumer_task and not self.consumer_task.done():
                self.consumer_task.cancel()
            
            # Clean up directories
            for dir_path in [
                self.config.queue_dir,
                self.config.processed_dir,
                self.config.failed_dir
            ]:
                if os.path.exists(dir_path):
                    for file in os.listdir(dir_path):
                        os.remove(os.path.join(dir_path, file))
                    os.rmdir(dir_path)
            
            if os.path.exists(self.config.data_dir):
                os.rmdir(self.config.data_dir)
            
            # Update state
            self.update_state(cleanup_complete=True)
            
        except Exception as e:
            raise CleanupError(f"Failed to clean up test resources: {e}")

    async def _run_producer(self) -> None:
        """Producer component that generates test data items."""
        try:
            for i in range(self.config.num_items):
                # Generate test data
                item_id = f"item_{i:05d}"
                data = {
                    "id": item_id,
                    "content": "x" * self.config.item_size_bytes,
                    "timestamp": str(asyncio.get_event_loop().time())
                }
                
                # Write to queue directory
                file_path = os.path.join(
                    self.config.queue_dir,
                    f"{item_id}.json"
                )
                with open(file_path, "w") as f:
                    json.dump(data, f)
                
                # Track produced item
                self.produced_items.add(item_id)
                self.update_state(items_produced=len(self.produced_items))
                
                # Simulate processing time
                await self.sleep(self.config.producer_delay)
                
        except Exception as e:
            self.logger.error("Producer failed: %s", e)
            raise

    async def _run_consumer(self) -> None:
        """Consumer component that processes queued items."""
        try:
            while (
                len(self.consumed_items) < self.config.num_items or
                os.listdir(self.config.queue_dir)
            ):
                # Check queue directory
                for file_name in os.listdir(self.config.queue_dir):
                    if not file_name.endswith(".json"):
                        continue
                    
                    # Read and process item
                    queue_path = os.path.join(
                        self.config.queue_dir,
                        file_name
                    )
                    try:
                        with open(queue_path, "r") as f:
                            data = json.load(f)
                        
                        # Simulate processing
                        await self.sleep(self.config.consumer_delay)
                        
                        # Move to processed directory
                        processed_path = os.path.join(
                            self.config.processed_dir,
                            file_name
                        )
                        os.rename(queue_path, processed_path)
                        
                        # Track consumed item
                        self.consumed_items.add(data["id"])
                        self.update_state(items_consumed=len(self.consumed_items))
                        
                    except Exception as e:
                        self.logger.error(
                            "Failed to process %s: %s", file_name, e
                        )
                        # Move to failed directory
                        failed_path = os.path.join(
                            self.config.failed_dir,
                            file_name
                        )
                        if os.path.exists(queue_path):
                            os.rename(queue_path, failed_path)
                        self.failed_items.add(file_name.split(".")[0])
                        self.update_state(items_failed=len(self.failed_items))
                
                # Short sleep to prevent busy loop
                await self.sleep(0.1)
                
        except Exception as e:
            self.logger.error("Consumer failed: %s", e)
            raise

    async def _validate_results(self) -> None:
        """Validate test results and resource usage."""
        # Get final metrics
        if not self.metrics:
            raise ValidationError("Metrics collector not initialized")
            
        metrics = await self.metrics.get_statistics()
        
        # Validate item counts
        if len(self.consumed_items) != self.config.num_items:
            raise ValidationError(
                f"Expected {self.config.num_items} consumed items, "
                f"got {len(self.consumed_items)}"
            )
            
        if self.failed_items:
            raise ValidationError(
                f"Had {len(self.failed_items)} failed items: "
                f"{sorted(self.failed_items)}"
            )
            
        # Validate metrics
        if metrics["cpu_percent"]["avg"] > 80.0:
            raise ValidationError(
                f"Average CPU usage too high: {metrics['cpu_percent']['avg']}%"
            )
            
        if metrics["memory_percent"]["max"] > 90.0:
            raise ValidationError(
                f"Peak memory usage too high: {metrics['memory_percent']['max']}%"
            )
            
        # Validate disk I/O
        expected_min_writes = (
            self.config.num_items * self.config.item_size_bytes
        )
        if metrics["disk_write_bytes"]["latest"] < expected_min_writes:
            raise ValidationError(
                f"Insufficient disk writes: "
                f"{metrics['disk_write_bytes']['latest']} < "
                f"{expected_min_writes}"
            )
            
        self.logger.info("All validations passed successfully")
        self.logger.info("Final metrics: %s", metrics)

