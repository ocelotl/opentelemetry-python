# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-opencensus`` distribution.

``__version__`` is the single place the release tooling rewrites, and
``pyproject.toml`` reads it from here rather than carrying its own copy.
``opentelemetry.exporter.opencensus.util.get_node`` sends the same string to
the collector as the ``exporter_version`` field of the ``LibraryInfo`` that
the OpenCensus ``Node`` message carries, next to ``language`` and
``core_library_version``. No field of that message names the exporter, so a
collector sees the version and not the distribution it came from.
"""

__version__ = "0.67b0.dev"
