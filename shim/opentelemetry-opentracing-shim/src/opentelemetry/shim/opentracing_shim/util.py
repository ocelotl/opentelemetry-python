# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Conversions between OpenTracing and OpenTelemetry representations.

The two APIs disagree on how a point in time is written down and on how a log
entry is named. The OpenTracing Python API passes a timestamp as a ``float``
number of seconds since the epoch, while the OpenTelemetry Python API passes an
``int`` number of nanoseconds since the epoch. The OpenTracing Python API names
a log entry through a field whose key is ``event`` inside the log fields, while
the OpenTelemetry Python API takes the event name as a separate argument.

The functions here hold both conversions in one place, so that every caller
performs them the same way. This module is internal to the shim: it is part of
neither the OpenTracing API nor the OpenTelemetry API, and nothing outside the
shim should import it.
"""

# A default event name to be used for logging events when a better event name
# can't be derived from the event's key-value pairs.
DEFAULT_EVENT_NAME = "log"


def time_seconds_to_ns(time_seconds):
    """Converts a time value in seconds to a time value in nanoseconds.

    This is the direction used when a timestamp arrives through the
    OpenTracing API and has to be handed to the OpenTelemetry API. Its callers
    under ``opentelemetry.shim.opentracing_shim`` are ``SpanShim.finish``,
    ``SpanShim.log_kv`` and ``TracerShim.start_span``.

    Args:
        time_seconds: A ``float`` as returned by ``time.time()``, which
            represents the number of seconds since the epoch.

    Returns:
        An ``int`` representing the number of nanoseconds since the epoch. The
        multiplication is carried out in binary floating point and the product
        is truncated towards zero, so the result can differ from the exact
        conversion of the argument. The imprecision was observed to stay below
        one microsecond.
    """

    return int(time_seconds * 1e9)


def time_seconds_from_ns(time_nanoseconds):
    """Converts a time value in nanoseconds to a time value in seconds.

    This is the reverse direction, for a timestamp read from the OpenTelemetry
    API that has to be handed back through the OpenTracing API. Nothing under
    ``opentelemetry.shim.opentracing_shim`` calls it today. Its callers are
    the tests of the shim, which use it to read a timestamp back off an
    OpenTelemetry span and compare it against the value given to the
    OpenTracing API.

    Args:
        time_nanoseconds: An ``int`` representing the number of nanoseconds
            since the epoch, as the OpenTelemetry API records them.

    Returns:
        A ``float`` representing the number of seconds since the epoch, in the
        form ``time.time()`` returns. A ``float`` holds 53 bits of mantissa, so
        at the magnitude of a timestamp measured from the epoch the result can
        only represent instants about 238 nanoseconds apart. A whole number of
        seconds survives the division unchanged; a nanosecond value that falls
        between two representable instants does not.
    """

    return time_nanoseconds / 1e9


def event_name_from_kv(key_values):
    """Picks the name of an OpenTelemetry event out of OpenTracing log fields.

    ``SpanShim.log_kv`` calls this to decide which name to pass to
    ``opentelemetry.trace.Span.add_event``. The ``event`` field is not removed
    from ``key_values``, which the caller passes on unchanged as the attributes
    of the OpenTelemetry event, so the name also stays recorded as an
    attribute.

    Args:
        key_values: The log fields given to ``SpanShim.log_kv``, or ``None``.

    Returns:
        The value stored under the ``event`` key of ``key_values``, or
        ``DEFAULT_EVENT_NAME`` when ``key_values`` is ``None`` or holds no
        ``event`` key. The value is returned as it is found, so a caller that
        stored something other than a string under ``event`` gets that object
        back and passes it on as the event name.
    """

    if key_values is None or "event" not in key_values:
        return DEFAULT_EVENT_NAME

    return key_values["event"]
