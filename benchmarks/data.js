window.BENCHMARK_DATA = {
  "lastUpdate": 1608593316418,
  "repoUrl": "https://github.com/ocelotl/opentelemetry-python",
  "entries": {
    "OpenTelemetry Python Benchmarks - Python 3.8 - core": [
      {
        "commit": {
          "author": {
            "email": "aboten@lightstep.com",
            "name": "alrex",
            "username": "codeboten"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "001163739d7cc09a26592b688f9880da02baf208",
          "message": "Remove SDK dependency from auto-instrumentation (#1420)",
          "timestamp": "2020-12-14T15:03:25-08:00",
          "tree_id": "3a2c11fff71c03c32ec35d12b2a7e3336dd0c7f9",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/001163739d7cc09a26592b688f9880da02baf208"
        },
        "date": 1608055702728,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 27318.15144909692,
            "unit": "iter/sec",
            "range": "stddev: 0.0000012599218965716674",
            "extra": "mean: 36.60569793177048 usec\nrounds: 4499"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 20358.69630876818,
            "unit": "iter/sec",
            "range": "stddev: 0.000002432099151059304",
            "extra": "mean: 49.11905874686658 usec\nrounds: 6911"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.5 - core": [
      {
        "commit": {
          "author": {
            "email": "aboten@lightstep.com",
            "name": "alrex",
            "username": "codeboten"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "001163739d7cc09a26592b688f9880da02baf208",
          "message": "Remove SDK dependency from auto-instrumentation (#1420)",
          "timestamp": "2020-12-14T15:03:25-08:00",
          "tree_id": "3a2c11fff71c03c32ec35d12b2a7e3336dd0c7f9",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/001163739d7cc09a26592b688f9880da02baf208"
        },
        "date": 1608055705100,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 20632.000411338657,
            "unit": "iter/sec",
            "range": "stddev: 0.000003650372899480281",
            "extra": "mean: 48.468397637799264 usec\nrounds: 1270"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 14359.574325823149,
            "unit": "iter/sec",
            "range": "stddev: 0.0000048885056388747515",
            "extra": "mean: 69.63994734869523 usec\nrounds: 5337"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.7 - core": [
      {
        "commit": {
          "author": {
            "email": "aboten@lightstep.com",
            "name": "alrex",
            "username": "codeboten"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "001163739d7cc09a26592b688f9880da02baf208",
          "message": "Remove SDK dependency from auto-instrumentation (#1420)",
          "timestamp": "2020-12-14T15:03:25-08:00",
          "tree_id": "3a2c11fff71c03c32ec35d12b2a7e3336dd0c7f9",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/001163739d7cc09a26592b688f9880da02baf208"
        },
        "date": 1608055715915,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 23457.627774431356,
            "unit": "iter/sec",
            "range": "stddev: 0.0000014187474402946084",
            "extra": "mean: 42.630056611691685 usec\nrounds: 4787"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 17905.2056254884,
            "unit": "iter/sec",
            "range": "stddev: 0.0000020623549663323264",
            "extra": "mean: 55.849679747686395 usec\nrounds: 6498"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aboten@lightstep.com",
            "name": "alrex",
            "username": "codeboten"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6f2b5ceefa87f443bf574eac7debe2b0e996e59d",
          "message": "Deleting unused file (#1492)",
          "timestamp": "2020-12-20T08:47:13-08:00",
          "tree_id": "87105ad8d7516d10a729ab4afa1ab5d7ce66a2d7",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6f2b5ceefa87f443bf574eac7debe2b0e996e59d"
        },
        "date": 1608593315490,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 23641.953529947266,
            "unit": "iter/sec",
            "range": "stddev: 0.0000028478066643463316",
            "extra": "mean: 42.29768909465539 usec\nrounds: 4429"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 18313.095822748553,
            "unit": "iter/sec",
            "range": "stddev: 0.000003771794966876123",
            "extra": "mean: 54.60573185871712 usec\nrounds: 6601"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.6 - core": [
      {
        "commit": {
          "author": {
            "email": "aboten@lightstep.com",
            "name": "alrex",
            "username": "codeboten"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "001163739d7cc09a26592b688f9880da02baf208",
          "message": "Remove SDK dependency from auto-instrumentation (#1420)",
          "timestamp": "2020-12-14T15:03:25-08:00",
          "tree_id": "3a2c11fff71c03c32ec35d12b2a7e3336dd0c7f9",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/001163739d7cc09a26592b688f9880da02baf208"
        },
        "date": 1608055724533,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 15057.641014425071,
            "unit": "iter/sec",
            "range": "stddev: 0.00003264213546028253",
            "extra": "mean: 66.41146505232858 usec\nrounds: 1116"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 10500.490407719295,
            "unit": "iter/sec",
            "range": "stddev: 0.00006191960567998818",
            "extra": "mean: 95.2336473032596 usec\nrounds: 6266"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python pypy3 - core": [
      {
        "commit": {
          "author": {
            "email": "aboten@lightstep.com",
            "name": "alrex",
            "username": "codeboten"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "001163739d7cc09a26592b688f9880da02baf208",
          "message": "Remove SDK dependency from auto-instrumentation (#1420)",
          "timestamp": "2020-12-14T15:03:25-08:00",
          "tree_id": "3a2c11fff71c03c32ec35d12b2a7e3336dd0c7f9",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/001163739d7cc09a26592b688f9880da02baf208"
        },
        "date": 1608055780602,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 166433.8070066168,
            "unit": "iter/sec",
            "range": "stddev: 0.00002199775431760577",
            "extra": "mean: 6.0083946764508225 usec\nrounds: 135136"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 87931.44035845278,
            "unit": "iter/sec",
            "range": "stddev: 0.00004268046845464659",
            "extra": "mean: 11.372496525969517 usec\nrounds: 172414"
          }
        ]
      }
    ]
  }
}