# Copyright 2019, OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import concurrent.futures
import contextvars
import unittest
from multiprocessing.dummy import Pool as ThreadPool

from opentelemetry.context import get_current, set_value, set_current
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from ..utils import new_context, merge_context_correlation


def do_work():
    get_current().set_value("say-something", "bar")


class TestContext(unittest.TestCase):
    spans = [
        "test_span1",
        "test_span2",
        "test_span3",
        "test_span4",
        "test_span5",
    ]

    def do_some_work(self, name):
        with self.tracer.start_as_current_span(name):
            pass

    def setUp(self):
        self.tracer_source = trace.TracerSource()
        self.tracer = self.tracer_source.get_tracer(__name__)
        self.memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(self.memory_exporter)
        self.tracer_source.add_span_processor(span_processor)

    def test_context(self):
        self.assertIsNone(get_current().value("say-something"))
        empty_context = get_current()
        get_current().set_value("say-something", "foo")
        self.assertEqual(get_current().value("say-something"), "foo")
        second_context = get_current()

        do_work()
        self.assertEqual(get_current().value("say-something"), "bar")
        third_context = get_current()

        self.assertIsNone(empty_context.get("say-something"))
        self.assertEqual(second_context.get("say-something"), "foo")
        self.assertEqual(third_context.get("say-something"), "bar")

    # FIXME Merge context has been removed. The merge method could be moved
    # outside of the methods of the merge object itself. Review this with Alex.

    def test_propagation(self):
        pass

    def test_with_futures(self):
        with self.tracer.start_as_current_span("futures_test"):
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=5
            ) as executor:
                # Start the load operations
                for span in self.spans:
                    executor.submit(
                        contextvars.copy_context().run,
                        self.do_some_work,
                        span,
                    )

        span_list = self.memory_exporter.get_finished_spans()
        expected = [
            "test_span1",
            "test_span2",
            "test_span3",
            "test_span4",
            "test_span5",
            "futures_test",
        ]
        self.assertEqual(len(span_list), len(expected))

    def test_with_threads(self):
        with self.tracer.start_as_current_span("threads_test"):
            pool = ThreadPool(5)  # create a thread pool
            pool.map(
                get_current().with_get_current_context(self.do_some_work),
                self.spans,
            )
            pool.close()
            pool.join()
        span_list = self.memory_exporter.get_finished_spans()
        expected = [
            "test_span1",
            "test_span2",
            "test_span3",
            "test_span4",
            "test_span5",
            "threads_test",
        ]
        self.assertEqual(len(span_list), len(expected))

    def test_merge(self):
        set_value("name", "first")
        set_value("somebool", True)
        set_value("key", "value")
        set_value("otherkey", "othervalue")
        src_ctx = get_current()

        set_value("name", "second")
        set_value("somebool", False)
        set_value("anotherkey", "anothervalue")
        dst_ctx = get_current()

        set_current(
            merge_context_correlation(src_ctx, dst_ctx)
        )
        current = get_current()
        self.assertEqual(current.get_value("name"), "first")
        self.assertTrue(current.get_value("somebool"))
        self.assertEqual(current.get_value("key"), "value")
        self.assertEqual(current.get_value("otherkey"), "othervalue")
        self.assertEqual(current.get_value("anotherkey"), "anothervalue")

    def test_restore_context_on_exit(self):
        get_current().set_get_current(new_context())
        get_current().set_value("a", "xxx")
        get_current().set_value("b", "yyy")

        self.assertEqual({"a": "xxx", "b": "yyy"}, get_current().snapshot)
        with get_current().use(a="foo"):
            self.assertEqual({"a": "foo", "b": "yyy"}, get_current().snapshot)
            get_current().set_value("a", "i_want_to_mess_it_but_wont_work")
            get_current().set_value("b", "i_want_to_mess_it")
        self.assertEqual({"a": "xxx", "b": "yyy"}, get_current().snapshot)

    def test_set_value(self):
        context = get_current().set_value("a", "yyy")
        context2 = get_current().set_value("a", "zzz")
        context3 = get_current().set_value("a", "---", context)
        current_context = get_current()
        self.assertEqual("yyy", get_current().value("a", context=context))
        self.assertEqual("zzz", get_current().value("a", context=context2))
        self.assertEqual("---", get_current().value("a", context=context3))
        self.assertEqual(
            "zzz", get_current().value("a", context=current_context)
        )
