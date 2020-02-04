# Overview

This example shows how to use auto-instrumentation in OpenTelemetry.

A uninstrumented script will be executed once without the agent and then a instrumented script will
be run with the agent. The results should show a `Span` being started in both cases.

## Preparation

This example will be executed in a separate virtual environment:

```sh
$ mkdir auto_instrumentation
$ virtualenv auto_instrumentation
$ source auto_instrumentation/bin/activate
```

## Installation

```sh
$ git clone git@github.com:open-telemetry/opentelemetry-python.git
$ cd opentelemetry-python
$ git checkout issue_300
$ pip3 install -e opentelemetry-api
$ pip3 install -e opentelemetry-sdk
$ pip3 install -e ext/opentelemetry-flask
$ pip3 install flask
$ pip3 install requests
```

## Execution of manually traced publisher

This is done in 3 separate consoles, one to run each of the scripts that make up this example:

```sh
$ source auto_instrumentation/bin/activate
$ python3 opentelemetry-python/examples/auto_instrumentation/formatter.py
```

```sh
$ source auto_instrumentation/bin/activate
$ python3 opentelemetry-python/examples/auto_instrumentation/publisher.py
```

```sh
$ source auto_instrumentation/bin/activate
$ python3 opentelemetry-python/examples/auto_instrumentation/hello.py testing
```

The execution of `publisher.py` should return an output similar to:

```sh
Hello, testing!
Span(name="publish", context=SpanContext(trace_id=0xd18be4c644d3be57a8623bbdbdbcef76, span_id=0x6162c475bab8d365, trace_state={}), kind=SpanKind.SERVER, parent=SpanContext(trace_id=0xd18be4c644d3be57a8623bbdbdbcef76, span_id=0xdafb264c5b1b6ed0, trace_state={}), start_time=2019-12-19T01:11:12.172866Z, end_time=2019-12-19T01:11:12.173383Z)
127.0.0.1 - - [18/Dec/2019 19:11:12] "GET /publish?helloStr=Hello%2C+testing%21 HTTP/1.1" 200 -
```

Now, kill the execution of `publisher.py` with `ctrl + c` and run this instead:

```sh
$ auto_agent python3 opentelemetry-python/examples/auto_instrumentation/hello.py testing
```

In the console where you previously executed `hello.py`, run again this:

```sh
$ python3 opentelemetry-python/examples/auto_instrumentation/hello.py testing
```

That should produce an output similar to this in the console where the `auto_agent` was executed:

```sh
Hello, testing!
Span(name="publish", context=SpanContext(trace_id=0xd18be4c644d3be57a8623bbdbdbcef76, span_id=0x6162c475bab8d365, trace_state={}), kind=SpanKind.SERVER, parent=SpanContext(trace_id=0xd18be4c644d3be57a8623bbdbdbcef76, span_id=0xdafb264c5b1b6ed0, trace_state={}), start_time=2019-12-19T01:11:12.172866Z, end_time=2019-12-19T01:11:12.173383Z)
127.0.0.1 - - [18/Dec/2019 19:11:12] "GET /publish?helloStr=Hello%2C+testing%21 HTTP/1.1" 200 -
```
