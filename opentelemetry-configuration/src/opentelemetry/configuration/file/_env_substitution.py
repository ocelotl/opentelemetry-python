# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Environment variable substitution for configuration files."""

import logging
import os
import re

_logger = logging.getLogger(__name__)


class EnvSubstitutionError(Exception):
    """Raised when environment variable substitution fails.

    This occurs when a ${VAR} reference is found but the environment
    variable is not set and no default value is provided.
    """


def substitute_env_vars(text: str) -> str:
    """Substitute environment variables in configuration text.

    Supports the following syntax:
    - ${VAR}: Substitute with environment variable VAR. Raises error if not found.
    - ${env:VAR}: Prefixed form of ${VAR}; the ``env:`` prefix is optional per
      the spec grammar and behaves identically.
    - ${VAR:-default}: Substitute with VAR if set and non-empty, otherwise use
      the default value.
    - $$: Escape sequence for literal $.

    Args:
        text: Configuration text with potential ${VAR} placeholders.

    Returns:
        Text with environment variables substituted.

    Raises:
        EnvSubstitutionError: If a required environment variable is not found.

    Examples:
        >>> os.environ['SERVICE_NAME'] = 'my-service'
        >>> substitute_env_vars('name: ${SERVICE_NAME}')
        'name: my-service'
        >>> substitute_env_vars('name: ${env:SERVICE_NAME}')
        'name: my-service'
        >>> substitute_env_vars('name: ${MISSING:-default}')
        'name: default'
        >>> substitute_env_vars('price: $$100')
        'price: $100'
    """
    # Pattern matches $$ (escape sequence) or
    # ${[env:]VAR_NAME} / ${[env:]VAR_NAME:-default_value}.
    # The optional ``env:`` prefix is part of the spec grammar for references.
    # Handling both in a single pass ensures $$ followed by ${VAR} works correctly.
    pattern = r"\$\$|\$\{(?:env:)?([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}"

    def replace_var(match) -> str:
        if match.group(1) is None:
            # Matched $$, return literal $
            return "$"

        var_name = match.group(1)
        has_default = match.group(2) is not None
        default_value = match.group(3) if has_default else None

        value = os.environ.get(var_name)

        # Per spec (configuration/data-model.md): when a default value is
        # provided via ``:-``, it applies when the referenced variable is
        # null, empty, or undefined. Treat a set-but-empty variable the same
        # as an unset one for the purpose of applying the default.
        if has_default and (value is None or value == ""):
            return default_value or ""

        # No default provided. An undefined variable is an error; a
        # set-but-empty variable substitutes to its (empty) value.
        if value is None:
            _logger.error(
                "Environment variable '%s' not found and no default provided",
                var_name,
            )
            raise EnvSubstitutionError(
                f"Environment variable '{var_name}' not found and no default provided"
            )

        # Per spec: "It MUST NOT be possible to inject YAML structures by
        # environment variables." Newlines are the primary injection vector —
        # a value like "legit\nmalicious_key: val" would create extra YAML
        # keys if substituted verbatim. Wrap such values in a YAML
        # double-quoted scalar so the newline is treated as literal text.
        # Simple values (no newlines) are returned as-is so that YAML type
        # coercion still applies per spec ("Node types MUST be interpreted
        # after environment variable substitution takes place").
        if "\n" in value or "\r" in value:
            escaped = (
                value.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t")
            )
            return f'"{escaped}"'
        return value

    return re.sub(pattern, replace_var, text)
