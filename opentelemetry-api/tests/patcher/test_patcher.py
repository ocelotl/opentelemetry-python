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
# type: ignore

from unittest import TestCase

from opentelemetry.patcher.base_patcher import BasePatcher


class TestSampler(TestCase):
    def test_protect(self):
        @BasePatcher.protect
        class TestPatcher(BasePatcher):
            def patch(self):
                return 1

            def unpatch(self):
                return 1

        test_patcher = TestPatcher()

        self.assertIs(test_patcher.unpatch(), None)
        self.assertEqual(test_patcher.patch(), 1)
        self.assertIs(test_patcher.patch(), None)
        self.assertEqual(test_patcher.unpatch(), 1)
        self.assertIs(test_patcher.unpatch(), None)
