"""Custom exceptions for SOLVENS CORE."""


class SolvensError(Exception):
    """Base exception for all SOLVENS CORE errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(SolvensError):
    """Raised when there's a configuration issue."""
    pass


class ProviderError(SolvensError):
    """Raised when a provider operation fails."""
    
    def __init__(
        self,
        message: str,
        provider: str | None = None,
        status_code: int | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.provider = provider
        self.status_code = status_code


class ProviderNotAvailableError(ProviderError):
    """Raised when a provider is not available."""
    pass


class ProviderAuthenticationError(ProviderError):
    """Raised when provider authentication fails."""
    pass


class ProviderRateLimitError(ProviderError):
    """Raised when provider rate limit is exceeded."""
    pass


class TaskError(SolvensError):
    """Raised when a task operation fails."""
    
    def __init__(self, message: str, task_id: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.task_id = task_id


class TaskNotFoundError(TaskError):
    """Raised when a task is not found."""
    pass


class TaskTimeoutError(TaskError):
    """Raised when a task times out."""
    pass


class TaskCancelledError(TaskError):
    """Raised when a task is cancelled."""
    pass


class RouterError(SolvensError):
    """Raised when routing fails."""
    
    def __init__(self, message: str, capability: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.capability = capability


class NoProviderAvailableError(RouterError):
    """Raised when no provider is available for a capability."""
    pass


class PluginError(SolvensError):
    """Raised when a plugin operation fails."""
    
    def __init__(self, message: str, plugin: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.plugin = plugin


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""
    pass


class PluginNotFoundError(PluginError):
    """Raised when a plugin is not found."""
    pass


class MemoryError(SolvensError):
    """Raised when a memory operation fails."""
    pass


class ValidationError(SolvensError):
    """Raised when validation fails."""
    pass


class OrchestratorError(SolvensError):
    """Raised when orchestrator operation fails."""
    pass
