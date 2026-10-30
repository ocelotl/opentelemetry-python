# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Public entry point for metrics encoding.

Re-exports ``encode_metrics``, which converts
:class:`opentelemetry.sdk.metrics.export.MetricsData` into the protobuf
``ExportMetricsServiceRequest`` that an OTLP exporter sends. Import it from here
rather than from the ``_internal`` subpackage that defines it, because only this
module is part of the supported surface.
"""

from opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder import (
    encode_metrics,
)

__all__ = ["encode_metrics"]
