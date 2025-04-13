"""
Dependency injection container for the application.
Provides a simple way to register and resolve dependencies.
"""

import logging
from typing import Dict, Any, Type, TypeVar, Optional, Callable

logger = logging.getLogger(__name__)

T = TypeVar('T')

class DIContainer:
    """
    Simple dependency injection container.
    Allows registering and resolving services by type.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one container exists"""
        if cls._instance is None:
            cls._instance = super(DIContainer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the container"""
        # Only initialize once (singleton pattern)
        if self._initialized:
            return
            
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._initialized = True
        
    def register(self, service_type: Type[T], implementation: T):
        """
        Register a service implementation.
        
        Args:
            service_type: Type of the service
            implementation: Implementation of the service
        """
        self._services[service_type] = implementation
        logger.debug(f"Registered service: {service_type.__name__}")
        
    def register_factory(self, service_type: Type[T], factory: Callable[[], T]):
        """
        Register a factory function for a service.
        
        Args:
            service_type: Type of the service
            factory: Factory function that creates the service
        """
        self._factories[service_type] = factory
        logger.debug(f"Registered factory for service: {service_type.__name__}")
        
    def resolve(self, service_type: Type[T]) -> Optional[T]:
        """
        Resolve a service implementation.
        
        Args:
            service_type: Type of the service to resolve
            
        Returns:
            The service implementation or None if not registered
        """
        # Check if we have a direct implementation
        if service_type in self._services:
            return self._services[service_type]
            
        # Check if we have a factory
        if service_type in self._factories:
            # Create the service using the factory
            implementation = self._factories[service_type]()
            # Cache the implementation
            self._services[service_type] = implementation
            return implementation
            
        logger.warning(f"Service not registered: {service_type.__name__}")
        return None
