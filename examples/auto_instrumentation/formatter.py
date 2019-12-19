from flask import Flask, request

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
from utils import get_as_list

app = Flask(__name__)

trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())
tracer = trace.tracer_source().get_tracer(__name__)

trace.tracer_source().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
set_global_httptextformat(TraceContextHTTPTextFormat)


@app.route("/format_request")
def format_request():

    with tracer.start_as_current_span(
        "format_request",
        parent=propagators.extract(get_as_list, request.headers),
    ):
        hello_to = request.args.get("helloTo")
        return "Hello, %s!" % hello_to


if __name__ == "__main__":
    app.run(port=8081)
