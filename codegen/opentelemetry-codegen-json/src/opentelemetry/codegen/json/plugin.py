# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=no-member

"""The ``protoc`` plugin entry point for the OTLP/JSON generator.

``protoc`` invokes a plugin as a separate process, with an empty argument vector. It writes a
serialized ``CodeGeneratorRequest`` to the standard input of that process and reads a serialized
``CodeGeneratorResponse`` back from its standard output, so a plugin must keep both streams free
of anything else. Diagnostics therefore go to standard error.

Nothing configures logging on the path ``protoc`` takes. The ``logging.basicConfig`` call below
runs only when this module is executed as ``__main__``, and ``protoc`` reaches ``main`` through
the console script instead, which imports the module under its own name. A record of ``WARNING``
or above therefore arrives at standard error through ``logging.lastResort``, carrying its message
alone and none of the formatting set up below, and a record under ``WARNING`` is dropped.

``protoc`` finds this module through the ``protoc-gen-otlp_json`` console script, which the
``opentelemetry-codegen-json`` distribution declares. The name after ``protoc-gen-`` is the plugin
name, so ``--otlp_json_out=<directory>`` on a ``protoc`` command line is what runs ``main``.

The actual generation lives in ``opentelemetry.codegen.json.generator``. This module only handles
the process protocol around it.
"""

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager

from google.protobuf.compiler import plugin_pb2 as plugin

from opentelemetry.codegen.json.generator import generate_plugin_response

_logger = logging.getLogger(__name__)


@contextmanager
def code_generation() -> Iterator[tuple[plugin.CodeGeneratorRequest, plugin.CodeGeneratorResponse],]:
    """
    Read the ``protoc`` request from standard input and write the response to standard output.

    Unless the version branch below is taken, on entry this reads every byte of standard input,
    parses it as a ``CodeGeneratorRequest``, and yields that request together with an empty
    ``CodeGeneratorResponse`` for the body of the ``with`` statement to fill in. On exit it
    serializes the response and writes it to standard output.

    Two cases write no response to standard output at all. A first command line argument of
    ``-V`` or ``--version`` prints the version and calls ``sys.exit`` before anything is read from
    standard input, so the body never runs and the call does not block on a stream that may never
    close. That branch answers a version query typed directly at the console script;
    ``protoc`` never reaches it, because ``protoc`` runs a plugin with an empty argument vector.
    An exception raised inside the body propagates instead, and because the serialization is
    placed after the ``yield`` rather than in a ``finally`` block, it is skipped, so ``protoc``
    reports the failure instead of accepting a partial result.

    Returns:
        A context manager yielding the parsed ``CodeGeneratorRequest`` and the empty
        ``CodeGeneratorResponse`` that the caller is expected to populate.
    """
    if len(sys.argv) > 1 and sys.argv[1] in ("-V", "--version"):
        print("opentelemetry-codegen-json 0.0.0")
        sys.exit(0)

    data = sys.stdin.buffer.read()

    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    response = plugin.CodeGeneratorResponse()

    yield request, response

    output = response.SerializeToString()
    sys.stdout.buffer.write(output)


def main() -> None:
    """
    Run one ``protoc`` plugin invocation.

    This is the callable behind the ``protoc-gen-otlp_json`` console script. It passes the request
    read from standard input to
    ``opentelemetry.codegen.json.generator.generate_plugin_response``, then copies the feature
    flags and every generated file from that result onto the response that ``code_generation``
    writes out.

    The copy is needed because ``code_generation`` owns the response object that gets serialized,
    and a protobuf message field cannot be rebound to another message, only merged into.
    """
    with code_generation() as (request, response):
        generated_response = generate_plugin_response(request)

        response.supported_features |= generated_response.supported_features
        for file in generated_response.file:
            response.file.add().CopyFrom(file)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        stream=sys.stderr,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
