# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from sys import path as sys_path
from textwrap import dedent

from tomlkit import load

# scripts/ (for find.py) and scripts/release/ (for edit.py) aren't packages,
# so make them importable the same way the release scripts do at runtime.
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys_path.insert(0, str(SCRIPTS_DIR))
sys_path.insert(0, str(SCRIPTS_DIR / "release"))

from edit import (  # noqa: E402
    edit_dependency_versions,
    edit_patch_dependency_versions,
    edit_version_files,
)

PACKAGE_ROOT_GLOBS = (
    "opentelemetry-*/pyproject.toml",
    "exporter/opentelemetry-*/pyproject.toml",
    "propagator/opentelemetry-*/pyproject.toml",
    "shim/opentelemetry-*/pyproject.toml",
    "tests/opentelemetry-*/pyproject.toml",
    "codegen/opentelemetry-*/pyproject.toml",
)
PRIVATE_PACKAGE_CLASSIFIER = "Private :: Do Not Upload"


def write_pyproject(target: Path, dependencies: str) -> None:
    """Writes a minimal pyproject.toml with the given dependencies array
    body under target."""
    target.mkdir()
    target.joinpath("pyproject.toml").write_text(
        dedent(
            f"""
            [project]
            dependencies = [
              {dependencies}
            ]
            """
        ),
        encoding="utf-8",
    )


def write_versioned_project(target: Path, name: str, version: str) -> None:
    """Writes a minimal hatch-versioned package under target, with its
    __version__ file set to version."""
    version_file = target / "src" / "opentelemetry" / "version" / "__init__.py"
    version_file.parent.mkdir(parents=True)
    version_file.write_text(
        f'__version__ = "{version}"\n',
        encoding="utf-8",
    )
    target.mkdir(exist_ok=True)
    target.joinpath("pyproject.toml").write_text(
        dedent(
            f"""
            [project]
            name = "{name}"

            [tool.hatch.version]
            path = "src/opentelemetry/version/__init__.py"
            """
        ),
        encoding="utf-8",
    )


def package_name(pyproject: Path) -> str | None:
    """The [project].name of pyproject, or None if it's flagged private."""
    with open(pyproject, encoding="utf-8") as file:
        project = load(file)["project"]
    if PRIVATE_PACKAGE_CLASSIFIER in project.get("classifiers", ()):
        return None
    return project["name"]


def test_all_release_packages_are_listed_in_repo_toml():
    root = Path(__file__).resolve().parents[2]
    releasable_package_names = {
        name
        for package_glob in PACKAGE_ROOT_GLOBS
        for pyproject in root.glob(package_glob)
        if (name := package_name(pyproject)) is not None
    }

    with open(root / "repo.toml", encoding="utf-8") as file:
        repo = load(file)
    repo_toml_package_names = set(repo["stable"]["packages"]) | set(
        repo["prerelease"]["packages"]
    )

    missing_package_names = sorted(
        releasable_package_names - repo_toml_package_names
    )
    assert not missing_package_names, (
        f"packages missing from repo.toml: {', '.join(missing_package_names)}"
    )


def test_edit_dependency_versions_matches_exact_package_name(tmp_path):
    target = tmp_path / "target"
    write_pyproject(
        target,
        '"opentelemetry-proto == 1.44.0.dev",\n'
        '  "opentelemetry-proto-json == 0.65b0.dev",',
    )

    edit_dependency_versions([target], "1.44.0", ["opentelemetry-proto"])

    pyproject = target.joinpath("pyproject.toml").read_text(encoding="utf-8")
    assert '"opentelemetry-proto == 1.44.0",' in pyproject
    assert '"opentelemetry-proto-json == 0.65b0.dev",' in pyproject


def test_edit_dependency_versions_matches_pins_with_extras(tmp_path):
    target = tmp_path / "target"
    write_pyproject(
        target,
        '"opentelemetry-exporter-http-transport[requests] == 1.44.0.dev",',
    )

    edit_dependency_versions(
        [target], "1.44.0", ["opentelemetry-exporter-http-transport"]
    )

    pyproject = target.joinpath("pyproject.toml").read_text(encoding="utf-8")
    assert (
        '"opentelemetry-exporter-http-transport[requests] == 1.44.0",'
        in pyproject
    )


def test_edit_patch_dependency_versions_matches_exact_package_name(tmp_path):
    target = tmp_path / "target"
    write_pyproject(
        target,
        '"opentelemetry-proto == 1.43.0",\n'
        '  "opentelemetry-proto-json == 1.43.0",',
    )

    edit_patch_dependency_versions(
        [target], "1.43.1", "1.43.0", ["opentelemetry-proto"]
    )

    pyproject = target.joinpath("pyproject.toml").read_text(encoding="utf-8")
    assert '"opentelemetry-proto == 1.43.1",' in pyproject
    assert '"opentelemetry-proto-json == 1.43.0",' in pyproject


def test_edit_version_files_matches_exact_project_name(tmp_path):
    proto = tmp_path / "opentelemetry-proto"
    proto_json = tmp_path / "opentelemetry-proto-json"
    write_versioned_project(proto, "opentelemetry-proto", "1.44.0.dev")
    write_versioned_project(
        proto_json, "opentelemetry-proto-json", "0.65b0.dev"
    )

    edit_version_files(
        [proto, proto_json], "1.45.0.dev", ["opentelemetry-proto"]
    )

    assert (
        proto.joinpath("src/opentelemetry/version/__init__.py").read_text(
            encoding="utf-8"
        )
        == '__version__ = "1.45.0.dev"\n'
    )
    assert (
        proto_json.joinpath("src/opentelemetry/version/__init__.py").read_text(
            encoding="utf-8"
        )
        == '__version__ = "0.65b0.dev"\n'
    )
