# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-otlp-common`` distribution.

The ``tool.hatch.version`` table of the ``pyproject.toml`` of the distribution
points at this module, so ``hatchling`` reads ``__version__`` from here when it
builds the wheel and the source distribution. The ``update_versions`` and
``update_patch_versions`` subcommands of ``scripts/eachdist.py`` rewrite the
``__version__`` assignment here, so this module is the single place that
records the version of the distribution.
"""

__version__ = "0.67b0.dev"
