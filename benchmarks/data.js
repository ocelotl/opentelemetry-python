window.BENCHMARK_DATA = {
  "lastUpdate": 1611866035472,
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
        "date": 1608593333947,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 25361.73642224003,
            "unit": "iter/sec",
            "range": "stddev: 0.00004483446535128743",
            "extra": "mean: 39.429476884046764 usec\nrounds: 4737"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 20536.09372578156,
            "unit": "iter/sec",
            "range": "stddev: 0.00006896685475262464",
            "extra": "mean: 48.694752437001846 usec\nrounds: 9541"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126817860,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 32357.54428368281,
            "unit": "iter/sec",
            "range": "stddev: 0.000001059784090947924",
            "extra": "mean: 30.90469385540724 usec\nrounds: 4524"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 22978.30208889609,
            "unit": "iter/sec",
            "range": "stddev: 0.0000022630348966225202",
            "extra": "mean: 43.51931644606738 usec\nrounds: 7777"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432544905,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 28410.044820043448,
            "unit": "iter/sec",
            "range": "stddev: 0.0000016469400868834257",
            "extra": "mean: 35.198818105858614 usec\nrounds: 4783"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 20294.24274406651,
            "unit": "iter/sec",
            "range": "stddev: 0.0000031362119439144394",
            "extra": "mean: 49.27505857750583 usec\nrounds: 9560"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491152483,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 31863.022596081377,
            "unit": "iter/sec",
            "range": "stddev: 0.000003943619428899388",
            "extra": "mean: 31.384342053066348 usec\nrounds: 5046"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 23131.40412398232,
            "unit": "iter/sec",
            "range": "stddev: 0.000006006860265417122",
            "extra": "mean: 43.23127098727283 usec\nrounds: 7576"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071477562,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 25905.415630813935,
            "unit": "iter/sec",
            "range": "stddev: 0.000014796039650938503",
            "extra": "mean: 38.60196702694557 usec\nrounds: 5277"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 16490.748165056506,
            "unit": "iter/sec",
            "range": "stddev: 0.000019624729091084104",
            "extra": "mean: 60.64006253633632 usec\nrounds: 10298"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245236052,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 16322.385403997137,
            "unit": "iter/sec",
            "range": "stddev: 0.00020310561331108353",
            "extra": "mean: 61.265554957127364 usec\nrounds: 3157"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 12085.63232279047,
            "unit": "iter/sec",
            "range": "stddev: 0.00007255499028134252",
            "extra": "mean: 82.74287793070214 usec\nrounds: 6398"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271821836,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 23232.602032486986,
            "unit": "iter/sec",
            "range": "stddev: 0.000019413787289693614",
            "extra": "mean: 43.04296172256831 usec\nrounds: 4598"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 15991.452524279233,
            "unit": "iter/sec",
            "range": "stddev: 0.000025332848806564194",
            "extra": "mean: 62.53340642332126 usec\nrounds: 9372"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852844807,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 21639.12768565938,
            "unit": "iter/sec",
            "range": "stddev: 0.000026519259205495285",
            "extra": "mean: 46.212583729182256 usec\nrounds: 4216"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 15258.614999562511,
            "unit": "iter/sec",
            "range": "stddev: 0.00003617298523437466",
            "extra": "mean: 65.53674760315216 usec\nrounds: 6676"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611866029467,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 24725.148889135642,
            "unit": "iter/sec",
            "range": "stddev: 0.000019520515100273307",
            "extra": "mean: 40.444650282344924 usec\nrounds: 4781"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 16765.397256781245,
            "unit": "iter/sec",
            "range": "stddev: 0.00002542582820769412",
            "extra": "mean: 59.64666298590218 usec\nrounds: 8059"
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
        "date": 1608593328247,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 20473.279220529497,
            "unit": "iter/sec",
            "range": "stddev: 0.000005083764524971905",
            "extra": "mean: 48.8441538469936 usec\nrounds: 1651"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 14136.618445343607,
            "unit": "iter/sec",
            "range": "stddev: 0.000004629961645030119",
            "extra": "mean: 70.73827477669423 usec\nrounds: 4702"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126871583,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 15617.96482890303,
            "unit": "iter/sec",
            "range": "stddev: 0.000016886068112172702",
            "extra": "mean: 64.02882904111635 usec\nrounds: 1398"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 10172.141011788164,
            "unit": "iter/sec",
            "range": "stddev: 0.000028394579816268948",
            "extra": "mean: 98.30772094499403 usec\nrounds: 3003"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432433692,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 24107.506669341732,
            "unit": "iter/sec",
            "range": "stddev: 0.000006251137901077054",
            "extra": "mean: 41.48085547443739 usec\nrounds: 2055"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 16175.723995399188,
            "unit": "iter/sec",
            "range": "stddev: 0.000008855872018956493",
            "extra": "mean: 61.82103504513473 usec\nrounds: 5764"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491151139,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 23132.797680439537,
            "unit": "iter/sec",
            "range": "stddev: 0.0000019458131846355297",
            "extra": "mean: 43.22866666687587 usec\nrounds: 1773"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 15309.410698694546,
            "unit": "iter/sec",
            "range": "stddev: 0.000002020894366019889",
            "extra": "mean: 65.31930063678227 usec\nrounds: 5026"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aaronabbott@google.com",
            "name": "Aaron Abbott",
            "username": "aabmass"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "76883321c2fb3f5f55c4136236183af7631253d3",
          "message": "boundlist typing wip (#1385)",
          "timestamp": "2021-01-15T10:09:06-08:00",
          "tree_id": "073d78c7e9c16897cbafb2296b0376dcb5fc55cc",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/76883321c2fb3f5f55c4136236183af7631253d3"
        },
        "date": 1610760487831,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 22584.650107180987,
            "unit": "iter/sec",
            "range": "stddev: 0.0000014265565793520912",
            "extra": "mean: 44.277861080612496 usec\nrounds: 1814"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 15087.72845334965,
            "unit": "iter/sec",
            "range": "stddev: 0.0000018914825810211757",
            "extra": "mean: 66.27902954987161 usec\nrounds: 5110"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071479965,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 23062.104265125767,
            "unit": "iter/sec",
            "range": "stddev: 0.0000014275970748995436",
            "extra": "mean: 43.36117764900525 usec\nrounds: 1897"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 15505.585798366748,
            "unit": "iter/sec",
            "range": "stddev: 0.0000013959926412386532",
            "extra": "mean: 64.49288746674331 usec\nrounds: 5625"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245144973,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 20817.1979429919,
            "unit": "iter/sec",
            "range": "stddev: 0.0000028819307333362487",
            "extra": "mean: 48.03720475438192 usec\nrounds: 1304"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 13639.689649560809,
            "unit": "iter/sec",
            "range": "stddev: 0.0000035315634133143953",
            "extra": "mean: 73.31545113507765 usec\nrounds: 5198"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271774058,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 23087.389281298958,
            "unit": "iter/sec",
            "range": "stddev: 0.0000013034838263896041",
            "extra": "mean: 43.31368903672496 usec\nrounds: 1952"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 15505.102596706083,
            "unit": "iter/sec",
            "range": "stddev: 0.0000015322905380806677",
            "extra": "mean: 64.49489732576428 usec\nrounds: 3029"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852837672,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 18123.25852203363,
            "unit": "iter/sec",
            "range": "stddev: 0.000017222923638035218",
            "extra": "mean: 55.17771535313226 usec\nrounds: 1472"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 11435.443208931703,
            "unit": "iter/sec",
            "range": "stddev: 0.000019451425686725938",
            "extra": "mean: 87.44741954723239 usec\nrounds: 4860"
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
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126838590,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 23764.060799297255,
            "unit": "iter/sec",
            "range": "stddev: 0.000002516760840708924",
            "extra": "mean: 42.08035017439325 usec\nrounds: 4592"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 17170.18177976635,
            "unit": "iter/sec",
            "range": "stddev: 0.000003591989479020993",
            "extra": "mean: 58.24050163396744 usec\nrounds: 6120"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432504951,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 26776.946661357462,
            "unit": "iter/sec",
            "range": "stddev: 0.0000011177631860726568",
            "extra": "mean: 37.34555745458189 usec\nrounds: 4447"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 19103.48538724738,
            "unit": "iter/sec",
            "range": "stddev: 0.0000017977144938470909",
            "extra": "mean: 52.34646870604851 usec\nrounds: 6407"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491169217,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 20498.401371668497,
            "unit": "iter/sec",
            "range": "stddev: 0.000053016389235574485",
            "extra": "mean: 48.78429209519393 usec\nrounds: 3694"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 14772.533435339405,
            "unit": "iter/sec",
            "range": "stddev: 0.00008210873506665198",
            "extra": "mean: 67.69319591504615 usec\nrounds: 6610"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aaronabbott@google.com",
            "name": "Aaron Abbott",
            "username": "aabmass"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "76883321c2fb3f5f55c4136236183af7631253d3",
          "message": "boundlist typing wip (#1385)",
          "timestamp": "2021-01-15T10:09:06-08:00",
          "tree_id": "073d78c7e9c16897cbafb2296b0376dcb5fc55cc",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/76883321c2fb3f5f55c4136236183af7631253d3"
        },
        "date": 1610760486111,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 27051.769755298876,
            "unit": "iter/sec",
            "range": "stddev: 0.0000014098333596686353",
            "extra": "mean: 36.96615818653125 usec\nrounds: 5051"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 19377.996960581153,
            "unit": "iter/sec",
            "range": "stddev: 0.0000014114759950064917",
            "extra": "mean: 51.60492088187477 usec\nrounds: 6623"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071490938,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 23103.909512142123,
            "unit": "iter/sec",
            "range": "stddev: 0.0000015605197237981333",
            "extra": "mean: 43.282717995171154 usec\nrounds: 4390"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 16651.746444991444,
            "unit": "iter/sec",
            "range": "stddev: 0.0000017910958551333401",
            "extra": "mean: 60.05376092552638 usec\nrounds: 6270"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245186719,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 22908.070129837226,
            "unit": "iter/sec",
            "range": "stddev: 0.00003575251340893149",
            "extra": "mean: 43.65273872186742 usec\nrounds: 4256"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 16487.903538428276,
            "unit": "iter/sec",
            "range": "stddev: 0.00001041925390823786",
            "extra": "mean: 60.65052465095425 usec\nrounds: 7018"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271773883,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 29652.307023428475,
            "unit": "iter/sec",
            "range": "stddev: 0.000002091437474383406",
            "extra": "mean: 33.72418878604939 usec\nrounds: 4762"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 21573.88310218942,
            "unit": "iter/sec",
            "range": "stddev: 0.000002487260267892662",
            "extra": "mean: 46.35234163749202 usec\nrounds: 6864"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852858333,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 17966.699704133836,
            "unit": "iter/sec",
            "range": "stddev: 0.00004147319005282877",
            "extra": "mean: 55.65852474118643 usec\nrounds: 4143"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 12294.001810951324,
            "unit": "iter/sec",
            "range": "stddev: 0.0000611927499555225",
            "extra": "mean: 81.34047931481628 usec\nrounds: 7300"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611865964419,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 26512.797830860167,
            "unit": "iter/sec",
            "range": "stddev: 0.0000010214972966083876",
            "extra": "mean: 37.71763381516935 usec\nrounds: 4637"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 18908.207483771563,
            "unit": "iter/sec",
            "range": "stddev: 0.0000013384003934185592",
            "extra": "mean: 52.8870862485656 usec\nrounds: 5774"
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
        "date": 1608593327524,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 19328.136524499303,
            "unit": "iter/sec",
            "range": "stddev: 0.000010091578131814837",
            "extra": "mean: 51.73804514120924 usec\nrounds: 1307"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 13002.46219615221,
            "unit": "iter/sec",
            "range": "stddev: 0.00007736741309881968",
            "extra": "mean: 76.90851047395684 usec\nrounds: 5824"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126863896,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 14515.187488353433,
            "unit": "iter/sec",
            "range": "stddev: 0.00007998722132790936",
            "extra": "mean: 68.89335744387533 usec\nrounds: 1424"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 10503.648636075546,
            "unit": "iter/sec",
            "range": "stddev: 0.00005770221059559956",
            "extra": "mean: 95.20501252921076 usec\nrounds: 5507"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432475498,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 21149.794663468354,
            "unit": "iter/sec",
            "range": "stddev: 0.000004640496204958557",
            "extra": "mean: 47.281782916185065 usec\nrounds: 1557"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 14119.351456991586,
            "unit": "iter/sec",
            "range": "stddev: 0.0000055015654188272595",
            "extra": "mean: 70.82478278453947 usec\nrounds: 4949"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491195049,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 14184.507033836577,
            "unit": "iter/sec",
            "range": "stddev: 0.00009290118892869735",
            "extra": "mean: 70.49945391930363 usec\nrounds: 1161"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 10058.164210690693,
            "unit": "iter/sec",
            "range": "stddev: 0.000027272315765601813",
            "extra": "mean: 99.42172140489741 usec\nrounds: 5438"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aaronabbott@google.com",
            "name": "Aaron Abbott",
            "username": "aabmass"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "76883321c2fb3f5f55c4136236183af7631253d3",
          "message": "boundlist typing wip (#1385)",
          "timestamp": "2021-01-15T10:09:06-08:00",
          "tree_id": "073d78c7e9c16897cbafb2296b0376dcb5fc55cc",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/76883321c2fb3f5f55c4136236183af7631253d3"
        },
        "date": 1610760502852,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 20443.048239911805,
            "unit": "iter/sec",
            "range": "stddev: 0.000001968684596861644",
            "extra": "mean: 48.91638410595045 usec\nrounds: 1359"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 13862.998016758618,
            "unit": "iter/sec",
            "range": "stddev: 0.0000017673976358984697",
            "extra": "mean: 72.13446895044822 usec\nrounds: 5137"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071503649,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 20377.200848148834,
            "unit": "iter/sec",
            "range": "stddev: 0.0000021193035266207244",
            "extra": "mean: 49.07445372168695 usec\nrounds: 1545"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 13719.041780727735,
            "unit": "iter/sec",
            "range": "stddev: 0.000004411745725664012",
            "extra": "mean: 72.89138818753231 usec\nrounds: 4673"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245145382,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 25435.827432115802,
            "unit": "iter/sec",
            "range": "stddev: 0.000001428687487555247",
            "extra": "mean: 39.31462432935754 usec\nrounds: 1866"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 17455.944934158848,
            "unit": "iter/sec",
            "range": "stddev: 0.0000018525542468999273",
            "extra": "mean: 57.28707347392805 usec\nrounds: 5131"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271791805,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 22802.219529938342,
            "unit": "iter/sec",
            "range": "stddev: 0.0000013968939288305797",
            "extra": "mean: 43.855379897866634 usec\nrounds: 1761"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 15487.635999297483,
            "unit": "iter/sec",
            "range": "stddev: 0.0000021048203656461856",
            "extra": "mean: 64.56763317819194 usec\nrounds: 5365"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852836065,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 21762.082671338678,
            "unit": "iter/sec",
            "range": "stddev: 0.00000612430068875916",
            "extra": "mean: 45.951484290473275 usec\nrounds: 1846"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 14469.299413221734,
            "unit": "iter/sec",
            "range": "stddev: 0.000005225464108558875",
            "extra": "mean: 69.11184649936966 usec\nrounds: 5342"
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
        "date": 1608593347575,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 281723.30591046595,
            "unit": "iter/sec",
            "range": "stddev: 0.000010964169615308154",
            "extra": "mean: 3.5495820864668133 usec\nrounds: 169492"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 194632.57532990238,
            "unit": "iter/sec",
            "range": "stddev: 0.0000070268452300366",
            "extra": "mean: 5.137886082558376 usec\nrounds: 120482"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126882084,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 243883.0478241517,
            "unit": "iter/sec",
            "range": "stddev: 0.000012113891889047916",
            "extra": "mean: 4.100325991993652 usec\nrounds: 151516"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 170648.33016236065,
            "unit": "iter/sec",
            "range": "stddev: 0.000006234122897439007",
            "extra": "mean: 5.860004601560213 usec\nrounds: 102031"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432697267,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 240684.05624221775,
            "unit": "iter/sec",
            "range": "stddev: 0.00004862741175825935",
            "extra": "mean: 4.154824443350862 usec\nrounds: 178572"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 170508.98670922968,
            "unit": "iter/sec",
            "range": "stddev: 0.000006693441148591157",
            "extra": "mean: 5.864793517923533 usec\nrounds: 113637"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491218246,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 228665.15456199093,
            "unit": "iter/sec",
            "range": "stddev: 0.000013902556118508403",
            "extra": "mean: 4.373206761281597 usec\nrounds: 140846"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 147785.71001782166,
            "unit": "iter/sec",
            "range": "stddev: 0.00007656734970387064",
            "extra": "mean: 6.766554086179298 usec\nrounds: 185186"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aaronabbott@google.com",
            "name": "Aaron Abbott",
            "username": "aabmass"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "76883321c2fb3f5f55c4136236183af7631253d3",
          "message": "boundlist typing wip (#1385)",
          "timestamp": "2021-01-15T10:09:06-08:00",
          "tree_id": "073d78c7e9c16897cbafb2296b0376dcb5fc55cc",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/76883321c2fb3f5f55c4136236183af7631253d3"
        },
        "date": 1610760529327,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 277761.43141466775,
            "unit": "iter/sec",
            "range": "stddev: 0.00004095607642427398",
            "extra": "mean: 3.6002118613332903 usec\nrounds: 199961"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 188854.33788898378,
            "unit": "iter/sec",
            "range": "stddev: 0.00003792770440071969",
            "extra": "mean: 5.295086208651667 usec\nrounds: 129871"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071619082,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 189861.9770417906,
            "unit": "iter/sec",
            "range": "stddev: 0.000021930271750723265",
            "extra": "mean: 5.2669840248207755 usec\nrounds: 131579"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 125047.83027581418,
            "unit": "iter/sec",
            "range": "stddev: 0.000026668947086377435",
            "extra": "mean: 7.996940033220333 usec\nrounds: 185186"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245358784,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 161728.35673566384,
            "unit": "iter/sec",
            "range": "stddev: 0.000027612785080369322",
            "extra": "mean: 6.1832075721541235 usec\nrounds: 128206"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 80942.68813334602,
            "unit": "iter/sec",
            "range": "stddev: 0.00005030075473558288",
            "extra": "mean: 12.354420430818745 usec\nrounds: 151516"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271882754,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 279083.78941875446,
            "unit": "iter/sec",
            "range": "stddev: 0.00004555613566006419",
            "extra": "mean: 3.583153296301057 usec\nrounds: 169492"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 192337.10830225193,
            "unit": "iter/sec",
            "range": "stddev: 0.0000053648816799888705",
            "extra": "mean: 5.199204713156706 usec\nrounds: 108696"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852903235,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 217497.82007827293,
            "unit": "iter/sec",
            "range": "stddev: 0.000055864172319202045",
            "extra": "mean: 4.597747230938319 usec\nrounds: 144907"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 148025.04607216627,
            "unit": "iter/sec",
            "range": "stddev: 0.0000749539243703077",
            "extra": "mean: 6.755613502815414 usec\nrounds: 196079"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.9 - core": [
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
        "date": 1608593369153,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 26257.418292819675,
            "unit": "iter/sec",
            "range": "stddev: 0.000001197463471654213",
            "extra": "mean: 38.08447536037688 usec\nrounds: 4647"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 19852.10710891054,
            "unit": "iter/sec",
            "range": "stddev: 0.00000212240958624459",
            "extra": "mean: 50.37248663398325 usec\nrounds: 7519"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126854265,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 22973.95033101025,
            "unit": "iter/sec",
            "range": "stddev: 0.000030284305438288753",
            "extra": "mean: 43.52755993601151 usec\nrounds: 3754"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 15539.663069344615,
            "unit": "iter/sec",
            "range": "stddev: 0.00010053159984351156",
            "extra": "mean: 64.35145958683742 usec\nrounds: 7844"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432660086,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 30534.013826648967,
            "unit": "iter/sec",
            "range": "stddev: 0.00008180115168437715",
            "extra": "mean: 32.75036179905168 usec\nrounds: 4602"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 22432.947536138086,
            "unit": "iter/sec",
            "range": "stddev: 0.000001362992997909949",
            "extra": "mean: 44.57728964903351 usec\nrounds: 6753"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491179111,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 23410.68322330516,
            "unit": "iter/sec",
            "range": "stddev: 0.000014359140351931785",
            "extra": "mean: 42.71554104002003 usec\nrounds: 2924"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 15356.577743651285,
            "unit": "iter/sec",
            "range": "stddev: 0.000024781865672962254",
            "extra": "mean: 65.11867531250053 usec\nrounds: 8482"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aaronabbott@google.com",
            "name": "Aaron Abbott",
            "username": "aabmass"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "76883321c2fb3f5f55c4136236183af7631253d3",
          "message": "boundlist typing wip (#1385)",
          "timestamp": "2021-01-15T10:09:06-08:00",
          "tree_id": "073d78c7e9c16897cbafb2296b0376dcb5fc55cc",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/76883321c2fb3f5f55c4136236183af7631253d3"
        },
        "date": 1610760533530,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 26348.231702193345,
            "unit": "iter/sec",
            "range": "stddev: 0.000016244610206832863",
            "extra": "mean: 37.953211103603415 usec\nrounds: 3008"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 17378.462237883236,
            "unit": "iter/sec",
            "range": "stddev: 0.00006925565400208544",
            "extra": "mean: 57.54249060196502 usec\nrounds: 9470"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071489919,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 23969.52952217476,
            "unit": "iter/sec",
            "range": "stddev: 0.000025291378316527017",
            "extra": "mean: 41.71963404934073 usec\nrounds: 5028"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 16576.909417444094,
            "unit": "iter/sec",
            "range": "stddev: 0.0000249099959516024",
            "extra": "mean: 60.324875694119875 usec\nrounds: 9364"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245256950,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 27252.547327374406,
            "unit": "iter/sec",
            "range": "stddev: 0.000010172803817218663",
            "extra": "mean: 36.693817571890925 usec\nrounds: 4621"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 19125.295290725302,
            "unit": "iter/sec",
            "range": "stddev: 0.000014771345420843837",
            "extra": "mean: 52.286774389566894 usec\nrounds: 8231"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271847981,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 27436.206771745794,
            "unit": "iter/sec",
            "range": "stddev: 0.0000014300352766121604",
            "extra": "mean: 36.44818718270539 usec\nrounds: 4728"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 19537.85373254474,
            "unit": "iter/sec",
            "range": "stddev: 0.0000016884307563402938",
            "extra": "mean: 51.18269456251853 usec\nrounds: 6345"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852825123,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 35463.374772898314,
            "unit": "iter/sec",
            "range": "stddev: 0.000004788286815163783",
            "extra": "mean: 28.19810597281949 usec\nrounds: 5492"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 24339.79027469797,
            "unit": "iter/sec",
            "range": "stddev: 0.000006314166372816879",
            "extra": "mean: 41.084988355036636 usec\nrounds: 6784"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611866034021,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 31469.958452630814,
            "unit": "iter/sec",
            "range": "stddev: 0.0000012250334265760206",
            "extra": "mean: 31.776336835818178 usec\nrounds: 4949"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 22334.965450310112,
            "unit": "iter/sec",
            "range": "stddev: 0.0000018828299681094736",
            "extra": "mean: 44.77284740935721 usec\nrounds: 7353"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.7 - exporter": [
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126784585,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 3503.953410145122,
            "unit": "iter/sec",
            "range": "stddev: 0.000011945845800870066",
            "extra": "mean: 285.3919224795239 usec\nrounds: 258"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4306.200494845973,
            "unit": "iter/sec",
            "range": "stddev: 0.000816898277275694",
            "extra": "mean: 232.22327924509904 usec\nrounds: 5300"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432491347,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2391.094975191364,
            "unit": "iter/sec",
            "range": "stddev: 0.00008464204127904394",
            "extra": "mean: 418.21843564368163 usec\nrounds: 202"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3466.173279505596,
            "unit": "iter/sec",
            "range": "stddev: 0.0009015148248780761",
            "extra": "mean: 288.5025990802851 usec\nrounds: 5001"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491135562,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2577.5193913835037,
            "unit": "iter/sec",
            "range": "stddev: 0.000008623076481973578",
            "extra": "mean: 387.969923075241 usec\nrounds: 208"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3125.1207550027743,
            "unit": "iter/sec",
            "range": "stddev: 0.0010473357331895992",
            "extra": "mean: 319.98763516551287 usec\nrounds: 4476"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aaronabbott@google.com",
            "name": "Aaron Abbott",
            "username": "aabmass"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "76883321c2fb3f5f55c4136236183af7631253d3",
          "message": "boundlist typing wip (#1385)",
          "timestamp": "2021-01-15T10:09:06-08:00",
          "tree_id": "073d78c7e9c16897cbafb2296b0376dcb5fc55cc",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/76883321c2fb3f5f55c4136236183af7631253d3"
        },
        "date": 1610760444419,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 3028.2528518821982,
            "unit": "iter/sec",
            "range": "stddev: 0.00000727208821238051",
            "extra": "mean: 330.22341558382556 usec\nrounds: 231"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4045.2165382406683,
            "unit": "iter/sec",
            "range": "stddev: 0.0008135641905968822",
            "extra": "mean: 247.20555514066908 usec\nrounds: 5087"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071460135,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2668.990033348909,
            "unit": "iter/sec",
            "range": "stddev: 0.000035035169949512483",
            "extra": "mean: 374.6735609743931 usec\nrounds: 205"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3116.559431037327,
            "unit": "iter/sec",
            "range": "stddev: 0.0010227575648587856",
            "extra": "mean: 320.86665508161235 usec\nrounds: 4546"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245140114,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2515.636199091593,
            "unit": "iter/sec",
            "range": "stddev: 0.000009343261224552899",
            "extra": "mean: 397.51375829347035 usec\nrounds: 211"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3405.1012042541306,
            "unit": "iter/sec",
            "range": "stddev: 0.0009112967069757882",
            "extra": "mean: 293.67702749940577 usec\nrounds: 4291"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271748461,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2369.571294169656,
            "unit": "iter/sec",
            "range": "stddev: 0.00008015344545749982",
            "extra": "mean: 422.0172663555242 usec\nrounds: 214"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3268.12244953666,
            "unit": "iter/sec",
            "range": "stddev: 0.0008834648443947705",
            "extra": "mean: 305.98608694780563 usec\nrounds: 5003"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852775747,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2520.224890663491,
            "unit": "iter/sec",
            "range": "stddev: 0.00006477314676397512",
            "extra": "mean: 396.7899863637699 usec\nrounds: 220"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3719.4726504345463,
            "unit": "iter/sec",
            "range": "stddev: 0.0007907774057190872",
            "extra": "mean: 268.8553174018284 usec\nrounds: 3264"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611866000533,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2533.328910571124,
            "unit": "iter/sec",
            "range": "stddev: 0.00007440205371436654",
            "extra": "mean: 394.73753124877726 usec\nrounds: 224"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3101.550630490635,
            "unit": "iter/sec",
            "range": "stddev: 0.0009350441990641621",
            "extra": "mean: 322.41936990137407 usec\nrounds: 4585"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.8 - exporter": [
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126785942,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 3929.2391072681667,
            "unit": "iter/sec",
            "range": "stddev: 0.000007129321909725742",
            "extra": "mean: 254.50220073149418 usec\nrounds: 274"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 5282.4698861330735,
            "unit": "iter/sec",
            "range": "stddev: 0.0007601485533214261",
            "extra": "mean: 189.30538584329346 usec\nrounds: 7078"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432570107,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 3125.42691890538,
            "unit": "iter/sec",
            "range": "stddev: 0.00003089468030924962",
            "extra": "mean: 319.9562894755609 usec\nrounds: 228"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4267.449555128202,
            "unit": "iter/sec",
            "range": "stddev: 0.0008374012105789777",
            "extra": "mean: 234.33200254196282 usec\nrounds: 6294"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491143122,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2994.368510916777,
            "unit": "iter/sec",
            "range": "stddev: 0.00001026916733555992",
            "extra": "mean: 333.9602311319501 usec\nrounds: 212"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4134.004001232704,
            "unit": "iter/sec",
            "range": "stddev: 0.0008614687963039268",
            "extra": "mean: 241.89623418405344 usec\nrounds: 5406"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aaronabbott@google.com",
            "name": "Aaron Abbott",
            "username": "aabmass"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "76883321c2fb3f5f55c4136236183af7631253d3",
          "message": "boundlist typing wip (#1385)",
          "timestamp": "2021-01-15T10:09:06-08:00",
          "tree_id": "073d78c7e9c16897cbafb2296b0376dcb5fc55cc",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/76883321c2fb3f5f55c4136236183af7631253d3"
        },
        "date": 1610760471513,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2359.3829751434764,
            "unit": "iter/sec",
            "range": "stddev: 0.00009466105188377083",
            "extra": "mean: 423.839626942798 usec\nrounds: 193"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3780.670106778209,
            "unit": "iter/sec",
            "range": "stddev: 0.0008748743892030813",
            "extra": "mean: 264.5033742053137 usec\nrounds: 4404"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071460096,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 3100.099522413339,
            "unit": "iter/sec",
            "range": "stddev: 0.00001722035183652981",
            "extra": "mean: 322.5702893633326 usec\nrounds: 235"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4368.182580644426,
            "unit": "iter/sec",
            "range": "stddev: 0.0008620375297252675",
            "extra": "mean: 228.92815983265808 usec\nrounds: 5731"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245160554,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2900.5168132454714,
            "unit": "iter/sec",
            "range": "stddev: 0.00005398706595864035",
            "extra": "mean: 344.76614492748666 usec\nrounds: 207"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3831.694509555352,
            "unit": "iter/sec",
            "range": "stddev: 0.0009227108894292597",
            "extra": "mean: 260.98113967755864 usec\nrounds: 6200"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271757043,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 3935.1791123744997,
            "unit": "iter/sec",
            "range": "stddev: 0.0000072671611656111556",
            "extra": "mean: 254.1180392159067 usec\nrounds: 255"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 5155.800614808608,
            "unit": "iter/sec",
            "range": "stddev: 0.0007776006649717735",
            "extra": "mean: 193.95629790798685 usec\nrounds: 6549"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852800283,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2516.069816482598,
            "unit": "iter/sec",
            "range": "stddev: 0.0003120278113081479",
            "extra": "mean: 397.4452511011697 usec\nrounds: 227"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3986.933999976523,
            "unit": "iter/sec",
            "range": "stddev: 0.0008528236686705778",
            "extra": "mean: 250.81930124900197 usec\nrounds: 5444"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611865998679,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 3026.167948204582,
            "unit": "iter/sec",
            "range": "stddev: 0.00010252588070945434",
            "extra": "mean: 330.45092576348827 usec\nrounds: 229"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4263.996025067584,
            "unit": "iter/sec",
            "range": "stddev: 0.0008462496864079231",
            "extra": "mean: 234.52179460794642 usec\nrounds: 5935"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.6 - exporter": [
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126802915,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 3112.85007730605,
            "unit": "iter/sec",
            "range": "stddev: 0.00000853652414706839",
            "extra": "mean: 321.2490081968319 usec\nrounds: 122"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4086.90069967933,
            "unit": "iter/sec",
            "range": "stddev: 0.0008120373989726633",
            "extra": "mean: 244.6841931046827 usec\nrounds: 5018"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432498604,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2395.8015469326533,
            "unit": "iter/sec",
            "range": "stddev: 0.000012462858848435961",
            "extra": "mean: 417.3968421050152 usec\nrounds: 95"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3240.763804624069,
            "unit": "iter/sec",
            "range": "stddev: 0.0009555549621459155",
            "extra": "mean: 308.5692325288114 usec\nrounds: 3978"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491145503,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2424.3670932611853,
            "unit": "iter/sec",
            "range": "stddev: 0.000016702452639017722",
            "extra": "mean: 412.4787878781304 usec\nrounds: 99"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3341.5316166668745,
            "unit": "iter/sec",
            "range": "stddev: 0.000929222588673213",
            "extra": "mean: 299.26396476759487 usec\nrounds: 4002"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aaronabbott@google.com",
            "name": "Aaron Abbott",
            "username": "aabmass"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "76883321c2fb3f5f55c4136236183af7631253d3",
          "message": "boundlist typing wip (#1385)",
          "timestamp": "2021-01-15T10:09:06-08:00",
          "tree_id": "073d78c7e9c16897cbafb2296b0376dcb5fc55cc",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/76883321c2fb3f5f55c4136236183af7631253d3"
        },
        "date": 1610760471282,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2514.222896077167,
            "unit": "iter/sec",
            "range": "stddev: 0.000024689640851423486",
            "extra": "mean: 397.73720999846773 usec\nrounds: 100"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3492.0255894275856,
            "unit": "iter/sec",
            "range": "stddev: 0.0009120479062327516",
            "extra": "mean: 286.3667445701395 usec\nrounds: 4052"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071467361,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2262.9111608552034,
            "unit": "iter/sec",
            "range": "stddev: 0.00005354226861876263",
            "extra": "mean: 441.9086428572292 usec\nrounds: 84"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3116.0485517225757,
            "unit": "iter/sec",
            "range": "stddev: 0.0009315445505844981",
            "extra": "mean: 320.91926149455924 usec\nrounds: 4176"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245131888,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2409.396705568234,
            "unit": "iter/sec",
            "range": "stddev: 0.000011277136264923758",
            "extra": "mean: 415.0416565644631 usec\nrounds: 99"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3250.9536165158866,
            "unit": "iter/sec",
            "range": "stddev: 0.0008921031068449284",
            "extra": "mean: 307.60205095504267 usec\nrounds: 4396"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271724863,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2693.1001102912646,
            "unit": "iter/sec",
            "range": "stddev: 0.000009802051307323186",
            "extra": "mean: 371.31928225714853 usec\nrounds: 124"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3583.594049932984,
            "unit": "iter/sec",
            "range": "stddev: 0.0008463280825334725",
            "extra": "mean: 279.04946432721664 usec\nrounds: 4331"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852810150,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2429.891206621114,
            "unit": "iter/sec",
            "range": "stddev: 0.000018368240779893424",
            "extra": "mean: 411.5410588240081 usec\nrounds: 119"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3376.089761417223,
            "unit": "iter/sec",
            "range": "stddev: 0.0008358495249128624",
            "extra": "mean: 296.2006553937765 usec\nrounds: 4051"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611866012143,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2212.9760187046195,
            "unit": "iter/sec",
            "range": "stddev: 0.00005260894545566339",
            "extra": "mean: 451.88017924629696 usec\nrounds: 106"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3416.328802628677,
            "unit": "iter/sec",
            "range": "stddev: 0.0007824809683176797",
            "extra": "mean: 292.71187223857237 usec\nrounds: 3123"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.9 - exporter": [
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126817141,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 951.4671617134708,
            "unit": "iter/sec",
            "range": "stddev: 0.00004312843409036067",
            "extra": "mean: 1.0510084217716225 msec\nrounds: 147"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3849.326018748801,
            "unit": "iter/sec",
            "range": "stddev: 0.001250740499047316",
            "extra": "mean: 259.7857378484776 usec\nrounds: 5699"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432599540,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 1093.4838092267312,
            "unit": "iter/sec",
            "range": "stddev: 0.000013014697381412056",
            "extra": "mean: 914.5082822096475 usec\nrounds: 163"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4309.29457121305,
            "unit": "iter/sec",
            "range": "stddev: 0.0012531113930569014",
            "extra": "mean: 232.05654277621215 usec\nrounds: 6721"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491142764,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 902.4231092708873,
            "unit": "iter/sec",
            "range": "stddev: 0.00011686340812997759",
            "extra": "mean: 1.1081276506847768 msec\nrounds: 146"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3795.2901717451127,
            "unit": "iter/sec",
            "range": "stddev: 0.00107978935978824",
            "extra": "mean: 263.4844648888045 usec\nrounds: 5625"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aaronabbott@google.com",
            "name": "Aaron Abbott",
            "username": "aabmass"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "76883321c2fb3f5f55c4136236183af7631253d3",
          "message": "boundlist typing wip (#1385)",
          "timestamp": "2021-01-15T10:09:06-08:00",
          "tree_id": "073d78c7e9c16897cbafb2296b0376dcb5fc55cc",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/76883321c2fb3f5f55c4136236183af7631253d3"
        },
        "date": 1610760451537,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 1131.1256933968398,
            "unit": "iter/sec",
            "range": "stddev: 0.00011401079259904369",
            "extra": "mean: 884.0750465113553 usec\nrounds: 172"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4592.293327670954,
            "unit": "iter/sec",
            "range": "stddev: 0.0010443004926797988",
            "extra": "mean: 217.75612502243277 usec\nrounds: 5559"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071458697,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 951.6782087756067,
            "unit": "iter/sec",
            "range": "stddev: 0.000030574507168860825",
            "extra": "mean: 1.0507753469385017 msec\nrounds: 147"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4163.287777452418,
            "unit": "iter/sec",
            "range": "stddev: 0.0009601634395736182",
            "extra": "mean: 240.19478197395136 usec\nrounds: 5825"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245202776,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 951.9520192635041,
            "unit": "iter/sec",
            "range": "stddev: 0.00008806218862315881",
            "extra": "mean: 1.0504731118419908 msec\nrounds: 152"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3855.8012674149513,
            "unit": "iter/sec",
            "range": "stddev: 0.0011237537015029457",
            "extra": "mean: 259.34946607619923 usec\nrounds: 5984"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271808363,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 904.2365442976742,
            "unit": "iter/sec",
            "range": "stddev: 0.00007538977420517854",
            "extra": "mean: 1.1059053146062636 msec\nrounds: 178"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3589.7367532530875,
            "unit": "iter/sec",
            "range": "stddev: 0.0012622060745928845",
            "extra": "mean: 278.5719590980539 usec\nrounds: 5721"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852802960,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 979.7529518509242,
            "unit": "iter/sec",
            "range": "stddev: 0.00007776593578306987",
            "extra": "mean: 1.0206654627687781 msec\nrounds: 188"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4150.950463579778,
            "unit": "iter/sec",
            "range": "stddev: 0.001109194393621245",
            "extra": "mean: 240.90868074045872 usec\nrounds: 5685"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611865930067,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 1016.8649885723052,
            "unit": "iter/sec",
            "range": "stddev: 0.00010044565372358514",
            "extra": "mean: 983.4147219524355 usec\nrounds: 205"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 4089.2523361625413,
            "unit": "iter/sec",
            "range": "stddev: 0.0011801612278640678",
            "extra": "mean: 244.54348076216436 usec\nrounds: 5510"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.5 - exporter": [
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "cd39fc17b21baf68eddc4ddd0acfe2e80df59eae",
          "message": "Update Jaeger exporter status code (#1488)",
          "timestamp": "2021-01-07T08:05:29-08:00",
          "tree_id": "2d2eb6aea5add7398b0ba85fe8a38da6ff809abb",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/cd39fc17b21baf68eddc4ddd0acfe2e80df59eae"
        },
        "date": 1610126817267,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2426.0119565393943,
            "unit": "iter/sec",
            "range": "stddev: 0.000059969438887445946",
            "extra": "mean: 412.19912264012856 usec\nrounds: 106"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3420.484508375751,
            "unit": "iter/sec",
            "range": "stddev: 0.0008653925145854911",
            "extra": "mean: 292.3562429682979 usec\nrounds: 5013"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "lechen@microsoft.com",
            "name": "Leighton Chen",
            "username": "lzchen"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "09ac955f5301fbb3d4fc521bdf86c0a76b4a3387",
          "message": "Move idsgenerator from api into sdk package (#1514)",
          "timestamp": "2021-01-11T12:39:23-08:00",
          "tree_id": "23ec81a5ee30e905bb2fae19dcbaf05fc04b00c3",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/09ac955f5301fbb3d4fc521bdf86c0a76b4a3387"
        },
        "date": 1610432400890,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2795.0822860637268,
            "unit": "iter/sec",
            "range": "stddev: 0.000009195008940259534",
            "extra": "mean: 357.771220184106 usec\nrounds: 109"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3734.5678964097037,
            "unit": "iter/sec",
            "range": "stddev: 0.000851292571509006",
            "extra": "mean: 267.7685953872652 usec\nrounds: 4639"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "db74594d93b7e42d26ed2061b7672d1ad823f30c",
          "message": "Update default port for OTLP exporter to 4317 (#1516)",
          "timestamp": "2021-01-12T12:14:49-08:00",
          "tree_id": "319abf2aeb7c5ad6e78c5bf358e34232b37ca479",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db74594d93b7e42d26ed2061b7672d1ad823f30c"
        },
        "date": 1610491155095,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2367.044701784305,
            "unit": "iter/sec",
            "range": "stddev: 0.00001106089791669764",
            "extra": "mean: 422.4677291671715 usec\nrounds: 96"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3277.7778339248043,
            "unit": "iter/sec",
            "range": "stddev: 0.0009083172611522555",
            "extra": "mean: 305.0847405367319 usec\nrounds: 4174"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "aaronabbott@google.com",
            "name": "Aaron Abbott",
            "username": "aabmass"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "76883321c2fb3f5f55c4136236183af7631253d3",
          "message": "boundlist typing wip (#1385)",
          "timestamp": "2021-01-15T10:09:06-08:00",
          "tree_id": "073d78c7e9c16897cbafb2296b0376dcb5fc55cc",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/76883321c2fb3f5f55c4136236183af7631253d3"
        },
        "date": 1610760491386,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 1582.1541249556376,
            "unit": "iter/sec",
            "range": "stddev: 0.0005110745069703663",
            "extra": "mean: 632.0496746978043 usec\nrounds: 83"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 2838.9195072611465,
            "unit": "iter/sec",
            "range": "stddev: 0.0009862456167752426",
            "extra": "mean: 352.2466901376687 usec\nrounds: 3934"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "9a1f594b751289635906a856684b59b3d4a425a5",
          "message": "Add support for OTEL_TRACE_SAMPLER and OTEL_TRACE_SAMPLER_ARG env variables (#1496)",
          "timestamp": "2021-01-18T21:08:45-08:00",
          "tree_id": "0aa9a54738cf435e660cb7d9b8fc9d4a424593c4",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/9a1f594b751289635906a856684b59b3d4a425a5"
        },
        "date": 1611071482637,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2071.839833430803,
            "unit": "iter/sec",
            "range": "stddev: 0.00005305164867278034",
            "extra": "mean: 482.66279268512716 usec\nrounds: 82"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 2691.680130774513,
            "unit": "iter/sec",
            "range": "stddev: 0.001069667697368953",
            "extra": "mean: 371.51516949090706 usec\nrounds: 4720"
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
          "id": "db9905a164c1f3604eeb8ce5939243948f5be2a8",
          "message": "rename instrumentation to shim (#1539)",
          "timestamp": "2021-01-20T15:51:31-08:00",
          "tree_id": "9bd1e424fd272c88e39f2a9bf78abc22fb9f429d",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/db9905a164c1f3604eeb8ce5939243948f5be2a8"
        },
        "date": 1611245113792,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2344.722249294624,
            "unit": "iter/sec",
            "range": "stddev: 0.000012671356988968578",
            "extra": "mean: 426.4897474747108 usec\nrounds: 99"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3256.3736863961312,
            "unit": "iter/sec",
            "range": "stddev: 0.0009520013677475448",
            "extra": "mean: 307.0900628443268 usec\nrounds: 3994"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271743002,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2345.7319697053476,
            "unit": "iter/sec",
            "range": "stddev: 0.000013680770233848152",
            "extra": "mean: 426.30616494757163 usec\nrounds: 97"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3085.5926562894756,
            "unit": "iter/sec",
            "range": "stddev: 0.00088497932262048",
            "extra": "mean: 324.08684858698496 usec\nrounds: 3857"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852801932,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2264.333851890685,
            "unit": "iter/sec",
            "range": "stddev: 0.000015188017430955802",
            "extra": "mean: 441.63098969041823 usec\nrounds: 97"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3282.50929032197,
            "unit": "iter/sec",
            "range": "stddev: 0.0009124595333847465",
            "extra": "mean: 304.6449869763852 usec\nrounds: 3916"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611866008153,
        "tool": "pytest",
        "benches": [
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_simple_span_processor",
            "value": 2278.455265336758,
            "unit": "iter/sec",
            "range": "stddev: 0.000035423631285118516",
            "extra": "mean: 438.89384848299795 usec\nrounds: 99"
          },
          {
            "name": "exporter/opentelemetry-exporter-otlp/tests/performance/benchmarks/test_benchmark_trace_exporter.py::test_batch_span_processor",
            "value": 3315.741616666913,
            "unit": "iter/sec",
            "range": "stddev: 0.0008253543025084374",
            "extra": "mean: 301.5916544803727 usec\nrounds: 3939"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.5 - propagator": [
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271699610,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 57904.47726131198,
            "unit": "iter/sec",
            "range": "stddev: 5.768142574718727e-7",
            "extra": "mean: 17.269821735669744 usec\nrounds: 9183"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 137764.50552444218,
            "unit": "iter/sec",
            "range": "stddev: 3.7917811603242705e-7",
            "extra": "mean: 7.258763759164221 usec\nrounds: 54055"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852754961,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 49399.07939025531,
            "unit": "iter/sec",
            "range": "stddev: 7.661624942461297e-7",
            "extra": "mean: 20.243292230204286 usec\nrounds: 7542"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 116381.37716144975,
            "unit": "iter/sec",
            "range": "stddev: 4.833859148187361e-7",
            "extra": "mean: 8.592439996759555 usec\nrounds: 51814"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611865988886,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 53246.67220856851,
            "unit": "iter/sec",
            "range": "stddev: 0.0000026211413916371967",
            "extra": "mean: 18.780516387634062 usec\nrounds: 8482"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 120588.6190697735,
            "unit": "iter/sec",
            "range": "stddev: 0.0000014495010835161339",
            "extra": "mean: 8.292656535202482 usec\nrounds: 60603"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.6 - propagator": [
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271708593,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 60820.7236949171,
            "unit": "iter/sec",
            "range": "stddev: 5.450628019311538e-7",
            "extra": "mean: 16.441764241676918 usec\nrounds: 9251"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 135286.2066918279,
            "unit": "iter/sec",
            "range": "stddev: 3.100530896027488e-7",
            "extra": "mean: 7.391736559499573 usec\nrounds: 54946"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852739694,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 44774.593790951185,
            "unit": "iter/sec",
            "range": "stddev: 0.000017012711380395128",
            "extra": "mean: 22.334094300641027 usec\nrounds: 6299"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 99271.34861267138,
            "unit": "iter/sec",
            "range": "stddev: 0.000020615874496440416",
            "extra": "mean: 10.07339996862253 usec\nrounds: 51029"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611865989241,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 39438.49550807344,
            "unit": "iter/sec",
            "range": "stddev: 0.00007037906113691241",
            "extra": "mean: 25.35593681040115 usec\nrounds: 7343"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 88309.57684338007,
            "unit": "iter/sec",
            "range": "stddev: 0.00004569613859547473",
            "extra": "mean: 11.323800155599578 usec\nrounds: 42373"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.7 - propagator": [
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271711503,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 79856.44406785398,
            "unit": "iter/sec",
            "range": "stddev: 4.617714749859342e-7",
            "extra": "mean: 12.522470937352287 usec\nrounds: 12301"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 172195.01447420134,
            "unit": "iter/sec",
            "range": "stddev: 3.062889522897546e-7",
            "extra": "mean: 5.807369063811207 usec\nrounds: 69931"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852734546,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 73500.93794585139,
            "unit": "iter/sec",
            "range": "stddev: 5.383276961118896e-7",
            "extra": "mean: 13.605268557752371 usec\nrounds: 10616"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 154682.0606349989,
            "unit": "iter/sec",
            "range": "stddev: 3.1199790154636764e-7",
            "extra": "mean: 6.464873792699763 usec\nrounds: 59521"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611865980925,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 72872.17646242188,
            "unit": "iter/sec",
            "range": "stddev: 9.755922050043775e-7",
            "extra": "mean: 13.722658613272952 usec\nrounds: 12707"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 146055.51608343047,
            "unit": "iter/sec",
            "range": "stddev: 4.16777611314923e-7",
            "extra": "mean: 6.846711625932537 usec\nrounds: 62894"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.8 - propagator": [
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271744519,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 88571.7313858452,
            "unit": "iter/sec",
            "range": "stddev: 6.019666443439466e-7",
            "extra": "mean: 11.290283980604354 usec\nrounds: 11124"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 188284.89793319593,
            "unit": "iter/sec",
            "range": "stddev: 6.893358878771965e-7",
            "extra": "mean: 5.311100417383464 usec\nrounds: 67568"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852733074,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 100916.18208088074,
            "unit": "iter/sec",
            "range": "stddev: 0.0000014809813266663997",
            "extra": "mean: 9.909213560997932 usec\nrounds: 12919"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 213911.2271185724,
            "unit": "iter/sec",
            "range": "stddev: 9.092408867710519e-7",
            "extra": "mean: 4.674836442529 usec\nrounds: 70917"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611865974742,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 97050.27303953219,
            "unit": "iter/sec",
            "range": "stddev: 9.338603401822134e-7",
            "extra": "mean: 10.303938038305805 usec\nrounds: 11378"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 217901.44678184364,
            "unit": "iter/sec",
            "range": "stddev: 2.677166394604504e-7",
            "extra": "mean: 4.589230658028488 usec\nrounds: 60245"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python 3.9 - propagator": [
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271803498,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 77384.84430759786,
            "unit": "iter/sec",
            "range": "stddev: 0.0000063863123090746836",
            "extra": "mean: 12.922426980987249 usec\nrounds: 9251"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 162850.1637006109,
            "unit": "iter/sec",
            "range": "stddev: 0.000007497451305405046",
            "extra": "mean: 6.1406140299522995 usec\nrounds: 65360"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852798030,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 91308.73844468332,
            "unit": "iter/sec",
            "range": "stddev: 7.734834684558038e-7",
            "extra": "mean: 10.951854302595805 usec\nrounds: 12423"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 179059.27617847497,
            "unit": "iter/sec",
            "range": "stddev: 3.6448211010115206e-7",
            "extra": "mean: 5.584742780950724 usec\nrounds: 64517"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611865913632,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 78217.61364732194,
            "unit": "iter/sec",
            "range": "stddev: 0.000015351961963058048",
            "extra": "mean: 12.784844146600202 usec\nrounds: 12300"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 166375.06089262283,
            "unit": "iter/sec",
            "range": "stddev: 0.000010096494319904076",
            "extra": "mean: 6.010516207386347 usec\nrounds: 66667"
          }
        ]
      }
    ],
    "OpenTelemetry Python Benchmarks - Python pypy3 - propagator": [
      {
        "commit": {
          "author": {
            "email": "anton.ryzhov@zalando.de",
            "name": "Anton Ryzhov",
            "username": "anton-ryzhov"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "6489bf50a576c9c772d2f7b78d677cf16b4526ac",
          "message": "Add `Span.set_attributes` method (#1520)",
          "timestamp": "2021-01-21T12:42:01-08:00",
          "tree_id": "b1637c968e9624dee4e4588021e48d8372f25eba",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/6489bf50a576c9c772d2f7b78d677cf16b4526ac"
        },
        "date": 1611271829134,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 398151.9130196396,
            "unit": "iter/sec",
            "range": "stddev: 0.0000028433563617305724",
            "extra": "mean: 2.5116041573575894 usec\nrounds: 57801"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 714306.197082686,
            "unit": "iter/sec",
            "range": "stddev: 0.00000203829428649862",
            "extra": "mean: 1.3999598548691612 usec\nrounds: 101011"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "ewan.higgs@gmail.com",
            "name": "Ewan Higgs",
            "username": "ehiggs"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9",
          "message": "1542. Allow missing carrier headers to continue without raising AttributeError (#1545)",
          "timestamp": "2021-01-27T08:31:32-08:00",
          "tree_id": "cd2a50fa811d6310e1d6bf9b75512412d2a30766",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/c026c0f6a53adae1af6cf36fb4bb830a31c6ffc9"
        },
        "date": 1611852823474,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 388228.275757469,
            "unit": "iter/sec",
            "range": "stddev: 0.0000031041489148906274",
            "extra": "mean: 2.5758041401001166 usec\nrounds: 50506"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 752160.4989886236,
            "unit": "iter/sec",
            "range": "stddev: 0.0000013335174363338934",
            "extra": "mean: 1.3295034787716553 usec\nrounds: 83334"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "srikanth.chekuri92@gmail.com",
            "name": "Srikanth Chekuri",
            "username": "lonewolf3739"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": false,
          "id": "18761d78e30a4293abd65a897129b57fbf0c0a15",
          "message": "Update Resource merge key conflict precedence (#1544)",
          "timestamp": "2021-01-28T09:20:50-08:00",
          "tree_id": "aa5e34bdc6bcc45b3961ba96d824d9cefdeb6a26",
          "url": "https://github.com/ocelotl/opentelemetry-python/commit/18761d78e30a4293abd65a897129b57fbf0c0a15"
        },
        "date": 1611866006267,
        "tool": "pytest",
        "benches": [
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_extract_single_header",
            "value": 446974.1429315886,
            "unit": "iter/sec",
            "range": "stddev: 0.0000029118553489591876",
            "extra": "mean: 2.237265881738073 usec\nrounds: 55249"
          },
          {
            "name": "propagator/opentelemetry-propagator-b3/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py::test_inject_empty_context",
            "value": 865418.680871302,
            "unit": "iter/sec",
            "range": "stddev: 0.00000126981216476984",
            "extra": "mean: 1.1555100694075386 usec\nrounds: 104167"
          }
        ]
      }
    ]
  }
}