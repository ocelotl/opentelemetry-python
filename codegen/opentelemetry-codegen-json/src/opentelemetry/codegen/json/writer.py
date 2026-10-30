# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Accumulates lines of Python source and tracks indentation.

``CodeWriter`` is the only thing in this module.
``opentelemetry.codegen.json.generator`` uses it to assemble every file it emits.

The writer has no model of the code it is building. It appends strings to a list and prefixes each
one with the current indentation, and the methods named after Python constructs only save the
caller from writing the keyword, the punctuation and the indentation bookkeeping by hand. Nothing
here parses or validates what it is given, so a syntactically invalid fragment passed in comes out
unchanged.

A method named after a block construct, such as ``if_`` or ``class_``, is a context manager that
writes the header line and indents the body for the duration of the ``with`` statement. A method
named after a statement writes one line and returns the writer, so calls can be chained. Names
that would collide with a Python keyword or a builtin carry a trailing underscore.
"""

from __future__ import annotations

from collections.abc import Generator, Iterable
from contextlib import contextmanager
from typing import Any


# pylint: disable-next=too-many-public-methods
class CodeWriter:
    """
    Builds a Python source file line by line, keeping track of the current indentation level.

    A new instance holds no lines and sits at indentation level zero. ``writeln`` and the methods
    built on it append one line each, prefixed with the current level's worth of spaces, and the
    block context managers raise the level for the duration of a ``with`` statement and lower it
    again on exit, including when the body raises. ``to_string`` and ``to_lines`` read the result
    out; neither clears the instance, and no method removes or rewrites a line once it has been
    appended.

    Args:
        indent_size: Number of spaces that one indentation level is worth. Four matches the
            formatting the repository applies to the generated files.
    """

    def __init__(self, indent_size: int = 4) -> None:
        """
        Initializes a new CodeWriter instance. The parameters are documented on the class.
        """
        self._lines: list[str] = []
        self._indent_level: int = 0
        self._indent_size: int = indent_size

    @contextmanager
    def indent(self) -> Generator[CodeWriter, None, None]:
        """
        Context manager to increase indentation level for a block of code.

        Use this for a block whose header has already been written, or for one that no other
        method covers. The level is lowered again in a ``finally`` clause, so an exception raised
        inside the ``with`` statement leaves the writer at the level it started from.

        Returns:
            A context manager yielding this ``CodeWriter``, so the body can be written through the
            name bound by ``as``.
        """
        self._indent_level += 1
        try:
            yield self
        finally:
            self._indent_level -= 1

    def writeln(self, line: str = "") -> CodeWriter:
        """
        Writes a line of code with proper indentation. If the line is empty, it writes a blank line.

        A blank line is written as the empty string rather than as the current indentation's worth
        of spaces, which keeps trailing whitespace out of the generated file. Every other method
        that writes a single line goes through this one, except ``blank_line``, which appends
        directly.

        Args:
            line: The line of code to write (default: empty string for a blank line)
        Returns:
            The CodeWriter instance
        """
        if not line:
            self._lines.append("")
            return self
        indent = " " * (self._indent_level * self._indent_size)
        self._lines.append(f"{indent}{line}")
        return self

    def writemany(self, *lines: str) -> CodeWriter:
        """
        Writes multiple lines of code with proper indentation.

        Args:
            *lines: Variable number of lines to write
        Returns:
            The CodeWriter instance
        """
        for line in lines:
            self.writeln(line)
        return self

    def comment(self, content: str | Iterable[str]) -> CodeWriter:
        """
        Writes a comment line or block. If content is a string, it writes a single comment line.

        An empty string, whether passed on its own or found in the iterable, becomes a bare ``#``
        rather than ``#`` followed by a space, so the generated file carries no trailing
        whitespace.

        Args:
            content: A string for a single comment line or an iterable of strings for multiple comment lines
        Returns:
            The CodeWriter instance
        """
        if isinstance(content, str):
            self.writeln(f"# {content}" if content else "#")
            return self
        for line in content:
            self.writeln(f"# {line}" if line else "#")
        return self

    def docstring(self, content: str | Iterable[str]) -> CodeWriter:
        """
        Writes a docstring. If content is a string, it writes a single-line docstring. If content is an iterable of strings, it writes a multi-line docstring.

        Nothing in the content is escaped, so a triple quote inside it closes the docstring early
        and breaks the generated file. The content the generator passes comes from protobuf
        message and enum names, which cannot contain one.

        Args:
            content: A string for a single-line docstring or an iterable of strings for a multi line docstring
        Returns:
            The CodeWriter instance
        """
        if isinstance(content, str):
            self.writeln(f'"""{content}"""')
            return self
        self.writeln('"""')
        for line in content:
            self.writeln(line)
        self.writeln('"""')
        return self

    def import_(self, module: str, *items: str) -> CodeWriter:
        """
        Writes an import statement. If items are provided, it writes a from-import statement.
        Otherwise, it writes a regular import statement.

        The import is written wherever the writer currently is, with no sorting and no grouping,
        so the caller decides the order. The generator sorts its own import lists before calling
        this.

        Args:
            module: The module to import
            *items: Optional items to import from the module (if empty, imports the whole module)
        Returns:
            The CodeWriter instance
        """
        if items:
            self.writeln(f"from {module} import {', '.join(items)}")
        else:
            self.writeln(f"import {module}")
        return self

    @contextmanager
    def block(self, header: str) -> Generator[CodeWriter, None, None]:
        """
        Create a generic code block with a header (e.g. if, for, while, try, etc.)

        The header is written exactly as given, trailing colon included, so this is the escape
        hatch for a construct that has no method of its own, such as ``try`` or ``with``.

        Args:
            header: The header line for the code block

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            body of the block.
        """
        self.writeln(header)
        with self.indent():
            yield self

    @contextmanager
    def class_(
        self,
        name: str,
        bases: Iterable[str] | None = None,
        decorators: Iterable[str] | None = None,
    ) -> Generator[CodeWriter, None, None]:
        """
        Generate a class definition with optional base classes and decorators.

        The body is not given a ``pass`` statement when nothing is written inside the ``with``
        statement, so an empty body produces a syntax error in the generated file. The caller is
        responsible for writing at least one statement.

        Args:
            name: The name of the class
            bases: Optional iterable of base class names. ``None`` and an empty iterable both
                produce a class statement with no parenthesized base list at all.
            decorators: Optional iterable of decorator names, written in the order given, each
                already without its leading ``@``

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            class body.
        """
        if decorators is not None:
            for dec in decorators:
                self.writeln(f"@{dec}")

        bases_str = f"({', '.join(bases)})" if bases else ""
        self.writeln(f"class {name}{bases_str}:")

        with self.indent():
            yield self

    @contextmanager
    def dataclass(
        self,
        name: str,
        bases: Iterable[str] | None = None,
        decorators: Iterable[str] | None = None,
        frozen: bool = False,
        slots: bool = False,
        decorator_name: str = "dataclasses.dataclass",
    ) -> Generator[CodeWriter, None, None]:
        """
        Generate a dataclass definition with optional base classes, decorators and dataclass parameters.

        The dataclass decorator is written last, immediately above the class statement, so any
        decorator passed in ``decorators`` wraps it. With neither ``frozen`` nor ``slots`` set the
        decorator is written bare, without parentheses.

        Args:
            name: The name of the dataclass
            bases: Optional iterable of base class names
            decorators: Optional iterable of additional decorator names, written above the
                dataclass decorator
            frozen: Whether to set frozen=True in the dataclass decorator
            slots: Whether to set slots=True in the dataclass decorator
            decorator_name: The full name of the dataclass decorator to use. The default assumes
                the generated module imports ``dataclasses`` rather than ``dataclass`` itself.

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            class body.
        """
        dc_params = []
        if frozen:
            dc_params.append("frozen=True")
        if slots:
            dc_params.append("slots=True")

        dc_decorator = f"{decorator_name}({', '.join(dc_params)})" if dc_params else decorator_name

        all_decorators = []
        if decorators is not None:
            all_decorators.extend(decorators)
        all_decorators.append(dc_decorator)

        for dec in all_decorators:
            self.writeln(f"@{dec}")

        bases_str = f"({', '.join(bases)})" if bases else ""
        self.writeln(f"class {name}{bases_str}:")

        with self.indent():
            yield self

    @contextmanager
    def enum(
        self,
        name: str,
        enum_type: str = "enum.Enum",
        bases: Iterable[str] | None = None,
        decorators: Iterable[str] | None = None,
    ) -> Generator[CodeWriter, None, None]:
        """
        Generate an enum definition with optional base classes and decorators.

        ``enum_type`` is written as the first base and anything in ``bases`` follows it, which is
        the opposite of the order Python's own enum documentation uses for mixins. The generated
        OTLP enums pass ``enum.IntEnum`` and nothing else, so the ordering does not arise there.

        Args:
            name: The name of the enum
            enum_type: The base enum type to inherit from (default: "enum.Enum")
            bases: Optional iterable of additional base class names
            decorators: Optional iterable of decorator names

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            enum body.
        """
        if decorators is not None:
            for dec in decorators:
                self.writeln(f"@{dec}")

        all_bases = [enum_type]
        if bases is not None:
            all_bases.extend(bases)

        bases_str = ", ".join(all_bases)
        self.writeln(f"class {name}({bases_str}):")

        with self.indent():
            yield self

    def field(
        self,
        name: str,
        type_hint: str,
        default: Any = None,
        default_factory: str | None = None,
    ) -> CodeWriter:
        """
        Write a dataclass field with optional default value or default factory.

        ``default`` is interpolated into the line as it is, so a string passed there is written
        without quotes and has to arrive already in Python source form: ``'""'`` for an empty
        string default, not ``""``. A ``default`` of ``None`` means no default at all rather than
        a default of ``None``, so to write ``= None`` pass the string ``"None"``.

        Args:
            name: The name of the field
            type_hint: The type hint for the field
            default: Optional default value for the field, already written as Python source
            default_factory: Optional default factory for the field, which takes precedence over
                ``default`` when both are given

        Returns:
            The CodeWriter instance
        """
        if default_factory:
            self.writeln(f"{name}: {type_hint} = dataclasses.field(default_factory={default_factory})")
        elif default is not None:
            self.writeln(f"{name}: {type_hint} = {default}")
        else:
            self.writeln(f"{name}: {type_hint}")
        return self

    def enum_member(self, name: str, value: Any) -> CodeWriter:
        """
        Write an enum member with a specific value.

        ``value`` is interpolated with ``str``, so an integer comes out as a numeric literal and a
        string comes out unquoted. Pass a string member value already quoted.

        Args:
            name: The name of the enum member
            value: The value of the enum member, already written as Python source

        Returns:
            The CodeWriter instance
        """
        self.writeln(f"{name} = {value}")
        return self

    @contextmanager
    def function(
        self,
        name: str,
        params: Iterable[str] | str,
        decorators: Iterable[str] | None = None,
        return_type: str | None = None,
    ) -> Generator[CodeWriter, None, None]:
        """
        Create a function definition with optional decorators and return type.

        As with ``class_``, an empty body produces a syntax error, so write at least a ``pass``
        statement inside the ``with`` statement.

        Args:
            name: The name of the function
            params: An iterable of parameter strings or a single string for the parameter list.
                An iterable is joined with ``", "``; a string is written as it stands, which is
                the way to pass something a comma would split wrongly, such as a default value
                holding a comma.
            decorators: Optional iterable of decorator names
            return_type: Optional return type hint for the function. ``None`` and the empty string
                both leave the arrow off entirely.

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            function body.
        """
        if decorators is not None:
            for dec in decorators:
                self.writeln(f"@{dec}")

        params_str = params if isinstance(params, str) else ", ".join(params)
        return_annotation = f" -> {return_type}" if return_type else ""
        self.writeln(f"def {name}({params_str}){return_annotation}:")

        with self.indent():
            yield self

    @contextmanager
    def method(
        self,
        name: str,
        params: Iterable[str] | str,
        decorators: Iterable[str] | None = None,
        return_type: str | None = None,
    ) -> Generator[CodeWriter, None, None]:
        """
        Create a method definition within a class with optional decorators and return type.

        This delegates to ``function`` and adds nothing. It exists so that generator code reads as
        what it is building, and it does not supply ``self``: the caller lists it in ``params``
        like any other parameter, or omits it for a ``staticmethod``.

        Args:
            name: The name of the method
            params: An iterable of parameter strings or a single string for the parameter list,
                including the receiver when there is one
            decorators: Optional iterable of decorator names
            return_type: Optional return type hint for the method

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            method body.
        """
        with self.function(name, params, decorators=decorators, return_type=return_type):
            yield self

    @contextmanager
    def if_(self, condition: str) -> Generator[CodeWriter, None, None]:
        """
        Create an if block

        Args:
            condition: The condition for the if statement, written as Python source without the
                ``if`` keyword and without the trailing colon

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            body of the branch.
        """
        self.writeln(f"if {condition}:")
        with self.indent():
            yield self

    @contextmanager
    def elif_(self, condition: str) -> Generator[CodeWriter, None, None]:
        """
        Create an elif block

        Nothing checks that an ``if`` block precedes this one at the same indentation level. The
        caller has to get that ordering right, which is why the generator decides between ``if_``
        and ``elif_`` from the position of a field within its oneof group.

        Args:
            condition: The condition for the elif statement, written as Python source without the
                ``elif`` keyword and without the trailing colon

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            body of the branch.
        """
        self.writeln(f"elif {condition}:")
        with self.indent():
            yield self

    @contextmanager
    def else_(self) -> Generator[CodeWriter, None, None]:
        """
        Create an else block

        As with ``elif_``, the preceding ``if`` block is the caller's responsibility.

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            body of the branch.
        """
        self.writeln("else:")
        with self.indent():
            yield self

    @contextmanager
    def for_(self, var: str, iterable: str) -> Generator[CodeWriter, None, None]:
        """
        Create a for loop

        Args:
            var: The loop variable, or several separated by commas for tuple unpacking
            iterable: The iterable to loop over, written as a Python expression

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            loop body.
        """
        self.writeln(f"for {var} in {iterable}:")
        with self.indent():
            yield self

    @contextmanager
    def while_(self, condition: str) -> Generator[CodeWriter, None, None]:
        """
        Create a while loop

        Args:
            condition: The condition for the while loop, written as Python source without the
                ``while`` keyword and without the trailing colon

        Returns:
            A context manager yielding this ``CodeWriter``, with the indentation raised for the
            loop body.
        """
        self.writeln(f"while {condition}:")
        with self.indent():
            yield self

    def assignment(self, var: str, value: str, type_hint: str | None = None) -> CodeWriter:
        """
        Write a variable assignment with optional type hint

        Args:
            var: The variable name
            value: The value to assign to the variable
            type_hint: Optional type hint for the variable
        Returns:
            The CodeWriter instance
        """
        if type_hint:
            self.writeln(f"{var}: {type_hint} = {value}")
        else:
            self.writeln(f"{var} = {value}")
        return self

    def return_(self, value: str | None = None) -> CodeWriter:
        """
        Write a return statement with an optional return value

        Args:
            value: The value to return, written as a Python expression. ``None`` writes a bare
                return statement, and so does the empty string, since the check is on truthiness.
        Returns:
            The CodeWriter instance
        """
        if value:
            self.writeln(f"return {value}")
        else:
            self.writeln("return")
        return self

    def pass_(self) -> CodeWriter:
        """
        Write a pass statement

        Returns:
            The CodeWriter instance
        """
        self.writeln("pass")
        return self

    def blank_line(self, count: int = 1) -> CodeWriter:
        """
        Write one or more blank lines

        These bypass ``writeln`` and are appended as empty strings, so the current indentation
        level has no effect on them.

        Args:
            count: The number of blank lines to write. Zero and any negative number write none.
        Returns:
            The CodeWriter instance
        """
        self._lines.extend([""] * count)
        return self

    def to_string(self) -> str:
        """
        Get the generated code as a single string with newline characters separating lines.

        The lines are joined rather than terminated, so the result has no trailing newline unless
        the last line written was blank. The generator relies on that: it ends each file with
        ``blank_line``.

        Returns:
            A string containing the entire generated code.
        """
        return "\n".join(self._lines)

    def to_lines(self) -> list[str]:
        """
        Get the generated code as a list of lines

        Returns:
            A list of strings, where each string is a line of generated code. This is the
            writer's own list and not a copy, so mutating it changes what the writer will produce
            and what a later call returns.
        """
        return self._lines
