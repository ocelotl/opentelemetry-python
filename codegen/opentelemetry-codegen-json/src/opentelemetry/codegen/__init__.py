# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Build time code generators for OpenTelemetry Python.

Nothing under ``opentelemetry.codegen`` runs while an application is emitting telemetry. These
modules are invoked by ``protoc`` during development and read protocol buffer descriptors, then
hand the Python source they build back to ``protoc``, which is the program that writes the files.
Those files are then committed to the repository and shipped as ordinary modules.

``opentelemetry.codegen.json`` is the only generator that currently lives here. It produces the
contents of the ``opentelemetry-proto-json`` distribution.
"""
