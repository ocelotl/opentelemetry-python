# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-otlp-json-common`` distribution.

``[tool.hatch.version]`` in the ``pyproject.toml`` of the distribution names
this module, so the ``__version__`` string below is the version that hatchling
writes into a built wheel or sdist. ``opentelemetry-exporter-otlp-json-http``
and ``opentelemetry-exporter-otlp-json-file`` require this distribution at an
exact version, so a change here has to be made in those two pins as well.
"""

__version__ = "0.67b0.dev"
