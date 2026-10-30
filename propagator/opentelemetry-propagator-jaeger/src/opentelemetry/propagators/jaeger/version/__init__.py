# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-propagator-jaeger`` distribution.

``pyproject.toml`` points ``tool.hatch.version`` at this module, so the version
that a build of the distribution publishes is whatever ``__version__`` is set
to here.

``__version__`` is written by the release tooling rather than edited by hand.
``eachdist.ini`` carries one version for every distribution listed under its
``[stable]`` section, this one among them, and the ``update_versions``
subcommand of ``scripts/eachdist.py`` substitutes that value into this file. An
edit made here alone is reverted by the next run of that subcommand.
"""

__version__ = "1.46.0.dev"
