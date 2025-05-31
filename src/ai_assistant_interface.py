#!/usr/bin/env python3

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
import json
from abc import ABC, abstractmethod

from ai_service_manager import AIServiceManager, AIRequest, AIRequestPriority
from validation_engine import ValidationEngine, ValidationResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelType(Enum):
    """Types of AI models available"""
    FAST = "fast"           # Quick, less accurate responses
    BALANCED = "balanced"   # Good balance of speed and accuracy
    ACCURATE = "accurate"   # Highest accuracy, slower responses
    SPECIALIZED = "specialized"  # Domain-specific models

class AssistantCapability(Enum):
    """Capabilities provided by the AI assistant"""
    CONTENT_GENERATION = "content_generation"
    CODE_REVIEW = "code_review"
    TECHNICAL_VALIDATION = "technical_validation"
    DOCUMENTATION_REVIEW = "documentation_review"
    QUALITY_ASSESSMENT = "quality_assessment"
    IMPROVEMENT_SUGGESTIONS = "improvement_suggestions"

@dataclass
class PromptTemplate:
    """Template for generating AI prompts"""
    template_id: str
    template: str
    parameters: Set[str]
    capability: AssistantCapability
    model_type: ModelType
    max_tokens: int
    temperature: float = 0.7
    
    def format(self, **kwargs) -> str:
        """Format the template with provided parameters"""
        missing_params = self.parameters - set(kwargs.keys())
        if missing_params:
            raise ValueError(f"Missing required parameters: {missing_params}")
        return self.template.format(**kwargs)

@dataclass
class AssistantContext:
    """Context for AI assistant interactions"""
    context_id: str
    session_id: str
    user_id: str
    timestamp: datetime
    conversation_history: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    capabilities: Set[AssistantCapability] = field(default_factory=set)

@dataclass
class AssistantResponse:
    """Response from AI assistant"""
    response_id: str
    context_id: str
    content: Any
    model_used: ModelType
    confidence_score: float
    processing_time: float
    metadata: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

class AssistantMetrics:
    """Metrics collection for AI assistant"""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_processing_time = 0.0
        self.response_times: List[float] = []
        self.model_usage: Dict[ModelType, int] = {model: 0 for model in ModelType}
        self.capability_usage: Dict[AssistantCapability, int] = {cap: 0 for cap in AssistantCapability}
        self.error_types: Dict[str, int] = {}
        
    def add_request(self, model_type: ModelType, capability: AssistantCapability, processing_time: float):
        """Record metrics for a successful request"""
        self.request_count += 1
        self.total_processing_time += processing_time
        self.response_times.append(processing_time)
        self.model_usage[model_type] += 1
        self.capability_usage[capability] += 1
    
    def add_error(self, error_type: str):
        """Record an error occurrence"""
        self.error_count += 1
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics"""
        return {
            'total_requests': self.request_count,
            'error_rate': self.error_count / max(1, self.request_count),
            'avg_processing_time': self.total_processing_time / max(1, self.request_count),
            'model_usage': self.model_usage,
            'capability_usage': {cap.value: count for cap, count in self.capability_usage.items()},
            'error_distribution': self.error_types
        }

class PromptManager:
    """Manages prompt templates and generation"""
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default prompt templates"""
        self.add_template(PromptTemplate(
            template_id="doc-review",
            template="Review the following documentation:\n\n{content}\n\nFocus on:\n{aspects}\n\nProvide specific improvements for:",
            parameters={"content", "aspects"},
            capability=AssistantCapability.DOCUMENTATION_REVIEW,
            model_type=ModelType.ACCURATE,
            max_tokens=1000
        ))
        
        self.add_template(PromptTemplate(
            template_id="code-review",
            template="Review this code:\n\n{code}\n\nCheck for:\n{check_aspects}\n\nProvide feedback on:",
            parameters={"code", "check_aspects"},
            capability=AssistantCapability.CODE_REVIEW,
            model_type=ModelType.SPECIALIZED,
            max_tokens=800
        ))
        
        self.add_template(PromptTemplate(
            template_id="quality-check",
            template="Assess the quality of:\n\n{content}\n\nEvaluate:\n{criteria}\n\nProvide a detailed analysis of:",
            parameters={"content", "criteria"},
            capability=AssistantCapability.QUALITY_ASSESSMENT,
            model_type=ModelType.BALANCED,
            max_tokens=600
        ))
    
    def add_template(self, template: PromptTemplate):
        """Add a new prompt template"""
        self.templates[template.template_id] = template
    
    def get_template(self, template_id: str) -> PromptTemplate:
        """Get a prompt template by ID"""
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")
        return self.templates[template_id]
    
    def generate_prompt(self, template_id: str, **kwargs) -> str:
        """Generate a prompt using a template"""
        template = self.get_template(template_id)
        return template.format(**kwargs)

class ModelSelector:
    """Selects appropriate AI models based on requirements"""
    
    def __init__(self):
        self.model_configs: Dict[ModelType, Dict] = {
            ModelType.FAST: {
                'max_tokens': 300,
                'temperature': 0.5,
                'timeout': 5
            },
            ModelType.BALANCED: {
                'max_tokens': 800,
                'temperature': 0.7,
                'timeout': 10
            },
            ModelType.ACCURATE: {
                'max_tokens': 2000,
                'temperature': 0.9,
                'timeout': 20
            },
            ModelType.SPECIALIZED: {
                'max_tokens': 1500,
                'temperature': 0.8,
                'timeout': 15
            }
        }
    
    def select_model(self, capability: AssistantCapability, context: AssistantContext) -> ModelType:
        """Select the most appropriate model based on requirements"""
        if capability == AssistantCapability.CODE_REVIEW:
            return ModelType.SPECIALIZED
        elif capability == AssistantCapability.TECHNICAL_VALIDATION:
            return ModelType.ACCURATE
        elif capability == AssistantCapability.CONTENT_GENERATION:
            return ModelType.BALANCED
        else:
            return ModelType.FAST
    
    def get_model_config(self, model_type: ModelType) -> Dict:
        """Get configuration for a model type"""
        return self.model_configs[model_type].copy()

