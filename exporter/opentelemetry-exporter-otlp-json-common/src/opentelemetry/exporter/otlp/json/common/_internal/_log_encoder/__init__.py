# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pyright: reportCallIssue=false

"""Encoding of SDK log records into OTLP JSON log messages.

``encode_logs`` is the entry point and is re-exported from
``opentelemetry.exporter.otlp.json.common._log_encoder``, which is where a log
record exporter should import it from. The rest of this module is private.

A log record exporter hands over a flat collection of records, while OTLP wants
them grouped first by resource and then by instrumentation scope. Rebuilding
that grouping is most of the work here, and it relies on both
``opentelemetry.sdk.resources.Resource`` and
``opentelemetry.sdk.util.instrumentation.InstrumentationScope`` being hashable,
so that each can be used as a dictionary key.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection
from typing import cast

from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
    _encode_value,
)
from opentelemetry.proto_json.collector.logs.v1.logs_service import (
    ExportLogsServiceRequest as JSONExportLogsServiceRequest,
)
from opentelemetry.proto_json.logs.v1.logs import LogRecord as JSONLogRecord
from opentelemetry.proto_json.logs.v1.logs import (
    ResourceLogs as JSONResourceLogs,
)
from opentelemetry.proto_json.logs.v1.logs import (
    ScopeLogs as JSONScopeLogs,
)
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.util.types import Attributes


def encode_logs(
    batch: Collection[ReadableLogRecord],
) -> JSONExportLogsServiceRequest:
    """Encode a batch of SDK log records as an OTLP export request.

    Args:
        batch: the log records to export, in any order and from any number of
            resources and instrumentation scopes.

    Returns:
        An ``ExportLogsServiceRequest`` holding every record in ``batch``,
        regrouped by resource and then by instrumentation scope. An empty
        ``batch`` gives a request with no resource logs.

    Raises:
        TypeError: if the body of a record, or any value nested inside a
            mapping or a sequence body, is of a type OTLP has no
            representation for. Unlike an attribute of such a type, which is
            dropped with a log message, a body of such a type fails the whole
            batch.
    """
    return JSONExportLogsServiceRequest(resource_logs=_encode_resource_logs(batch))


def _encode_log(readable_log_record: ReadableLogRecord) -> JSONLogRecord:
    """Encode one SDK log record as an OTLP JSON ``LogRecord``.

    A trace or span identifier of zero is treated as absent and left out of the
    result, since zero is the identifier the SDK uses for a record that was
    emitted outside any span.

    Args:
        readable_log_record: the record to encode, together with the
            instrumentation scope and the resource it was emitted under.

    Returns:
        The encoded ``LogRecord``. ``severity_number`` is the numeric value of
        the severity, or ``None`` when the record carries no severity.
        ``dropped_attributes_count`` is what the SDK log record limits dropped,
        and is zero when the attributes were never bounded.

    Raises:
        TypeError: if the body of the record, or any value nested inside a
            mapping or a sequence body, is of a type OTLP has no
            representation for.
    """
    return JSONLogRecord(
        time_unix_nano=readable_log_record.log_record.timestamp,
        observed_time_unix_nano=readable_log_record.log_record.observed_timestamp,
        span_id=_encode_span_id(readable_log_record.log_record.span_id)
        if readable_log_record.log_record.span_id
        else None,
        trace_id=_encode_trace_id(readable_log_record.log_record.trace_id)
        if readable_log_record.log_record.trace_id
        else None,
        flags=int(readable_log_record.log_record.trace_flags),
        body=_encode_value(readable_log_record.log_record.body),
        severity_text=readable_log_record.log_record.severity_text,
        attributes=_encode_attributes(cast(Attributes, readable_log_record.log_record.attributes)),
        dropped_attributes_count=readable_log_record.dropped_attributes,
        severity_number=getattr(readable_log_record.log_record.severity_number, "value", None),
        event_name=readable_log_record.log_record.event_name,
    )


def _encode_resource_logs(
    batch: Collection[ReadableLogRecord],
) -> list[JSONResourceLogs]:
    """Group a flat collection of SDK log records into OTLP ``ResourceLogs``.

    Records sharing a resource end up in one ``ResourceLogs``, and within it
    records sharing an instrumentation scope end up in one ``ScopeLogs``. The
    schema URL of the resource is written on the ``ResourceLogs`` and the
    schema URL of the scope on the ``ScopeLogs``.

    Args:
        batch: the log records to group, in any order.

    Returns:
        One ``ResourceLogs`` per distinct resource, in the order each resource
        was first seen in ``batch``. A record whose instrumentation scope is
        absent or falsy is grouped under a scope of ``None``, which encodes as
        an empty scope message and leaves the schema URL of the ``ScopeLogs``
        unset.

    Raises:
        TypeError: if the body of a record, or any value nested inside a
            mapping or a sequence body, is of a type OTLP has no
            representation for.
    """
    sdk_resource_logs = defaultdict(lambda: defaultdict(list))

    for readable_log in batch:
        sdk_resource = readable_log.resource
        sdk_instrumentation = readable_log.instrumentation_scope or None
        sdk_resource_logs[sdk_resource][sdk_instrumentation].append(_encode_log(readable_log))

    json_resource_logs = []
    for sdk_resource, sdk_instrumentations in sdk_resource_logs.items():
        scope_logs = []
        for sdk_instrumentation, json_logs in sdk_instrumentations.items():
            scope_logs.append(
                JSONScopeLogs(
                    scope=(_encode_instrumentation_scope(sdk_instrumentation)),
                    log_records=json_logs,
                    schema_url=sdk_instrumentation.schema_url if sdk_instrumentation else None,
                )
            )
        json_resource_logs.append(
            JSONResourceLogs(
                resource=_encode_resource(sdk_resource),
                scope_logs=scope_logs,
                schema_url=sdk_resource.schema_url,
            )
        )

    return json_resource_logs
