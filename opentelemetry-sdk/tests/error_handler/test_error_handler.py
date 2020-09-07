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
from logging import ERROR

from opentelemetry.sdk.error_handler import DefaultErrorHandler, logger


class TestErrorHandler(TestCase):

    def test_default_error_handler(self):

        try:
            raise Exception("some exception")
        except Exception as error:
            with self.assertLogs(logger, ERROR):
                DefaultErrorHandler().handle(error)