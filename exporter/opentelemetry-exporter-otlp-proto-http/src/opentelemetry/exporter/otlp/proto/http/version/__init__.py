# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-otlp-proto-http`` distribution.

``pyproject.toml`` reads ``__version__`` from this file, through the path its
``[tool.hatch.version]`` table declares, so this is where the built
distribution takes its version from. The string is not edited here by hand:
``scripts/eachdist.py`` rewrites it from the version recorded for the
``[stable]`` package set in ``eachdist.ini``. The exporters also send it in the
``User-Agent`` header of every export request, unless the resolved headers
carry a ``user-agent`` key of their own, which replaces it.
"""

__version__ = "1.46.0.dev"
