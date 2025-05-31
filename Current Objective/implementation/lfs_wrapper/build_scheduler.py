"""
Build scheduling and execution coordination module.

Manages build execution order, parallel builds, resource allocation,
and build process optimization.

Dependencies:
    - networkx>=2.6
    - psutil>=5.8
"""

import logging
import multiprocessing
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from queue import PriorityQueue
from threading import Lock, Thread
from typing import Dict, List, Optional, Set, Tuple

import psutil

from .build_manager import BuildManager, BuildPhase, BuildStatus
from .dependency_resolver import DependencyResolver
from .exceptions import SchedulerError


class BuildPriority(Enum):
    """Build priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(order=True)
class BuildTask:
    """Represents a scheduled build task."""
    priority: BuildPriority
    package: str = field(compare=False)
    phase: BuildPhase = field(compare=False)
    dependencies: Set[str] = field(default_factory=set, compare=False)
    estimated_duration: float = field(default=3600.0, compare=False)
    resource_requirements: Dict = field(default_factory=dict, compare=False)
    start_time: Optional[float] = field(default=None, compare=False)
    completion_time: Optional[float] = field(default=None, compare=False)


class ResourceAllocation:
    """Manages system resource allocation for builds."""
    
    def __init__(self, config: Dict):
        """Initialize resource allocation with config."""
        self.config = config
        self.max_cpu = multiprocessing.cpu_count()
        self.max_memory = psutil.virtual_memory().total
        self.allocated_cpu = 0
        self.allocated_memory = 0
        self.lock = Lock()

    def can_allocate(self, requirements: Dict) -> bool:
        """Check if resources can be allocated."""
        with self.lock:
            needed_cpu = requirements.get('cpu_count', 1)
            needed_memory = requirements.get('memory_mb', 1024) * 1024 * 1024
            
            return (
                self.allocated_cpu + needed_cpu <= self.max_cpu and
                self.allocated_memory + needed_memory <= self.max_memory
            )

    def allocate(self, requirements: Dict) -> bool:
        """Attempt to allocate resources."""
        with self.lock:
            if self.can_allocate(requirements):
                self.allocated_cpu += requirements.get('cpu_count', 1)
                self.allocated_memory += requirements.get('memory_mb', 1024) * 1024 * 1024
                return True
            return False

    def release(self, requirements: Dict) -> None:
        """Release allocated resources."""
        with self.lock:
            self.allocated_cpu -= requirements.get('cpu_count', 1)
            self.allocated_memory -= requirements.get('memory_mb', 1024) * 1024 * 1024


class BuildScheduler:
    """
    Manages build task scheduling and execution.

    Coordinates build task execution, handles resource allocation,
    and optimizes build process execution.

    Attributes:
        build_manager (BuildManager): Build process manager
        dependency_resolver (DependencyResolver): Dependency resolution
        resource_manager (ResourceAllocation): Resource allocation
        build_queue (PriorityQueue): Priority-based build queue
        active_builds (Dict): Currently executing builds
        completed_builds (Set): Completed build packages
    """

    def __init__(
        self,
        build_manager: BuildManager,
        dependency_resolver: DependencyResolver,
        config: Dict
    ):
        """Initialize the build scheduler."""
        self.build_manager = build_manager
        self.dependency_resolver = dependency_resolver
        self.resource_manager = ResourceAllocation(config)
        self.build_queue = PriorityQueue()
        self.active_builds: Dict[str, BuildTask] = {}
        self.completed_builds: Set[str] = set()
        self.logger = logging.getLogger(__name__)
        self.scheduler_thread: Optional[Thread] = None
        self.is_running = False
        self.lock = Lock()

    def schedule_build(
        self,
        package: str,
        priority: BuildPriority = BuildPriority.NORMAL,
        resource_requirements: Optional[Dict] = None
    ) -> None:
        """
        Schedule a package for building.

        Args:
            package: Package name to build
            priority: Build priority level
            resource_requirements: Resource requirements dict
        
        Raises:
            SchedulerError: If scheduling fails
        """
        try:
            # Get dependencies and create build task
            deps = set(self.dependency_resolver.resolve_dependencies(package))
            deps.remove(package)  # Remove self from dependencies
            
            task = BuildTask(
                priority=priority,
                package=package,
                phase=BuildPhase.SYSTEM,  # Default phase
                dependencies=deps,
                resource_requirements=resource_requirements or {}
            )
            
            self.build_queue.put(task)
            self.logger.info(f"Scheduled build for {package} with priority {priority}")
            
        except Exception as e:
            raise SchedulerError(f"Failed to schedule build for {package}: {e}")

    def start_scheduler(self) -> None:
        """Start the build scheduler thread."""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            return

        self.is_running = True
        self.scheduler_thread = Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()

    def stop_scheduler(self) -> None:
        """Stop the build scheduler thread."""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()

    def _scheduler_loop(self) -> None:
        """Main scheduler loop processing build queue."""
        while self.is_running:
            try:
                self._process_queue()
                time.sleep(1)  # Prevent tight loop
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")

    def _process_queue(self) -> None:
        """Process the build queue and start ready builds."""
        if self.build_queue.empty():
            return

        with self.lock:
            # Try to get a task without removing it
            try:
                task = self.build_queue.queue[0]
            except IndexError:
                return

            # Check if dependencies are met
            if not task.dependencies.issubset(self.completed_builds):
                return

            # Check resource availability
            if not self.resource_manager.can_allocate(task.resource_requirements):
                return

            # Remove task from queue and start build
            task = self.build_queue.get()
            self._start_build(task)

    def _start_build(self, task: BuildTask) -> None:
        """Start a build task execution."""
        try:
            # Allocate resources
            if not self.resource_manager.allocate(task.resource_requirements):
                self.build_queue.put(task)  # Put back in queue
                return

            task.start_time = time.time()
            self.active_builds[task.package] = task
            
            # Start build in separate thread
            build_thread = Thread(
                target=self._execute_build,
                args=(task,)
            )
            build_thread.daemon = True
            build_thread.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start build for {task.package}: {e}")
            self.resource_manager.release(task.resource_requirements)

    def _execute_build(self, task: BuildTask) -> None:
        """Execute a build task."""
        try:
            self.logger.info(f"Starting build of {task.package}")
            self.build_manager.execute_phase(task.phase)
            
            task.completion_time = time.time()
            self.completed_builds.add(task.package)
            
        except Exception as e:
            self.logger.error(f"Build failed for {task.package}: {e}")
        finally:
            self.resource_manager.release(task.resource_requirements)
            with self.lock:
                self.active_builds.pop(task.package, None)

    def get_build_status(self) -> Dict:
        """Get current build process status."""
        with self.lock:
            return {
                'queued_builds': self.build_queue.qsize(),
                'active_builds': [
                    {
                        'package': pkg,
                        'running_time': time.time() - task.start_time
                        if task.start_time else 0
                    }
                    for pkg, task in self.active_builds.items()
                ],
                'completed_builds': len(self.completed_builds),
                'resource_usage': {
                    'cpu': self.resource_manager.allocated_cpu,
                    'memory': self.resource_manager.allocated_memory
                }
            }

    def estimate_completion_time(self, package: str) -> Optional[float]:
        """Estimate completion time for a package build."""
        with self.lock:
            # If already complete
            if package in self.completed_builds:
                return 0.0
            
            # If currently building
            if package in self.active_builds:
                task = self.active_builds[package]
                elapsed = time.time() - task.start_time
                return max(0, task.estimated_duration - elapsed)
            
            # If in queue, estimate based on dependencies
            for task in self.build_queue.queue:
                if task.package == package:
                    # Sum up estimates for incomplete dependencies
                    total_time = task.estimated_duration
                    for dep in task.dependencies:
                        if dep not in self.completed_builds:
                            total_time += self.estimate_completion_time(dep) or 0
                    return total_time
            
            return None

