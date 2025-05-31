#!/usr/bin/env python3

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import aiohttp
import json
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class AIService:
    """Represents an AI service endpoint"""
    service_id: str
    endpoint: str
    capabilities: Set[str]
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0
    
    def is_available(self) -> bool:
        """Check if service is available for requests"""
        return self.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]

class AIRequestPriority(Enum):
    HIGH = 0
    MEDIUM = 1
    LOW = 2

@dataclass
class AIRequest:
    """Represents a request to an AI service"""
    request_id: str
    content: dict
    priority: AIRequestPriority
    timestamp: datetime
    service_capability: str
    retry_count: int = 0
    max_retries: int = 3

class AIServiceManager:
    """Manages AI service discovery, health monitoring, and request handling"""
    
    def __init__(self):
        self.services: Dict[str, AIService] = {}
        self.request_queue: Dict[AIRequestPriority, deque] = {
            AIRequestPriority.HIGH: deque(),
            AIRequestPriority.MEDIUM: deque(),
            AIRequestPriority.LOW: deque()
        }
        self.health_check_interval = timedelta(seconds=30)
        self.service_timeout = timedelta(seconds=10)
        self.degraded_threshold = 3
        self.unhealthy_threshold = 5
        
        # Initialize monitoring
        self.monitoring_task = None
        self.is_running = False

    async def start(self):
        """Start the service manager"""
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitor_services())
        logger.info("AI Service Manager started")

    async def stop(self):
        """Stop the service manager"""
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("AI Service Manager stopped")

    async def register_service(self, service: AIService):
        """Register a new AI service"""
        self.services[service.service_id] = service
        await self._check_service_health(service)
        logger.info(f"Registered new service: {service.service_id}")

    async def unregister_service(self, service_id: str):
        """Unregister an AI service"""
        if service_id in self.services:
            del self.services[service_id]
            logger.info(f"Unregistered service: {service_id}")

    async def submit_request(self, request: AIRequest) -> str:
        """Submit a new AI request"""
        self.request_queue[request.priority].append(request)
        logger.info(f"Queued request {request.request_id} with priority {request.priority}")
        return request.request_id

    async def _process_request_queue(self):
        """Process requests in the queue based on priority"""
        for priority in AIRequestPriority:
            queue = self.request_queue[priority]
            while queue:
                request = queue[0]  # Peek at next request
                service = self._select_service(request.service_capability)
                
                if not service:
                    # No available service, leave request in queue
                    break
                
                # Remove request from queue
                queue.popleft()
                
                try:
                    await self._process_request(request, service)
                except Exception as e:
                    logger.error(f"Error processing request {request.request_id}: {e}")
                    if request.retry_count < request.max_retries:
                        request.retry_count += 1
                        queue.append(request)  # Requeue for retry

    async def _process_request(self, request: AIRequest, service: AIService):
        """Process a single AI request"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    service.endpoint,
                    json=request.content,
                    timeout=self.service_timeout.total_seconds()
                ) as response:
                    if response.status == 200:
                        service.success_count += 1
                        service.failure_count = 0
                        return await response.json()
                    else:
                        raise Exception(f"Service returned status {response.status}")
        except Exception as e:
            service.failure_count += 1
            service.success_count = 0
            await self._update_service_status(service)
            raise

    def _select_service(self, capability: str) -> Optional[AIService]:
        """Select best available service with required capability"""
        available_services = [
            s for s in self.services.values()
            if capability in s.capabilities and s.is_available()
        ]
        
        if not available_services:
            return None
            
        # Simple round-robin selection for now
        # TODO: Implement more sophisticated load balancing
        return min(available_services, key=lambda s: s.success_count)

    async def _monitor_services(self):
        """Monitor health of all registered services"""
        while self.is_running:
            for service in self.services.values():
                if datetime.now() - (service.last_health_check or datetime.min) >= self.health_check_interval:
                    await self._check_service_health(service)
            await asyncio.sleep(self.health_check_interval.total_seconds())

    async def _check_service_health(self, service: AIService):
        """Check health of a single service"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{service.endpoint}/health",
                    timeout=self.service_timeout.total_seconds()
                ) as response:
                    service.last_health_check = datetime.now()
                    if response.status == 200:
                        await self._update_service_status(service)
                    else:
                        service.failure_count += 1
                        await self._update_service_status(service)
        except Exception as e:
            logger.error(f"Health check failed for service {service.service_id}: {e}")
            service.failure_count += 1
            await self._update_service_status(service)

    async def _update_service_status(self, service: AIService):
        """Update service status based on health checks"""
        if service.failure_count >= self.unhealthy_threshold:
            service.status = ServiceStatus.UNHEALTHY
        elif service.failure_count >= self.degraded_threshold:
            service.status = ServiceStatus.DEGRADED
        elif service.failure_count == 0:
            service.status = ServiceStatus.HEALTHY
        
        logger.info(f"Service {service.service_id} status updated to {service.status}")

    async def get_service_stats(self) -> Dict:
        """Get statistics about registered services"""
        return {
            service_id: {
                "status": service.status.value,
                "success_count": service.success_count,
                "failure_count": service.failure_count,
                "last_health_check": service.last_health_check.isoformat() if service.last_health_check else None
            }
            for service_id, service in self.services.items()
        }

# Example usage
async def main():
    # Create and start service manager
    manager = AIServiceManager()
    await manager.start()
    
    # Register example service
    service = AIService(
        service_id="ai-service-1",
        endpoint="http://localhost:8000/ai",
        capabilities={"text-generation", "code-review"}
    )
    await manager.register_service(service)
    
    # Submit example request
    request = AIRequest(
        request_id="req-1",
        content={"prompt": "Review this code"},
        priority=AIRequestPriority.HIGH,
        timestamp=datetime.now(),
        service_capability="code-review"
    )
    await manager.submit_request(request)
    
    # Run for a while
    await asyncio.sleep(60)
    
    # Stop service manager
    await manager.stop()

if __name__ == "__main__":
    asyncio.run(main())

