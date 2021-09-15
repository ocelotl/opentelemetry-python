# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import TestCase
from inspect import signature, Signature, isabstract
from logging import ERROR

from opentelemetry.metrics import _DefaultMeter, Meter
from opentelemetry.metrics.instrument import (
    Instrument,
    Counter,
    DefaultCounter,
    ObservableCounter,
    DefaultObservableCounter,
)


class ChildInstrument(Instrument):
    def __init__(self, name, *args, unit="", description="", **kwargs):
        super().__init__(
            name, *args, unit=unit, description=description, **kwargs
        )


class TestInstrument(TestCase):

    def test_instrument_has_name(self):
        """
        Test that the instrument has name.
        """

        init_signature = signature(Instrument.__init__)
        self.assertIn("name", init_signature.parameters.keys())
        self.assertIs(
            init_signature.parameters["name"].default, Signature.empty
        )

        self.assertTrue(hasattr(Instrument, "name"))

    def test_instrument_has_unit(self):
        """
        Test that the instrument has unit.
        """

        init_signature = signature(Instrument.__init__)
        self.assertIn("unit", init_signature.parameters.keys())
        self.assertIs(
            init_signature.parameters["unit"].default, ""
        )

        self.assertTrue(hasattr(Instrument, "unit"))

    def test_instrument_has_description(self):
        """
        Test that the instrument has description.
        """

        init_signature = signature(Instrument.__init__)
        self.assertIn("description", init_signature.parameters.keys())
        self.assertIs(
            init_signature.parameters["description"].default, ""
        )

        self.assertTrue(hasattr(Instrument, "description"))

    def test_instrument_name_syntax(self):
        """
        Test that instrument names conform to the specified syntax.
        """

        with self.assertLogs(level=ERROR):
            ChildInstrument("")

        with self.assertLogs(level=ERROR):
            ChildInstrument(None)

        with self.assertLogs(level=ERROR):
            ChildInstrument("1a")

        with self.assertLogs(level=ERROR):
            ChildInstrument("_a")

        with self.assertLogs(level=ERROR):
            ChildInstrument("!a ")

        with self.assertLogs(level=ERROR):
            ChildInstrument("a ")

        with self.assertLogs(level=ERROR):
            ChildInstrument("a%")

        with self.assertLogs(level=ERROR):
            ChildInstrument("a" * 64)

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=ERROR):
                ChildInstrument("abc_def_ghi")

    def test_instrument_unit_syntax(self):
        """
        Test that instrument unit conform to the specified syntax.
        """

        with self.assertLogs(level=ERROR):
            ChildInstrument("name", unit="a" * 64)

        with self.assertLogs(level=ERROR):
            ChildInstrument("name", unit="ñ")

        child_instrument = ChildInstrument("name", unit="a")
        self.assertEqual(child_instrument.unit, "a")

        child_instrument = ChildInstrument("name", unit="A")
        self.assertEqual(child_instrument.unit, "A")

        child_instrument = ChildInstrument("name")
        self.assertEqual(child_instrument.unit, "")

        child_instrument = ChildInstrument("name", unit=None)
        self.assertEqual(child_instrument.unit, "")

    def test_instrument_description_syntax(self):
        """
        Test that instrument description conform to the specified syntax.
        """

        child_instrument = ChildInstrument("name", description="a")
        self.assertEqual(child_instrument.description, "a")

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=ERROR):
                ChildInstrument("name", description="a" * 1024)

        child_instrument = ChildInstrument("name")
        self.assertEqual(child_instrument.description, "")

        child_instrument = ChildInstrument("name", description=None)
        self.assertEqual(child_instrument.description, "")


