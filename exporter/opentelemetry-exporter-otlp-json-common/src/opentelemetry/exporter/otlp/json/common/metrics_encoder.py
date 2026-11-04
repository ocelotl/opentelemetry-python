# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Public access to the OTLP JSON metrics encoder.

``encode_metrics`` is implemented in
``opentelemetry.exporter.otlp.json.common._internal.metrics_encoder`` and
re-exported here. A metric exporter should import it from this module, because
the implementation module is private and its contents can change in any
release.

``split_metrics_data``, which cuts an encoded request into smaller ones, is
deliberately left out of this module. An exporter that needs it has to accept
that it is reaching into private code.
"""

from opentelemetry.exporter.otlp.json.common._internal.metrics_encoder import (
    encode_metrics,
)

__all__ = ["encode_metrics"]
