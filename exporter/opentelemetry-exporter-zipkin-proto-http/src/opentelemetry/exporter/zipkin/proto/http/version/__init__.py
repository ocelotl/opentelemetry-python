# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-zipkin-proto-http`` distribution.

``__version__`` is the single place the version is written. The distribution
declares ``version`` as dynamic and points ``[tool.hatch.version]`` at this
file, so hatchling reads the value from here when it builds the distribution,
and a release updates this file rather than the packaging metadata.
"""

__version__ = "1.46.0.dev"
