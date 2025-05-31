#!/usr/bin/env python3

import asyncio
import pytest
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set
import json
import time

from ai_service_manager import AIServiceManager, AIRequest, AIRequestPriority
from document_processor import DocumentProcessor, DocumentMetadata
from validation_engine import ValidationEngine, ValidationRule, ValidationCategory, ValidationSeverity
from ai_assistant_interface import (
    AIAssistantInterface,
    AssistantCapability,
    ModelType,
    PromptTemplate,
    AssistantContext
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test fixtures and utilities
@pytest.fixture
async def ai_service_manager():
    """Fixture for AIServiceManager"""
    manager = AIServiceManager()
    await manager.start()
    yield manager
    await manager.stop()

@pytest.fixture
async def validation_engine(ai_service_manager):
    """Fixture for ValidationEngine"""
    engine = ValidationEngine(ai_service_manager)
    yield engine

@pytest.fixture
async def document_processor(ai_service_manager):
    """Fixture for DocumentProcessor"""
    processor = DocumentProcessor(ai_service_manager)
    await processor.start()
    yield processor
    await processor.stop()

@pytest.fixture
async def ai_assistant(ai_service_manager, validation_engine):
    """Fixture for AIAssistantInterface"""
    assistant = AIAssistantInterface(ai_service_manager, validation_engine)
    yield assistant
    await assistant.cleanup_contexts()

@pytest.fixture
def sample_document():
    """Fixture for sample document content"""
    return {
        'content': """# Test Document
        
        ## Introduction
        This is a test document for integration testing.
        
        ## Prerequisites
        - Python 3.8+
        - Required packages
        
        ## Steps
        1. First step
        2. Second step
        
        ## Conclusion
        Test document complete.""",
        'metadata': DocumentMetadata(
            doc_id="test-doc-1",
            title="Test Document",
            author="Integration Test",
            created_at=datetime.now(),
            last_modified=datetime.now(),
            version="1.0",
            doc_type="technical",
            tags=["test", "integration"]
        )
    }

class TestAIWorkflowIntegration:
    """Integration tests for AI workflow system"""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(
        self,
        ai_service_manager,
        document_processor,
        validation_engine,
        ai_assistant,
        sample_document
    ):
        """Test complete end-to-end document processing workflow"""
        # 1. Process document
        doc_id = await document_processor.process_document(
            sample_document['content'],
            sample_document['metadata']
        )
        
        # 2. Create AI assistant context
        context = await ai_assistant.create_context(
            "test-session",
            "test-user",
            {AssistantCapability.DOCUMENTATION_REVIEW}
        )
        
        # 3. Submit for AI review
        response = await ai_assistant.process_request(
            context.context_id,
            "doc-review",
            content=sample_document['content'],
            aspects="clarity,completeness,accuracy"
        )
        
        # 4. Validate response
        validation_result = await ai_assistant.validate_response(response)
        
        # Assertions
        assert doc_id == sample_document['metadata'].doc_id
        assert response.confidence_score >= ai_assistant.confidence_threshold
        assert validation_result.passed
        assert len(validation_result.issues) == 0

    @pytest.mark.asyncio
    async def test_component_interaction(
        self,
        ai_service_manager,
        document_processor,
        validation_engine,
        ai_assistant
    ):
        """Test interaction between all components"""
        # Register test service
        service = await ai_service_manager.register_service({
            'service_id': 'test-service',
            'endpoint': 'http://localhost:8000/test',
            'capabilities': ['documentation_review']
        })
        
        # Create and validate document
        doc_id = await document_processor.process_document(
            "Test content",
            DocumentMetadata(
                doc_id="test-doc-2",
                title="Test",
                author="Test",
                created_at=datetime.now(),
                last_modified=datetime.now(),
                version="1.0",
                doc_type="test",
                tags=["test"]
            )
        )
        
        # Verify service registration
        assert 'test-service' in ai_service_manager.services
        
        # Verify document processing
        status = await document_processor.get_status(doc_id)
        assert status['state'] == 'complete'
        
        # Verify validation rules
        validation_result = await validation_engine.validate_document(
            doc_id,
            "Test content",
            {'type': 'test'}
        )
        assert validation_result is not None

    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        ai_service_manager,
        document_processor,
        ai_assistant
    ):
        """Test error handling and recovery"""
        # Test invalid service registration
        with pytest.raises(ValueError):
            await ai_service_manager.register_service({
                'service_id': '',  # Invalid ID
                'endpoint': 'http://invalid',
                'capabilities': []
            })
        
        # Test invalid document processing
        with pytest.raises(ValueError):
            await document_processor.process_document(
                "",  # Empty content
                None  # Invalid metadata
            )
        
        # Test AI assistant error recovery
        context = await ai_assistant.create_context(
            "test-session",
            "test-user",
            {AssistantCapability.DOCUMENTATION_REVIEW}
        )
        
        # Simulate service failure and retry
        response = await ai_assistant.process_request(
            context.context_id,
            "doc-review",
            content="Test content",
            aspects="test"
        )
        
        # Verify metrics recorded the error
        metrics = ai_assistant.get_metrics()
        assert metrics['error_count'] > 0

    @pytest.mark.asyncio
    async def test_load_performance(
        self,
        ai_service_manager,
        document_processor,
        validation_engine,
        ai_assistant
    ):
        """Test system performance under load"""
        start_time = time.time()
        
        # Create multiple concurrent requests
        tasks = []
        for i in range(10):
            context = await ai_assistant.create_context(
                f"test-session-{i}",
                f"test-user-{i}",
                {AssistantCapability.DOCUMENTATION_REVIEW}
            )
            
            task = ai_assistant.process_request(
                context.context_id,
                "doc-review",
                content=f"Test content {i}",
                aspects="test"
            )
            tasks.append(task)
        
        # Wait for all requests to complete
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify performance
        total_time = time.time() - start_time
        assert total_time < 30  # Should complete within 30 seconds
        
        # Check success rate
        success_count = sum(1 for r in responses if not isinstance(r, Exception))
        assert success_count >= 8  # At least 80% success rate

    @pytest.mark.asyncio
    async def test_validation_rules(self, validation_engine):
        """Test validation rule execution"""
        # Add custom validation rule
        validation_engine.add_custom_rule(ValidationRule(
            rule_id="TEST001",
            name="Test Rule",
            description="Test validation rule",
            category=ValidationCategory.CUSTOM,
            severity=ValidationSeverity.ERROR,
            validation_fn=lambda c, m, p: []
        ))
        
        # Validate with custom rule
        result = await validation_engine.validate_document(
            "test-doc-3",
            "Test content",
            {'type': 'test'}
        )
        
        # Verify rule execution
        assert result.passed
        assert ValidationCategory.CUSTOM in result.category_results

    @pytest.mark.asyncio
    async def test_model_selection(self, ai_assistant):
        """Test AI model selection and fallback"""
        # Test different capabilities
        contexts = {}
        for capability in AssistantCapability:
            context = await ai_assistant.create_context(
                f"test-session-{capability.value}",
                "test-user",
                {capability}
            )
            contexts[capability] = context
        
        # Verify model selection for each capability
        for capability, context in contexts.items():
            response = await ai_assistant.process_request(
                context.context_id,
                "doc-review",
                content="Test content",
                aspects="test"
            )
            
            if capability == AssistantCapability.CODE_REVIEW:
                assert response.model_used == ModelType.SPECIALIZED
            elif capability == AssistantCapability.TECHNICAL_VALIDATION:
                assert response.model_used == ModelType.ACCURATE

    @pytest.mark.asyncio
    async def test_metrics_collection(
        self,
        ai_assistant,
        validation_engine
    ):
        """Test metrics collection accuracy"""
        # Generate some activity
        context = await ai_assistant.create_context(
            "test-session",
            "test-user",
            {AssistantCapability.DOCUMENTATION_REVIEW}
        )
        
        # Success case
        await ai_assistant.process_request(
            context.context_id,
            "doc-review",
            content="Test content",
            aspects="test"
        )
        
        # Error case
        try:
            await ai_assistant.process_request(
                "invalid-context",
                "doc-review",
                content="Test content",
                aspects="test"
            )
        except ValueError:
            pass
        
        # Verify metrics
        metrics = ai_assistant.get_metrics()
        assert metrics['total_requests'] == 1
        assert metrics['error_count'] == 1
        assert 'ValueError' in metrics['error_distribution']

    @pytest.mark.asyncio
    async def test_context_management(self, ai_assistant):
        """Test context management and cleanup"""
        # Create contexts
        contexts = []
        for i in range(5):
            context = await ai_assistant.create_context(
                f"test-session-{i}",
                "test-user",
                {AssistantCapability.DOCUMENTATION_REVIEW}
            )
            contexts.append(context)
        
        # Verify context creation
        assert len(ai_assistant.active_contexts) == 5
        
        # Simulate context timeout
        ai_assistant.context_timeout = timedelta(seconds=0)  # Immediate timeout
        await ai_assistant.cleanup_contexts()
        
        # Verify cleanup
        assert len(ai_assistant.active_contexts) == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

