# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Exceptions raised by declarative configuration.

Nearly every error this package raises itself is a
``ConfigurationError`` or a subclass of it. Three places raise something
else. ``_resource._coerce_attribute_value`` lets the ``ValueError`` from
``int()`` or ``float()`` out when an attribute value does not fit its
declared type. ``_conversion._dict_to_dataclass`` raises ``TypeError``
for a class that is not a dataclass, and lets the one from the dataclass
constructor out. ``file._loader._dict_to_model`` re-raises that second
``TypeError`` with a message of its own.

That is still not the whole set a caller sees, because an SDK
constructor or a plugin reached through the configuration raises its own
exceptions and nothing here translates them: a plugin component handed a
configuration mapping its constructor does not accept raises
``TypeError``, a view with an empty selector raises a bare
``Exception``, and a Prometheus reader on a bound port raises
``OSError``. A caller that wants to survive any bad configuration file
has to catch more than ``ConfigurationError``.

``MissingDependencyError`` is the subclass raised when the configuration
selects a component whose package is not installed. It also inherits
``ImportError``, so code written before this package existed, which
caught ``ImportError`` around an optional exporter, keeps working. The
three ``otlp_file/development`` exporters are the exception: they report
a missing ``opentelemetry-exporter-otlp-json-file`` as a plain
``ConfigurationError``, so an ``except MissingDependencyError`` branch
does not catch that one.
"""


class ConfigurationError(Exception):
    """Raised when configuration loading, parsing, validation, or instantiation fails.

    This includes errors from:
    - File not found or inaccessible
    - Invalid YAML/JSON syntax
    - Schema validation failures
    - Environment variable substitution errors
    - Missing required SDK extensions (e.g., propagator packages not installed)
    """


class MissingDependencyError(ConfigurationError, ImportError):
    """Raised when an optional dependency is not installed.

    Inherits from both :class:`ConfigurationError` and :class:`ImportError` to
    maintain backwards compatibility with callers that catch ``ImportError``.

    The exception message is built from the four arguments and always ends
    with the ``pip install`` command that resolves it, so the text can be
    logged as-is and acted on without further lookup. Every argument is kept
    as an attribute of the same name, except that ``install_name`` falls back
    to ``package`` when it is ``None``.

    Args:
        package: Import-time name of the package that could not be imported.
            It appears in the message as the thing that is missing.
        feature: Description of what needed the package, for example
            ``"otlp_grpc span exporter"``. ``None`` produces a message that
            names only the package.
        install_name: Distribution name to put in the ``pip install``
            command, for when it differs from ``package``. ``None`` means use
            ``package``.
        extras: Extras to request in the ``pip install`` command, for example
            ``"file-configuration"``. ``None`` means install no extras.
    """

    def __init__(
        self,
        package: str,
        feature: str | None = None,
        install_name: str | None = None,
        extras: str | None = None,
    ) -> None:
        """Build the installation hint message. Parameters are documented on the class."""
        self.package = package
        self.feature = feature
        self.install_name = install_name or package
        self.extras = extras

        if extras:
            install_cmd = f'pip install "{self.install_name}[{extras}]"'
        else:
            install_cmd = f"pip install {self.install_name}"

        if feature:
            message = f"{feature} requires '{package}'. Install it with: {install_cmd}"
        else:
            message = f"'{package}' is required but not installed. Install it with: {install_cmd}"

        super().__init__(message)
