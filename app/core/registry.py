"""Application service registry — dependency inversion / IoC container.

All concrete service classes are imported and registered **once**, in
``main.py`` (the composition root).  Every other module depends only on the
interface (Protocol) and resolves the implementation via ``registry.get()``.

Usage
-----
Composition root (``main.py``) registers concrete implementations::

    from core.registry import registry
    from services.protocols import ILogParserService
    from services.log_parser_service import LogParserService

    registry.register(ILogParserService, LogParserService())

All other callsites depend only on the interface — no concrete import::

    from core.registry import registry
    from services.protocols import ILogParserService

    parser = registry.get(ILogParserService)
    parser.start("/path/to/log")

Testing
-------
Swap implementations without touching production code::

    registry.register(ILogParserService, FakeLogParserService())
"""
from __future__ import annotations

import logging
from typing import Any, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceRegistry:
    """Type-keyed IoC container.

    Services are keyed by their **interface type** (a Protocol or ABC), not
    by the concrete class.  This enforces that callsites depend on
    abstractions rather than implementations.
    """

    def __init__(self) -> None:
        self._services: dict[type, Any] = {}

    def register(self, interface: type[T], impl: T) -> None:
        """Register *impl* as the concrete provider of *interface*.

        Re-registering replaces the existing binding (useful for tests).
        """
        if interface in self._services:
            log.warning(
                "Re-registering %s — previous implementation replaced.",
                interface.__name__,
            )
        self._services[interface] = impl
        log.debug("Registered: %s → %s", interface.__name__, type(impl).__name__)

    def get(self, interface: type[T]) -> T:
        """Resolve the registered implementation for *interface*.

        Raises
        ------
        KeyError
            If *interface* has not been registered yet.  This is a
            programming error — check that ``main.py`` registers all
            services before they are resolved.
        """
        impl: T | None = self._services.get(interface)  # type: ignore[assignment]
        if impl is None:
            raise KeyError(
                f"No service registered for '{interface.__name__}'. "
                "Register it in the composition root (app/main.py) before use."
            )
        return impl

    def is_registered(self, interface: type) -> bool:
        """Return ``True`` if *interface* has a registered implementation."""
        return interface in self._services


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import this instance everywhere — never instantiate ServiceRegistry directly.
registry: ServiceRegistry = ServiceRegistry()
