# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The OpenCensus tracer interface implemented over the OpenTelemetry tracing API.

``ShimTracer`` presents the method set of ``opencensus.trace.tracers.base.Tracer`` and creates an
OpenTelemetry span for every OpenCensus span it is asked for. ``install_shim`` puts one of these in
place of the ``tracer`` attribute of every OpenCensus ``Tracer``.

This module also holds the two pieces of context translation the shim needs. The current shim span
is kept in the OpenTelemetry context under a key of the shim's own, because what OpenCensus callers
expect back is the shim span and not the OpenTelemetry span. An OpenCensus ``SpanContext`` is
turned into an OpenTelemetry context whose current span is a non-recording OpenTelemetry span with
the same identifiers, which is how trace context that an OpenCensus instrumentation extracted from
an incoming request becomes the parent of an OpenTelemetry span.
"""

import logging

import wrapt
from opencensus.trace import execution_context
from opencensus.trace.blank_span import BlankSpan
from opencensus.trace.span_context import SpanContext
from opencensus.trace.tracers.base import Tracer as BaseTracer
from opencensus.trace.tracestate import Tracestate

from opentelemetry import context, trace
from opentelemetry.shim.opencensus._shim_span import ShimSpan

_logger = logging.getLogger(__name__)

_SHIM_SPAN_KEY = context.create_key("opencensus-shim-span-key")
_SAMPLED = trace.TraceFlags(trace.TraceFlags.SAMPLED)


def set_shim_span_in_context(span: ShimSpan, ctx: context.Context) -> context.Context:
    """Record a shim span as the current one in an OpenTelemetry context.

    The shim keeps a context key separate from the one OpenTelemetry uses for the current span,
    because an OpenCensus caller asking for the current span has to be handed the shim span, which
    carries the OpenCensus method set, rather than the OpenTelemetry span underneath it.

    Args:
        span: The shim span to record as the current one.
        ctx: The OpenTelemetry context to build on. It is not modified.

    Returns:
        A new OpenTelemetry context, holding everything ``ctx`` holds plus ``span`` under the key
        of the shim.
    """
    return context.set_value(_SHIM_SPAN_KEY, span, ctx)


def get_shim_span_in_context() -> ShimSpan:
    """Return the shim span recorded as current in the OpenTelemetry context.

    Returns:
        The shim span that the most recent ``ShimTracer.start_span`` attached to the context, or
        ``None`` when no shim span is current. ``None`` is what a caller sees before the shim has
        started any span, and after the last one has been ended by ``ShimTracer.end_span`` or by
        leaving its ``with`` block, those being the two ways that restore the context. Ending a
        shim span with ``ShimSpan.finish`` alone leaves it under the key of the shim, so it keeps
        being reported after it has ended. Starting a span straight through the OpenTelemetry API
        does not produce ``None`` either: it leaves the key of the shim in place, so a shim span
        that encloses it is still the one reported.
    """
    return context.get_value(_SHIM_SPAN_KEY)


def set_oc_span_in_context(oc_span_context: SpanContext, ctx: context.Context) -> context.Context:
    """Returns an OTel context with oc_span_context set as the current span, when it has a span ID.

    The OpenCensus identifiers are hexadecimal strings and the OpenTelemetry ones are integers, so
    both are parsed. The resulting OpenTelemetry span context is wrapped in a non-recording span,
    which makes it usable as a parent without producing a span of its own.

    ``opencensus.trace.tracer.Tracer`` builds a ``SpanContext`` with a fresh random trace ID and a
    ``None`` span ID when it is given none. OpenTelemetry rejects that as invalid, so ``ctx`` is
    returned untouched in that case and the span started next becomes a root span.

    The ``tracestate`` of ``oc_span_context`` is carried over only when it really is an OpenCensus
    ``Tracestate``. The OpenCensus ``SpanContext`` constructor stores whatever it is given without
    checking the type, so anything else is dropped. The sampled flag is set only when the
    OpenCensus trace options have tracing enabled.

    Args:
        oc_span_context: The OpenCensus ``SpanContext`` to translate.
        ctx: The OpenTelemetry context returned unchanged when ``oc_span_context`` has no span ID.
            It is not read on the other path: the context returned there is built on the context
            current at the time of the call. The only caller in this package,
            ``ShimTracer.start_span``, passes the current context, and so does every call in
            ``tests/test_shim.py``, so the two agree.

    Returns:
        An OpenTelemetry context whose current span is the non-recording span built from
        ``oc_span_context``, or ``ctx`` itself when ``oc_span_context`` has no span ID.
    """

    # If no SpanContext is passed to the opencensus.trace.tracer.Tracer, it creates a new one
    # with a random trace ID and a None span ID to be the parent:
    # https://github.com/census-instrumentation/opencensus-python/blob/2e08df591b507612b3968be8c2538dedbf8fab37/opencensus/trace/tracer.py#L47.
    #
    # OpenTelemetry considers this an invalid SpanContext and will ignore it, so we can just
    # return early
    if oc_span_context.span_id is None:
        return ctx

    trace_id = int(oc_span_context.trace_id, 16)
    span_id = int(oc_span_context.span_id, 16)
    is_remote = oc_span_context.from_header
    trace_flags = _SAMPLED if oc_span_context.trace_options.get_enabled() else None
    trace_state = (
        trace.TraceState(tuple(oc_span_context.tracestate.items()))
        # OC SpanContext does not validate this type
        if isinstance(oc_span_context.tracestate, Tracestate)
        else None
    )

    return trace.set_span_in_context(
        trace.NonRecordingSpan(
            trace.SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                is_remote=is_remote,
                trace_flags=trace_flags,
                trace_state=trace_state,
            )
        )
    )


# pylint: disable=abstract-method
class ShimTracer(wrapt.ObjectProxy):
    """The OpenCensus tracer interface, backed by an OpenTelemetry tracer.

    ``install_shim`` puts an instance of this class in place of the ``tracer`` attribute of every
    OpenCensus ``Tracer``, so OpenCensus code that calls ``start_span``, ``end_span`` or
    ``current_span`` reaches these methods. Being a ``wrapt.ObjectProxy``, anything not overridden
    here is handled by the wrapped OpenCensus tracer instead.

    ``finish`` is one of those: it is not overridden, so it reaches the wrapped OpenCensus tracer
    and ends no OpenTelemetry span. Overriding it would mean keeping a list of every span the shim
    tracer has created.

    Args:
        wrapped: The OpenCensus tracer to proxy. ``install_shim`` passes an
            ``opencensus.trace.tracers.noop_tracer.NoopTracer``, so the OpenCensus side records
            nothing.
        oc_span_context: The OpenCensus ``SpanContext`` of the OpenCensus ``Tracer`` this instance
            serves. It supplies the parent of a span started while the OpenTelemetry context holds
            no current span, provided it carries a span ID. The one an OpenCensus ``Tracer`` builds
            for itself when given none has a random trace ID and no span ID, and a span started
            under that is a root span with a trace ID of its own.
        otel_tracer: The OpenTelemetry tracer that creates the spans.
    """

    def __init__(
        self,
        wrapped: BaseTracer,
        *,
        oc_span_context: SpanContext,
        otel_tracer: trace.Tracer,
    ) -> None:
        """The parameters are documented on the class docstring."""
        super().__init__(wrapped)
        self._self_oc_span_context = oc_span_context
        self._self_otel_tracer = otel_tracer

    # For now, finish() is not implemented by the shim. It would require keeping a list of all
    # spans created so they can all be finished.
    # def finish(self):
    #    """End spans and send to reporter."""

    def span(self, name="span"):
        """Start a span and make it current, doing exactly what ``start_span`` does.

        The OpenCensus tracer interface carries both names, so the shim carries both too.

        Args:
            name: The name given to the OpenTelemetry span.

        Returns:
            The started shim span.
        """
        return self.start_span(name=name)

    def start_span(self, name="span"):
        """Start an OpenTelemetry span, wrap it in a shim span, and make it current.

        The parent is the span current in the OpenTelemetry context. When there is none, the
        OpenCensus ``SpanContext`` given at construction supplies the parent instead, which is how
        trace context that an OpenCensus instrumentation extracted from an incoming request is
        honoured. That only happens when the ``SpanContext`` carries a span ID. The one an
        OpenCensus ``Tracer`` builds for itself when given none does not, so an application that
        passes no propagated context gets a root span with a trace ID unrelated to the OpenCensus
        one.

        The shim span is attached to the OpenTelemetry context and also set as the current span of
        the OpenCensus ``execution_context``, matching what
        ``opencensus.trace.tracers.context_tracer.ContextTracer`` does. The token needed to detach
        it is stored on the shim span itself, so the context is restored only by ``end_span`` or by
        leaving the shim span's ``with`` block. A caller that does neither leaves the shim span
        attached to the context, and the OpenTelemetry span is then ended only if that caller calls
        ``finish`` on the shim span, which ends it without restoring the context.

        Args:
            name: The name given both to the OpenTelemetry span and to the OpenCensus
                ``BlankSpan`` that the returned shim span wraps.

        Returns:
            The shim span wrapping the OpenTelemetry span that was started.
        """
        parent_ctx = context.get_current()
        # If there is no current span in context, use the one provided to the OC Tracer at
        # creation time
        if trace.get_current_span(parent_ctx) is trace.INVALID_SPAN:
            parent_ctx = set_oc_span_in_context(self._self_oc_span_context, parent_ctx)

        span = self._self_otel_tracer.start_span(name, context=parent_ctx)
        shim_span = ShimSpan(
            BlankSpan(name=name, context_tracer=self),
            otel_span=span,
            shim_tracer=self,
        )

        ctx = trace.set_span_in_context(span)
        ctx = set_shim_span_in_context(shim_span, ctx)

        # OpenCensus's ContextTracer calls execution_context.set_current_span(span) which is
        # equivalent to the below. This can cause context to leak but is equivalent.
        # pylint: disable=protected-access
        shim_span._self_token = context.attach(ctx)
        # Also set it in OC's context, equivalent to
        # https://github.com/census-instrumentation/opencensus-python/blob/2e08df591b507612b3968be8c2538dedbf8fab37/opencensus/trace/tracers/context_tracer.py#L94
        execution_context.set_current_span(shim_span)
        return shim_span

    def end_span(self):
        """Finishes the current span in the context and restores the context from before the
        span was started.

        The OpenCensus ``execution_context`` is reset as well, to whichever shim span becomes
        current once the OpenTelemetry context has been restored.

        When no shim span is current, a warning is logged and nothing is ended. That happens when
        this is called more times than ``start_span``, or from a thread other than the one that
        started the span, since the OpenTelemetry context is per thread.
        """
        span = self.current_span()
        if not span:
            _logger.warning("No active span, cannot do end_span.")
            return

        span.finish()

        # pylint: disable=protected-access
        context.detach(span._self_token)
        # Also reset the OC execution_context, equivalent to
        # https://github.com/census-instrumentation/opencensus-python/blob/2e08df591b507612b3968be8c2538dedbf8fab37/opencensus/trace/tracers/context_tracer.py#L114-L117
        execution_context.set_current_span(self.current_span())

    # pylint: disable=no-self-use
    def current_span(self):
        """Return the shim span current in the OpenTelemetry context.

        The answer comes from the OpenTelemetry context and not from the wrapped OpenCensus
        tracer, so it is shared with any other shim tracer in the same context. A span started
        straight through the OpenTelemetry API is not reported here, because only
        ``ShimTracer.start_span`` writes the key the lookup reads.

        Returns:
            The current shim span, or ``None`` when no shim span is current.
        """
        return get_shim_span_in_context()

    def add_attribute_to_current_span(self, attribute_key, attribute_value):
        """Set an attribute on the OpenTelemetry span behind the current shim span.

        Args:
            attribute_key: The name of the attribute.
            attribute_value: The value of the attribute. Nothing is converted here, so an
                OpenTelemetry SDK span is what cleans it. A value that is not a ``bool``, ``str``,
                ``None``, ``bytes``, ``int``, ``float``, or a mapping or sequence of those, is
                logged as a warning and then passed through ``str``, or replaced by ``None`` when
                its type defines neither ``__str__`` nor ``__repr__``. The attribute key survives
                either way, so a bad value shows up on the span rather than disappearing from it.
                A non-recording span, which is what the shim holds while no OpenTelemetry tracer
                provider has been set, drops the attribute with no warning at all.

        Raises:
            AttributeError: When no shim span is current in the OpenTelemetry context, since
                ``current_span`` then returns ``None``.
        """
        self.current_span().add_attribute(attribute_key, attribute_value)
