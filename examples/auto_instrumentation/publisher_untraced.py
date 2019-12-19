from flask import Flask, request

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerSource
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)

app = Flask(__name__)

trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())

trace.tracer_source().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)


@app.route("/publish_request")
def publish_request():
    hello_str = request.args.get("helloStr")
    print(hello_str)
    return "published"


if __name__ == "__main__":
    app.run(port=8082)
