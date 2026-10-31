# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Monkeypatching of the OpenCensus ``Tracer`` class.

The two functions here are the whole public surface of the shim. ``install_shim`` replaces the
``tracer`` attribute of ``opencensus.trace.tracer.Tracer`` with a property, so that an application
already instrumented with OpenCensus records through the OpenTelemetry API without any of its
OpenCensus calls being changed. ``uninstall_shim`` removes that property again.

The patch is applied to the OpenCensus class itself rather than to its instances, so it reaches
OpenCensus tracers that already exist as well as ones created afterwards.
"""

from functools import lru_cache
from logging import getLogger

from opencensus.trace.span_context import SpanContext
from opencensus.trace.tracer import Tracer
from opencensus.trace.tracers.noop_tracer import NoopTracer

from opentelemetry import trace
from opentelemetry.shim.opencensus._shim_tracer import ShimTracer
from opentelemetry.shim.opencensus.version import __version__

_logger = getLogger(__name__)


def install_shim(
    tracer_provider: trace.TracerProvider | None = None,
) -> None:
    """Patch the OpenCensus ``Tracer`` class so that OpenCensus spans are recorded by OpenTelemetry.

    ``opencensus.trace.tracer.Tracer.__init__`` assigns ``self.tracer`` either a ``NoopTracer`` or
    a ``ContextTracer``, depending on the sampling decision. This function replaces
    ``Tracer.tracer`` with a property whose getter returns a shim tracer instead, and whose setter
    discards the value the OpenCensus constructor assigns. Because the property lives on the class,
    every OpenCensus ``Tracer`` uses a shim tracer from then on, including instances created before
    this call.

    The shim tracer returned depends on the ``span_context`` attribute of the OpenCensus ``Tracer``
    being read, which is how OpenCensus instrumentations hand propagated trace context to the
    tracer. One shim tracer is built per OpenCensus ``SpanContext`` and kept in a cache of the 128
    most recently used ones.

    Calling this function a second time installs a fresh property and a fresh cache. The shim
    tracers of the previous call are then reachable only from the shim spans that hold a reference
    to one, which every shim span keeps for its whole lifetime, ended or not.

    Args:
        tracer_provider: The :class:`opentelemetry.trace.TracerProvider` to obtain the tracer from.
            When ``None``, the tracer comes from the global tracer provider. If no global provider
            has been set at the moment of this call, and ``OTEL_PYTHON_TRACER_PROVIDER`` is absent
            from the environment, the tracer is a proxy that looks the global provider up on every
            span start and keeps the first real one it finds, so a provider set after the shim is
            installed is still honoured. A span started before that provider is set is
            non-recording, and it does not stop later spans from being recorded. When
            ``OTEL_PYTHON_TRACER_PROVIDER`` is set, and names an installed entry point of the
            ``opentelemetry_tracer_provider`` group, this call loads the provider it names and
            makes it the global one, so the tracer is a real tracer from the start and a later
            ``opentelemetry.trace.set_tracer_provider`` is refused with a warning.

    Raises:
        StopIteration: When ``tracer_provider`` is ``None``, no global provider has been set, and
            ``OTEL_PYTHON_TRACER_PROVIDER`` is present in the environment with a value that matches
            no installed entry point, the empty string included. Nothing is patched in that case,
            so every OpenCensus ``Tracer`` keeps recording through OpenCensus.
    """
    otel_tracer = trace.get_tracer(
        "opentelemetry-opencensus-shim",
        __version__,
        tracer_provider=tracer_provider,
    )

    @lru_cache
    def cached_shim_tracer(span_context: SpanContext) -> ShimTracer:
        """Return the shim tracer for one OpenCensus ``SpanContext``, building it on first use.

        The OpenCensus ``SpanContext`` class defines neither ``__eq__`` nor ``__hash__``, so the
        cache keys on object identity: two OpenCensus ``Tracer`` instances share a shim tracer only
        when they share the very same ``SpanContext`` object.

        The wrapped OpenCensus tracer is a ``NoopTracer``, so the OpenCensus side of the shim
        tracer records nothing and only the OpenTelemetry span carries the data.

        Args:
            span_context: The OpenCensus ``SpanContext`` the shim tracer serves. It becomes the
                parent of any span the shim tracer starts while the OpenTelemetry context holds no
                current span, provided it carries a span ID. The one an OpenCensus ``Tracer``
                builds for itself when given none has a random trace ID and no span ID, and a span
                started under that is a root span with a trace ID of its own.

        Returns:
            The shim tracer bound to ``span_context``.
        """
        return ShimTracer(
            NoopTracer(),
            oc_span_context=span_context,
            otel_tracer=otel_tracer,
        )

    def fget_tracer(self: Tracer) -> ShimTracer:
        """Getter of the patched ``tracer`` property of the OpenCensus ``Tracer`` class.

        The shim tracer is selected by the ``span_context`` attribute of the OpenCensus ``Tracer``
        the attribute is read on, so a request whose propagated trace context was written into
        that attribute starts spans under the right parent.

        Returns:
            The shim tracer for the ``span_context`` of this OpenCensus ``Tracer``.
        """
        # self.span_context is how instrumentations pass propagated context into OpenCensus e.g.
        # https://github.com/census-instrumentation/opencensus-python/blob/fd064f438c5e490d25b004ee2545be55d2e28679/contrib/opencensus-ext-flask/opencensus/ext/flask/flask_middleware.py#L147-L153
        return cached_shim_tracer(self.span_context)

    def fset_tracer(self, value) -> None:
        """Setter of the patched ``tracer`` property of the OpenCensus ``Tracer`` class.

        ``opencensus.trace.tracer.Tracer.__init__`` assigns ``self.tracer`` unconditionally, so the
        property needs a setter for OpenCensus tracer construction to work at all. The assignment
        is dropped rather than stored, which is what keeps the shim in place.

        Args:
            value: The OpenCensus tracer the caller is trying to install. It is discarded.
        """
        # ignore attempts to set the value

    # Tracer's constructor sets self.tracer to either a NoopTracer or ContextTracer depending
    # on sampler:
    # https://github.com/census-instrumentation/opencensus-python/blob/2e08df591b507612b3968be8c2538dedbf8fab37/opencensus/trace/tracer.py#L63.
    # We monkeypatch Tracer.tracer with a property to return a shim instance instead. This
    # makes all instances of Tracer (even those already created) use a ShimTracer.
    Tracer.tracer = property(fget_tracer, fset_tracer)
    _logger.info("Installed OpenCensus shim")


def uninstall_shim() -> None:
    """Remove the ``tracer`` property from the OpenCensus ``Tracer`` class.

    An OpenCensus ``Tracer`` created after this call has its OpenCensus sampling decision honoured
    again, because its constructor can store a real OpenCensus tracer on the instance once more.
    The sampler a ``Tracer`` built with no sampler uses is
    ``opencensus.trace.samplers.ProbabilitySampler`` at a rate of 0.0001, so what the constructor
    usually stores is an ``opencensus.trace.tracers.noop_tracer.NoopTracer``, which records
    nothing.

    An OpenCensus ``Tracer`` created while the shim was installed is left with no ``tracer``
    attribute at all: the property setter dropped the value its constructor assigned, and there is
    now no class attribute to fall back on, so reading ``tracer`` on it raises ``AttributeError``.

    Does nothing when the shim is not installed. The plain OpenCensus ``Tracer`` class carries no
    ``tracer`` class attribute, so the presence of one is what the check looks for.
    """
    if hasattr(Tracer, "tracer"):
        del Tracer.tracer
