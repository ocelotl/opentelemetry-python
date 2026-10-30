# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Build time code generators for OpenTelemetry Python.

Nothing under ``opentelemetry.codegen`` runs while an application is emitting telemetry. These
modules are invoked by ``protoc`` during development, read protocol buffer descriptors, and write
Python source files that are then committed to the repository and shipped as ordinary modules.

``opentelemetry.codegen.json`` is the only generator that currently lives here. It produces the
contents of the ``opentelemetry-proto-json`` distribution.
"""
