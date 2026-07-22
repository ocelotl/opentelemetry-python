# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import logging
import unittest
from unittest.mock import patch

from opentelemetry.configuration._sdk import configure_sdk
from opentelemetry.configuration.models import (
    AttributeLimits as AttributeLimitsConfig,
)
from opentelemetry.configuration.models import (
    OpenTelemetryConfiguration,
    SeverityNumber,
)
from opentelemetry.configuration.models import (
    Propagator as PropagatorConfig,
)
from opentelemetry.configuration.models import (
    Resource as ResourceConfig,
)
from opentelemetry.configuration.models import (
    SimpleSpanProcessor as SimpleSpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    SpanExporter as SpanExporterConfig,
)
from opentelemetry.configuration.models import (
    SpanProcessor as SpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    TracerProvider as TracerProviderConfig,
)
from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider

_MIN_CONFIG_KWARGS = {"file_format": "1.0"}


def _config(**kwargs) -> OpenTelemetryConfiguration:
    return OpenTelemetryConfiguration(**{**_MIN_CONFIG_KWARGS, **kwargs})


class TestConfigureSdk(unittest.TestCase):
    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    # pylint: disable=no-self-use
    def test_calls_each_signal_with_resource(
        self,
        mock_create_resource,
        mock_tracer,
        mock_meter,
        mock_logger,
        mock_propagator,
    ):
        sentinel_resource = object()
        mock_create_resource.return_value = sentinel_resource

        resource_cfg = ResourceConfig()
        tracer_cfg = TracerProviderConfig(processors=[])
        propagator_cfg = PropagatorConfig()
        config = _config(
            resource=resource_cfg,
            tracer_provider=tracer_cfg,
            propagator=propagator_cfg,
        )

        configure_sdk(config)

        mock_create_resource.assert_called_once_with(resource_cfg)
        mock_tracer.assert_called_once_with(
            tracer_cfg, sentinel_resource, None
        )
        mock_meter.assert_called_once_with(None, sentinel_resource)
        mock_logger.assert_called_once_with(None, sentinel_resource)
        mock_propagator.assert_called_once_with(propagator_cfg)

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    # pylint: disable=no-self-use
    def test_disabled_skips_everything(
        self,
        mock_create_resource,
        mock_tracer,
        mock_meter,
        mock_logger,
        mock_propagator,
    ):
        config = _config(
            disabled=True,
            tracer_provider=TracerProviderConfig(processors=[]),
        )

        configure_sdk(config)

        mock_create_resource.assert_not_called()
        mock_tracer.assert_not_called()
        mock_meter.assert_not_called()
        mock_logger.assert_not_called()
        mock_propagator.assert_not_called()

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    def test_absent_sections_pass_none(
        self,
        mock_create_resource,  # noqa: ARG002
        mock_tracer,
        mock_meter,
        mock_logger,
        mock_propagator,
    ):
        configure_sdk(_config())

        # Each configure_* is called exactly once, with config=None.
        self.assertEqual(mock_tracer.call_args.args[0], None)
        self.assertEqual(mock_meter.call_args.args[0], None)
        self.assertEqual(mock_logger.call_args.args[0], None)
        self.assertEqual(mock_propagator.call_args.args[0], None)


class TestConfigureSdkIntegration(unittest.TestCase):
    """End-to-end: build a real OpenTelemetryConfiguration and apply it."""

    @patch(
        "opentelemetry.configuration._tracer_provider.trace.set_tracer_provider"
    )
    def test_applies_tracer_provider_globally(self, mock_set_tracer):
        config = _config(
            tracer_provider=TracerProviderConfig(
                processors=[
                    SpanProcessorConfig(
                        simple=SimpleSpanProcessorConfig(
                            exporter=SpanExporterConfig(console={})
                        )
                    )
                ]
            )
        )

        configure_sdk(config)

        mock_set_tracer.assert_called_once()
        self.assertIsInstance(
            mock_set_tracer.call_args[0][0], SdkTracerProvider
        )


class TestConfigureSdkLogLevel(unittest.TestCase):
    """Top-level ``log_level`` is applied to the SDK's internal logger."""

    def setUp(self):
        self._otel_logger = logging.getLogger("opentelemetry")
        self._original_level = self._otel_logger.level
        self.addCleanup(self._otel_logger.setLevel, self._original_level)

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    def test_log_level_sets_internal_logger_level(self, *_mocks):
        configure_sdk(_config(log_level=SeverityNumber.debug))
        self.assertEqual(self._otel_logger.level, logging.DEBUG)

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    def test_log_level_error_maps_to_logging_error(self, *_mocks):
        configure_sdk(_config(log_level=SeverityNumber.error))
        self.assertEqual(self._otel_logger.level, logging.ERROR)

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    def test_log_level_absent_leaves_internal_logger_untouched(self, *_mocks):
        self._otel_logger.setLevel(logging.WARNING)
        configure_sdk(_config())
        self.assertEqual(self._otel_logger.level, logging.WARNING)


class TestConfigureSdkAttributeLimits(unittest.TestCase):
    """Top-level ``attribute_limits`` are threaded to the tracer provider."""

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    def test_attribute_limits_passed_to_tracer_provider(
        self,
        mock_create_resource,
        mock_tracer,
        _mock_meter,
        _mock_logger,
        _mock_propagator,
    ):
        sentinel_resource = object()
        mock_create_resource.return_value = sentinel_resource
        limits = AttributeLimitsConfig(
            attribute_count_limit=7, attribute_value_length_limit=42
        )

        configure_sdk(_config(attribute_limits=limits))

        mock_tracer.assert_called_once_with(None, sentinel_resource, limits)

    def test_attribute_limits_applied_to_span_limits(self):
        from opentelemetry.configuration._tracer_provider import (  # noqa: PLC0415
            create_tracer_provider,
        )

        provider = create_tracer_provider(
            None,
            None,
            AttributeLimitsConfig(
                attribute_count_limit=9, attribute_value_length_limit=11
            ),
        )
        span_limits = provider._span_limits
        self.assertEqual(span_limits.max_span_attributes, 9)
        self.assertEqual(span_limits.max_attribute_length, 11)
