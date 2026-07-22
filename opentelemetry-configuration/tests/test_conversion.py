# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import unittest
from dataclasses import dataclass
from typing import Any, ClassVar

from opentelemetry.configuration._common import _additional_properties
from opentelemetry.configuration._conversion import _dict_to_dataclass
from opentelemetry.configuration.models import ExemplarFilter, SpanExporter


@dataclass
class _Inner:
    value: int | None = None


@dataclass
class _Middle:
    inner: _Inner | None = None
    items: list[_Inner] | None = None


@dataclass
class _Outer:
    middle: _Middle | None = None
    name: str | None = None


@_additional_properties
@dataclass
class _WithExtras:
    known: str | None = None
    additional_properties: ClassVar[dict[str, Any]]


@dataclass
class _WithEnum:
    filter: ExemplarFilter | None = None


class TestDictToDataclass(unittest.TestCase):
    def test_raises_on_non_dataclass(self):
        # _dict_to_dataclass is internal and assumes cls is a dataclass.
        with self.assertRaises(TypeError) as ctx:
            _dict_to_dataclass({"x": 1}, dict)
        self.assertIn("not a dataclass", str(ctx.exception))

    def test_converts_flat_dict(self):
        result = _dict_to_dataclass({"value": 42}, _Inner)
        self.assertIsInstance(result, _Inner)
        self.assertEqual(result.value, 42)

    def test_converts_nested_dataclass(self):
        result = _dict_to_dataclass(
            {"middle": {"inner": {"value": 7}}}, _Outer
        )
        self.assertIsInstance(result, _Outer)
        self.assertIsInstance(result.middle, _Middle)
        self.assertIsInstance(result.middle.inner, _Inner)
        self.assertEqual(result.middle.inner.value, 7)

    def test_converts_list_of_dataclasses(self):
        result = _dict_to_dataclass(
            {"middle": {"items": [{"value": 1}, {"value": 2}]}}, _Outer
        )
        self.assertEqual(len(result.middle.items), 2)
        self.assertIsInstance(result.middle.items[0], _Inner)
        self.assertEqual(result.middle.items[0].value, 1)
        self.assertEqual(result.middle.items[1].value, 2)

    def test_present_null_dataclass_becomes_defaults_instance(self):
        # A present-but-null value for a dataclass-typed field must build that
        # dataclass with all defaults, so it is distinguishable from an absent
        # key. Primitives present-null stay None (their "use default" value).
        result = _dict_to_dataclass({"middle": None, "name": "test"}, _Outer)
        self.assertIsInstance(result.middle, _Middle)
        self.assertIsNone(result.middle.inner)
        self.assertIsNone(result.middle.items)
        self.assertEqual(result.name, "test")

    def test_present_null_primitive_stays_none(self):
        result = _dict_to_dataclass({"name": None}, _Outer)
        self.assertIsNone(result.name)

    def test_missing_optional_fields_default_to_none(self):
        # Absent keys stay None; this is what "not configured" looks like and
        # must remain distinguishable from present-null.
        result = _dict_to_dataclass({}, _Outer)
        self.assertIsNone(result.middle)
        self.assertIsNone(result.name)

    def test_present_null_mapping_alias_becomes_empty_dict(self):
        # The console exporter field is typed as ``dict[str, Any] | None``.
        # A present-null value must become an empty mapping so a component
        # factory selecting on ``value is not None`` still fires and builds
        # the console exporter with defaults.
        result = _dict_to_dataclass({"console": None}, SpanExporter)
        self.assertEqual(result.console, {})

    def test_absent_component_stays_none(self):
        # Absent component keys must remain None ("not configured").
        result = _dict_to_dataclass({}, SpanExporter)
        self.assertIsNone(result.console)
        self.assertIsNone(result.otlp_http)

    def test_populated_component_mapping_still_converts(self):
        # A populated component mapping must still convert into a typed
        # dataclass instance with its values carried through.
        result = _dict_to_dataclass(
            {"otlp_http": {"endpoint": "http://localhost:4318"}}, SpanExporter
        )
        self.assertIsNone(result.console)
        self.assertEqual(
            result.otlp_http.endpoint, "http://localhost:4318"
        )

    def test_unknown_keys_routed_to_additional_properties(self):
        result = _dict_to_dataclass(
            {"known": "yes", "my_plugin": {"opt": True}}, _WithExtras
        )
        self.assertEqual(result.known, "yes")
        self.assertEqual(
            result.additional_properties, {"my_plugin": {"opt": True}}
        )

    def test_primitive_values_pass_through(self):
        result = _dict_to_dataclass({"name": "hello"}, _Outer)
        self.assertEqual(result.name, "hello")

    def test_empty_list_converted(self):
        result = _dict_to_dataclass({"middle": {"items": []}}, _Outer)
        self.assertEqual(result.middle.items, [])

    def test_enum_value_coerced_from_string(self):
        result = _dict_to_dataclass({"filter": "always_on"}, _WithEnum)
        self.assertIs(result.filter, ExemplarFilter.always_on)

    def test_enum_value_already_enum_passes_through(self):
        result = _dict_to_dataclass(
            {"filter": ExemplarFilter.trace_based}, _WithEnum
        )
        self.assertIs(result.filter, ExemplarFilter.trace_based)
