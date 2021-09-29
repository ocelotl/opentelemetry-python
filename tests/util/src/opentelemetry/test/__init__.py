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


from traceback import format_tb


class AssertNotRaisesMixin:
    class _AssertNotRaises:
        def __init__(self, test_case):
            self._test_case = test_case

        def __enter__(self):
            return self

        def __exit__(self, type_, value, tb):  # pylint: disable=invalid-name
            if value is not None and type_ in self._exception_types:

                # Using a single-use variable here because the f string can't
                # contain a backslash.
                formatted_tb = "\n".join(format_tb(tb))

                self._test_case.fail(
                    f"Unexpected exception was raised:\n{formatted_tb}"
                )

            return True

        def __call__(self, exception, *exceptions):
            # pylint: disable=attribute-defined-outside-init
            self._exception_types = (exception, *exceptions)
            return self

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        # pylint: disable=invalid-name
        self.assertNotRaises = self._AssertNotRaises(self)
