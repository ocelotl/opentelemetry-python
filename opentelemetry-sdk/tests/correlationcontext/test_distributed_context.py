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

import unittest

from opentelemetry import correlationcontext as cctx_api
from opentelemetry.sdk import correlationcontext


class TestCorrelationContextManager(unittest.TestCase):
    def setUp(self):
        self.manager = correlationcontext.CorrelationContextManager()

    def test_use_context(self):
        # Context is None initially
        self.assertIsNone(self.manager.current_context())

        # Start initial context
        dctx = cctx_api.CorrelationContext()
        with self.manager.use_context(dctx) as current:
            self.assertIs(current, dctx)
            self.assertIs(self.manager.current_context(), dctx)

            # Context is overridden
            nested_dctx = cctx_api.CorrelationContext()
            with self.manager.use_context(nested_dctx) as current:
                self.assertIs(current, nested_dctx)
                self.assertIs(self.manager.current_context(), nested_dctx)

            # Context is restored
            self.assertIs(self.manager.current_context(), dctx)
