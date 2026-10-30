# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Names that the span encoder used to live under.

The encoding itself moved to
``opentelemetry.exporter.otlp.proto.common.trace_encoder``, which is what
:class:`~opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter`
calls. This module defines no encoding of its own. It only re-imports the names
the removed encoder exposed, protobuf, SDK and standard library alike, so that
code written against the old import path keeps working, and nothing here should
be used in new code.
"""

import logging  # noqa: F401
from collections import abc  # noqa: F401
from collections.abc import Sequence  # noqa: F401

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (  # noqa: F401
    ExportTraceServiceRequest as PB2ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    AnyValue as PB2AnyValue,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    ArrayValue as PB2ArrayValue,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    InstrumentationScope as PB2InstrumentationScope,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    KeyValue as PB2KeyValue,
)
from opentelemetry.proto.resource.v1.resource_pb2 import (  # noqa: F401
    Resource as PB2Resource,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (  # noqa: F401
    ResourceSpans as PB2ResourceSpans,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (  # noqa: F401
    ScopeSpans as PB2ScopeSpans,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (  # noqa: F401
    Span as PB2SPan,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (  # noqa: F401
    Status as PB2Status,
)
from opentelemetry.sdk.trace import (
    Event,  # noqa: F401
    Resource,  # noqa: F401
)
from opentelemetry.sdk.trace import Span as SDKSpan  # noqa: F401
from opentelemetry.sdk.util.instrumentation import (  # noqa: F401
    InstrumentationScope,
)
from opentelemetry.trace import (
    Link,  # noqa: F401
    SpanKind,  # noqa: F401
)
from opentelemetry.trace.span import (  # noqa: F401
    SpanContext,
    Status,
    TraceState,
)
from opentelemetry.util.types import Attributes  # noqa: F401
