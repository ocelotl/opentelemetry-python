# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Single source of the distribution version.

``pyproject.toml`` points ``hatch`` at the ``__version__`` assignment below,
so editing it changes the version of the built distribution. The release
tooling of the repository rewrites it across every package at once, which is
why it is a plain string literal and not computed.
"""

__version__ = "0.67b0.dev"
