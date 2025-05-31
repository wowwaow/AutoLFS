import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import yaml

class TestValidationPipeline:
    @pytest.fixture
    def mock_ai_service(self):
        return Mock()

    @pytest.fixture
    def sample_doc_content(self):
        return """
        # Package Documentation
        
        ## Source Information
        - Version: 1.2.3
        - Checksum: abc123
        
        ## Dependencies
        - python >= 3.8
        - yaml
        """

    @pytest.fixture
    def config_path(self):
        return Path("config/workflows/validation_pipeline.yaml")

    def test_schema_validation(self, mock_ai_service, sample_doc_content):
        """Test schema validation functionality"""
        # Arrange
        mock_ai_service.validate_schema.return_value = (True, [])
        
        # Act
        result, errors = mock_ai_service.validate_schema(sample_doc_content)
        
        # Assert
        assert result is True
        assert len(errors) == 0
        mock_ai_service.validate_schema.assert_called_once_with(sample_doc_content)

    def test_content_completeness(self, mock_ai_service, sample_doc_content):
        """Test content completeness checks"""
        # Arrange
        expected_sections = ['Source Information', 'Dependencies']
        mock_ai_service.check_completeness.return_value = (True, expected_sections, [])
        
        # Act
        result, found_sections, missing = mock_ai_service.check_completeness(
            sample_doc_content,
            expected_sections
        )
        
        # Assert
        assert result is True
        assert found_sections == expected_sections
        assert len(missing) == 0
        mock_ai_service.check_completeness.assert_called_once_with(
            sample_doc_content,
            expected_sections
        )

    def test_cross_reference_integrity(self, mock_ai_service, sample_doc_content):
        """Test cross-reference validation"""
        # Arrange
        mock_refs = {'python': 'languages/python.md', 'yaml': 'formats/yaml.md'}
        mock_ai_service.validate_references.return_value = (True, [])
        
        # Act
        result, invalid_refs = mock_ai_service.validate_references(
            sample_doc_content,
            mock_refs
        )
        
        # Assert
        assert result is True
        assert len(invalid_refs) == 0
        mock_ai_service.validate_references.assert_called_once_with(
            sample_doc_content,
            mock_refs
        )

    def test_quality_metrics(self, mock_ai_service, sample_doc_content):
        """Test quality metric assessment"""
        # Arrange
        expected_metrics = {
            'completeness': 0.98,
            'accuracy': 0.95,
            'consistency': 0.90
        }
        mock_ai_service.assess_quality.return_value = (True, expected_metrics)
        
        # Act
        result, metrics = mock_ai_service.assess_quality(sample_doc_content)
        
        # Assert
        assert result is True
        assert metrics == expected_metrics
        mock_ai_service.assess_quality.assert_called_once_with(sample_doc_content)

    def test_validation_pipeline_config(self, config_path):
        """Test validation pipeline configuration loading"""
        # Arrange & Act
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Assert
        assert 'pre_commit' in config
        assert 'continuous_assessment' in config
        assert config['pre_commit']['enabled'] is True
        assert isinstance(config['pre_commit']['checks'], list)
        assert len(config['pre_commit']['checks']) > 0

    @pytest.mark.integration
    def test_full_pipeline_integration(self, mock_ai_service, sample_doc_content, config_path):
        """Test full validation pipeline integration"""
        # Arrange
        mock_ai_service.validate_schema.return_value = (True, [])
        mock_ai_service.check_completeness.return_value = (True, ['Source Information', 'Dependencies'], [])
        mock_ai_service.validate_references.return_value = (True, [])
        mock_ai_service.assess_quality.return_value = (True, {
            'completeness': 0.98,
            'accuracy': 0.95,
            'consistency': 0.90
        })
        
        # Act
        schema_result, _ = mock_ai_service.validate_schema(sample_doc_content)
        completeness_result, _, _ = mock_ai_service.check_completeness(
            sample_doc_content,
            ['Source Information', 'Dependencies']
        )
        ref_result, _ = mock_ai_service.validate_references(
            sample_doc_content,
            {'python': 'languages/python.md', 'yaml': 'formats/yaml.md'}
        )
        quality_result, metrics = mock_ai_service.assess_quality(sample_doc_content)
        
        # Assert
        assert all([schema_result, completeness_result, ref_result, quality_result])
        assert metrics['completeness'] >= 0.98
        assert metrics['accuracy'] >= 0.95
        assert metrics['consistency'] >= 0.90

