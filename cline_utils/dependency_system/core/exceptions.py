"""
Custom exception classes for the dependency tracking system.
"""

class DependencySystemError(Exception):
    """Base class for dependency system exceptions."""
    pass

class TrackerError(DependencySystemError):
    """Exception related to tracker operations."""
    pass

class EmbeddingError(DependencySystemError):
    """Exception related to embedding operations."""
    pass

class AnalysisError(DependencySystemError):
    """Exception related to analysis operations."""
    pass

class ConfigurationError(DependencySystemError):
    """Exception related to configuration errors."""
    pass

class CacheError(DependencySystemError):
    """Exception related to cache operations."""
    pass