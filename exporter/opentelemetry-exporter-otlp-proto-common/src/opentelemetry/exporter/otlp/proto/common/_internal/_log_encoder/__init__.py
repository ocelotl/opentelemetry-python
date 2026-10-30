# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Conversion of SDK log records into the protobuf log export request.

``encode_logs`` is the only name the OTLP exporters import from here, by way of
``opentelemetry.exporter.otlp.proto.common._log_encoder``. Everything else is
private to this module.

The encoding regroups a flat sequence of log records into the two levels of
nesting the protocol requires, resource then instrumentation scope, and then
converts each record field by field.
"""

from collections import defaultdict
from collections.abc import Sequence

from opentelemetry.exporter.otlp.proto.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
    _encode_value,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord as PB2LogRecord
from opentelemetry.proto.logs.v1.logs_pb2 import (
    ResourceLogs,
    ScopeLogs,
)
from opentelemetry.sdk._logs import ReadableLogRecord


def encode_logs(
    batch: Sequence[ReadableLogRecord],
) -> ExportLogsServiceRequest:
    """Encode log records as the protobuf request body of an OTLP log export.

    Args:
        batch: The log records to export, in any order. They are grouped by
            resource and by instrumentation scope during encoding, so records
            that share a resource and a scope end up in one ``ScopeLogs``
            message whatever order they arrive in. An empty sequence produces a
            request with no ``resource_logs``, which the protocol allows.

    Returns:
        The ``ExportLogsServiceRequest`` to send over gRPC or, serialized, as the
        body of an HTTP request.
    """
    return ExportLogsServiceRequest(resource_logs=_encode_resource_logs(batch))


def _encode_log(readable_log_record: ReadableLogRecord) -> PB2LogRecord:
    """Encode one log record, without its resource or its instrumentation scope.

    A trace or span identifier of 0 means the record was not emitted inside a
    recording span, and is encoded as an absent field rather than as eight or
    sixteen zero bytes, which is what the protocol asks for. A severity number
    that is ``None`` rather than an enum member leaves ``severity_number`` at
    ``SEVERITY_NUMBER_UNSPECIFIED``.

    Args:
        readable_log_record: The record as the SDK's log processors see it,
            holding both the log record itself and the count of attributes the
            attribute limit dropped.

    Returns:
        The protobuf ``LogRecord``.
    """
    span_id = (
        None if readable_log_record.log_record.span_id == 0 else _encode_span_id(readable_log_record.log_record.span_id)
    )
    trace_id = (
        None
        if readable_log_record.log_record.trace_id == 0
        else _encode_trace_id(readable_log_record.log_record.trace_id)
    )
    return PB2LogRecord(
        time_unix_nano=readable_log_record.log_record.timestamp,
        observed_time_unix_nano=readable_log_record.log_record.observed_timestamp,
        span_id=span_id,
        trace_id=trace_id,
        flags=int(readable_log_record.log_record.trace_flags),
        body=_encode_value(readable_log_record.log_record.body),
        severity_text=readable_log_record.log_record.severity_text,
        attributes=_encode_attributes(readable_log_record.log_record.attributes),
        dropped_attributes_count=readable_log_record.dropped_attributes,
        severity_number=getattr(readable_log_record.log_record.severity_number, "value", None),
        event_name=readable_log_record.log_record.event_name,
    )


def _encode_resource_logs(
    batch: Sequence[ReadableLogRecord],
) -> list[ResourceLogs]:
    """Group log records by resource and instrumentation scope and encode each group.

    Grouping uses the resource and the instrumentation scope as dictionary keys,
    so two records share a group only when both compare equal. Records with no
    instrumentation scope form a group of their own, whose ``ScopeLogs`` message
    carries an empty scope and no schema URL.

    Args:
        batch: The log records to group and encode.

    Returns:
        One ``ResourceLogs`` per distinct resource, each holding one
        ``ScopeLogs`` per distinct instrumentation scope found under that
        resource. The resources appear in the order their first record was seen.
    """
    sdk_resource_logs = defaultdict(lambda: defaultdict(list))

    for readable_log in batch:
        sdk_resource = readable_log.resource
        sdk_instrumentation = readable_log.instrumentation_scope or None
        pb2_log = _encode_log(readable_log)

        sdk_resource_logs[sdk_resource][sdk_instrumentation].append(pb2_log)

    pb2_resource_logs = []

    for sdk_resource, sdk_instrumentations in sdk_resource_logs.items():
        scope_logs = []
        for sdk_instrumentation, pb2_logs in sdk_instrumentations.items():
            scope_logs.append(
                ScopeLogs(
                    scope=(_encode_instrumentation_scope(sdk_instrumentation)),
                    log_records=pb2_logs,
                    schema_url=sdk_instrumentation.schema_url if sdk_instrumentation else None,
                )
            )
        pb2_resource_logs.append(
            ResourceLogs(
                resource=_encode_resource(sdk_resource),
                scope_logs=scope_logs,
                schema_url=sdk_resource.schema_url,
            )
        )

    return pb2_resource_logs
