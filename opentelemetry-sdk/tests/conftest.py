from os import environ


def pytest_sessionstart(session):
    environ["OPENTELEMETRY_CONTEXT"] = "contextvars_context"


def pytest_sessionfinish(session):
    environ.pop("OPENTELEMETRY_CONTEXT")
