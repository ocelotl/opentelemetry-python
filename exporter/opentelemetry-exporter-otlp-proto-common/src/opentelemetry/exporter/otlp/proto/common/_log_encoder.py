# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Entry point for log record encoding.

Re-exports ``encode_logs``, which converts a sequence of
``opentelemetry.sdk._logs.ReadableLogRecord`` into the protobuf
``ExportLogsServiceRequest`` that an OTLP exporter sends. The leading underscore
in the module name mirrors the one in ``opentelemetry.sdk._logs``, the SDK
package the records come from, and the two sibling modules ``trace_encoder`` and
``metrics_encoder`` carry no underscore.
"""

from opentelemetry.exporter.otlp.proto.common._internal._log_encoder import (
    encode_logs,
)

__all__ = ["encode_logs"]
