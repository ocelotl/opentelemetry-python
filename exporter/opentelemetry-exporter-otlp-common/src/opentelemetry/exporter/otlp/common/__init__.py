# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Code shared by the OTLP exporters.

The OTLP exporter distributions for traces, metrics and logs import this
package regardless of the encoding they send. ``http`` submits a serialized
payload over HTTP and retries it when the failure is transient,
``_aggregation`` turns the OTLP metric environment variables into the
temporality and aggregation preferences an exporter passes to the SDK, and
``_exporter_metrics`` records how much telemetry an exporter submitted and how
long each attempt took.

Every name in this package is internal to the OTLP exporters. Nothing here is
covered by the backward compatibility policy of the project, so an application
that imports it may break on any release.
"""
