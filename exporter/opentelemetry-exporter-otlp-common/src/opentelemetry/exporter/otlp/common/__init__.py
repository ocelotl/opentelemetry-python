# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Code shared by the OTLP exporters.

The OTLP exporter distributions for traces, metrics and logs import this
package regardless of the encoding they send. ``http`` submits a serialized
payload over HTTP and retries it when the failure is transient,
``_aggregation`` turns the OTLP metric environment variables into the
temporality and aggregation preferences an exporter passes to the SDK, and
``_exporter_metrics`` records how much telemetry an exporter finished
exporting, whether it succeeded or failed, and how long each export operation
took, counting every retry of one payload as part of the same export operation.

Every name in this package is internal to the OTLP exporters and is not covered
by the backward compatibility policy of the project, so an application that
imports one may break on any release. ``Compression`` is the one name an
application meets anyway. The OTLP JSON over HTTP exporters give it as the only
type of their ``compression`` constructor parameter, so selecting a compression
scheme for one of those in code means importing it from
``opentelemetry.exporter.otlp.common.http``. The OTLP protobuf over HTTP
exporters accept it alongside their own
``opentelemetry.exporter.otlp.proto.http.Compression``, which is the one to
prefer there.
"""
