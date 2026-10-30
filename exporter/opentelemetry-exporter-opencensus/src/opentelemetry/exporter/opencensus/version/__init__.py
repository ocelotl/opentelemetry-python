# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-opencensus`` distribution.

``__version__`` is the single place the release tooling rewrites, and
``pyproject.toml`` reads it from here rather than carrying its own copy.
``opentelemetry.exporter.opencensus.util.get_node`` sends the same string to
the collector as the ``exporter_version`` field of the OpenCensus ``Node``
message, which is how a collector reports which exporter produced a span.
"""

__version__ = "0.67b0.dev"
