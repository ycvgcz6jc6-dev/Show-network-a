import asyncio
import pytest
from custom_components.dmx_monitor.qlcplus_bridge import QlcPlusBridge


def test_function_write_requires_matching_response():
    async def run():
        b=QlcPlusBridge('127.0.0.1')
        async def no_reply(*args, **kwargs): return None
        b._query=no_reply
        with pytest.raises(TimeoutError):
            await b.set_function_status('42', True)
        assert b.state.last_command['status']=='timeout_unconfirmed'
    asyncio.run(run())


def test_function_write_records_confirmed_response():
    async def run():
        b=QlcPlusBridge('127.0.0.1')
        async def reply(*args, **kwargs): return ['QLC+API','setFunctionStatus','42','1']
        b._query=reply
        await b.set_function_status('42', True)
        assert b.snapshot()['qlcplus']['last_command']['status']=='confirmed_response'
    asyncio.run(run())
