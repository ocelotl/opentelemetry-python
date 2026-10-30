# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-otlp-json-http`` distribution.

``__version__`` is the single place the release tooling rewrites when the
distribution is published. The three exporters in this package send it to the
collector in the ``user-agent`` request header, formatted as
``OTel-OTLP-JSON-Exporter-Python/<version>``, so a backend can attribute a
payload to the exporter release that produced it.
"""

__version__ = "0.67b0.dev"
