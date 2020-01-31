#!/usr/bin/env python3

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

from shutil import which
from os import execl
from os.path import dirname
from sys import argv, path


def run() -> None:
    path.insert(0, dirname(__name__))
    python3 = which(argv[1])
    execl(python3, python3, *argv[2:])  # type: ignore


if __name__ == "__main__":
    run()
