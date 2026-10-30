# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""B3 trace context propagation, in both of the encodings B3 defines.

B3 is the propagation format of Zipkin, specified at
https://github.com/openzipkin/b3-propagation. It carries a trace id, a span id,
a sampling state and, optionally, the span id of the parent, plus a separate
debug flag that only the multi-header encoding has. The specification gives two
ways of writing those fields into a carrier, and this module implements one
class for each.

``B3MultiFormat`` writes one header per field: ``x-b3-traceid``,
``x-b3-spanid`` and ``x-b3-sampled``. ``B3SingleFormat`` writes the one header
named ``b3``, holding the same fields joined by ``-``.

What differs between the two is injection, and with it the set of header names
each one reports through ``fields``. ``B3SingleFormat`` inherits
``B3MultiFormat.extract`` unchanged, so either class reads a carrier written in
either encoding, and a ``b3`` header with a non-empty value wins when a carrier
holds both.

Both classes are registered as ``opentelemetry_propagator`` entry points, under
the names ``b3`` for ``B3SingleFormat`` and ``b3multi`` for ``B3MultiFormat``,
so either can be selected by name through the ``OTEL_PROPAGATORS`` environment
variable.

``B3Format`` is the pre-1.2.0 name of the multi-header propagator and is kept
only so that existing imports resolve.
"""

import collections.abc
from re import compile as re_compile

from typing_extensions import deprecated

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.propagators.textmap import (
    CarrierT,
    Getter,
    Setter,
    TextMapPropagator,
    default_getter,
    default_setter,
)
from opentelemetry.trace import format_span_id, format_trace_id


class B3MultiFormat(TextMapPropagator):
    """Propagator for the B3 HTTP multi-header format.

    Injection writes one header per field: ``x-b3-traceid``, ``x-b3-spanid``
    and ``x-b3-sampled``. Extraction reads those headers but also reads the
    single ``b3`` header of the other B3 encoding, and prefers it when both are
    present and its value is not empty, so this class accepts a carrier written
    either way.
    ``B3SingleFormat`` inherits that extraction and overrides injection, along
    with the ``fields`` property that reports what injection writes.

    This class is registered as the ``opentelemetry_propagator`` entry point
    named ``b3multi``.

    See: https://github.com/openzipkin/b3-propagation
         https://github.com/openzipkin/b3-propagation#multiple-headers
    """

    SINGLE_HEADER_KEY = "b3"
    TRACE_ID_KEY = "x-b3-traceid"
    SPAN_ID_KEY = "x-b3-spanid"
    SAMPLED_KEY = "x-b3-sampled"
    FLAGS_KEY = "x-b3-flags"
    _SAMPLE_PROPAGATE_VALUES = {"1", "True", "true", "d"}
    _trace_id_regex = re_compile(r"[\da-fA-F]{16}|[\da-fA-F]{32}")
    _span_id_regex = re_compile(r"[\da-fA-F]{16}")

    def extract(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        getter: Getter = default_getter,
    ) -> Context:
        """Read a B3 span context out of the carrier, in either B3 encoding.

        The single ``b3`` header is looked up first and takes precedence over
        the multi-header fields when a carrier carries both. Only when it is
        absent, or present with an empty value, are ``x-b3-traceid``,
        ``x-b3-spanid``, ``x-b3-sampled`` and ``x-b3-flags`` read.
        ``B3SingleFormat`` inherits this method unchanged, which is why both
        propagators accept both encodings on extraction.

        A single ``b3`` header is read as up to four ``-`` separated fields:
        trace id, span id, sampling state and parent span id. The parent span
        id is read and then discarded, because OpenTelemetry records the parent
        on the span rather than in the propagated context. A ``b3`` header of
        one field carries a sampling state and no ids, and one of more than
        four fields is malformed; neither yields a span. The B3 sampling state
        "deferred" has no counterpart in a ``SpanContext``, so a ``b3`` header
        that omits the sampling state is treated as sampled.

        Sampling is turned on, in either encoding, when the sampling state is
        one of ``1``, ``True``, ``true`` or ``d``. The multi-header encoding
        has a second way of turning it on, ``x-b3-flags`` set to ``1``, which
        is enough on its own; B3 defines no behaviour for the sampling state
        and that flag disagreeing, so either one alone is honoured. A carrier
        read through the single ``b3`` header never consults ``x-b3-flags``,
        even when the carrier also carries it. The debug state ``d`` is read as
        plain sampling and its distinction from ordinary sampling is lost.

        A trace id of 16 hexadecimal characters is accepted as well as one of
        32, and the next injection writes it back zero padded to 32.

        Args:
            carrier: the object the headers are read from. It is never
                subscripted here, only passed to ``getter``.
            context: the context the result is derived from, so that values
                the caller already put in it are preserved. ``None`` means an
                empty context, and an empty context is then also what is
                returned on failure.
            getter: reads one header out of ``carrier`` by name and returns
                every value found for it, of which only the first is used.

        Returns:
            A context holding a non-recording span whose span context carries
            the extracted ids and is marked remote. The context passed in is
            returned unchanged when a trace id or a span id is missing, is not
            hexadecimal, or is of a length B3 does not allow.
        """
        if context is None:
            context = Context()
        trace_id = trace.INVALID_TRACE_ID
        span_id = trace.INVALID_SPAN_ID
        sampled = "0"
        flags = None

        single_header = _extract_first_element(getter.get(carrier, self.SINGLE_HEADER_KEY))
        if single_header:
            # The b3 spec calls for the sampling state to be
            # "deferred", which is unspecified. This concept does not
            # translate to SpanContext, so we set it as recorded.
            sampled = "1"
            fields = single_header.split("-", 4)

            if len(fields) == 1:
                sampled = fields[0]
            elif len(fields) == 2:
                trace_id, span_id = fields
            elif len(fields) == 3:
                trace_id, span_id, sampled = fields
            elif len(fields) == 4:
                trace_id, span_id, sampled, _ = fields
        else:
            trace_id = _extract_first_element(getter.get(carrier, self.TRACE_ID_KEY)) or trace_id
            span_id = _extract_first_element(getter.get(carrier, self.SPAN_ID_KEY)) or span_id
            sampled = _extract_first_element(getter.get(carrier, self.SAMPLED_KEY)) or sampled
            flags = _extract_first_element(getter.get(carrier, self.FLAGS_KEY)) or flags

        if (
            trace_id == trace.INVALID_TRACE_ID
            or span_id == trace.INVALID_SPAN_ID
            or self._trace_id_regex.fullmatch(trace_id) is None
            or self._span_id_regex.fullmatch(span_id) is None
        ):
            return context

        trace_id = int(trace_id, 16)
        span_id = int(span_id, 16)
        options = 0
        # The b3 spec provides no defined behavior for both sample and
        # flag values set. Since the setting of at least one implies
        # the desire for some form of sampling, propagate if either
        # header is set to allow.
        if sampled in self._SAMPLE_PROPAGATE_VALUES or flags == "1":
            options |= trace.TraceFlags.SAMPLED

        return trace.set_span_in_context(
            trace.NonRecordingSpan(
                trace.SpanContext(
                    # trace an span ids are encoded in hex, so must be converted
                    trace_id=trace_id,
                    span_id=span_id,
                    is_remote=True,
                    trace_flags=trace.TraceFlags(options),
                    trace_state=trace.TraceState(),
                )
            ),
            context,
        )

    def inject(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        setter: Setter = default_setter,
    ) -> None:
        """Write the current span context into the carrier as B3 multi headers.

        Three headers are written: ``x-b3-traceid``, always as 32 hexadecimal
        characters even when the id was extracted from a 16 character one,
        ``x-b3-spanid`` as 16 hexadecimal characters, and ``x-b3-sampled`` as
        ``1`` or ``0``. ``x-b3-flags`` is never written, so a debug flag that
        ``extract`` read from an incoming request reaches the next hop only as
        the sampled bit it set. ``x-b3-parentspanid``, the header this encoding
        gives the parent span id, is never written either.

        Nothing at all is written when the context holds no span, or when the
        span's span context is invalid, which is the case whenever either id is
        zero. The carrier is then left exactly as the caller passed it, rather
        than receiving headers full of zeros.

        Args:
            carrier: the object the headers are written to. It is never
                subscripted here, only passed to ``setter``.
            context: the context to take the current span from. ``None`` means
                whichever context is currently attached. That context is held
                in a ``ContextVar``, so each thread has its own and, under
                asyncio, so does each task.
            setter: writes one header into ``carrier`` under a given name.
        """
        span = trace.get_current_span(context=context)

        span_context = span.get_span_context()
        if not span_context.is_valid:
            return

        sampled = (trace.TraceFlags.SAMPLED & span_context.trace_flags) != 0
        setter.set(
            carrier,
            self.TRACE_ID_KEY,
            format_trace_id(span_context.trace_id),
        )
        setter.set(carrier, self.SPAN_ID_KEY, format_span_id(span_context.span_id))
        setter.set(carrier, self.SAMPLED_KEY, "1" if sampled else "0")

    @property
    def fields(self) -> set[str]:
        """The header names this propagator's ``inject`` may write.

        A caller that has to clear any propagation headers already present in a
        carrier before injecting into it, such as an instrumentation that
        reuses a request object, reads the names from here instead of hard
        coding them. ``b3`` and ``x-b3-flags`` are absent because ``inject``
        never writes either, even though ``extract`` reads both. A caller
        reusing a carrier that already holds a ``b3`` header has to delete that
        header as well, because ``extract`` at the next hop prefers it over the
        three names returned here.

        Returns:
            The three multi-header names, ``x-b3-traceid``, ``x-b3-spanid`` and
            ``x-b3-sampled``.
        """
        return {
            self.TRACE_ID_KEY,
            self.SPAN_ID_KEY,
            self.SAMPLED_KEY,
        }


class B3SingleFormat(B3MultiFormat):
    """Propagator for the B3 HTTP single-header format.

    Injection writes the one header named ``b3``, whose value holds the trace
    id, the span id and the sampling state joined by ``-``. Extraction comes
    from ``B3MultiFormat`` and is not overridden, so this propagator reads the
    multi-header encoding too.

    This class is registered as the ``opentelemetry_propagator`` entry point
    named ``b3``.

    See: https://github.com/openzipkin/b3-propagation
         https://github.com/openzipkin/b3-propagation#single-header
    """

    def inject(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        setter: Setter = default_setter,
    ) -> None:
        """Write the current span context into the carrier as one ``b3`` header.

        The value is the trace id, the span id and the sampling state joined by
        ``-``, for example
        ``80f198ee56343ba864fe8b2a57d3eff7-e457b5a2e4d86bd1-1``. The trace id is
        always 32 hexadecimal characters, even when it was extracted from a 16
        character one, and the sampling state is ``1`` or ``0``. B3 allows a
        fourth field holding the parent span id and this propagator never
        writes it, so the single header is always three fields long. The B3
        debug state ``d`` is never written either, so an incoming debug flag
        reaches the next hop only as the sampled bit it set.

        Nothing is written when the context holds no span, or when the span's
        span context is invalid, which is the case whenever either id is zero.

        Args:
            carrier: the object the header is written to. It is never
                subscripted here, only passed to ``setter``.
            context: the context to take the current span from. ``None`` means
                whichever context is currently attached. That context is held
                in a ``ContextVar``, so each thread has its own and, under
                asyncio, so does each task.
            setter: writes the header into ``carrier`` under the name ``b3``.
        """
        span = trace.get_current_span(context=context)

        span_context = span.get_span_context()
        if not span_context.is_valid:
            return

        sampled = (trace.TraceFlags.SAMPLED & span_context.trace_flags) != 0

        fields = [
            format_trace_id(span_context.trace_id),
            format_span_id(span_context.span_id),
            "1" if sampled else "0",
        ]

        setter.set(carrier, self.SINGLE_HEADER_KEY, "-".join(fields))

    @property
    def fields(self) -> set[str]:
        """The header name this propagator's ``inject`` may write.

        A caller that has to clear any propagation headers already present in a
        carrier before injecting into it reads the name from here instead of
        hard coding it. The multi-header names are absent even though
        ``extract`` reads them, because this propagator never writes them.

        Returns:
            The single-header name, ``b3``, on its own.
        """
        return {self.SINGLE_HEADER_KEY}


class B3Format(B3MultiFormat):
    """Deprecated former name of ``B3MultiFormat``.

    Before version 1.2.0 this was the only B3 propagator in the package and it
    implemented the multi-header format. Adding the single-header format made
    the name ambiguous, so the two formats became ``B3MultiFormat`` and
    ``B3SingleFormat`` and this name was kept only so that existing imports
    keep resolving. It adds no behaviour of its own: construct it and it warns,
    then behaves exactly like ``B3MultiFormat``.

    ``B3Format()`` is the only call that succeeds. The signature accepts
    ``*args`` and ``**kwargs`` and forwards them to the base class, but neither
    ``B3MultiFormat`` nor anything it inherits from defines a constructor, so
    they reach ``object.__init__``, which raises ``TypeError`` on any argument
    at all.

    Args:
        *args: forwarded to the base class, which rejects every one of them.
        **kwargs: forwarded to the base class, which rejects every one of them.
    """

    @deprecated(
        "B3Format is deprecated in favor of B3MultiFormat. Deprecated since version 1.2.0.",
    )
    def __init__(self, *args, **kwargs):
        """Warn that this class is deprecated, then construct it.

        The arguments are documented on the class. The decorator emits a
        ``DeprecationWarning``, which Python's default warning filters hide
        outside ``__main__``, so run with ``-W default`` to see it.
        """
        super().__init__(*args, **kwargs)


def _extract_first_element(
    items: collections.abc.Iterable[CarrierT],
) -> CarrierT | None:
    """Return the first value a getter found for a header, or ``None``.

    ``Getter.get`` answers with every value present for a header name, because
    HTTP allows a name to repeat, and with ``None`` when the name is absent. B3
    defines no meaning for a repeated header, so this keeps the first value and
    drops the rest.

    Args:
        items: what ``Getter.get`` returned, which is ``None`` when the header
            was absent and otherwise an iterable of its values. An iterator is
            accepted and is advanced by one element.

    Returns:
        The first value, or ``None`` when ``items`` is ``None`` or empty.
    """
    if items is None:
        return None
    return next(iter(items), None)
