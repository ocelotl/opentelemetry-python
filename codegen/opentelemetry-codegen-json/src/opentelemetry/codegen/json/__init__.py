# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Protocol buffer plugin that generates OTLP/JSON dataclasses.

``protoc`` discovers this generator as the plugin named ``otlp_json``, through the
``protoc-gen-otlp_json`` console script declared in the distribution metadata of
``opentelemetry-codegen-json``. Passing ``--otlp_json_out=<directory>`` to ``protoc`` makes it run
``opentelemetry.codegen.json.plugin.main``, which hands the request to
``opentelemetry.codegen.json.generator``.

For each ``.proto`` file the generator emits one Python module holding a ``slots=True`` dataclass
per protobuf message and an ``enum.IntEnum`` per protobuf enum. Every generated message class
carries ``to_dict`` and ``from_dict`` methods that implement the Proto3 JSON mapping, with the
OTLP deviation that ``trace_id``, ``span_id`` and ``parent_span_id`` are hex encoded rather than
base64 encoded. Alongside those modules it copies
``opentelemetry.codegen.json.runtime.json_codec`` into the output tree as ``_json_codec``, which is
the only part of this distribution that the generated code imports at runtime.

The modules here are hand-written. The modules they emit, which make up the
``opentelemetry-proto-json`` distribution, carry an ``AUTO-GENERATED`` header and must never be
edited by hand.
"""
