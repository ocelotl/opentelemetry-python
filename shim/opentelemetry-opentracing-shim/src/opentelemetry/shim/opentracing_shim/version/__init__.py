# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Version of the ``opentelemetry-opentracing-shim`` distribution.

``opentelemetry.shim.opentracing_shim.create_tracer`` passes ``__version__``
to ``opentelemetry.trace.TracerProvider.get_tracer`` as the version of the
instrumentation scope, so every span created through the shim carries it. This
is the version of the shim itself, not of the OpenTracing API it implements
nor of the OpenTelemetry API it calls.
"""

__version__ = "0.67b0.dev"
