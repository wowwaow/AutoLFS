"""
Toolchain validation implementation.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import subprocess
import re

from .validation import ValidationResult, ValidationLevel, BuildPlatform

@dataclass
class ToolchainComponent:
    """Toolchain component specification."""
    name: str
    version: str
    path: Path
    features: List[str]

class ToolchainValidator:
    """Validates toolchain requirements and functionality."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.required_versions = {
            "gcc": {
                "minimum": "10.2.0",
                "recommended": "11.2.0",
                "features": ["plugins", "lto"]
            },
            "binutils": {
                "minimum": "2.36",
                "recommended": "2.37",
                "features": ["gold", "plugins"]
            },
            "glibc": {
                "minimum": "2.33",
                "recommended": "2.34",
                "features": ["multiarch"]
            }
        }

    def validate_toolchain(self, platform: BuildPlatform) -> ValidationResult:
        """Validate toolchain for target platform."""
        messages = []
        details = {}

        # Validate component versions
        version_result = self._validate_versions()
        messages.extend(version_result.messages)
        details["versions"] = version_result.details

        # Validate features
        feature_result = self._validate_features()
        messages.extend(feature_result.messages)
        details["features"] = feature_result.details

        # Validate target support
        target_result = self._validate_target_support(platform)
        messages.extend(target_result.messages)
        details["target"] = target_result.details

        # Run compilation tests
        test_result = self._run_compilation_tests(platform)
        messages.extend(test_result.messages)
        details["tests"] = test_result.details

        success = all(r.success for r in [
            version_result, feature_result, target_result, test_result
        ])
        return ValidationResult(
            success=success,
            level=ValidationLevel.L3_TOOLCHAIN,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_versions(self) -> ValidationResult:
        """Validate toolchain component versions."""
        messages = []
        details = {}
        success = True

        for component, requirements in self.required_versions.items():
            try:
                version = self._get_component_version(component)
                details[component] = {"version": version}

                if self._compare_versions(version, requirements["minimum"]) < 0:
                    messages.append(
                        f"{component} version {version} is below minimum "
                        f"required version {requirements['minimum']}"
                    )
                    success = False
                elif self._compare_versions(version, requirements["recommended"]) < 0:
                    messages.append(
                        f"Warning: {component} version {version} is below recommended "
                        f"version {requirements['recommended']}"
                    )
            except Exception as e:
                messages.append(f"Failed to validate {component} version: {e}")
                success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L3_TOOLCHAIN,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_features(self) -> ValidationResult:
        """Validate toolchain features."""
        messages = []
        details = {}
        success = True

        feature_tests = {
            "lto": self._test_lto_support,
            "pic": self._test_pic_support,
            "relro": self._test_relro_support,
            "ssp": self._test_stack_protection,
            "multilib": self._test_multilib_support
        }

        for feature, test_func in feature_tests.items():
            try:
                feature_supported = test_func()
                details[feature] = {"supported": feature_supported}

                if not feature_supported:
                    messages.append(f"Required feature not supported: {feature}")
                    success = False
            except Exception as e:
                messages.append(f"Failed to test feature {feature}: {e}")
                success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L3_TOOLCHAIN,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_target_support(self, platform: BuildPlatform) -> ValidationResult:
        """Validate target platform support."""
        messages = []
        details = {}
        success = True

        try:
            # Check target triple support
            triple_result = self._check_target_triple(platform.triple)
            messages.extend(triple_result.messages)
            details["triple"] = triple_result.details
            success = success and triple_result.success

            # Check target features
            feature_result = self._check_target_features(platform.features)
            messages.extend(feature_result.messages)
            details["features"] = feature_result.details
            success = success and feature_result.success

            # Check ABI compatibility
            abi_result = self._check_abi_compatibility(platform.abi)
            messages.extend(abi_result.messages)
            details["abi"] = abi_result.details
            success = success and abi_result.success

        except Exception as e:
            messages.append(f"Failed to validate target support: {e}")
            success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L3_TOOLCHAIN,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _run_compilation_tests(self, platform: BuildPlatform) -> ValidationResult:
        """Run compilation test suite."""
        messages = []
        details = {}
        success = True

        test_cases = {
            "basic": {
                "source": self._get_test_source("hello.c"),
                "flags": ["-O2", "-Wall"],
                "expected": ["executable", "symbols"]
            },
            "advanced": {
                "source": self._get_test_source("features.cpp"),
                "flags": ["-O3", "-flto"],
                "expected": ["optimizations", "lto"]
            }
        }

        for test_name, test_case in test_cases.items():
            try:
                test_result = self._run_test_case(test_case, platform)
                messages.extend(test_result.messages)
                details[test_name] = test_result.details
                success = success and test_result.success
            except Exception as e:
                messages.append(f"Test case {test_name} failed: {e}")
                success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L3_TOOLCHAIN,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _get_component_version(self, component: str) -> str:
        """Get component version."""
        result = subprocess.run(
            [f"{self.config['toolchain_prefix']}-{component}", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get {component} version")

        version_match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
        if not version_match:
            raise RuntimeError(f"Could not parse {component} version")

        return version_match.group(1)

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare version strings."""
        v1_parts = [int(x) for x in version1.split(".")]
        v2_parts = [int(x) for x in version2.split(".")]

        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            if v1 < v2:
                return -1
            if v1 > v2:
                return 1
        return 0

    def _test_lto_support(self) -> bool:
        """Test LTO support."""
        test_source = """
            int foo() { return 42; }
            int main() { return foo(); }
        """
        return self._compile_test(test_source, ["-flto"])

    def _test_pic_support(self) -> bool:
        """Test PIC support."""
        test_source = """
            int global = 42;
            int* get_global() { return &global; }
        """
        return self._compile_test(test_source, ["-fPIC", "-shared"])

    def _test_relro_support(self) -> bool:
        """Test RELRO support."""
        test_source = "int main() { return 0; }"
        return self._compile_test(test_source, ["-Wl,-z,relro", "-Wl,-z,now"])

    def _test_stack_protection(self) -> bool:
        """Test stack protection support."""
        test_source = """
            char* unsafe(char* buf) {
                char local[16];
                strcpy(local, buf);
                return local;
            }
        """
        return self._compile_test(test_source, ["-fstack-protector-strong"])

    def _test_multilib_support(self) -> bool:
        """Test multilib support."""
        test_source = "int main() { return 0; }"
        return all([
            self._compile_test(test_source, ["-m32"]),
            self._compile_test(test_source, ["-m64"])
        ])

    def _compile_test(self, source: str, flags: List[str]) -> bool:
        """Compile test case."""
        with tempfile.NamedTemporaryFile(suffix=".c") as f:
            f.write(source.encode())
            f.flush()

            result = subprocess.run(
                [
                    f"{self.config['toolchain_prefix']}-gcc",
                    f.name,
                    *flags,
                    "-o", "/dev/null"
                ],
                capture_output=True
            )
            return result.returncode == 0

    def _check_target_triple(self, triple: str) -> ValidationResult:
        """Check target triple support."""
        result = subprocess.run(
            [f"{self.config['toolchain_prefix']}-gcc", "-dumpmachine"],
            capture_output=True,
            text=True
        )
        
        success = result.returncode == 0 and result.stdout.strip() == triple
        return ValidationResult(
            success=success,
            level=ValidationLevel.L3_TOOLCHAIN,
            messages=[
                f"Target triple mismatch: expected {triple}, "
                f"got {result.stdout.strip()}"
            ] if not success else [],
            timestamp=datetime.utcnow(),
            details={"actual": result.stdout.strip(), "expected": triple}
        )

    def _check_target_features(self, features: List[str]) -> ValidationResult:
        """Check target feature support."""
        result = subprocess.run(
            [f"{self.config['toolchain_prefix']}-gcc", "-march=native", "-Q", "--help=target"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return ValidationResult(
                success=False,
                level=ValidationLevel.L3_TOOLCHAIN,
                messages=["Failed to query target features"],
                timestamp=datetime.utcnow(),
                details={"error": result.stderr}
            )

        supported_features = set()
        for line in result.stdout.splitlines():
            if "enabled" in line.lower():
                feature = line.split()[0]
                supported_features.add(feature)

        missing_features = set(features) - supported_features
        return ValidationResult(
            success=len(missing_features) == 0,
            level=ValidationLevel.L3_TOOLCHAIN,
            messages=[f"Missing features: {missing_features}"] if missing_features else [],
            timestamp=datetime.utcnow(),
            details={
                "supported": list(supported_features),
                "required": features,
                "missing": list(missing_features)
            }
        )

    def _check_abi_compatibility(self, abi: str) -> ValidationResult:
        """Check ABI compatibility."""
        result = subprocess.run(
            [f"{self.config['toolchain_prefix']}-gcc", "-print-multiarch"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return ValidationResult(
                success=False,
                level=ValidationLevel.L3_TOOLCHAIN,
                messages=["Failed to query ABI information"],
                timestamp=datetime.utcnow(),
                details={"error": result.stderr}
            )

        current_abi = result.stdout.strip().split("-")[-1]
        success = current_abi == abi
        return ValidationResult(
            success=success,
            level=ValidationLevel.L3_TOOLCHAIN,
            messages=[f"ABI mismatch: expected {abi}, got {current_abi}"] if not success else [],
            timestamp=datetime.utcnow(),
            details={"actual": current_abi, "expected": abi}
        )

    def _get_test_source(self, name: str) -> str:
        """Get test source code."""
        test_sources = {
            "hello.c": """
                #include <stdio.h>
                int main() {
                    printf("Hello, World!\\n");
                    return 0;
                }
            """,
            "features.cpp": """
                int __attribute__((noinline)) foo(int x) { return x * 2; }
                int main() {
                    volatile int result = 0;
                    for (int i = 0; i < 1000; ++i) {
                        result += foo(i);
                    }
                    return result != 0;
                }
            """
        }
        return test_sources.get(name, "int main() { return 0; }")

