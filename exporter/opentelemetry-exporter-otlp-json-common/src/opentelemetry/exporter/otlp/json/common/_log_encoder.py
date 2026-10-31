# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Access to the OTLP JSON log record encoder.

``encode_logs`` is implemented in
``opentelemetry.exporter.otlp.json.common._internal._log_encoder`` and
re-exported here. A log record exporter should import it from this module
rather than from the implementation module, whose contents can change in any
release. The leading underscore in the name of this module mirrors the one on
``opentelemetry.sdk._logs``, the logs part of the SDK being unstable, and is
not an instruction to import from somewhere else.
"""

from opentelemetry.exporter.otlp.json.common._internal._log_encoder import (
    encode_logs,
)

__all__ = ["encode_logs"]
