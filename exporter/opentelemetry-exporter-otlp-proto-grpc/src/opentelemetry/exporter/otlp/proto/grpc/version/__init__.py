# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-otlp-proto-grpc`` distribution.

The value is read by ``opentelemetry.exporter.otlp.proto.grpc`` to build this
package's default ``grpc.primary_user_agent`` channel option, which is how the
version reaches the receiver. An exporter given a ``channel_options`` entry of
that same name keeps the caller's value and drops the default, and then sends
no version at all.
"""

__version__ = "1.46.0.dev"
