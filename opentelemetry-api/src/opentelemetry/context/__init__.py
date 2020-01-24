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


from pkg_resources import iter_entry_points
from os import environ

from opentelemetry.context.context import Context


# FIXME use a better implementation of a configuration manager to avoid having
# to get configuration values straight from environment variables
_CONTEXT = {
    entry_point.name: entry_point.load() for entry_point in (
        iter_entry_points("opentelemetry_context")
    )
}[environ.get("OPENTELEMETRY_CONTEXT", "no_op_context")]()


def create_key(key: str) -> "object":
    # FIXME Implement this
    raise NotImplementedError


def get_value(key: str, context: "Context") -> "object":
    return context.get_value(key)


def set_value(context: "Context", key: str, value: "object") -> "Context":
    new_context = context.copy()
    new_context.set_value(key, value)
    return new_context


def remove_value(context: "Context", key: str, value: "object") -> "Context":
    new_context = context.copy()
    new_context.remove_value(key)
    return new_context


def get_current() -> "Context":
    return _CONTEXT


def set_current(context: "Context"):
    global _CONTEXT
    _CONTEXT = context


__all__ = [
    "get_value",
    "set_value",
    "get_current",
    "set_current",
    "Context",
]
