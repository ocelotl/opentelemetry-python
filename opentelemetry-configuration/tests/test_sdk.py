# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import unittest
from unittest.mock import patch

import opentelemetry.configuration._config_provider as config_provider_module
from opentelemetry.configuration._config_provider import ConfigProperties
from opentelemetry.configuration._sdk import Providers, configure_sdk, create
from opentelemetry.configuration.models import (
    ExperimentalGeneralInstrumentation,
    ExperimentalInstrumentation,
    OpenTelemetryConfiguration,
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
    @patch("opentelemetry.configuration._sdk.set_config_provider")
    @patch("opentelemetry.configuration._sdk.set_global_textmap")
    @patch("opentelemetry.configuration._sdk.set_logger_provider")
    @patch("opentelemetry.configuration._sdk.metrics.set_meter_provider")
    @patch("opentelemetry.configuration._sdk.trace.set_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_logger_provider")
    @patch("opentelemetry.configuration._sdk.create_meter_provider")
    @patch("opentelemetry.configuration._sdk.create_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    # pylint: disable=no-self-use,too-many-arguments,too-many-positional-arguments
    def test_installs_present_sections_as_globals(
        self,
        mock_create_resource,
        mock_create_tracer,
        mock_create_meter,
        mock_create_logger,
        mock_set_tracer,
        mock_set_meter,
        mock_set_logger,
        mock_set_textmap,
        mock_set_config,
    ):
        sentinel_resource = object()
        mock_create_resource.return_value = sentinel_resource
        sentinel_tracer = object()
        mock_create_tracer.return_value = sentinel_tracer

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
        mock_create_tracer.assert_called_once_with(
            tracer_cfg, sentinel_resource
        )
        mock_set_tracer.assert_called_once_with(sentinel_tracer)
        # Absent meter/logger sections are not built or installed.
        mock_create_meter.assert_not_called()
        mock_create_logger.assert_not_called()
        mock_set_meter.assert_not_called()
        mock_set_logger.assert_not_called()
        # Propagator and ConfigProvider are always installed.
        mock_set_textmap.assert_called_once()
        mock_set_config.assert_called_once()

    @patch("opentelemetry.configuration._sdk.set_config_provider")
    @patch("opentelemetry.configuration._sdk.set_global_textmap")
    @patch("opentelemetry.configuration._sdk.trace.set_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    # pylint: disable=no-self-use
    def test_disabled_skips_everything(
        self,
        mock_create_resource,
        mock_set_tracer,
        mock_set_textmap,
        mock_set_config,
    ):
        config = _config(
            disabled=True,
            tracer_provider=TracerProviderConfig(processors=[]),
        )

        configure_sdk(config)

        mock_create_resource.assert_not_called()
        mock_set_tracer.assert_not_called()
        mock_set_textmap.assert_not_called()
        mock_set_config.assert_not_called()

    @patch("opentelemetry.configuration._sdk.set_config_provider")
    @patch("opentelemetry.configuration._sdk.set_global_textmap")
    @patch("opentelemetry.configuration._sdk.set_logger_provider")
    @patch("opentelemetry.configuration._sdk.metrics.set_meter_provider")
    @patch("opentelemetry.configuration._sdk.trace.set_tracer_provider")
    def test_absent_sections_do_not_set_provider_globals(
        self,
        mock_set_tracer,
        mock_set_meter,
        mock_set_logger,
        mock_set_textmap,
        mock_set_config,
    ):
        configure_sdk(_config())

        # No provider globals set when their sections are absent.
        mock_set_tracer.assert_not_called()
        mock_set_meter.assert_not_called()
        mock_set_logger.assert_not_called()
        # Propagator and ConfigProvider are always installed.
        mock_set_textmap.assert_called_once()
        mock_set_config.assert_called_once()


class TestCreate(unittest.TestCase):
    """The pure ``create`` builder returns providers without mutating globals."""

    def test_returns_providers_without_mutating_globals(self):
        config = _config(
            tracer_provider=TracerProviderConfig(
                processors=[
                    SpanProcessorConfig(
                        simple=SimpleSpanProcessorConfig(
                            exporter=SpanExporterConfig(console={})
                        )
                    )
                ]
            ),
            propagator=PropagatorConfig(),
        )

        with (
            patch(
                "opentelemetry.configuration._sdk.trace.set_tracer_provider"
            ) as set_tracer,
            patch(
                "opentelemetry.configuration._sdk.metrics.set_meter_provider"
            ) as set_meter,
            patch(
                "opentelemetry.configuration._sdk.set_logger_provider"
            ) as set_logger,
            patch(
                "opentelemetry.configuration._sdk.set_global_textmap"
            ) as set_textmap,
            patch(
                "opentelemetry.configuration._sdk.set_config_provider"
            ) as set_config,
        ):
            providers = create(config)

        set_tracer.assert_not_called()
        set_meter.assert_not_called()
        set_logger.assert_not_called()
        set_textmap.assert_not_called()
        set_config.assert_not_called()

        self.assertIsInstance(providers, Providers)
        self.assertIsInstance(providers.tracer_provider, SdkTracerProvider)
        # Absent sections yield None providers.
        self.assertIsNone(providers.meter_provider)
        self.assertIsNone(providers.logger_provider)
        # Propagator is always built.
        self.assertIsNotNone(providers.propagator)
        # ConfigProvider is always present with a read view.
        self.assertIsInstance(
            providers.config_provider.get_instrumentation_config(),
            ConfigProperties,
        )

    def test_exposes_instrumentation_config(self):
        config = _config(
            instrumentation_development=ExperimentalInstrumentation(
                general=ExperimentalGeneralInstrumentation(
                    stability_opt_in_list="http"
                )
            )
        )

        providers = create(config)

        instrumentation = (
            providers.config_provider.get_instrumentation_config()
        )
        general = instrumentation.get_config("general")
        self.assertIsNotNone(general)
        self.assertEqual(general.get_string("stability_opt_in_list"), "http")

    def test_configure_sdk_sets_config_provider_from_create(self):
        config_provider_module._CONFIG_PROVIDER = None
        config = _config(
            instrumentation_development=ExperimentalInstrumentation(
                general=ExperimentalGeneralInstrumentation(
                    stability_opt_in_list="db"
                )
            )
        )

        configure_sdk(config)

        provider = config_provider_module.get_config_provider()
        self.assertIsNotNone(provider)
        self.assertEqual(
            provider.get_instrumentation_config()
            .get_config("general")
            .get_string("stability_opt_in_list"),
            "db",
        )


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
