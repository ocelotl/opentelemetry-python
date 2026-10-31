# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-configuration`` distribution.

``pyproject.toml`` points hatchling's version source at this module, so
``__version__`` is the single place the distribution version is written
down. The declarative configuration packages track the SDK's ``0.x``
series rather than the stable ``1.x`` API version.
"""

__version__ = "0.67b0.dev"
