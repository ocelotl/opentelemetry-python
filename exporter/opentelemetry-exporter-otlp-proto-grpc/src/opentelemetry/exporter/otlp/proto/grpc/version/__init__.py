# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-otlp-proto-grpc`` distribution.

This constant has two consumers. ``pyproject.toml`` declares
``dynamic = ["version"]`` and points ``[tool.hatch.version]`` at this file, so
the value is the version of the built distribution and there is no other
source for it. ``opentelemetry.exporter.otlp.proto.grpc`` also reads it to
build this package's default ``grpc.primary_user_agent`` channel option, which
is how the version reaches the receiver. An exporter given a
``channel_options`` entry of that same name keeps the caller's value and drops
the default, and then sends no version of this package at all.
"""

__version__ = "1.46.0.dev"
