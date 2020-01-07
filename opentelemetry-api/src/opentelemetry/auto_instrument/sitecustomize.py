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

from logging import getLogger

from pkg_resources import iter_entry_points

_LOG = getLogger(__file__)

for entry_point in iter_entry_points("opentelemetry_patcher"):
    try:
        entry_point.load()().patch()  # type: ignore

        _LOG.debug("Patched %s", entry_point.name)

    except Exception as error:  # pylint: disable=broad-except

        _LOG.exception(
            "Patching of %s failed with: %s", entry_point.name, error
        )
