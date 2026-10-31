# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Fail when a branch leaves a public API object less documented than main does.

The check is a comparison rather than an absolute threshold. It collects every
documentation gap in the public API at the current working tree, collects the
same set at a base git ref, and reports only the gaps the branch introduces.
That lets the repository adopt the check while gaps remain, and still refuses
any pull request that adds a new one.

Three kinds of gap are reported, named by the ``Gap.rule`` strings
``missing-docstring``, ``undocumented-parameter`` and ``missing-returns``.
"""

from __future__ import annotations

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from dataclasses import dataclass
from logging import ERROR, getLogger
from sys import exit as sys_exit, stderr

from griffe import (
    Alias,
    Class,
    DocstringSectionKind,
    Function,
    Kind,
    Module,
    Object,
    Parser,
    load,
    load_git,
)

from eachdist import find_projectroot, find_targets

DIRECTORIES_NOT_SEARCHED: tuple[str, ...] = (
    "docs",
    "scripts",
    "opentelemetry-docker-tests",
    "examples",
    "_template",
)

MODULES_NOT_CHECKED: tuple[str, ...] = (
    "opentelemetry.proto",
    "opentelemetry.proto_json",
    "opentelemetry.semconv",
)

PARAMETERS_NEVER_DOCUMENTED: frozenset[str] = frozenset({"self", "cls"})

ROOT_MODULE: str = "opentelemetry"


@dataclass(frozen=True, order=True)
class Gap:
    """One documentation gap at one public API object.

    Attributes:
        path: The fully qualified name of the object, as griffe reports it.
            This is the identity used to compare two refs, so a gap that
            merely moves to a different line is not reported as new.
        rule: Which of the three checks the object failed.
        detail: What is missing, for example the name of an undocumented
            parameter. The empty string when the rule needs no detail.
    """

    path: str
    rule: str
    detail: str = ""

    def __str__(self) -> str:
        """Render the gap as one line of the report.

        Returns:
            The qualified name, the rule and the detail, separated by spaces.
        """
        suffix: str = f" ({self.detail})" if self.detail else ""
        return f"{self.path}: {self.rule}{suffix}"


def documented_parameter_names(obj: Object) -> set[str]:
    """Collect the parameter names a Google-style docstring documents.

    Args:
        obj: Any griffe object. One with no docstring contributes nothing.

    Returns:
        The names appearing in the ``Args:`` sections of the docstring. An
        object with no docstring, or a docstring with no ``Args:`` section,
        gives the empty set.
    """
    if obj.docstring is None:
        return set()
    names: set[str] = set()
    for section in obj.docstring.parsed:
        if section.kind is DocstringSectionKind.parameters:
            names.update(parameter.name for parameter in section.value)
    return names


def has_returns_section(obj: Object) -> bool:
    """Say whether a docstring documents a return value.

    Args:
        obj: Any griffe object. One with no docstring documents nothing.

    Returns:
        ``True`` when the docstring carries a ``Returns:`` or ``Yields:``
        section.
    """
    if obj.docstring is None:
        return False
    return any(
        section.kind in (DocstringSectionKind.returns, DocstringSectionKind.yields)
        for section in obj.docstring.parsed
    )


def returns_a_value(function: Function) -> bool:
    """Say whether a function's annotation promises a value to its caller.

    An unannotated function is treated as returning nothing, so that adding
    this check does not demand a ``Returns:`` section from code that has no
    annotations at all.

    Args:
        function: The function to inspect.

    Returns:
        ``True`` when the return annotation is present and is not ``None``.
    """
    annotation = function.returns
    if annotation is None:
        return False
    return str(annotation) not in ("None", "NoneType")


def gaps_of_function(function: Function, parameters_documented_elsewhere: set[str]) -> list[Gap]:
    """Collect the gaps of one public function or method.

    Args:
        function: The function to inspect.
        parameters_documented_elsewhere: Parameter names that another object's
            docstring already documents. This carries the repository's
            convention that constructor parameters are documented on the class
            rather than on ``__init__``, which is what the rendered API
            reference shows.

    Returns:
        Every gap found, which is the empty list for a fully documented
        function.
    """
    if function.docstring is None:
        return [Gap(function.path, "missing-docstring")]

    gaps: list[Gap] = []
    documented: set[str] = documented_parameter_names(function) | parameters_documented_elsewhere
    for parameter in function.parameters:
        if parameter.name in PARAMETERS_NEVER_DOCUMENTED:
            continue
        if parameter.name not in documented:
            gaps.append(Gap(function.path, "undocumented-parameter", parameter.name))

    if returns_a_value(function) and not has_returns_section(function):
        gaps.append(Gap(function.path, "missing-returns"))
    return gaps


def gaps_of_object(obj: Object) -> list[Gap]:
    """Walk one public object and everything public inside it.

    Submodules are not descended into, because ``walk_modules`` already
    enumerates every module and it is the only place that applies
    ``MODULES_NOT_CHECKED``. Descending here as well would both report the
    gaps of a generated tree and do the work of walking it twice.

    Args:
        obj: The module or class to walk.

    Returns:
        Every gap found in the object, its public functions, and its public
        classes including the classes nested inside those.
    """
    gaps: list[Gap] = []
    if obj.docstring is None:
        gaps.append(Gap(obj.path, "missing-docstring"))

    constructor_parameters: set[str] = set()
    if isinstance(obj, Class):
        constructor_parameters = documented_parameter_names(obj)

    for member in obj.members.values():
        if isinstance(member, Alias):
            continue
        if not member.is_public:
            continue
        if member.kind is Kind.ATTRIBUTE:
            continue
        if isinstance(member, Function):
            if member.name.startswith("__") and member.name != "__init__":
                continue
            documented_elsewhere = constructor_parameters if member.name == "__init__" else set()
            if member.name == "__init__" and member.docstring is None and constructor_parameters:
                gaps.extend(gaps_of_function(member, documented_elsewhere)[1:])
                continue
            gaps.extend(gaps_of_function(member, documented_elsewhere))
        elif isinstance(member, Class):
            gaps.extend(gaps_of_object(member))
    return gaps


def collect_gaps(root: Module) -> set[Gap]:
    """Collect every documentation gap reachable from a loaded root module.

    Args:
        root: The module griffe loaded, normally ``opentelemetry``.

    Returns:
        The set of gaps, which is what two refs are compared on.
    """
    gaps: set[Gap] = set()
    for module in walk_modules(root):
        gaps.update(gaps_of_object(module))
    return gaps


def walk_modules(root: Module) -> list[Module]:
    """List the modules to check, skipping the generated trees.

    Args:
        root: The module griffe loaded.

    Returns:
        Every module at or below the root whose name is not under one of
        ``MODULES_NOT_CHECKED``, in a deterministic order.
    """
    found: list[Module] = []
    pending: list[Module] = [root]
    while pending:
        module = pending.pop()
        if module.path.startswith(MODULES_NOT_CHECKED):
            continue
        found.append(module)
        for member in module.members.values():
            if isinstance(member, Module) and not isinstance(member, Alias):
                pending.append(member)
    return sorted(found, key=lambda module: module.path)


def search_paths() -> list[str]:
    """Build the list of source directories griffe searches.

    Returns:
        One ``src`` directory per distribution in the repository, excluding
        the directories in ``DIRECTORIES_NOT_SEARCHED``.
    """
    rootpath = find_projectroot()
    paths: list[str] = []
    for target in find_targets("DEFAULT", rootpath):
        relative = target.relative_to(rootpath)
        if not any(excluded in str(relative) for excluded in DIRECTORIES_NOT_SEARCHED):
            paths.append(str(relative / "src"))
    return paths


def main() -> int:
    """Run the check and report.

    Returns:
        ``0`` when the branch introduces no gap, ``1`` when it introduces at
        least one.
    """
    parser = ArgumentParser(
        description="Fail when a branch introduces a public API documentation gap",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--module",
        default=ROOT_MODULE,
        help="Name of the module to check",
    )
    parser.add_argument(
        "--against",
        default="main",
        help="Git ref to compare against",
    )
    arguments = parser.parse_args()

    getLogger("griffe").setLevel(ERROR)

    paths: list[str] = search_paths()
    current: set[Gap] = collect_gaps(
        load(arguments.module, search_paths=paths, docstring_parser=Parser.google)
    )
    base: set[Gap] = collect_gaps(
        load_git(
            arguments.module,
            ref=arguments.against,
            search_paths=paths,
            docstring_parser=Parser.google,
        )
    )

    introduced: list[Gap] = sorted(current - base)
    closed: list[Gap] = sorted(base - current)

    if closed:
        print(f"This branch closes {len(closed)} documentation gaps. Thank you.")
        print()

    if not introduced:
        print("This branch introduces no public API documentation gaps.")
        return 0

    print("This branch introduces the following public API documentation gaps:", file=stderr)
    print(file=stderr)
    for gap in introduced:
        print(f"  {gap}", file=stderr)
    print(file=stderr)
    print(
        "Every public module, class, function and method needs a docstring, "
        "every parameter needs an entry in an Args: section, and every "
        "function whose annotation returns a value needs a Returns: section. "
        "Constructor parameters belong on the class docstring, because "
        "docs/conf.py does not set special-members and an __init__ docstring "
        "is therefore never rendered.",
        file=stderr,
    )
    return 1


if __name__ == "__main__":
    sys_exit(main())
