# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-test-utils`` distribution.

``[tool.hatch.version]`` in ``tests/opentelemetry-test-utils/pyproject.toml``
points at this module, so ``__version__`` is the version that the built sdist
and wheel carry. That is its only reader: nothing in this repository imports
``__version__`` from here. A test asserting on an instrumentation scope version
wants the version module of the package under test instead, which is on a
different version line from this one.
"""

__version__ = "0.67b0.dev"
