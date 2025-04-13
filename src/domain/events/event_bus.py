"""
Event bus for domain events.
Provides a simple way to publish and subscribe to events.
"""

import logging
import asyncio
import inspect
from typing import Dict, List, Type, Callable, Any, TypeVar, Union, Awaitable

logger = logging.getLogger(__name__)

# Type variable for event types
T = TypeVar('T')

class Event:
    """Base class for all domain events"""
    pass

class EventBus:
    """
    Simple event bus for domain events.
    Allows publishing events and subscribing to them.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one event bus exists"""
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the event bus"""
        # Only initialize once (singleton pattern)
        if self._initialized:
            return

        self._handlers: Dict[Type[Event], List[Callable[[Event], None]]] = {}
        self._initialized = True

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]):
        """
        Subscribe to an event.

        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when the event is published
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"ANALYTICS: Subscribed to event: {event_type.__name__} with handler {handler.__name__} from {handler.__module__}")

        # Log all current subscriptions
        for event, handlers in self._handlers.items():
            logger.info(f"ANALYTICS: Current subscriptions for {event.__name__}: {len(handlers)} handlers")
            for h in handlers:
                logger.info(f"ANALYTICS: - Handler: {h.__name__} from {h.__module__}")

    def publish(self, event: Event):
        """
        Publish an event.

        Args:
            event: Event to publish
        """
        event_type = type(event)
        logger.info(f"ANALYTICS: Publishing event: {event_type.__name__}")

        if event_type in self._handlers:
            logger.info(f"ANALYTICS: Found {len(self._handlers[event_type])} handlers for event {event_type.__name__}")
            for handler in self._handlers[event_type]:
                try:
                    logger.info(f"ANALYTICS: Calling handler {handler.__name__} from {handler.__module__} for event {event_type.__name__}")

                    # Check if the handler is a coroutine function
                    if inspect.iscoroutinefunction(handler):
                        # Create a task to run the coroutine
                        # This prevents the "coroutine was never awaited" warning
                        # but doesn't block the current thread
                        task = asyncio.create_task(handler(event))
                        logger.info(f"ANALYTICS: Created task {task.get_name()} for async handler {handler.__name__}")
                    else:
                        # Regular function, just call it
                        handler(event)
                        logger.info(f"ANALYTICS: Called sync handler {handler.__name__} successfully")
                except Exception as e:
                    logger.error(f"ANALYTICS: Error in event handler {handler.__name__} for {event_type.__name__}: {e}", exc_info=True)
        else:
            logger.warning(f"ANALYTICS: No handlers found for event {event_type.__name__}")

        logger.info(f"ANALYTICS: Finished publishing event: {event_type.__name__}")

    def unsubscribe(self, event_type: Type[Event], handler: Callable[[Event], None]):
        """
        Unsubscribe from an event.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove
        """
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
                logger.debug(f"Unsubscribed from event: {event_type.__name__}")

    def clear_handlers(self, event_type: Type[Event] = None):
        """
        Clear all handlers for an event type or all handlers if no type is specified.

        Args:
            event_type: Type of event to clear handlers for, or None to clear all
        """
        if event_type:
            if event_type in self._handlers:
                self._handlers[event_type] = []
                logger.debug(f"Cleared handlers for event: {event_type.__name__}")
        else:
            self._handlers = {}
            logger.debug("Cleared all event handlers")
