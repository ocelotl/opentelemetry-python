import sys
import time

import requests
from flask import Flask

from opentelemetry import propagators, trace
from opentelemetry.context.propagation.tracecontexthttptextformat import (
    TraceContextHTTPTextFormat,
)
from opentelemetry.propagators import set_global_httptextformat
from opentelemetry.sdk.trace import TracerSource
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)

app = Flask(__name__)

trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())
tracer = trace.tracer_source().get_tracer(__name__)

trace.tracer_source().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
set_global_httptextformat(TraceContextHTTPTextFormat)


def http_get(port, path, param, value):

    headers = {}
    propagators.inject(tracer, dict.__setitem__, headers)

    requested = requests.get(
        "http://localhost:{}/{}".format(port, path),
        params={param: value},
        headers=headers,
    )

    assert requested.status_code == 200
    return requested.text


assert len(sys.argv) == 2

hello_to = sys.argv[1]

with tracer.start_as_current_span("hello") as hello_span:

    with tracer.start_as_current_span("hello-format", parent=hello_span):
        hello_str = http_get(8081, "format_request", "helloTo", hello_to)

    with tracer.start_as_current_span("hello-publish", parent=hello_span):
        http_get(8082, "publish_request", "helloStr", hello_str)

# yield to IOLoop to flush the spans
time.sleep(2)
