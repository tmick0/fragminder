import asyncio

__all__ = ['recurring_task']

class recurring_task (object):
    def __init__(self, delta_time, fn, *args):
        self._delta_time = delta_time
        self._fn = fn
        self._args = args
        
    async def start(self):
        self._task = asyncio.ensure_future(self._run())

    async def _run(self):
        while True:
            await self._fn(*self._args)
            await asyncio.sleep(self._delta_time)

    async def stop(self):
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
