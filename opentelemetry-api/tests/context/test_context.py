# Copyright 2019, OpenTelemetry Authors
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
from unittest.mock import Mock, patch

from opentelemetry.context import (
    get_current, set_value, set_current, get_value, remove_value
)


class TestContext(TestCase):

    def setUp(self):
        self.mock_context = patch("opentelemetry.context._CONTEXT").start()

        self.mock_context_copy = Mock(**{"get_value.return_value": "value"})
        self.mock_context.configure_mock(
            **{
                "copy.return_value": self.mock_context_copy,
                "get_value.return_value": "value",
            }
        )

    def tearDown(self):
        self.mock_context.stop()

    def test_get_current(self):
        self.assertIs(get_current(), self.mock_context)

    def test_set_current(self):
        mock_context = Mock()
        set_current(mock_context)
        from opentelemetry.context import _CONTEXT
        self.assertIs(_CONTEXT, mock_context)

    def test_set_value(self):
        self.assertIs(
            set_value(self.mock_context, "key", "value"),
            self.mock_context_copy
        )
        self.mock_context_copy.set_value.assert_called_with("key", "value")

    def test_get_value(self):
        self.assertEqual(get_value(self.mock_context, "key"), "value")
        self.mock_context.get_value.assert_called_with("key")

    def test_remove_value(self):
        self.assertIs(
            remove_value(self.mock_context, "key"),
            self.mock_context_copy
        )
        self.mock_context_copy.remove_value.assert_called_with("key")
