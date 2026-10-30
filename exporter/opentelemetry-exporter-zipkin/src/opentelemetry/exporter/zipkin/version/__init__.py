# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-exporter-zipkin`` distribution.

``opentelemetry-exporter-zipkin`` carries no exporter code of its own. It is a
meta-distribution whose only purpose is to install every supported Zipkin
exporter at a single matching version, so its dependencies are
``opentelemetry-exporter-zipkin-json`` and
``opentelemetry-exporter-zipkin-proto-http``.

An exporter class is therefore imported from one of those two distributions.
``opentelemetry-exporter-zipkin-json`` provides
``opentelemetry.exporter.zipkin.json.ZipkinExporter``, which sends spans as
Zipkin JSON over HTTP, and ``opentelemetry-exporter-zipkin-proto-http``
provides ``opentelemetry.exporter.zipkin.proto.http.ZipkinExporter``, which
sends them as Zipkin protobuf over HTTP. Once the serialization is settled,
depending on that one distribution directly leaves the other one, and the
dependencies it brings, out of the environment.

``opentelemetry-exporter-zipkin`` also registers an
``opentelemetry_traces_exporter`` entry point named ``zipkin``, which resolves
to ``opentelemetry.exporter.zipkin.proto.http.ZipkinExporter``. The two
distributions it depends on register their own entry points, ``zipkin_json``
and ``zipkin_proto``, so those two names work without this one installed.
"""

__version__ = "1.46.0.dev"
"""The installed version of ``opentelemetry-exporter-zipkin``, as a :pep:`440` string."""
