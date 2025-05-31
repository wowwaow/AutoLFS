"""Custom exceptions for the LFS wrapper system."""

class LFSError(Exception):
    """Base exception class for LFS-related errors."""
    
    def __init__(self, message: str = None, *args, **kwargs):
        """Initialize the exception with an optional message."""
        self.message = message or "An error occurred in the LFS wrapper system"
        super().__init__(self.message, *args)


class LFSConfigError(LFSError):
    """Exception raised for configuration-related errors."""
    
    def __init__(self, message: str = None, *args, **kwargs):
        """Initialize the configuration error."""
        self.message = message or "Configuration error occurred"
        super().__init__(self.message, *args)


class LFSEnvironmentError(LFSError):
    """Exception raised for environment-related errors."""
    
    def __init__(self, message: str = None, *args, **kwargs):
        """Initialize the environment error."""
        self.message = message or "Environment setup error occurred"
        super().__init__(self.message, *args)


class LFSBuildError(LFSError):
    """Exception raised for build-related errors."""
    
    def __init__(self, message: str = None, build_step: str = None, *args, **kwargs):
        """Initialize the build error."""
        self.build_step = build_step
        self.message = f"Build error in step '{build_step}': {message}" if build_step else message or "Build error occurred"
        super().__init__(self.message, *args)


class LFSDependencyError(LFSError):
    """Exception raised for dependency-related errors."""
    
    def __init__(self, message: str = None, dependency: str = None, *args, **kwargs):
        """Initialize the dependency error."""
        self.dependency = dependency
        self.message = f"Dependency error for '{dependency}': {message}" if dependency else message or "Dependency error occurred"
        super().__init__(self.message, *args)


class LFSValidationError(LFSError):
    """Exception raised for validation-related errors."""
    
    def __init__(self, message: str = None, validation_type: str = None, *args, **kwargs):
        """Initialize the validation error."""
        self.validation_type = validation_type
        self.message = f"Validation error ({validation_type}): {message}" if validation_type else message or "Validation error occurred"
        super().__init__(self.message, *args)


class LFSScriptError(LFSError):
    """Exception raised for script-related errors."""
    
    def __init__(self, message: str = None, script_name: str = None, *args, **kwargs):
        """Initialize the script error."""
        self.script_name = script_name
        self.message = f"Script error in '{script_name}': {message}" if script_name else message or "Script error occurred"
        super().__init__(self.message, *args)


class LFSPermissionError(LFSError):
    """Exception raised for permission-related errors."""
    
    def __init__(self, message: str = None, path: str = None, *args, **kwargs):
        """Initialize the permission error."""
        self.path = path
        self.message = f"Permission error for '{path}': {message}" if path else message or "Permission error occurred"
        super().__init__(self.message, *args)


class LFSResourceError(LFSError):
    """Exception raised for resource-related errors."""
    
    def __init__(self, message: str = None, resource_type: str = None, *args, **kwargs):
        """Initialize the resource error."""
        self.resource_type = resource_type
        self.message = f"Resource error ({resource_type}): {message}" if resource_type else message or "Resource error occurred"
        super().__init__(self.message, *args)


class LFSTimeoutError(LFSError):
    """Exception raised for timeout-related errors."""
    
    def __init__(self, message: str = None, timeout: float = None, *args, **kwargs):
        """Initialize the timeout error."""
        self.timeout = timeout
        self.message = f"Operation timed out after {timeout}s: {message}" if timeout else message or "Operation timed out"
        super().__init__(self.message, *args)
