# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Encoders shared by the OTLP JSON exporters.

This package converts the telemetry that the OpenTelemetry SDK holds in memory
into the dataclasses of ``opentelemetry.proto_json``, whose ``to_dict`` methods
produce the OTLP JSON wire representation. It performs no input and output of
its own. ``opentelemetry-exporter-otlp-json-http`` and
``opentelemetry-exporter-otlp-json-file`` depend on this package, which is what
makes the two of them encode the three signals identically.

The three entry points are ``encode_spans`` in
``opentelemetry.exporter.otlp.json.common.trace_encoder``, ``encode_metrics``
in ``opentelemetry.exporter.otlp.json.common.metrics_encoder`` and
``encode_logs`` in ``opentelemetry.exporter.otlp.json.common._log_encoder``.
Everything under ``opentelemetry.exporter.otlp.json.common._internal`` is
private and can change in any release.
"""
