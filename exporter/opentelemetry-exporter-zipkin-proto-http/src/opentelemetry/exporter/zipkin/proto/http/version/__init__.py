# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-zipkin-proto-http`` distribution.

``__version__`` is where this distribution stores its own version number. The
packaging metadata declares ``version`` as dynamic and points
``[tool.hatch.version]`` at this file, so hatchling reads the value from here
when it builds the distribution and the metadata states no version of its own.

A release does not stop at this file. ``scripts/eachdist.py`` also rewrites the
version pins that other packages of the repository are declared with, so the
dependency on ``opentelemetry-exporter-zipkin-json`` moves at the same time.
"""

__version__ = "1.46.0.dev"