class AIAssistantInterface:
    """Main interface for AI assistance capabilities"""
    
    def __init__(self, ai_service_manager: AIServiceManager, validation_engine: ValidationEngine):
        self.ai_service_manager = ai_service_manager
        self.validation_engine = validation_engine
        self.prompt_manager = PromptManager()
        self.model_selector = ModelSelector()
        self.metrics = AssistantMetrics()
        self.active_contexts: Dict[str, AssistantContext] = {}
        
        # Configuration
        self.context_timeout = timedelta(hours=1)
        self.max_retries = 3
        self.confidence_threshold = 0.7
    
    async def create_context(self, session_id: str, user_id: str, capabilities: Set[AssistantCapability]) -> AssistantContext:
        """Create a new assistant context"""
        context = AssistantContext(
            context_id=f"ctx-{session_id}-{datetime.now().timestamp()}",
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.now(),
            capabilities=capabilities
        )
        self.active_contexts[context.context_id] = context
        return context
    
    async def process_request(self, context_id: str, template_id: str, **kwargs) -> AssistantResponse:
        """Process an AI assistance request"""
        start_time = datetime.now()
        
        try:
            # Get context
            context = self.active_contexts.get(context_id)
            if not context:
                raise ValueError(f"Invalid context ID: {context_id}")
            
            # Get template and generate prompt
            template = self.prompt_manager.get_template(template_id)
            prompt = template.format(**kwargs)
            
            # Select model
            model_type = self.model_selector.select_model(template.capability, context)
            model_config = self.model_selector.get_model_config(model_type)
            
            # Create AI request
            request = AIRequest(
                request_id=f"req-{context_id}-{len(context.conversation_history)}",
                content={
                    'prompt': prompt,
                    'context': context.conversation_history,
                    'config': model_config
                },
                priority=AIRequestPriority.HIGH,
                timestamp=datetime.now(),
                service_capability=template.capability.value
            )
            
            # Submit request and wait for response
            response_content = await self._submit_request(request, model_type)
            
            # Process response
            processed_response = await self._process_response(response_content, template.capability)
            
            # Calculate metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create response object
            response = AssistantResponse(
                response_id=f"resp-{request.request_id}",
                context_id=context_id,
                content=processed_response,
                model_used=model_type,
                confidence_score=self._calculate_confidence(processed_response),
                processing_time=processing_time,
                metadata={
                    'template_used': template_id,
                    'model_config': model_config
                }
            )
            
            # Update context
            context.conversation_history.append({
                'prompt': prompt,
                'response': response.content,
                'timestamp': response.timestamp
            })
            
            # Update metrics
            self.metrics.add_request(model_type, template.capability, processing_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            self.metrics.add_error(type(e).__name__)
            raise
    
    async def _submit_request(self, request: AIRequest, model_type: ModelType) -> Any:
        """Submit request to AI service and handle retries"""
        retries = 0
        while retries < self.max_retries:
            try:
                await self.ai_service_manager.submit_request(request)
                # TODO: Implement response waiting mechanism
                return {"content": "Sample response"}  # Placeholder
            except Exception as e:
                retries += 1
                if retries == self.max_retries:
                    raise
                logger.warning(f"Retry {retries}/{self.max_retries} after error: {e}")
                await asyncio.sleep(2 ** retries)  # Exponential backoff
    
    async def _process_response(self, response: Any, capability: AssistantCapability) -> Any:
        """Process and validate AI response"""
        # TODO: Implement response processing based on capability
        return response
    
    def _calculate_confidence(self, response: Any) -> float:
        """Calculate confidence score for response"""
        # TODO: Implement confidence calculation
        return 0.85
    
    async def validate_response(self, response: AssistantResponse) -> ValidationResult:
        """Validate an AI response"""
        if isinstance(response.content, str):
            return await self.validation_engine.validate_document(
                response.response_id,
                response.content,
                {'type': 'ai_response', 'context_id': response.context_id}
            )
        return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics.get_summary()
    
    async def cleanup_contexts(self):
        """Clean up expired contexts"""
        now = datetime.now()
        expired = [
            ctx_id for ctx_id, ctx in self.active_contexts.items()
            if now - ctx.timestamp > self.context_timeout
        ]
        for ctx_id in expired:
            del self.active_contexts[ctx_id]

# Example usage
async def main():
    # Create components
    ai_manager = AIServiceManager()
    validation_engine = ValidationEngine(ai_manager)
    assistant = AIAssistantInterface(ai_manager, validation_engine)
    
    # Start services
    await ai_manager.start()
    
    # Create context
    context = await assistant.create_context(
        "session-1",
        "user-1",
        {AssistantCapability.DOCUMENTATION_REVIEW}
    )
    
    # Process request
    response = await assistant.process_request(
        context.context_id,
        "doc-review",
        content="Example documentation content",
        aspects="clarity,completeness,accuracy"
    )
    
    print(f"Response: {response}")
    print(f"Metrics: {assistant.get_metrics()}")
    
    # Stop services
    await ai_manager.stop()

if __name__ == "__main__":
    asyncio.run(main())

