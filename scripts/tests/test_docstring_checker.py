# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from sys import modules as sys_modules
from sys import path as sys_path
from textwrap import dedent

from griffe import Parser, load

SCRIPTS_DIRECTORY = Path(__file__).parents[1]
sys_path.insert(0, str(SCRIPTS_DIRECTORY))

_spec = spec_from_file_location("docstring_checker", SCRIPTS_DIRECTORY / "docstring_checker.py")
checker = module_from_spec(_spec)
sys_modules["docstring_checker"] = checker
_spec.loader.exec_module(checker)


def load_sample_module(tmp_path: Path, source: str, name: str = "mod"):
    """Write one throwaway module and load it with griffe.

    Args:
        tmp_path: The pytest temporary directory to write the package into.
        source: The module source. It is dedented before being written.
        name: The name of the module inside the package.

    Returns:
        The griffe module, loaded with the Google docstring parser the
        repository uses.
    """
    package = tmp_path / "sample_pkg"
    package.mkdir(exist_ok=True)
    (package / "__init__.py").write_text('"""Package docstring."""\n')
    (package / f"{name}.py").write_text(dedent(source))
    return load(
        f"sample_pkg.{name}",
        search_paths=[str(tmp_path)],
        docstring_parser=Parser.google,
    )


def gaps_for(tmp_path: Path, source: str) -> set[tuple[str, str, str]]:
    """Collect the gaps of one throwaway module built from source text.

    Args:
        tmp_path: The pytest temporary directory to write the module into.
        source: The module source. It is dedented before being written.

    Returns:
        One tuple per gap, holding the qualified name, the rule and the
        detail, so that assertions do not depend on the dataclass identity.
    """
    module = load_sample_module(tmp_path, source)
    return {(gap.path, gap.rule, gap.detail) for gap in checker.gaps_of_object(module)}


def test_fully_documented_module_has_no_gaps(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""


        def visible(value: int) -> str:
            """Summarize.

            Args:
                value: The value.

            Returns:
                The text.
            """
            return str(value)
        ''',
    )
    assert gaps == set()


def test_missing_docstrings_are_reported(tmp_path):
    gaps = gaps_for(
        tmp_path,
        """
        def visible(value):
            return value


        class Thing:
            def method(self):
                return None
        """,
    )
    assert ("sample_pkg.mod", "missing-docstring", "") in gaps
    assert ("sample_pkg.mod.visible", "missing-docstring", "") in gaps
    assert ("sample_pkg.mod.Thing", "missing-docstring", "") in gaps
    assert ("sample_pkg.mod.Thing.method", "missing-docstring", "") in gaps


def test_undocumented_parameter_is_reported(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""


        def visible(first: int, second: int) -> None:
            """Summarize.

            Args:
                first: The first value.
            """
        ''',
    )
    assert ("sample_pkg.mod.visible", "undocumented-parameter", "second") in gaps
    assert ("sample_pkg.mod.visible", "undocumented-parameter", "first") not in gaps


def test_missing_returns_is_reported_only_when_a_value_is_returned(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""


        def returns_value(value: int) -> str:
            """Summarize.

            Args:
                value: The value.
            """
            return str(value)


        def returns_nothing(value: int) -> None:
            """Summarize.

            Args:
                value: The value.
            """
        ''',
    )
    assert ("sample_pkg.mod.returns_value", "missing-returns", "") in gaps
    assert ("sample_pkg.mod.returns_nothing", "missing-returns", "") not in gaps


def test_a_yields_section_satisfies_the_returns_rule(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""

        from typing import Iterator


        def counted(value: int) -> Iterator[int]:
            """Summarize.

            Args:
                value: The value.

            Yields:
                Each number below the value.
            """
            yield from range(value)
        ''',
    )
    assert not any(rule == "missing-returns" for _, rule, _ in gaps)


def test_unannotated_return_is_not_required_to_be_documented(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""


        def visible(value):
            """Summarize.

            Args:
                value: The value.
            """
            return value
        ''',
    )
    assert not any(rule == "missing-returns" for _, rule, _ in gaps)


def test_constructor_parameters_may_be_documented_on_the_class(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""


        class Thing:
            """Hold a name.

            Args:
                name: The name to hold.
            """

            def __init__(self, name: str):
                """Initialize. Parameters are documented on the class."""
                self.name = name
        ''',
    )
    assert gaps == set()


def test_constructor_parameter_documented_nowhere_is_reported(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""


        class Thing:
            """Hold a name."""

            def __init__(self, name: str):
                """Initialize."""
                self.name = name
        ''',
    )
    assert ("sample_pkg.mod.Thing.__init__", "undocumented-parameter", "name") in gaps


def test_self_and_cls_are_never_required(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""


        class Thing:
            """Hold nothing."""

            def method(self) -> None:
                """Do nothing."""

            @classmethod
            def build(cls) -> None:
                """Build nothing."""
        ''',
    )
    assert gaps == set()


def test_private_members_are_not_checked(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""


        def _private(value):
            return value


        class _Private:
            def method(self):
                return None
        ''',
    )
    assert gaps == set()


def test_dunder_methods_other_than_init_are_not_checked(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""


        class Thing:
            """Hold nothing."""

            def __repr__(self) -> str:
                return "Thing()"
        ''',
    )
    assert gaps == set()


def test_nested_classes_are_checked(tmp_path):
    gaps = gaps_for(
        tmp_path,
        '''
        """Module docstring."""


        class Outer:
            """Hold an inner class."""

            class Inner:
                def method(self) -> None:
                    """Do nothing."""
        ''',
    )
    assert ("sample_pkg.mod.Outer.Inner", "missing-docstring", "") in gaps


def test_generated_trees_are_not_walked(tmp_path, monkeypatch):
    package = tmp_path / "sample_pkg"
    package.mkdir()
    (package / "__init__.py").write_text('"""Package docstring."""\n')
    for name in ("kept", "generated"):
        subpackage = package / name
        subpackage.mkdir()
        (subpackage / "__init__.py").write_text("")

    root = load(
        "sample_pkg",
        search_paths=[str(tmp_path)],
        docstring_parser=Parser.google,
    )
    monkeypatch.setattr(checker, "MODULES_NOT_CHECKED", ("sample_pkg.generated",))
    walked = {module.path for module in checker.walk_modules(root)}
    assert "sample_pkg.kept" in walked
    assert "sample_pkg.generated" not in walked
    assert {gap.path for gap in checker.collect_gaps(root)} == {"sample_pkg.kept"}


def test_gap_renders_with_and_without_detail():
    assert str(checker.Gap("a.b", "missing-docstring")) == "a.b: missing-docstring"
    assert (
        str(checker.Gap("a.b", "undocumented-parameter", "x")) == "a.b: undocumented-parameter (x)"
    )
