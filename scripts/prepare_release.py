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

from configparser import ConfigParser
from pathlib import Path
from git import Repo
from git.db import GitDB
from ipdb import set_trace

current_path = Path(__file__)

config_parser = ConfigParser()
config_parser.read(current_path.parent.joinpath("eachdist.ini"))


repo = Repo(__file__, odbt=GitDB, search_parent_directories=True)

set_trace
release_branch = repo.create_head(
    "release/{}".format(
        "-".join(
            [
                config_parser["stable"]["version"],
                config_parser["prerelease"]["version"]
            ]
        )
    )
)


def get_version_file_paths(path):
    """
    Gets the paths of the Python packages under ``path``.
    """
    for directory in [
        child for child in path.iterdir() if child.is_dir()
        and not child.name.startswith(".")
    ]:

        version_file_path = directory / "version.py"

        if version_file_path.exists():
            yield version_file_path
        else:
            yield from get_version_file_paths(directory)


for version_file_path in list(
    get_version_file_paths(current_path.parent.parent)
):

    print(version_file_path)

    with open(curr_file, encoding="utf-8") as _file:
        text = _file.read()

    if replace in text:
        print(f"{curr_file} already contains {replace}")
        continue

    with open(curr_file, "w", encoding="utf-8") as _file:
        _file.write(re.sub(search, replace, text))
