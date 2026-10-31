# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Global text map propagator construction from declarative configuration.

The propagator is the one global that declarative configuration always
sets, even when the configuration file has no ``propagator`` section. A
missing tracer, meter or logger provider leaves the corresponding global
alone; a missing propagator installs an empty composite that propagates
nothing. That is deliberate: the SDK otherwise defaults to W3C trace
context plus baggage, and a configuration file is meant to describe the
whole configuration rather than add to a default.

In a ``composite`` entry, ``tracecontext`` and ``baggage`` are
constructed directly from the API package, and every other name,
declared in the schema or not, is loaded from the
``opentelemetry_propagator`` entry point group. In ``composite_list``
every name goes through that entry point group, ``tracecontext`` and
``baggage`` included. Either way, a propagator the schema names but no
installed package provides is a configuration error rather than a
silently missing header.
"""

from __future__ import annotations

from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.configuration._common import load_entry_point
from opentelemetry.configuration.models import (
    Propagator as PropagatorConfig,
)
from opentelemetry.configuration.models import (
    TextMapPropagator as TextMapPropagatorConfig,
)
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)

# Propagators bundled with the SDK — no entry point lookup needed.
_PROPAGATOR_REGISTRY: dict[str, type[TextMapPropagator]] = {
    "tracecontext": TraceContextTextMapPropagator,
    "baggage": W3CBaggagePropagator,
}


def _propagators_from_textmap_config(
    config: TextMapPropagatorConfig,
) -> list[TextMapPropagator]:
    """Resolve a TextMapPropagator config to a list of propagators.

    Known names (tracecontext, baggage) are bootstrapped directly via
    _PROPAGATOR_REGISTRY. Known schema fields not in the registry (b3, b3multi)
    and unknown plugin names from additional_properties are loaded via the
    ``opentelemetry_propagator`` entry point group.

    The schema permits one propagator per entry, with ``minProperties`` and
    ``maxProperties`` both 1 on ``TextMapPropagator``. If several fields are
    set, which is possible only when schema validation was bypassed, every
    one of them is returned.

    Args:
        config: One entry of the ``composite`` list from the propagator
            configuration.

    Returns:
        The propagators the entry selects, in a fixed order: tracecontext,
        then baggage, then b3, then b3multi, then the plugin names in the
        order they were written. An entry that selects nothing gives an
        empty list.

    Raises:
        ConfigurationError: If a name has to be loaded from the entry point
            group and no installed package registers it.
    """
    result: list[TextMapPropagator] = []
    for name, cls in _PROPAGATOR_REGISTRY.items():
        if getattr(config, name, None) is not None:
            result.append(cls())

    # Known schema fields not in registry (b3, b3multi) — loaded via entry point
    for name in ("b3", "b3multi"):
        if getattr(config, name, None) is not None:
            result.append(load_entry_point("opentelemetry_propagator", name)())

    # Plugin propagators from additional_properties
    for name, plugin_config in config.additional_properties.items():
        result.append(load_entry_point("opentelemetry_propagator", name)(**(plugin_config or {})))

    return result


def create_propagator(
    config: PropagatorConfig | None,
) -> CompositePropagator:
    """Create a CompositePropagator from declarative config.

    If config is None or has no propagators defined, returns an empty
    CompositePropagator (no-op), ensuring "what you see is what you get"
    semantics — the env-var-based default propagators are not used.

    A propagator is kept once per class, so naming the same propagator in
    both ``composite`` and ``composite_list`` injects its headers once. The
    first instance built wins, which means an instance that ``composite``
    constructed with options is not replaced by a bare one from
    ``composite_list``.

    In ``composite_list``, an empty name and the name ``none`` in any case
    are skipped, so ``composite_list: none`` yields a propagator that
    propagates nothing.

    Args:
        config: Propagator config from the parsed config file, or None.

    Returns:
        A CompositePropagator wrapping all configured propagators, in the
        order they were first seen: the ``composite`` entries first, then
        the ``composite_list`` names.

    Raises:
        ConfigurationError: If a name has to be loaded from the
            ``opentelemetry_propagator`` entry point group and no installed
            package registers it.
    """
    if config is None:
        return CompositePropagator([])

    propagators: dict[type[TextMapPropagator], TextMapPropagator] = {}

    # Process structured composite list
    if config.composite:
        for entry in config.composite:
            for propagator in _propagators_from_textmap_config(entry):
                propagators.setdefault(type(propagator), propagator)

    # Process composite_list (comma-separated propagator names via entry_points)
    if config.composite_list:
        for name in config.composite_list.split(","):
            name = name.strip()
            if not name or name.lower() == "none":
                continue
            propagator = load_entry_point("opentelemetry_propagator", name)()
            propagators.setdefault(type(propagator), propagator)

    return CompositePropagator(list(propagators.values()))


def configure_propagator(config: PropagatorConfig | None) -> None:
    """Configure the global text map propagator from declarative config.

    Always calls set_global_textmap to override any defaults (including the
    env-var-based tracecontext+baggage default set by the SDK).

    This is the only ``configure_*`` function that sets its global when the
    corresponding configuration section is absent. The other three return
    without touching theirs.

    Args:
        config: Propagator config from the parsed config file, or None.
            ``None`` installs an empty composite rather than leaving the
            SDK default in place.

    Raises:
        ConfigurationError: If a configured propagator name cannot be loaded.
            The global is left as it was, because the composite is built
            before it is set.
    """
    set_global_textmap(create_propagator(config))
