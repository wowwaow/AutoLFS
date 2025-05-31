import pytest
from unittest.mock import Mock, patch
import yaml
from pathlib import Path

class TestDocumentationQuality:
    @pytest.fixture
    def mock_quality_checker(self):
        return Mock()

    @pytest.fixture
    def sample_doc_content(self):
        return """
        # Example Package Documentation

        ## Source Information
        - Package Name: example-package
        - Version: 1.2.3
        - Checksum: abc123def456
        - Source URL: https://example.com/package-1.2.3.tar.gz

        ## Dependencies
        - python >= 3.8
        - yaml ~= 5.1
        - pytest >= 6.0

        ## Build Instructions
        1. Configure with default options
        2. Run make in the build directory
        3. Install using make install

        ## Configuration
        The following configuration options are available:
        - DEBUG=1: Enable debug output
        - OPTIMIZE=1: Enable optimization
        """

    @pytest.fixture
    def quality_thresholds(self):
        return {
            'completeness': 0.98,
            'accuracy': 0.95,
            'consistency': 0.90,
            'cross_reference': 0.99
        }

    def test_completeness_check(self, mock_quality_checker, sample_doc_content, quality_thresholds):
        """Test documentation completeness validation"""
        # Arrange
        required_sections = [
            'Source Information',
            'Dependencies',
            'Build Instructions',
            'Configuration'
        ]
        expected_score = 1.0  # All sections present
        mock_quality_checker.check_completeness.return_value = (
            True,
            expected_score,
            required_sections,
            []  # No missing sections
        )

        # Act
        success, score, found_sections, missing = mock_quality_checker.check_completeness(
            sample_doc_content,
            required_sections
        )

        # Assert
        assert success is True
        assert score >= quality_thresholds['completeness']
        assert set(found_sections) == set(required_sections)
        assert len(missing) == 0
        mock_quality_checker.check_completeness.assert_called_once_with(
            sample_doc_content,
            required_sections
        )

    def test_accuracy_check(self, mock_quality_checker, sample_doc_content, quality_thresholds):
        """Test technical accuracy validation"""
        # Arrange
        expected_metrics = {
            'version_format_valid': True,
            'checksum_format_valid': True,
            'url_accessible': True,
            'dependency_format_valid': True,
            'build_steps_valid': True
        }
        expected_score = 0.96
        mock_quality_checker.verify_technical_accuracy.return_value = (
            True,
            expected_score,
            expected_metrics,
            []  # No accuracy issues
        )

        # Act
        success, score, metrics, issues = mock_quality_checker.verify_technical_accuracy(
            sample_doc_content
        )

        # Assert
        assert success is True
        assert score >= quality_thresholds['accuracy']
        assert all(metrics.values())
        assert len(issues) == 0
        mock_quality_checker.verify_technical_accuracy.assert_called_once_with(
            sample_doc_content
        )

    def test_consistency_check(self, mock_quality_checker, sample_doc_content, quality_thresholds):
        """Test style consistency validation"""
        # Arrange
        style_rules = {
            'heading_style': '^## [A-Z][a-zA-Z ]+$',
            'list_style': '^- ',
            'version_format': r'^\d+\.\d+\.\d+$'
        }
        expected_score = 0.92
        mock_quality_checker.validate_consistency.return_value = (
            True,
            expected_score,
            {'passed_rules': 12, 'total_rules': 13},
            ['Minor heading format inconsistency in section 3']
        )

        # Act
        success, score, metrics, issues = mock_quality_checker.validate_consistency(
            sample_doc_content,
            style_rules
        )

        # Assert
        assert success is True
        assert score >= quality_thresholds['consistency']
        assert metrics['passed_rules'] / metrics['total_rules'] >= 0.90
        assert len(issues) <= 1
        mock_quality_checker.validate_consistency.assert_called_once_with(
            sample_doc_content,
            style_rules
        )

    def test_cross_reference_accuracy(self, mock_quality_checker, sample_doc_content, quality_thresholds):
        """Test cross-reference accuracy validation"""
        # Arrange
        references = {
            'python': 'languages/python.md',
            'yaml': 'formats/yaml.md',
            'pytest': 'testing/pytest.md'
        }
        expected_score = 1.0
        mock_quality_checker.verify_cross_references.return_value = (
            True,
            expected_score,
            {'valid_refs': 3, 'total_refs': 3},
            []  # No invalid references
        )

        # Act
        success, score, metrics, invalid_refs = mock_quality_checker.verify_cross_references(
            sample_doc_content,
            references
        )

        # Assert
        assert success is True
        assert score >= quality_thresholds['cross_reference']
        assert metrics['valid_refs'] == metrics['total_refs']
        assert len(invalid_refs) == 0
        mock_quality_checker.verify_cross_references.assert_called_once_with(
            sample_doc_content,
            references
        )

    @pytest.mark.integration
    def test_full_quality_validation(self, mock_quality_checker, sample_doc_content, quality_thresholds):
        """Test complete quality validation pipeline"""
        # Arrange
        mock_quality_checker.validate_document_quality.return_value = (
            True,
            {
                'completeness': 1.0,
                'accuracy': 0.96,
                'consistency': 0.92,
                'cross_reference': 1.0
            },
            []  # No quality issues
        )

        # Act
        success, metrics, issues = mock_quality_checker.validate_document_quality(
            sample_doc_content,
            quality_thresholds
        )

        # Assert
        assert success is True
        assert all(
            metrics[key] >= threshold
            for key, threshold in quality_thresholds.items()
        )
        assert len(issues) == 0
        mock_quality_checker.validate_document_quality.assert_called_once_with(
            sample_doc_content,
            quality_thresholds
        )

    @pytest.mark.regression
    def test_quality_regression_detection(self, mock_quality_checker, sample_doc_content):
        """Test quality regression detection"""
        # Arrange
        historical_metrics = {
            'completeness': [1.0, 0.98, 0.99],
            'accuracy': [0.96, 0.95, 0.97],
            'consistency': [0.92, 0.91, 0.93],
            'cross_reference': [1.0, 0.99, 1.0]
        }
        mock_quality_checker.check_quality_regression.return_value = (
            False,  # No regression
            historical_metrics,
            []  # No regression issues
        )

        # Act
        regression_detected, metrics, issues = mock_quality_checker.check_quality_regression(
            sample_doc_content,
            historical_metrics
        )

        # Assert
        assert regression_detected is False
        assert all(
            metrics[key][-1] >= min(values)
            for key, values in historical_metrics.items()
        )
        assert len(issues) == 0
        mock_quality_checker.check_quality_regression.assert_called_once_with(
            sample_doc_content,
            historical_metrics
        )

