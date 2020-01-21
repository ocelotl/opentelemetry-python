from asyncio import sleep, gather, get_event_loop
from unittest import TestCase

from opentelemetry.context.async_context import AsyncRuntimeContext
from pdb import set_trace


class TestAsync(TestCase):

    def test_async_context(self):
        local_context = AsyncRuntimeContext()

        async def waiting(async_name, first_sleep, second_sleep):

            await sleep(first_sleep)

            local_context.set_value("async_name", async_name)

            self.assertEqual(async_name, local_context.value("async_name"))

            await sleep(second_sleep)

            self.assertEqual(async_name, local_context.value("async_name"))

        async def main():
            await gather(
                waiting("A", 0, 1), waiting("B", 0.1, 3), waiting("C", 2, 1)
            )

        loop = get_event_loop()
        loop.run_until_complete(main())
        loop.close()