class TestCounter(TestCase):

    def test_create_counter(self):
        """
        Test that the Counter can be created with create_counter.
        """

        self.assertTrue(
            isinstance(
                _DefaultMeter("name").create_counter("name"),
                Counter
            )
        )

    def test_api_counter_abstract(self):
        """
        Test that the API Counter is an abstract class.
        """

        self.assertTrue(isabstract(Counter))

    def test_create_counter_api(self):
        """
        Test that the API for creating a counter accepts the name of the instrument.
        Test that the API for creating a counter accepts the unit of the instrument.
        Test that the API for creating a counter accepts the description of the
        """

        create_counter_signature = signature(Meter.create_counter)
        self.assertIn("name", create_counter_signature.parameters.keys())
        self.assertIs(
            create_counter_signature.parameters["name"].default,
            Signature.empty
        )

        create_counter_signature = signature(Meter.create_counter)
        self.assertIn("unit", create_counter_signature.parameters.keys())
        self.assertIs(
            create_counter_signature.parameters["unit"].default, ""
        )

        create_counter_signature = signature(Meter.create_counter)
        self.assertIn(
            "description", create_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_counter_signature.parameters["description"].default, ""
        )

    def test_counter_add_method(self):
        """
        Test that the counter has an add method.
        Test that the add method returns None.
        Test that the add method accepts optional attributes.
        Test that the add method accepts the increment amount.
        Test that the add method accepts only positive amounts.
        """

        self.assertTrue(hasattr(Counter, "add"))

        self.assertIsNone(DefaultCounter("name").add(1))

        add_signature = signature(Counter.add)
        self.assertIn(
            "attributes", add_signature.parameters.keys()
        )
        self.assertIs(
            add_signature.parameters["attributes"].default, None
        )

        self.assertIn(
            "amount", add_signature.parameters.keys()
        )
        self.assertIs(
            add_signature.parameters["amount"].default, Signature.empty
        )

        with self.assertLogs(level=ERROR):
            DefaultCounter("name").add(-1)


class TestObservableCounter(TestCase):

    def test_create_observable_counter(self):
        """
        Test that the ObservableCounter can be created with create_observable_counter.
        """

        def callback():
            yield

        self.assertTrue(
            isinstance(
                _DefaultMeter("name").create_observable_counter(
                    "name", callback()
                ),
                ObservableCounter
            )
        )

    def test_api_observable_counter_abstract(self):
        """
        Test that the API ObservableCounter is an abstract class.
        """

        self.assertTrue(isabstract(ObservableCounter))

    def test_create_observable_counter_api(self):
        """
        Test that the API for creating a observable_counter accepts the name of the instrument.
        Test that the API for creating a observable_counter accepts a callback.
        Test that the API for creating a observable_counter accepts the unit of the instrument.
        Test that the API for creating a observable_counter accepts the description of the instrument
        """

        create_observable_counter_signature = signature(Meter.create_observable_counter)
        self.assertIn("name", create_observable_counter_signature.parameters.keys())
        self.assertIs(
            create_observable_counter_signature.parameters["name"].default,
            Signature.empty
        )
        create_observable_counter_signature = signature(Meter.create_observable_counter)
        self.assertIn("callback", create_observable_counter_signature.parameters.keys())
        self.assertIs(
            create_observable_counter_signature.parameters["callback"].default,
            Signature.empty
        )
        create_observable_counter_signature = signature(Meter.create_observable_counter)
        self.assertIn("unit", create_observable_counter_signature.parameters.keys())
        self.assertIs(
            create_observable_counter_signature.parameters["unit"].default, ""
        )

        create_observable_counter_signature = signature(Meter.create_observable_counter)
        self.assertIn(
            "description", create_observable_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_counter_signature.parameters["description"].default, ""
        )

    def test_observable_counter_callback(self):
        """
        Test that the API for creating a asynchronous counter accepts a callback.
        Test that the callback function reports measurements.
        Test that there is a way to pass state to the callback.
        """

        create_observable_counter_signature = signature(
            Meter.create_observable_counter
        )
        self.assertIn(
            "callback", create_observable_counter_signature.parameters.keys()
        )
        self.assertIs(
            create_observable_counter_signature.parameters["name"].default,
            Signature.empty
        )

        def callback():
            yield

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=ERROR):
                observable_counter = DefaultObservableCounter(
                    "name", callback()
                )

        with self.assertLogs(level=ERROR):
            observable_counter.observe()

        # FIXME implement this: Test that the callback function has a timeout.