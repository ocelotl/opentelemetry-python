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
from logging import getLogger

_LOG = getLogger(__name__)


class BasePatcher(ABC):
    """An ABC for patchers"""

    @staticmethod
    def protect(class_):

        class_._unprotected_patch = class_.patch

        @wraps(class_.patch)
        def protected_patch(self):
            if not protected_patch._protected:
                protected_patch._protected = True
                protected_unpatch._protected = True

                return self._unprotected_patch()

            else:
                _LOG.warning("Attempting to patch while already patched")

                return None

        protected_patch._protected = False
        class_.patch = protected_patch

        class_._unprotected_unpatch = class_.unpatch

        @wraps(class_.unpatch)
        def protected_unpatch(self):
            if not protected_unpatch._protected:
                protected_unpatch._protected = True
                protected_patch._protected = False

                return self._unprotected_unpatch()

            else:
                _LOG.warning("Attempting to unpatch while already unpatched")

                return None

        protected_unpatch._protected = True
        class_.unpatch = protected_unpatch

        return class_

    @abstractmethod
    def patch(self) -> None:
        """Patch"""

    @abstractmethod
    def unpatch(self) -> None:
        """Unpatch"""


__all__ = ["BasePatcher"]
