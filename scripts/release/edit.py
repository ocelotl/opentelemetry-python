#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Shared file-editing helpers used by update_version.py and
update_patch_version.py: rewriting repo.toml's version fields, bumping
each package's pinned dependencies, and rewriting each package's
__version__."""

from logging import getLogger
from os import walk
from os.path import basename, join
from pathlib import Path
from re import escape, sub

from tomlkit import dump, load

logger = getLogger(__name__)

# PEP 508 allowed specifier operators
OPERATORS_PATTERN = "|".join(
    escape(op) for op in ["==", "!=", "<=", ">=", "<", ">", "===", "~=", "="]
)


def edit_version_files(
    package_directory_paths: list[Path], version: str, packages: list[str]
) -> None:
    """Rewrites __version__ to version in the version file of each package
    directory whose pyproject.toml [project].name is one of packages."""
    logger.info("updating version/__init__.py files")

    package_names = set(packages)
    replace = f'__version__ = "{version}"'

    for package_directory_path in package_directory_paths:
        pyproject_path = package_directory_path.joinpath("pyproject.toml")
        if not pyproject_path.exists():
            continue

        with open(pyproject_path, encoding="utf-8") as file:
            pyproject = load(file)

        if pyproject.get("project", {}).get("name") not in package_names:
            continue

        version_file_path = package_directory_path.joinpath(
            pyproject["tool"]["hatch"]["version"]["path"]
        )

        with open(version_file_path) as file:
            text = file.read()

        if replace in text:
            logger.info("%s already contains %s", version_file_path, replace)
            continue

        with open(version_file_path, "w", encoding="utf-8") as file:
            file.write(sub("__version__ .*", replace, text))


def edit_dependency_versions(
    package_directory_paths: list[Path], version: str, packages: list[str]
) -> None:
    """Rewrites every pyproject.toml dependency pin on one of packages that
    currently ends in ".dev" to version."""
    logger.info("updating dependencies")

    for pkg in packages:
        edit_files(
            package_directory_paths,
            "pyproject.toml",
            rf"({basename(pkg)}(?:\[[^\]]+\])?\s*)({OPERATORS_PATTERN})(.*\.dev)",
            r"\1\2 " + version,
        )


def edit_patch_dependency_versions(
    package_directory_paths: list[Path],
    version: str,
    prev_version: str,
    packages: list[str],
) -> None:
    """Rewrites every pyproject.toml dependency pin on one of packages from
    the exact prev_version to version (the patch-release case, which can't
    rely on a ".dev" suffix to locate the pin)."""
    logger.info("updating patch dependencies")

    for pkg in packages:
        search = (
            rf"({basename(pkg)}(?:\[[^\]]+\])?\s*)"
            rf"(\s?({OPERATORS_PATTERN})\s?)(.*{escape(prev_version)})"
        )
        replace = r"\g<1>\g<2>" + version
        logger.debug("search=%r replace=%r pkg=%r", search, replace, pkg)
        edit_files(package_directory_paths, "pyproject.toml", search, replace)


def edit_files(
    package_directory_paths: list[Path],
    filename: str,
    search: str,
    replace: str,
) -> None:
    """Finds filename under each package directory and replaces every
    regex match of search with replace."""
    for package_directory_path in package_directory_paths:
        curr_file = None
        for root, _, files in walk(package_directory_path):
            if filename in files:
                curr_file = join(root, filename)
                break

        if curr_file is None:
            logger.warning(
                "file missing: %s/%s", package_directory_path, filename
            )
            continue

        with open(curr_file, encoding="utf-8") as _file:
            text = _file.read()

        if replace in text:
            logger.info("%s already contains %s", curr_file, replace)
            continue

        with open(curr_file, "w", encoding="utf-8") as _file:
            _file.write(sub(search, replace, text))


def edit_repo_toml_version(
    root_path: Path, section: str, version: str
) -> None:
    """Sets repo.toml's [section].version to version."""
    repo_toml_path = root_path / "repo.toml"
    with open(repo_toml_path, encoding="utf-8") as file:
        data = load(file)
    data[section]["version"] = version
    with open(repo_toml_path, "w", encoding="utf-8") as file:
        dump(data, file)
