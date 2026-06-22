"""Pure-Python equivalents of opentelemetry/proto/logs/v1/logs_pb2.py.

Field numbers:
    LogRecord      time_unix_nano=1  severity_number=2  severity_text=3
                   body=5  attributes=6  dropped_attrs_count=7  flags=8
                   trace_id=9  span_id=10  observed_time_unix_nano=11
                   event_name=12
    ScopeLogs      scope=1  log_records=2  schema_url=3
    ResourceLogs   resource=1  scope_logs=2  schema_url=3
"""

from __future__ import annotations

from opentelemetry.pyproto.common.v1.common_pyproto2 import (
    AnyValue,
    InstrumentationScope,
    KeyValue,
)
from opentelemetry.pyproto.resource.v1.resource_pyproto2 import Resource
from opentelemetry.pyproto._pyprotobuf.fields import (
    _byt,
    _fix32,
    _fix64,
    _msg,
    _str,
    _u64,
)


class LogRecord:
    def __init__(
        self,
        time_unix_nano: int = 0,
        severity_number: int = 0,
        severity_text: str = "",
        body: AnyValue | None = None,
        attributes: list[KeyValue] | None = None,
        dropped_attributes_count: int = 0,
        flags: int = 0,
        trace_id: bytes = b"",
        span_id: bytes = b"",
        observed_time_unix_nano: int = 0,
        event_name: str = "",
    ):
        self.time_unix_nano = time_unix_nano
        self.severity_number = severity_number
        self.severity_text = severity_text
        self.body = body
        self.attributes: list[KeyValue] = list(attributes) if attributes else []
        self.dropped_attributes_count = dropped_attributes_count
        self.flags = flags
        self.trace_id = trace_id
        self.span_id = span_id
        self.observed_time_unix_nano = observed_time_unix_nano
        self.event_name = event_name

    def SerializeToString(self) -> bytes:
        result = (
            _fix64(1, self.time_unix_nano)
            + _u64(2, self.severity_number)
            + _str(3, self.severity_text)
        )
        if self.body is not None:
            result += _msg(5, self.body.SerializeToString())
        result += (
            b"".join(_msg(6, kv.SerializeToString()) for kv in self.attributes)
            + _u64(7, self.dropped_attributes_count)
            + _fix32(8, self.flags)
            + _byt(9, self.trace_id)
            + _byt(10, self.span_id)
            + _fix64(11, self.observed_time_unix_nano)
            + _str(12, self.event_name)
        )
        return result


class ScopeLogs:
    def __init__(
        self,
        scope: InstrumentationScope | None = None,
        log_records: list[LogRecord] | None = None,
        schema_url: str = "",
    ):
        self.scope = scope
        self.log_records: list[LogRecord] = list(log_records) if log_records else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.scope is not None:
            result += _msg(1, self.scope.SerializeToString())
        result += b"".join(_msg(2, lr.SerializeToString()) for lr in self.log_records)
        result += _str(3, self.schema_url)
        return result


class ResourceLogs:
    def __init__(
        self,
        resource: Resource | None = None,
        scope_logs: list[ScopeLogs] | None = None,
        schema_url: str = "",
    ):
        self.resource = resource
        self.scope_logs: list[ScopeLogs] = list(scope_logs) if scope_logs else []
        self.schema_url = schema_url

    def SerializeToString(self) -> bytes:
        result = b""
        if self.resource is not None:
            result += _msg(1, self.resource.SerializeToString())
        result += b"".join(_msg(2, sl.SerializeToString()) for sl in self.scope_logs)
        result += _str(3, self.schema_url)
        return result
