# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Conversions from OpenTelemetry values to OpenCensus protobuf messages.

Two tracing models meet in this package. OpenTelemetry is the model the
calling application uses, and its names come from ``opentelemetry.trace`` and
``opentelemetry.sdk.trace``. OpenCensus is the model the collector expects on
the wire, and its names come from the generated ``opencensus.proto`` modules.
Every function here reads a value of the first model and produces a message of
the second, so none of them is a general purpose helper.

Inside this distribution the functions are called from
``opentelemetry.exporter.opencensus.trace_exporter`` and from its tests.
"""

from os import getpid
from socket import gethostname
from time import time

# pylint: disable=wrong-import-position
from google.protobuf.timestamp_pb2 import (  # pylint: disable=no-name-in-module
    Timestamp,
)
from opencensus.proto.agent.common.v1 import common_pb2
from opencensus.proto.trace.v1 import trace_pb2

from opentelemetry.exporter.opencensus.version import (
    __version__ as opencensusexporter_exporter_version,
)
from opentelemetry.trace import SpanKind
from opentelemetry.util._importlib_metadata import version

OPENTELEMETRY_VERSION = version("opentelemetry-api")


def proto_timestamp_from_time_ns(time_ns):
    """Convert a nanosecond timestamp to the OpenCensus timestamp message.

    OpenTelemetry records span and event times as an integer number of
    nanoseconds since the Unix epoch, while OpenCensus carries every time in
    the protobuf ``Timestamp`` message. Four fields of three different
    OpenCensus messages are filled from here: ``start_time`` and ``end_time``
    on a span, ``time`` on a time event, and ``start_timestamp`` on the
    process identifier that ``get_node`` builds. The first three come from
    the OpenTelemetry span model and the fourth from a wall clock reading, so
    the argument is a count of nanoseconds and nothing narrower.

    Args:
        time_ns: Time in nanoseconds since the Unix epoch, or ``None``.
            ``None`` leaves the message at its default value, so a reader of
            the message sees the Unix epoch and cannot tell that no time was
            given.

    Returns:
        A ``google.protobuf.timestamp_pb2.Timestamp``.
    """
    ts = Timestamp()
    if time_ns is not None:
        # pylint: disable=no-member
        ts.FromNanoseconds(time_ns)
    return ts


# pylint: disable=no-member
def get_collector_span_kind(kind: SpanKind):
    """Translate an OpenTelemetry span kind to an OpenCensus span kind.

    OpenCensus names only the server and the client role, so of the five
    OpenTelemetry kinds only ``SERVER`` and ``CLIENT`` survive the
    translation. ``INTERNAL``, ``PRODUCER`` and ``CONSUMER`` all become
    ``SPAN_KIND_UNSPECIFIED`` and the collector cannot tell them apart from
    each other afterwards.

    Args:
        kind: The kind of the OpenTelemetry span being exported.

    Returns:
        A member of the OpenCensus ``trace_pb2.Span.SpanKind`` enumeration.
    """
    if kind is SpanKind.SERVER:
        return trace_pb2.Span.SpanKind.SERVER
    if kind is SpanKind.CLIENT:
        return trace_pb2.Span.SpanKind.CLIENT
    return trace_pb2.Span.SpanKind.SPAN_KIND_UNSPECIFIED


def add_proto_attribute_value(pb_attributes, key, value):
    """Store one OpenTelemetry attribute in an OpenCensus attribute map.

    The OpenCensus ``AttributeValue`` message is a union of a string, an
    integer, a boolean and a double, so the Python type of the OpenTelemetry
    attribute value decides which field is written. ``bool`` is tested before
    ``int`` on purpose, since ``bool`` is a subclass of ``int`` in Python and
    would otherwise be exported as 0 or 1.

    An OpenTelemetry attribute value may also be a sequence, and OpenCensus
    has no field for one. Such a value, and any other type that does not match
    the four cases, is written as the result of ``str()`` on it, so a tuple
    reaches the collector as its Python text form rather than as a list.

    The message is modified in place. The string case writes the nested
    ``value`` field of a ``TruncatableString`` and sets no truncation count,
    so no value is shortened here.

    Args:
        pb_attributes: The OpenCensus ``Attributes`` message to write into.
            A span, a link and an annotation each carry one.
        key: The OpenTelemetry attribute key, used unchanged as the key of
            the OpenCensus attribute map.
        value: The OpenTelemetry attribute value.
    """

    if isinstance(value, bool):
        pb_attributes.attribute_map[key].bool_value = value
    elif isinstance(value, int):
        pb_attributes.attribute_map[key].int_value = value
    elif isinstance(value, str):
        pb_attributes.attribute_map[key].string_value.value = value
    elif isinstance(value, float):
        pb_attributes.attribute_map[key].double_value = value
    else:
        pb_attributes.attribute_map[key].string_value.value = str(value)


# pylint: disable=no-member
def get_node(service_name, host_name):
    """Build the OpenCensus ``Node`` message that identifies this process.

    OpenCensus describes the process the spans came from with a ``Node``
    rather than with a resource. The agent protocol asks for the node on the
    first request of a stream and on any later request that changes it, and
    this exporter opens a fresh call per batch, so every request it sends
    carries one. The message is filled from the service name taken from the
    OpenTelemetry resource plus values read from the running process.

    OpenCensus does have a ``Resource`` message, carried by both
    ``ExportTraceServiceRequest`` and ``Span``, and a free-form ``attributes``
    map on the node itself. This exporter fills none of the three, so the
    service name is the only resource attribute that travels.

    ``start_timestamp`` is the moment this function runs, which is when the
    exporter was constructed or when a later batch replaced the node, and not
    the moment the process started.

    Args:
        service_name: The value of the ``service.name`` resource attribute of
            the spans being exported. ``None`` leaves the service name empty
            in the message.
        host_name: The host name to report. ``None`` means the exporter was
            not told one, in which case the host name of the machine is read
            with ``socket.gethostname()``.

    Returns:
        An OpenCensus ``common_pb2.Node`` carrying the process identifier,
        the version of this exporter, the version of ``opentelemetry-api``
        and the service name.
    """
    return common_pb2.Node(
        identifier=common_pb2.ProcessIdentifier(
            host_name=gethostname() if host_name is None else host_name,
            pid=getpid(),
            start_timestamp=proto_timestamp_from_time_ns(int(time() * 1e9)),
        ),
        library_info=common_pb2.LibraryInfo(
            language=common_pb2.LibraryInfo.Language.Value("PYTHON"),
            exporter_version=opencensusexporter_exporter_version,
            core_library_version=OPENTELEMETRY_VERSION,
        ),
        service_info=common_pb2.ServiceInfo(name=service_name),
    )
