# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access
import unittest
from unittest.mock import Mock

import opentelemetry._logs._internal as logs_internal
from opentelemetry._logs import NoOpLogger
from opentelemetry._logs.severity import SeverityNumber


class TestLoggerEnabled(unittest.TestCase):
    def test_noop_logger_enabled_returns_false_by_default(self):
        logger = NoOpLogger("noop-test")
        self.assertFalse(logger.enabled())

    def test_noop_logger_enabled_accepts_parameters(self):
        logger = NoOpLogger("noop-test")
        self.assertFalse(
            logger.enabled(
                context=None,
                severity_number=SeverityNumber.INFO,
                event_name="my.event",
            )
        )

    def test_proxy_logger_delegates_enabled_to_real_logger(self):
        logger = logs_internal.ProxyLogger("proxy-test")
        real_logger = Mock()
        real_logger.enabled.return_value = True
        logger._real_logger = real_logger

        result = logger.enabled(
            severity_number=SeverityNumber.WARN, event_name="warn.event"
        )

        self.assertTrue(result)
        real_logger.enabled.assert_called_once_with(
            context=None,
            severity_number=SeverityNumber.WARN,
            event_name="warn.event",
        )

    def test_proxy_logger_enabled_falls_back_to_noop(self):
        # No real logger and no provider set: proxy uses its no-op logger,
        # whose enabled() returns False.
        logger = logs_internal.ProxyLogger("proxy-test")
        self.assertFalse(logger.enabled())
