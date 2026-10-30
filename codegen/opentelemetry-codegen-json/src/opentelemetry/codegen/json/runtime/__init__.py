# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Source modules that the generator copies verbatim into its output.

The generator does not import a module under ``opentelemetry.codegen.json.runtime`` in order to
call it. It reads the text of the module off disk and writes that text into the generated package,
so that the generated code never requires ``opentelemetry-codegen-json`` to be installed.

``opentelemetry.codegen.json.runtime.json_codec`` is the only such module. It lands in the output
tree as ``_json_codec``, next to the generated message modules.

Changing a module here changes every package generated afterwards, so the copies already committed
under ``opentelemetry-proto-json`` stay as they are until the next regeneration.
"""
