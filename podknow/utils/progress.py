"""
Centralized progress bar management for PodKnow.

This module provides a simple context-based approach to managing progress bars,
eliminating the need for suppress_progress flags throughout the codebase.
"""

from contextlib import contextmanager
from typing import Optional
import threading


class ProgressContext:
    """
    Centralized progress bar context manager.

    This class provides a thread-safe way to track whether progress bars
    should be displayed. Services check this context instead of receiving
    suppress_progress parameters.

    Usage:
        # In workflow (suppress nested progress):
        with ProgressContext.suppress():
            service.process_data()  # No progress bars shown

        # In service:
        if ProgressContext.should_show_progress():
            # Show progress bar
            pass
    """

    _local = threading.local()

    @classmethod
    def should_show_progress(cls) -> bool:
        """
        Check if progress bars should be shown.

        Returns:
            True if progress should be shown, False if suppressed
        """
        return not getattr(cls._local, 'suppressed', False)

    @classmethod
    @contextmanager
    def suppress(cls):
        """
        Context manager to temporarily suppress progress bars.

        This is useful when orchestrating multiple operations and you want
        to show only the outer progress indicator.

        Example:
            with ProgressContext.suppress():
                # Progress bars in this block will be suppressed
                service.operation()
        """
        previous_state = getattr(cls._local, 'suppressed', False)
        cls._local.suppressed = True
        try:
            yield
        finally:
            cls._local.suppressed = previous_state

    @classmethod
    @contextmanager
    def enable(cls):
        """
        Context manager to explicitly enable progress bars.

        Example:
            with ProgressContext.enable():
                # Progress bars in this block will be shown
                service.operation()
        """
        previous_state = getattr(cls._local, 'suppressed', False)
        cls._local.suppressed = False
        try:
            yield
        finally:
            cls._local.suppressed = previous_state
