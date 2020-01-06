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

from abc import ABC, abstractmethod
from functools import wraps

from ipdb import set_trace


class BasePatcher(ABC):
    """An ABC for patchers"""

    @staticmethod
    def protect(methd):

        methods = []

        1 / 0

        while True:

            print("sdfsdf")
            1 / 0

            methods.append(method)

            set_trace()

            name = method.__name__

            @wraps(method)
            def protected(self):

                if name == "patch":
                    self.unpatch._protected = False

                elif name == "unpatch":
                    self.patch._protected = False

                getattr(self, name)._protected = True

                return method(self)

            protected._protected = name == "unpatch"

            yield protected

    @abstractmethod
    def patch(self) -> None:
        """Patch"""

    @abstractmethod
    def unpatch(self) -> None:
        """Unpatch"""


__all__ = ["BasePatcher"]
