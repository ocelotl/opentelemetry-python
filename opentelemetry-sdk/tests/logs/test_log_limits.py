# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import patch

from opentelemetry._logs import LogRecord as APILogRecord
from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider, LogRecordLimits
from opentelemetry.sdk._logs._internal import (
    _DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT,
)
from opentelemetry.sdk._logs.export import (
    InMemoryLogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_ATTRIBUTE_COUNT_LIMIT,
    OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
    OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT,
    OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT,
)


class TestLogLimits(unittest.TestCase):
    def test_log_limits_repr_unset(self):
        expected = (
            f"LogRecordLimits("
            f"max_attributes={_DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT}, "
            f"max_attribute_length=None, "
            f"max_log_record_attributes={_DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT}, "
            f"max_log_record_attribute_length=None)"
        )
        limits = str(LogRecordLimits())

        self.assertEqual(expected, limits)

    def test_log_limits_max_attributes(self):
        expected = 1
        limits = LogRecordLimits(max_attributes=1)

        self.assertEqual(expected, limits.max_attributes)

    def test_log_limits_max_attribute_length(self):
        expected = 1
        limits = LogRecordLimits(max_attribute_length=1)

        self.assertEqual(expected, limits.max_attribute_length)

    def test_log_limits_max_log_record_attributes(self):
        limits = LogRecordLimits(max_log_record_attributes=5)

        self.assertEqual(5, limits.max_log_record_attributes)

    def test_log_limits_max_log_record_attribute_length(self):
        limits = LogRecordLimits(max_log_record_attribute_length=10)

        self.assertEqual(10, limits.max_log_record_attribute_length)

    @patch.dict("os.environ", {OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT: "7"})
    def test_logrecord_count_env_var(self):
        limits = LogRecordLimits()

        self.assertEqual(7, limits.max_log_record_attributes)
        self.assertEqual(
            _DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT, limits.max_attributes
        )

    @patch.dict(
        "os.environ", {OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT: "20"}
    )
    def test_logrecord_length_env_var(self):
        limits = LogRecordLimits()

        self.assertEqual(20, limits.max_log_record_attribute_length)
        self.assertIsNone(limits.max_attribute_length)

    @patch.dict(
        "os.environ",
        {
            OTEL_ATTRIBUTE_COUNT_LIMIT: "50",
            OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT: "3",
        },
    )
    def test_logrecord_count_env_takes_precedence(self):
        limits = LogRecordLimits()

        self.assertEqual(50, limits.max_attributes)
        self.assertEqual(3, limits.max_log_record_attributes)

    @patch.dict(
        "os.environ",
        {
            OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT: "100",
            OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT: "25",
        },
    )
    def test_logrecord_length_env_takes_precedence(self):
        limits = LogRecordLimits()

        self.assertEqual(100, limits.max_attribute_length)
        self.assertEqual(25, limits.max_log_record_attribute_length)

    @patch.dict("os.environ", {OTEL_ATTRIBUTE_COUNT_LIMIT: "42"}, clear=True)
    def test_global_count_env_applies_as_fallback(self):
        limits = LogRecordLimits()

        self.assertEqual(42, limits.max_attributes)
        self.assertEqual(42, limits.max_log_record_attributes)

    @patch.dict(
        "os.environ", {OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT: "60"}, clear=True
    )
    def test_global_length_env_applies_as_fallback(self):
        limits = LogRecordLimits()

        self.assertEqual(60, limits.max_attribute_length)
        self.assertEqual(60, limits.max_log_record_attribute_length)

    def test_invalid_env_vars_raise(self):
        env_vars = [
            OTEL_ATTRIBUTE_COUNT_LIMIT,
            OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
            OTEL_LOGRECORD_ATTRIBUTE_COUNT_LIMIT,
            OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT,
        ]

        bad_values = ["bad", "-1"]
        test_cases = {
            env_var: bad_value
            for env_var in env_vars
            for bad_value in bad_values
        }

        for env_var, bad_value in test_cases.items():
            with self.subTest(f"Testing {env_var}={bad_value}"):
                with (
                    self.assertRaises(ValueError) as error,
                    patch.dict("os.environ", {env_var: bad_value}, clear=True),
                ):
                    LogRecordLimits()

                expected_msg = f"{env_var} must be a non-negative integer but got {bad_value}"
                self.assertEqual(
                    expected_msg,
                    str(error.exception),
                    f"Unexpected error message for {env_var}={bad_value}",
                )


class TestLoggerProviderLimits(unittest.TestCase):
    @staticmethod
    def _emit_and_get_record(provider, attributes):
        exporter = InMemoryLogRecordExporter()
        provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
        logger = provider.get_logger("test_logger_provider_limits")
        logger.emit(
            APILogRecord(
                body="body",
                severity_number=SeverityNumber.WARN,
                attributes=attributes,
            )
        )
        finished = exporter.get_finished_logs()
        assert len(finished) == 1
        return finished[0]

    def test_default_provider_uses_default_attribute_count_limit(self):
        provider = LoggerProvider()
        attributes = {
            f"key_{index}": index
            for index in range(_DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT + 5)
        }

        record = self._emit_and_get_record(provider, attributes)

        self.assertEqual(
            len(record.log_record.attributes),
            _DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT,
        )
        self.assertEqual(record.dropped_attributes, 5)

    def test_programmatic_limits_bound_attribute_count(self):
        provider = LoggerProvider(
            limits=LogRecordLimits(max_log_record_attributes=2)
        )
        attributes = {"a": 1, "b": 2, "c": 3, "d": 4}

        record = self._emit_and_get_record(provider, attributes)

        self.assertEqual(len(record.log_record.attributes), 2)
        self.assertEqual(record.dropped_attributes, 2)

    def test_programmatic_limits_bound_attribute_value_length(self):
        provider = LoggerProvider(
            limits=LogRecordLimits(max_log_record_attribute_length=3)
        )
        attributes = {"key": "abcdefgh"}

        record = self._emit_and_get_record(provider, attributes)

        self.assertEqual(record.log_record.attributes["key"], "abc")

    def test_programmatic_limits_via_global_fallbacks(self):
        provider = LoggerProvider(
            limits=LogRecordLimits(max_attributes=1, max_attribute_length=2)
        )
        attributes = {"first": "abcd", "second": "efgh"}

        record = self._emit_and_get_record(provider, attributes)

        # max_attributes / max_attribute_length act as global fallbacks for the
        # log-record-specific limits when the latter are unset.
        self.assertEqual(len(record.log_record.attributes), 1)
        # BoundedAttributes evicts the oldest key when full, so "second"
        # survives and its value is truncated to the length limit.
        self.assertEqual(record.log_record.attributes["second"], "ef")
