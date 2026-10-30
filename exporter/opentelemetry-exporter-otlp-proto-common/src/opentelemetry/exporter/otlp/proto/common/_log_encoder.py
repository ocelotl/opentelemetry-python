# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Entry point for log record encoding.

Re-exports ``encode_logs``, which converts a sequence of
``opentelemetry.sdk._logs.ReadableLogRecord`` into the protobuf
``ExportLogsServiceRequest`` that an OTLP exporter sends. The module name keeps
the leading underscore that the SDK logs packages carry, because the logs signal
is not yet covered by the stability guarantees that apply to traces and metrics.
"""

from opentelemetry.exporter.otlp.proto.common._internal._log_encoder import (
    encode_logs,
)

__all__ = ["encode_logs"]
