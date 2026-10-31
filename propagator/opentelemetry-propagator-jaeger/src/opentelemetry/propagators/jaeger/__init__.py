# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Trace context propagation in the Jaeger format.

The Jaeger format carries trace identity in one header, ``uber-trace-id``,
whose value is four colon-separated hexadecimal fields, and carries each
baggage entry in a header of its own, named with the ``uberctx-`` prefix.
``JaegerPropagator`` reads that representation in ``extract`` and writes it in
``inject``.

The format is specified at
https://www.jaegertracing.io/docs/1.19/client-libraries/#propagation-format
"""

import collections.abc
import itertools
import urllib.parse

from opentelemetry import baggage, trace
from opentelemetry.context import Context
from opentelemetry.propagators.textmap import (
    CarrierT,
    Getter,
    Setter,
    TextMapPropagator,
    default_getter,
    default_setter,
)
from opentelemetry.trace import SpanContext, format_span_id, format_trace_id


class JaegerPropagator(TextMapPropagator):
    """Propagator for the Jaeger format.

    ``TRACE_ID_KEY`` names the header holding trace identity, and
    ``BAGGAGE_PREFIX`` is prepended to a baggage key to name the header holding
    that entry. Both are read through ``self``, so a subclass can rename them.

    ``DEBUG_FLAG`` is bit 1 of the flags field of the trace identity header.
    ``inject`` sets it on every sampled span, and ``extract`` discards it,
    keeping only bit 0, the sampled bit.

    The Jaeger format bounds neither the number of baggage entries nor their
    size, so the three ``MAX_BAGGAGE_`` attributes bound the work an untrusted
    carrier can cause. ``MAX_BAGGAGE_ENTRIES`` caps how many entries are
    considered, ``MAX_BAGGAGE_ENTRY_BYTES`` caps the UTF-8 size of a single
    ``key=value`` entry, and ``MAX_BAGGAGE_TOTAL_BYTES`` caps the size of all
    accepted entries joined by commas. An entry over a limit is dropped with no
    error reported, on extract and on inject alike.

    An instance holds no state, so one instance can serve any number of
    concurrent calls.

    See: https://www.jaegertracing.io/docs/1.19/client-libraries/#propagation-format
    """

    TRACE_ID_KEY = "uber-trace-id"
    BAGGAGE_PREFIX = "uberctx-"
    DEBUG_FLAG = 0x02
    # The Jaeger format defines no baggage limits, so the W3C Baggage spec
    # limits are borrowed to bound an unbounded inbound carrier on extract.
    MAX_BAGGAGE_ENTRIES = 180
    MAX_BAGGAGE_ENTRY_BYTES = 4096
    MAX_BAGGAGE_TOTAL_BYTES = 8192

    def extract(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        getter: Getter[CarrierT] = default_getter,
    ) -> Context:
        """Read a Jaeger trace context out of a carrier.

        When ``getter`` reports no values at all for ``TRACE_ID_KEY``, the
        context is returned unchanged and no baggage is read. A header whose
        value is the empty string is not that case, because a getter reports
        it as one empty value: baggage is read, and the header is then found
        malformed. Otherwise baggage is read before the trace identity header
        is parsed, so a carrier whose trace identity header is malformed still
        contributes its baggage entries.

        A malformed trace identity header is reported by returning without
        adding a span to the context, never by raising. A value holding no
        ``:`` at all is percent-decoded before it is split, so a client that
        encoded the delimiters along with everything else is still
        understood. The header is malformed when the value does not then
        split into exactly four colon-separated fields, when its flags field
        is not hexadecimal, or when its trace id or span id field is not
        hexadecimal or is zero.

        Of the flags field only the sampled bit is kept, so the debug bit that
        ``inject`` writes does not survive a round trip. The parent span id
        field has to be present but is never read, because ``SpanContext`` has
        nowhere to hold it.

        Args:
            carrier: the object holding the Jaeger headers, read through
                ``getter``.
            context: the context the extracted values are added to. An empty
                ``Context`` is used when this is ``None``.
            getter: reads the values of a key out of ``carrier``. Defaults to
                ``opentelemetry.propagators.textmap.default_getter``, which
                treats the carrier as a mapping.

        Returns:
            A ``Context`` holding the accepted baggage entries, and a
            non-recording remote span when the trace identity header was not
            malformed. Not malformed is a weaker condition than
            ``SpanContext.is_valid``, which also bounds each id by its width
            and rejects a negative one. A header of ``-1:-2:3:1``, or one
            whose trace id does not fit in 128 bits, is accepted here and its
            span is added, yet the ``SpanContext`` of that span reports
            ``is_valid`` as ``False`` and ``inject`` writes nothing for it.
        """
        if context is None:
            context = Context()
        header = getter.get(carrier, self.TRACE_ID_KEY)
        if not header:
            return context

        context = self._extract_baggage(getter, carrier, context)

        trace_id, span_id, flags = _parse_trace_id_header(header)
        if trace_id == trace.INVALID_TRACE_ID or span_id == trace.INVALID_SPAN_ID:
            return context

        span = trace.NonRecordingSpan(
            trace.SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                is_remote=True,
                trace_flags=trace.TraceFlags(flags & trace.TraceFlags.SAMPLED),
            )
        )
        return trace.set_span_in_context(span, context)

    def inject(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        setter: Setter[CarrierT] = default_setter,
    ) -> None:
        """Write a trace context into a carrier in the Jaeger format.

        Nothing at all is written when the span taken from the context has an
        invalid span context, so a carrier handed over in that state is left
        exactly as it was.

        The parent span id field is taken from the parent of the span when the
        span is recording and exposes one, and is sixteen zeros otherwise. A
        non-recording span, which is what ``extract`` produces, therefore
        always writes sixteen zeros there.

        ``DEBUG_FLAG`` is set in the flags field whenever the span is sampled,
        whether or not the debug bit was set on the header this context came
        from.

        Each baggage entry of the context that fits the ``MAX_BAGGAGE_`` limits
        becomes its own header, and an entry past ``MAX_BAGGAGE_ENTRIES`` or
        over a byte limit is dropped with no error reported. The value is
        converted with ``str`` and then percent-encoded, so a baggage value
        that is not a string is written as its ``str`` form.

        Args:
            carrier: the object the headers are written into, through
                ``setter``.
            context: the context holding the span and the baggage to write. The
                current context is used when this is ``None``.
            setter: writes the value of a key into ``carrier``. Defaults to
                ``opentelemetry.propagators.textmap.default_setter``, which
                treats the carrier as a mutable mapping.
        """
        span = trace.get_current_span(context=context)
        span_context = span.get_span_context()
        if not span_context.is_valid:
            return

        # Non-recording spans do not have a parent; the API Span type does not
        # declare a parent attribute, so it has to be accessed via getattr
        parent: SpanContext | None = getattr(span, "parent", None) if span.is_recording() else None
        span_parent_id = parent.span_id if parent else 0
        trace_flags = span_context.trace_flags
        if trace_flags.sampled:
            trace_flags |= self.DEBUG_FLAG

        # set span identity
        setter.set(
            carrier,
            self.TRACE_ID_KEY,
            _format_uber_trace_id(
                span_context.trace_id,
                span_context.span_id,
                span_parent_id,
                trace_flags,
            ),
        )

        # set span baggage, if any
        baggage_entries = baggage.get_all(context=context)
        if not baggage_entries:
            return
        self._inject_baggage(setter, carrier, baggage_entries)

    @property
    def fields(self) -> set[str]:
        """The one carrier key ``inject`` sets that can be named before it runs.

        Only ``TRACE_ID_KEY`` is reported. The baggage headers that ``inject``
        writes are named after the baggage keys of the context it is given, and
        those are not known until ``inject`` runs, so a caller reusing a
        carrier has to clear the ``BAGGAGE_PREFIX`` keys itself.

        Returns:
            A set whose one member is ``TRACE_ID_KEY``.
        """
        return {self.TRACE_ID_KEY}

    def _extract_baggage(
        self,
        getter: Getter[CarrierT],
        carrier: CarrierT,
        context: Context,
    ) -> Context:
        """Read the ``BAGGAGE_PREFIX`` headers of a carrier into a context.

        At most ``MAX_BAGGAGE_ENTRIES`` prefixed keys are looked at, in the
        order ``getter.keys`` reports them, and the keys past that point are
        never read at all. A key whose value is absent or an empty sequence is
        skipped.

        Only the leading ``BAGGAGE_PREFIX`` is removed from a key, so the
        carrier key ``uberctx-a-uberctx-b`` yields the baggage key
        ``a-uberctx-b``.

        The byte limits are then measured on that shortened key and on the
        value as it appears in the carrier, before any decoding. An accepted
        value is percent-decoded and stripped of surrounding whitespace before
        it is stored, so the value stored can be shorter than the one measured.

        Args:
            getter: reads the values of a key out of ``carrier``.
            carrier: the object holding the Jaeger headers.
            context: the context the baggage entries are added to.

        Returns:
            A new ``Context`` holding the accepted baggage entries, or
            ``context`` itself when no entry was accepted.
        """
        # The limit bounds the candidates inspected, not the entries kept, so a
        # carrier full of oversized ones cannot force unbounded work.
        candidates = itertools.islice(
            (key for key in getter.keys(carrier) if key.startswith(self.BAGGAGE_PREFIX)),
            self.MAX_BAGGAGE_ENTRIES,
        )
        pairs = []
        for key in candidates:
            value = _extract_first_element(getter.get(carrier, key))
            if value is not None:
                pairs.append((key.removeprefix(self.BAGGAGE_PREFIX), value))

        for baggage_key, value in _limit_baggage_bytes(
            pairs, self.MAX_BAGGAGE_ENTRY_BYTES, self.MAX_BAGGAGE_TOTAL_BYTES
        ):
            context = baggage.set_baggage(
                baggage_key,
                urllib.parse.unquote(value).strip(),
                context=context,
            )
        return context

    def _inject_baggage(
        self,
        setter: Setter[CarrierT],
        carrier: CarrierT,
        baggage_entries: collections.abc.Mapping[str, object],
    ) -> None:
        """Write baggage entries into a carrier as ``BAGGAGE_PREFIX`` headers.

        At most ``MAX_BAGGAGE_ENTRIES`` entries are considered, in the
        iteration order of ``baggage_entries``, and the entries past that point
        are dropped. Each value is converted with ``str`` and percent-encoded,
        and the byte limits are measured on that encoded form, so a value with
        many characters needing encoding can exceed a limit that its plain form
        would meet.

        An entry over a limit is dropped with no error reported, and a later
        entry small enough to still fit is written even after a larger one has
        been dropped.

        Args:
            setter: writes the value of a key into ``carrier``.
            carrier: the object the headers are written into.
            baggage_entries: the baggage of the context, keyed by baggage key,
                with the ``BAGGAGE_PREFIX`` not yet applied.
        """
        candidates = itertools.islice(baggage_entries.items(), self.MAX_BAGGAGE_ENTRIES)
        pairs = [(key, urllib.parse.quote(str(value))) for key, value in candidates]

        for key, encoded_value in _limit_baggage_bytes(
            pairs, self.MAX_BAGGAGE_ENTRY_BYTES, self.MAX_BAGGAGE_TOTAL_BYTES
        ):
            setter.set(carrier, self.BAGGAGE_PREFIX + key, encoded_value)


def _limit_baggage_bytes(
    pairs: collections.abc.Iterable[tuple[str, str]],
    max_entry_bytes: int,
    max_total_bytes: int,
) -> collections.abc.Iterator[tuple[str, str]]:
    """Yield the pairs of an iterable that fit a per-entry and a total byte budget.

    A pair costs the UTF-8 length of its key, plus the UTF-8 length of its
    value, plus one byte for the ``=`` that joins them in a W3C Baggage header.
    That cost on its own is what ``max_entry_bytes`` is compared against, and a
    pair over it is skipped. Charging bytes rather than characters is what makes
    the budget match what a receiver has to parse, since one character can
    occupy several bytes.

    The running total compared against ``max_total_bytes`` charges one further
    byte per pair, for the ``,`` that separates it from an already accepted
    pair. The first pair accepted is charged no such byte, so the separator
    never affects the per-entry limit and affects the total only from the
    second accepted pair onwards.

    A pair that would take the running total past ``max_total_bytes`` is
    skipped. Skipping continues rather than stopping, so a pair small enough to
    still fit is yielded even after a larger one has been skipped, and the
    yielded pairs are therefore not always a prefix of ``pairs``.

    Args:
        pairs: the candidate key and value pairs, in the order they are to be
            considered. Both halves are counted exactly as given, so a caller
            that percent-encodes its values has to do so before calling.
        max_entry_bytes: the largest a single pair is allowed to be.
        max_total_bytes: the largest all yielded pairs together are allowed to
            be.

    Yields:
        Each pair that fits, in the order it was given.
    """
    total_bytes = 0
    accepted = 0
    for key, value in pairs:
        entry_bytes = len(key.encode()) + len(value.encode()) + 1
        if entry_bytes > max_entry_bytes:
            continue
        separator_bytes = 1 if accepted > 0 else 0
        if total_bytes + separator_bytes + entry_bytes > max_total_bytes:
            continue
        yield key, value
        total_bytes += separator_bytes + entry_bytes
        accepted += 1


def _format_uber_trace_id(trace_id, span_id, parent_span_id, flags):
    """Render the four fields of a ``uber-trace-id`` header value.

    Args:
        trace_id: the trace id, rendered zero-padded to 32 hexadecimal
            characters.
        span_id: the span id, rendered zero-padded to 16 hexadecimal
            characters.
        parent_span_id: the span id of the parent, rendered zero-padded to 16
            hexadecimal characters. ``inject`` passes 0 when it finds no
            parent, which renders as 16 zeros.
        flags: the flags field, rendered zero-padded to 2 hexadecimal
            characters. Bit 0 is the sampled bit and bit 1 is the debug bit.

    Returns:
        The four fields joined by colons.
    """
    return f"{format_trace_id(trace_id)}:{format_span_id(span_id)}:{format_span_id(parent_span_id)}:{flags:02x}"


def _extract_first_element(
    items: collections.abc.Iterable[str] | None,
) -> str | None:
    """Take the first element of an iterable, treating no element as ``None``.

    A getter reports the values of a carrier key as a sequence, because one
    header name can appear several times, and the Jaeger format reads only the
    first occurrence.

    Args:
        items: the values a getter reported, or ``None`` when the key was
            absent from the carrier.

    Returns:
        The first element, or ``None`` when ``items`` is ``None`` or has no
        element. The two cases are not distinguished, because both callers
        treat an absent key and an empty sequence of values the same way. A
        key present with the empty string is neither case, since the getter
        reports it as a sequence of one element.
    """
    if items is None:
        return None
    return next(iter(items), None)


def _parse_trace_id_header(
    items: collections.abc.Iterable[str],
) -> tuple[int, int, int]:
    """Split a ``uber-trace-id`` header value into a trace id, a span id and flags.

    Only the first value is read, and an empty ``items`` gives the invalid
    result. A value with no ``:`` in it is percent-decoded first, because some
    Jaeger clients encode the delimiter along with everything else.

    The value has to split into exactly four colon-separated fields and its
    flags field has to be hexadecimal. Failing either of those discards the
    whole value and gives the invalid result. The third field, the parent span
    id, has to be present but its content is discarded, because
    ``SpanContext`` has nowhere to hold it.

    A trace id or span id field that is not hexadecimal becomes the invalid id
    on its own, leaving the other two values as they were parsed. No width is
    checked, so a field with more hexadecimal digits than the format allows is
    still parsed into an integer.

    Args:
        items: the values a getter reported for the ``TRACE_ID_KEY`` header.

    Returns:
        The trace id, the span id and the flags, as integers. The invalid
        result is ``(INVALID_TRACE_ID, INVALID_SPAN_ID, 0)`` from
        ``opentelemetry.trace``, and the caller detects it by checking each id
        against those two values rather than the tuple as a whole.
    """
    invalid_header_result = (trace.INVALID_TRACE_ID, trace.INVALID_SPAN_ID, 0)

    header = _extract_first_element(items)
    if header is None:
        return invalid_header_result

    # some Jaeger clients URL-encode the header value, including the ":"
    # delimiter, so decode it when no plain delimiter can be found
    if ":" not in header:
        header = urllib.parse.unquote(header)

    fields = header.split(":")
    if len(fields) != 4:
        return invalid_header_result

    trace_id_str, span_id_str, _parent_id_str, flags_str = fields
    flags = _int_from_hex_str(flags_str)
    if flags is None:
        return invalid_header_result

    trace_id = _int_from_hex_str(trace_id_str)
    if trace_id is None:
        trace_id = trace.INVALID_TRACE_ID
    span_id = _int_from_hex_str(span_id_str)
    if span_id is None:
        span_id = trace.INVALID_SPAN_ID
    return trace_id, span_id, flags


def _int_from_hex_str(identifier: str) -> int | None:
    """Parse hexadecimal text into an integer, reporting a failure as ``None``.

    This is ``int(identifier, 16)`` with its ``ValueError`` turned into a
    return value, so that ``_parse_trace_id_header`` can check three fields in
    a row without a ``try`` block around each one.

    The parse is as permissive as ``int`` itself: surrounding whitespace, a
    leading sign, a leading ``0x`` and underscores between digits are all
    accepted, and no width is enforced.

    Args:
        identifier: the text of one field of the trace identity header.

    Returns:
        The integer value, or ``None`` when ``identifier`` is not hexadecimal.
    """
    try:
        return int(identifier, 16)
    except ValueError:
        return None
