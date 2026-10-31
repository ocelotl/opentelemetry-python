# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Public access to the OTLP JSON span encoder.

``encode_spans`` is implemented in
``opentelemetry.exporter.otlp.json.common._internal.trace_encoder`` and
re-exported here. A span exporter should import it from this module, because
the implementation module is private and its contents can change in any
release.
"""

from opentelemetry.exporter.otlp.json.common._internal.trace_encoder import (
    encode_spans,
)

__all__ = ["encode_spans"]
