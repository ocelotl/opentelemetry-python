# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-test-utils`` distribution.

``[tool.hatch.version]`` in ``tests/opentelemetry-test-utils/pyproject.toml``
points at this module, so ``__version__`` is the version that the built sdist
and wheel carry. Tests that assert on an instrumentation scope version import
it from here rather than hard-coding a string.
"""

__version__ = "0.67b0.dev"
