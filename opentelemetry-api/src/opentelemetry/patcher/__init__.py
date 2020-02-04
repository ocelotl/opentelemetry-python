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

"""
OpenTelemetry patcher

This includes the base patcher class and a no-op implementation.
"""

from abc import ABC, abstractmethod
from logging import getLogger

_LOG = getLogger(__name__)


class BasePatcher(ABC):
    """An ABC for patchers"""

    @abstractmethod
    def _patch(self) -> None:
        """Patch"""

    @abstractmethod
    def _unpatch(self) -> None:
        """Unpatch"""

    def patch(self) -> None:
        """Patch"""

        if not hasattr(self, "_is_patched"):
            self._is_patched = False

        if not self._is_patched:
            result = self._patch()
            self._is_patched = True
            return result

        else:
            _LOG.warning("Attempting to patch while already patched")

            return None

    def unpatch(self) -> None:
        """Unpatch"""

        if not hasattr(self, "_is_patched"):
            self._is_patched = False

        if self._is_patched:
            result = self._unpatch()
            self._is_patched = False
            return result

        else:
            _LOG.warning("Attempting to unpatch while already unpatched")

            return None


class NoOpPatcher(BasePatcher):
    def _patch(self) -> None:
        """Patch"""

    def _unpatch(self) -> None:
        """Unpatch"""


__all__ = ["BasePatcher", "NoOpPatcher"]
