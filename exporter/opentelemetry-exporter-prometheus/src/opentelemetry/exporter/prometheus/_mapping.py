# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Translation of OpenTelemetry metric names, attribute keys and units to Prometheus spellings.

Prometheus accepts a narrower character set than OpenTelemetry does, and names
its units in words rather than in UCUM symbols. The functions here perform the
rewrites the OpenTelemetry to Prometheus compatibility specification requires,
at
https://github.com/open-telemetry/opentelemetry-specification/blob/v1.33.0/specification/compatibility/prometheus_and_openmetrics.md.
``_CustomCollector`` calls ``sanitize_full_name`` and ``map_unit`` once per
translated metric, and ``sanitize_attribute`` once per resource label, scope
label and data point attribute of every data point, plus once per resource
attribute carried by ``target_info``. All of them operate on single strings
and hold no state.
"""

from re import UNICODE, compile

_SANITIZE_NAME_RE = compile(r"[^a-zA-Z0-9:]+", UNICODE)
# Same as name, but doesn't allow ":"
_SANITIZE_ATTRIBUTE_KEY_RE = compile(r"[^a-zA-Z0-9]+", UNICODE)

# UCUM style annotations which are text enclosed in curly braces https://ucum.org/ucum#para-6.
_UNIT_ANNOTATION = compile(r"\{[^}]*\}")

# Remaps common UCUM and SI units to prometheus conventions. Copied from
# https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.101.0/pkg/translator/prometheus/normalize_name.go#L19
# See specification:
# https://github.com/open-telemetry/opentelemetry-specification/blob/v1.33.0/specification/compatibility/prometheus_and_openmetrics.md#metric-metadata-1
_UNIT_MAPPINGS = {
    # Time
    "d": "days",
    "h": "hours",
    "min": "minutes",
    "s": "seconds",
    "ms": "milliseconds",
    "us": "microseconds",
    "ns": "nanoseconds",
    # Bytes
    "By": "bytes",
    "KiBy": "kibibytes",
    "MiBy": "mebibytes",
    "GiBy": "gibibytes",
    "TiBy": "tibibytes",
    "KBy": "kilobytes",
    "MBy": "megabytes",
    "GBy": "gigabytes",
    "TBy": "terabytes",
    # SI
    "m": "meters",
    "V": "volts",
    "A": "amperes",
    "J": "joules",
    "W": "watts",
    "g": "grams",
    # Misc
    "Cel": "celsius",
    "Hz": "hertz",
    # TODO(https://github.com/open-telemetry/opentelemetry-specification/issues/4058): the
    # specification says to normalize "1" to ratio but that may change. Update this mapping or
    # remove TODO once a decision is made.
    "1": "",
    "%": "percent",
}
# Similar to _UNIT_MAPPINGS, but for "per" unit denominator.
# Example: s => per second (singular)
# Copied from https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/80317ce83ed87a2dff0c316bb939afbfaa823d5e/pkg/translator/prometheus/normalize_name.go#L58
_PER_UNIT_MAPPINGS = {
    "s": "second",
    "m": "minute",
    "h": "hour",
    "d": "day",
    "w": "week",
    "mo": "month",
    "y": "year",
}


def sanitize_full_name(name: str) -> str:
    """sanitize the given metric name according to Prometheus rule, including sanitizing
    leading digits

    https://github.com/open-telemetry/opentelemetry-specification/blob/v1.33.0/specification/compatibility/prometheus_and_openmetrics.md#metric-metadata-1

    Args:
        name: The metric name as recorded through the OpenTelemetry API, already
            carrying the configured prefix when ``PrometheusMetricReader`` was
            given one. An empty string is accepted and returned unchanged.

    Returns:
        The name with every run of characters outside ``a-zA-Z0-9:`` collapsed
        into a single underscore. A leading digit is replaced by an underscore
        rather than prefixed with one, so ``5xx_responses`` becomes
        ``_xx_responses`` and the digit is lost.
    """
    # Leading number special case
    if name and name[0].isdigit():
        name = "_" + name[1:]
    return _sanitize_name(name)


def _sanitize_name(name: str) -> str:
    """sanitize the given metric name according to Prometheus rule, but does not handle
    sanitizing a leading digit.

    Args:
        name: A metric name, or a fragment of one such as a unit, whose leading
            character has already been dealt with by the caller.

    Returns:
        The name with every run of characters outside ``a-zA-Z0-9:`` collapsed
        into a single underscore. A name starting with a digit is returned with
        that digit intact, which is why ``sanitize_full_name`` exists.
    """
    return _SANITIZE_NAME_RE.sub("_", name)


def sanitize_attribute(key: str) -> str:
    """sanitize the given metric attribute key according to Prometheus rule.

    https://github.com/open-telemetry/opentelemetry-specification/blob/v1.33.0/specification/compatibility/prometheus_and_openmetrics.md#metric-attributes

    Args:
        key: An attribute key taken from a metric data point, from an
            instrumentation scope or from the resource.

    Returns:
        The key with every run of characters outside ``a-zA-Z0-9`` collapsed
        into a single underscore, and a leading digit replaced by an
        underscore. A colon is not allowed in a label name, so unlike
        ``sanitize_full_name`` this replaces it. Two distinct keys can sanitize
        to the same label name, in which case the later one overwrites the
        earlier one in the exported label set.
    """
    # Leading number special case
    if key and key[0].isdigit():
        key = "_" + key[1:]
    return _SANITIZE_ATTRIBUTE_KEY_RE.sub("_", key)


def map_unit(unit: str) -> str:
    """Maps unit to common prometheus metric names if available and sanitizes any invalid
    characters

    See:
    - https://github.com/open-telemetry/opentelemetry-specification/blob/v1.33.0/specification/compatibility/prometheus_and_openmetrics.md#metric-metadata-1
    - https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.101.0/pkg/translator/prometheus/normalize_name.go#L108

    The exported value becomes a suffix of the Prometheus metric name, so an
    empty result means the metric name carries no unit suffix at all. That is
    what the dimensionless UCUM unit ``1`` maps to, and it is also what an
    input consisting only of a UCUM annotation produces.

    Args:
        unit: The unit recorded on the instrument, in UCUM notation. An empty
            string is accepted.

    Returns:
        The Prometheus spelling of the unit. A unit listed in the mapping
        copied from the collector, such as ``ms``, becomes its English name,
        ``milliseconds``. A ratio written with a single ``/``, such as ``m/s``,
        becomes ``meters_per_second``, and the denominator is singular. A
        ratio with an empty numerator, such as ``/s``, becomes ``per_second``.
        Any other unit is sanitized and stripped of surrounding underscores.
    """
    # remove curly brace unit annotations
    unit = _UNIT_ANNOTATION.sub("", unit)

    if unit in _UNIT_MAPPINGS:
        return _UNIT_MAPPINGS[unit]

    # replace "/" with "per" units like m/s -> meters_per_second
    ratio_unit_subparts = unit.split("/", maxsplit=1)
    if len(ratio_unit_subparts) == 2:
        bottom = _sanitize_name(ratio_unit_subparts[1])
        if bottom:
            top = _sanitize_name(ratio_unit_subparts[0])
            top = _UNIT_MAPPINGS.get(top, top)
            bottom = _PER_UNIT_MAPPINGS.get(bottom, bottom)
            return f"{top}_per_{bottom}" if top else f"per_{bottom}"

    return (
        # since units end up as a metric name suffix, they must be sanitized
        _sanitize_name(unit)
        # strip surrounding "_" chars since it will lead to consecutive underscores in the
        # metric name
        .strip("_")
    )
