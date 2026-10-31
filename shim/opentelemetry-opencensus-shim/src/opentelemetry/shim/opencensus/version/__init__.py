# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-opencensus-shim`` distribution.

``hatchling`` reads ``__version__`` from this module at build time, as configured by the
``tool.hatch.version`` table of ``shim/opentelemetry-opencensus-shim/pyproject.toml``, so this
assignment is the single place the distribution version is written. ``install_shim`` passes the
same string as the version of the instrumentation scope of the OpenTelemetry tracer it creates,
which is how a backend can tell which release of the shim produced a span.
"""

__version__ = "0.67b0.dev"
