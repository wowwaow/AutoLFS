#!/usr/bin/env python3

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
import json
import re

from ai_service_manager import AIServiceManager, AIRequest, AIRequestPriority

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ValidationCategory(Enum):
    """Categories of validation checks"""
    QUALITY = "quality"
    CONSISTENCY = "consistency"
    TECHNICAL = "technical"
    COMPLETENESS = "completeness"
    CUSTOM = "custom"

@dataclass
class ValidationRule:
    """Represents a single validation rule"""
    rule_id: str
    name: str
    description: str
    category: ValidationCategory
    severity: ValidationSeverity
    validation_fn: Callable
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not callable(self.validation_fn):
            raise ValueError("validation_fn must be callable")

@dataclass
class ValidationIssue:
    """Represents a validation issue found during checks"""
    rule_id: str
    severity: ValidationSeverity
    message: str
    location: Optional[str]
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ValidationResult:
    """Results from running validation checks"""
    doc_id: str
    timestamp: datetime
    passed: bool
    issues: List[ValidationIssue]
    metrics: Dict[str, float]
    category_results: Dict[ValidationCategory, bool]

class ValidationEngine:
    """Manages document validation rules and execution"""
    
    def __init__(self, ai_service_manager: AIServiceManager):
        self.ai_service_manager = ai_service_manager
        self.rules: Dict[str, ValidationRule] = {}
        self.results_history: Dict[str, List[ValidationResult]] = {}
        self.custom_rules: Dict[str, ValidationRule] = {}
        
        # Initialize built-in rules
        self._initialize_built_in_rules()

    def _initialize_built_in_rules(self):
        """Initialize the set of built-in validation rules"""
        # Quality rules
        self.add_rule(ValidationRule(
            rule_id="QUAL001",
            name="Minimum Content Length",
            description="Validates that content meets minimum length requirements",
            category=ValidationCategory.QUALITY,
            severity=ValidationSeverity.ERROR,
            validation_fn=self._check_content_length,
            parameters={"min_length": 100}
        ))
        
        self.add_rule(ValidationRule(
            rule_id="QUAL002",
            name="Grammar Check",
            description="Checks for basic grammar issues",
            category=ValidationCategory.QUALITY,
            severity=ValidationSeverity.WARNING,
            validation_fn=self._check_grammar,
            parameters={"language": "en"}
        ))
        
        # Consistency rules
        self.add_rule(ValidationRule(
            rule_id="CONS001",
            name="Terminology Consistency",
            description="Checks for consistent use of technical terms",
            category=ValidationCategory.CONSISTENCY,
            severity=ValidationSeverity.WARNING,
            validation_fn=self._check_terminology
        ))
        
        # Technical rules
        self.add_rule(ValidationRule(
            rule_id="TECH001",
            name="Code Block Validation",
            description="Validates code blocks for syntax errors",
            category=ValidationCategory.TECHNICAL,
            severity=ValidationSeverity.ERROR,
            validation_fn=self._validate_code_blocks
        ))
        
        # Completeness rules
        self.add_rule(ValidationRule(
            rule_id="COMP001",
            name="Required Sections",
            description="Checks for presence of all required sections",
            category=ValidationCategory.COMPLETENESS,
            severity=ValidationSeverity.ERROR,
            validation_fn=self._check_required_sections,
            parameters={"required_sections": ["introduction", "prerequisites", "steps", "conclusion"]}
        ))

    def add_rule(self, rule: ValidationRule):
        """Add a new validation rule"""
        if rule.rule_id in self.rules:
            raise ValueError(f"Rule with ID {rule.rule_id} already exists")
        self.rules[rule.rule_id] = rule
        logger.info(f"Added validation rule: {rule.rule_id} - {rule.name}")

    def add_custom_rule(self, rule: ValidationRule):
        """Add a custom validation rule"""
        if not rule.rule_id.startswith("CUSTOM"):
            rule.rule_id = f"CUSTOM_{rule.rule_id}"
        rule.category = ValidationCategory.CUSTOM
        self.custom_rules[rule.rule_id] = rule
        logger.info(f"Added custom validation rule: {rule.rule_id}")

    def disable_rule(self, rule_id: str):
        """Disable a validation rule"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
        elif rule_id in self.custom_rules:
            self.custom_rules[rule_id].enabled = False
        logger.info(f"Disabled validation rule: {rule_id}")

    def enable_rule(self, rule_id: str):
        """Enable a validation rule"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
        elif rule_id in self.custom_rules:
            self.custom_rules[rule_id].enabled = True
        logger.info(f"Enabled validation rule: {rule_id}")

    async def validate_document(self, doc_id: str, content: str, metadata: Dict) -> ValidationResult:
        """Run all enabled validation rules against a document"""
        issues = []
        metrics = {}
        category_results = {category: True for category in ValidationCategory}
        
        # Combine built-in and custom rules
        all_rules = {**self.rules, **self.custom_rules}
        enabled_rules = {rid: rule for rid, rule in all_rules.items() if rule.enabled}
        
        try:
            # Run validation rules
            for rule in enabled_rules.values():
                try:
                    rule_issues = await self._execute_rule(rule, content, metadata)
                    if rule_issues:
                        issues.extend(rule_issues)
                        category_results[rule.category] = False
                except Exception as e:
                    logger.error(f"Error executing rule {rule.rule_id}: {e}")
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.ERROR,
                        message=f"Rule execution failed: {str(e)}",
                        location=None,
                        context={"error": str(e)}
                    ))
            
            # Calculate validation metrics
            metrics = await self._calculate_metrics(content, issues)
            
            # Create validation result
            result = ValidationResult(
                doc_id=doc_id,
                timestamp=datetime.now(),
                passed=len(issues) == 0,
                issues=issues,
                metrics=metrics,
                category_results=category_results
            )
            
            # Store result in history
            if doc_id not in self.results_history:
                self.results_history[doc_id] = []
            self.results_history[doc_id].append(result)
            
            # Request AI analysis for complex issues
            await self._request_ai_analysis(doc_id, content, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Validation failed for document {doc_id}: {e}")
            raise

    async def _execute_rule(self, rule: ValidationRule, content: str, metadata: Dict) -> List[ValidationIssue]:
        """Execute a single validation rule"""
        try:
            if asyncio.iscoroutinefunction(rule.validation_fn):
                return await rule.validation_fn(content, metadata, rule.parameters)
            return rule.validation_fn(content, metadata, rule.parameters)
        except Exception as e:
            logger.error(f"Error executing rule {rule.rule_id}: {e}")
            return [ValidationIssue(
                rule_id=rule.rule_id,
                severity=rule.severity,
                message=f"Rule execution failed: {str(e)}",
                location=None,
                context={"error": str(e)}
            )]

    async def _request_ai_analysis(self, doc_id: str, content: str, result: ValidationResult):
        """Request AI analysis for complex validation issues"""
        try:
            complex_issues = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
            if complex_issues:
                request = AIRequest(
                    request_id=f"validation-{doc_id}",
                    content={
                        'doc_id': doc_id,
                        'content': content,
                        'issues': [i.__dict__ for i in complex_issues]
                    },
                    priority=AIRequestPriority.HIGH,
                    timestamp=datetime.now(),
                    service_capability="validation-analysis"
                )
                await self.ai_service_manager.submit_request(request)
                logger.info(f"Requested AI analysis for document {doc_id}")
        except Exception as e:
            logger.error(f"Failed to request AI analysis: {e}")

    async def _calculate_metrics(self, content: str, issues: List[ValidationIssue]) -> Dict[str, float]:
        """Calculate validation metrics"""
        total_issues = len(issues)
        error_count = len([i for i in issues if i.severity == ValidationSeverity.ERROR])
        warning_count = len([i for i in issues if i.severity == ValidationSeverity.WARNING])
        
        return {
            'quality_score': self._calculate_quality_score(total_issues, error_count, warning_count),
            'error_density': error_count / len(content) if content else 0,
            'warning_density': warning_count / len(content) if content else 0
        }

    def _calculate_quality_score(self, total_issues: int, errors: int, warnings: int) -> float:
        """Calculate overall quality score"""
        base_score = 100
        error_penalty = 10
        warning_penalty = 5
        
        score = base_score - (errors * error_penalty) - (warnings * warning_penalty)
        return max(0.0, min(100.0, score))

    # Built-in validation functions
    def _check_content_length(self, content: str, metadata: Dict, params: Dict) -> List[ValidationIssue]:
        """Check if content meets minimum length requirements"""
        min_length = params.get('min_length', 100)
        if len(content) < min_length:
            return [ValidationIssue(
                rule_id="QUAL001",
                severity=ValidationSeverity.ERROR,
                message=f"Content length ({len(content)}) is below minimum required length ({min_length})",
                location=None,
                context={"actual_length": len(content), "min_length": min_length}
            )]
        return []

    def _check_grammar(self, content: str, metadata: Dict, params: Dict) -> List[ValidationIssue]:
        """Check for basic grammar issues"""
        # TODO: Implement grammar checking
        return []

    def _check_terminology(self, content: str, metadata: Dict, params: Dict) -> List[ValidationIssue]:
        """Check for consistent terminology usage"""
        # TODO: Implement terminology consistency checking
        return []

    def _validate_code_blocks(self, content: str, metadata: Dict, params: Dict) -> List[ValidationIssue]:
        """Validate code blocks in content"""
        # TODO: Implement code block validation
        return []

    def _check_required_sections(self, content: str, metadata: Dict, params: Dict) -> List[ValidationIssue]:
        """Check for presence of required sections"""
        required_sections = params.get('required_sections', [])
        issues = []
        
        for section in required_sections:
            if not re.search(fr"#{1,6}\s+{section}", content, re.IGNORECASE):
                issues.append(ValidationIssue(
                    rule_id="COMP001",
                    severity=ValidationSeverity.ERROR,
                    message=f"Required section '{section}' not found",
                    location=None,
                    context={"missing_section": section}
                ))
        
        return issues

    def get_validation_history(self, doc_id: str) -> List[ValidationResult]:
        """Get validation history for a document"""
        return self.results_history.get(doc_id, [])

    def get_rules_summary(self) -> Dict[str, Any]:
        """Get summary of all validation rules"""
        return {
            'built_in_rules': len(self.rules),
            'custom_rules': len(self.custom_rules),
            'enabled_rules': len([r for r in {**self.rules, **self.custom_rules}.values() if r.enabled]),
            'rules_by_category': self._get_rules_by_category()
        }

    def _get_rules_by_category(self) -> Dict[str, int]:
        """Get count of rules by category"""
        categories = {}
        for rule in {**self.rules, **self.custom_rules}.values():
            if rule.category.value not in categories:
                categories[rule.category.value] = 0
            categories[rule.category.value] += 1
        return categories

# Example usage
async def main():
    # Create and start AI Service Manager
    ai_manager = AIServiceManager()
    await ai_manager.start()
    
    # Create Validation Engine
    validation_engine = ValidationEngine(ai_manager)
    
    # Add custom rule
    validation_engine.add_custom_rule(ValidationRule(
        rule_id="TEST001",
        name="Test Custom Rule",
        description="Example custom validation rule",
        category=ValidationCategory.CUSTOM,
        severity=ValidationSeverity.WARNING,
        validation_fn=lambda c, m, p: []
    ))
    
    # Validate example document
    result = await validation_engine.validate_document(
        "doc-1",
        "Example content",
        {"type": "technical"}
    )
    
    print(f"Validation result: {result}")
    
    # Stop AI Service Manager
    await ai_manager.stop()

if __name__ == "__main__":
    asyncio.run(main())

