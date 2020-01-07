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
    def protect(class_) -> None:  # type: ignore[no-untyped-def]
        """
        Provides a class decorator that protects patch and unpatch methods

        A protected patch method can't be called again until its corresponding
        unpatch method has been called and vice versa. A protected patch method
        must be called first before its corresponding unpatch method can be
        called.

        To use this decorator simply decorate the patcher class:

        .. code-block:: python

            from opentelemetry.patcher.base_patcher import BasePatcher

            @BasePatcher.protect
            class PatcherClass(BasePatcher):
                ...
        """

        # pylint: disable=protected-access

        class_._unprotected_patch = class_.patch
        class_._unprotected_patch._protected = False

        @wraps(class_.patch)
        def protected_patch(self):
            if not self._unprotected_patch.__func__._protected:
                self._unprotected_patch.__func__._protected = True
                self._unprotected_unpatch.__func__._protected = False

                return self._unprotected_patch()

            _LOG.warning("Attempting to patch while already patched")

            return None

        class_.patch = protected_patch

        class_._unprotected_unpatch = class_.unpatch
        class_._unprotected_unpatch._protected = True

        @wraps(class_.unpatch)
        def protected_unpatch(self):
            if not self._unprotected_unpatch.__func__._protected:
                self._unprotected_unpatch.__func__._protected = True
                self._unprotected_patch.__func__._protected = False

                return self._unprotected_unpatch()

            _LOG.warning("Attempting to unpatch while already unpatched")

            return None

        class_.unpatch = protected_unpatch

        return class_

    @abstractmethod
    def patch(self) -> None:
        """Patch"""

    @abstractmethod
    def unpatch(self) -> None:
        """Unpatch"""


__all__ = ["BasePatcher"]
