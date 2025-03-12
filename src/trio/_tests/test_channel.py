from __future__ import annotations

from typing import TYPE_CHECKING, Union

import pytest

import trio
from trio import EndOfChannel, background_with_channel, open_memory_channel

from ..testing import Matcher, RaisesGroup, assert_checkpoints, wait_all_tasks_blocked

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


async def test_channel() -> None:
    with pytest.raises(TypeError):
        open_memory_channel(1.0)
    with pytest.raises(ValueError, match=r"^max_buffer_size must be >= 0$"):
        open_memory_channel(-1)

    s, r = open_memory_channel[Union[int, str, None]](2)
    repr(s)  # smoke test
    repr(r)  # smoke test

    s.send_nowait(1)
    with assert_checkpoints():
        await s.send(2)
    with pytest.raises(trio.WouldBlock):
        s.send_nowait(None)

    with assert_checkpoints():
        assert await r.receive() == 1
    assert r.receive_nowait() == 2
    with pytest.raises(trio.WouldBlock):
        r.receive_nowait()

    s.send_nowait("last")
    await s.aclose()
    with pytest.raises(trio.ClosedResourceError):
        await s.send("too late")
    with pytest.raises(trio.ClosedResourceError):
        s.send_nowait("too late")
    with pytest.raises(trio.ClosedResourceError):
        s.clone()
    await s.aclose()

    assert r.receive_nowait() == "last"
    with pytest.raises(EndOfChannel):
        await r.receive()
    await r.aclose()
    with pytest.raises(trio.ClosedResourceError):
        await r.receive()
    with pytest.raises(trio.ClosedResourceError):
        r.receive_nowait()
    await r.aclose()


async def test_553(autojump_clock: trio.abc.Clock) -> None:
    s, r = open_memory_channel[str](1)
    with trio.move_on_after(10) as timeout_scope:
        await r.receive()
    assert timeout_scope.cancelled_caught
    await s.send("Test for PR #553")


async def test_channel_multiple_producers() -> None:
    async def producer(send_channel: trio.MemorySendChannel[int], i: int) -> None:
        # We close our handle when we're done with it
        async with send_channel:
            for j in range(3 * i, 3 * (i + 1)):
                await send_channel.send(j)

    send_channel, receive_channel = open_memory_channel[int](0)
    async with trio.open_nursery() as nursery:
        # We hand out clones to all the new producers, and then close the
        # original.
        async with send_channel:
            for i in range(10):
                nursery.start_soon(producer, send_channel.clone(), i)

        got = [value async for value in receive_channel]

        got.sort()
        assert got == list(range(30))


async def test_channel_multiple_consumers() -> None:
    successful_receivers = set()
    received = []

    async def consumer(receive_channel: trio.MemoryReceiveChannel[int], i: int) -> None:
        async for value in receive_channel:
            successful_receivers.add(i)
            received.append(value)

    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel[int](1)
        async with send_channel:
            for i in range(5):
                nursery.start_soon(consumer, receive_channel, i)
            await wait_all_tasks_blocked()
            for i in range(10):
                await send_channel.send(i)

    assert successful_receivers == set(range(5))
    assert len(received) == 10
    assert set(received) == set(range(10))


async def test_close_basics() -> None:
    async def send_block(
        s: trio.MemorySendChannel[None],
        expect: type[BaseException],
    ) -> None:
        with pytest.raises(expect):
            await s.send(None)

    # closing send -> other send gets ClosedResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.ClosedResourceError)
        await wait_all_tasks_blocked()
        await s.aclose()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.ClosedResourceError):
        await s.send(None)

    # and receive gets EndOfChannel
    with pytest.raises(EndOfChannel):
        r.receive_nowait()
    with pytest.raises(EndOfChannel):
        await r.receive()

    # closing receive -> send gets BrokenResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.BrokenResourceError)
        await wait_all_tasks_blocked()
        await r.aclose()

    # and it's persistent
    with pytest.raises(trio.BrokenResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.BrokenResourceError):
        await s.send(None)

    # closing receive -> other receive gets ClosedResourceError
    async def receive_block(r: trio.MemoryReceiveChannel[int]) -> None:
        with pytest.raises(trio.ClosedResourceError):
            await r.receive()

    _s2, r2 = open_memory_channel[int](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(receive_block, r2)
        await wait_all_tasks_blocked()
        await r2.aclose()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        r2.receive_nowait()
    with pytest.raises(trio.ClosedResourceError):
        await r2.receive()


async def test_close_sync() -> None:
    async def send_block(
        s: trio.MemorySendChannel[None],
        expect: type[BaseException],
    ) -> None:
        with pytest.raises(expect):
            await s.send(None)

    # closing send -> other send gets ClosedResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.ClosedResourceError)
        await wait_all_tasks_blocked()
        s.close()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.ClosedResourceError):
        await s.send(None)

    # and receive gets EndOfChannel
    with pytest.raises(EndOfChannel):
        r.receive_nowait()
    with pytest.raises(EndOfChannel):
        await r.receive()

    # closing receive -> send gets BrokenResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.BrokenResourceError)
        await wait_all_tasks_blocked()
        r.close()

    # and it's persistent
    with pytest.raises(trio.BrokenResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.BrokenResourceError):
        await s.send(None)

    # closing receive -> other receive gets ClosedResourceError
    async def receive_block(r: trio.MemoryReceiveChannel[None]) -> None:
        with pytest.raises(trio.ClosedResourceError):
            await r.receive()

    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(receive_block, r)
        await wait_all_tasks_blocked()
        r.close()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        r.receive_nowait()
    with pytest.raises(trio.ClosedResourceError):
        await r.receive()


async def test_receive_channel_clone_and_close() -> None:
    s, r = open_memory_channel[None](10)

    r2 = r.clone()
    r3 = r.clone()

    s.send_nowait(None)
    await r.aclose()
    with r2:
        pass

    with pytest.raises(trio.ClosedResourceError):
        r.clone()

    with pytest.raises(trio.ClosedResourceError):
        r2.clone()

    # Can still send, r3 is still open
    s.send_nowait(None)

    await r3.aclose()

    # But now the receiver is really closed
    with pytest.raises(trio.BrokenResourceError):
        s.send_nowait(None)


async def test_close_multiple_send_handles() -> None:
    # With multiple send handles, closing one handle only wakes senders on
    # that handle, but others can continue just fine
    s1, r = open_memory_channel[str](0)
    s2 = s1.clone()

    async def send_will_close() -> None:
        with pytest.raises(trio.ClosedResourceError):
            await s1.send("nope")

    async def send_will_succeed() -> None:
        await s2.send("ok")

    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_will_close)
        nursery.start_soon(send_will_succeed)
        await wait_all_tasks_blocked()
        await s1.aclose()
        assert await r.receive() == "ok"


async def test_close_multiple_receive_handles() -> None:
    # With multiple receive handles, closing one handle only wakes receivers on
    # that handle, but others can continue just fine
    s, r1 = open_memory_channel[str](0)
    r2 = r1.clone()

    async def receive_will_close() -> None:
        with pytest.raises(trio.ClosedResourceError):
            await r1.receive()

    async def receive_will_succeed() -> None:
        assert await r2.receive() == "ok"

    async with trio.open_nursery() as nursery:
        nursery.start_soon(receive_will_close)
        nursery.start_soon(receive_will_succeed)
        await wait_all_tasks_blocked()
        await r1.aclose()
        await s.send("ok")


async def test_inf_capacity() -> None:
    send, receive = open_memory_channel[int](float("inf"))

    # It's accepted, and we can send all day without blocking
    with send:
        for i in range(10):
            send.send_nowait(i)

    got = [i async for i in receive]
    assert got == list(range(10))


async def test_statistics() -> None:
    s, r = open_memory_channel[None](2)

    assert s.statistics() == r.statistics()
    stats = s.statistics()
    assert stats.current_buffer_used == 0
    assert stats.max_buffer_size == 2
    assert stats.open_send_channels == 1
    assert stats.open_receive_channels == 1
    assert stats.tasks_waiting_send == 0
    assert stats.tasks_waiting_receive == 0

    s.send_nowait(None)
    assert s.statistics().current_buffer_used == 1

    s2 = s.clone()
    assert s.statistics().open_send_channels == 2
    await s.aclose()
    assert s2.statistics().open_send_channels == 1

    r2 = r.clone()
    assert s2.statistics().open_receive_channels == 2
    await r2.aclose()
    assert s2.statistics().open_receive_channels == 1

    async with trio.open_nursery() as nursery:
        s2.send_nowait(None)  # fill up the buffer
        assert s.statistics().current_buffer_used == 2
        nursery.start_soon(s2.send, None)
        nursery.start_soon(s2.send, None)
        await wait_all_tasks_blocked()
        assert s.statistics().tasks_waiting_send == 2
        nursery.cancel_scope.cancel()
    assert s.statistics().tasks_waiting_send == 0

    # empty out the buffer again
    try:
        while True:
            r.receive_nowait()
    except trio.WouldBlock:
        pass

    async with trio.open_nursery() as nursery:
        nursery.start_soon(r.receive)
        await wait_all_tasks_blocked()
        assert s.statistics().tasks_waiting_receive == 1
        nursery.cancel_scope.cancel()
    assert s.statistics().tasks_waiting_receive == 0


async def test_channel_fairness() -> None:
    # We can remove an item we just sent, and send an item back in after, if
    # no-one else is waiting.
    s, r = open_memory_channel[Union[int, None]](1)
    s.send_nowait(1)
    assert r.receive_nowait() == 1
    s.send_nowait(2)
    assert r.receive_nowait() == 2

    # But if someone else is waiting to receive, then they "own" the item we
    # send, so we can't receive it (even though we run first):

    result: int | None = None

    async def do_receive(r: trio.MemoryReceiveChannel[int | None]) -> None:
        nonlocal result
        result = await r.receive()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(do_receive, r)
        await wait_all_tasks_blocked()
        s.send_nowait(2)
        with pytest.raises(trio.WouldBlock):
            r.receive_nowait()
    assert result == 2

    # And the analogous situation for send: if we free up a space, we can't
    # immediately send something in it if someone is already waiting to do
    # that
    s, r = open_memory_channel[Union[int, None]](1)
    s.send_nowait(1)
    with pytest.raises(trio.WouldBlock):
        s.send_nowait(None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(s.send, 2)
        await wait_all_tasks_blocked()
        assert r.receive_nowait() == 1
        with pytest.raises(trio.WouldBlock):
            s.send_nowait(3)
        assert (await r.receive()) == 2


async def test_unbuffered() -> None:
    s, r = open_memory_channel[int](0)
    with pytest.raises(trio.WouldBlock):
        r.receive_nowait()
    with pytest.raises(trio.WouldBlock):
        s.send_nowait(1)

    async def do_send(s: trio.MemorySendChannel[int], v: int) -> None:
        with assert_checkpoints():
            await s.send(v)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(do_send, s, 1)
        with assert_checkpoints():
            assert await r.receive() == 1
    with pytest.raises(trio.WouldBlock):
        r.receive_nowait()


async def test_background_with_channel() -> None:
    @background_with_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        await trio.sleep_forever()  # simulate deadlock

    async with agen() as recv_chan:
        async for x in recv_chan:
            assert x == 1
            break  # exit, cleanup should be quick


async def test_background_with_channel_exhaust() -> None:
    @background_with_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1

    async with agen() as recv_chan:
        async for x in recv_chan:
            assert x == 1


async def test_background_with_channel_broken_resource() -> None:
    @background_with_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        yield 2

    async with agen() as recv_chan:
        assert await recv_chan.__anext__() == 1

        # close the receiving channel
        await recv_chan.aclose()

        # trying to get the next element errors
        with pytest.raises(trio.ClosedResourceError):
            await recv_chan.__anext__()

        # but we don't get an error on exit of the cm


async def test_background_with_channel_cancelled() -> None:
    with trio.CancelScope() as cs:

        @background_with_channel
        async def agen() -> AsyncGenerator[None]:  # pragma: no cover
            raise AssertionError(
                "cancel before consumption means generator should not be iterated"
            )
            yield  # indicate that we're an iterator

        async with agen():
            cs.cancel()


async def test_background_with_channel_recv_closed(
    autojump_clock: trio.testing.MockClock,
) -> None:
    event = trio.Event()

    @background_with_channel
    async def agen() -> AsyncGenerator[int]:
        await event.wait()
        yield 1

    async with agen() as recv_chan:
        await recv_chan.aclose()
        event.set()
        # wait for agen to try sending on the closed channel
        await trio.sleep(1)


async def test_background_with_channel_no_race() -> None:
    # this previously led to a race condition due to
    # https://github.com/python-trio/trio/issues/1559
    @background_with_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        raise ValueError("oae")

    with RaisesGroup(ValueError):
        async with agen() as recv_chan:
            async for x in recv_chan:
                assert x == 1


async def test_background_with_channel_buffer_size_too_small(
    autojump_clock: trio.testing.MockClock,
) -> None:
    @background_with_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        raise AssertionError(
            "buffer size 0 means we shouldn't be asked for another value"
        )  # pragma: no cover

    with trio.move_on_after(5):
        async with agen() as recv_chan:
            async for x in recv_chan:  # pragma: no branch
                assert x == 1
                await trio.sleep_forever()


async def test_background_with_channel_no_interleave() -> None:
    @background_with_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        raise AssertionError  # pragma: no cover

    async with agen() as recv_chan:
        assert await recv_chan.__anext__() == 1
        await trio.lowlevel.checkpoint()


async def test_background_with_channel_genexit_finally() -> None:
    events: list[str] = []

    @background_with_channel
    async def agen(stuff: list[str]) -> AsyncGenerator[int]:
        try:
            yield 1
        except BaseException as e:
            stuff.append(repr(e))
            raise
        finally:
            stuff.append("finally")
            raise ValueError("agen")

    with RaisesGroup(
        Matcher(ValueError, match="^agen$"),
        Matcher(TypeError, match="^iterator$"),
    ):
        async with agen(events) as recv_chan:
            async for i in recv_chan:  # pragma: no branch
                assert i == 1
                raise TypeError("iterator")

    assert events == ["GeneratorExit()", "finally"]


async def test_background_with_channel_nested_loop() -> None:
    @background_with_channel
    async def agen() -> AsyncGenerator[int]:
        for i in range(2):
            yield i

    ii = 0
    async with agen() as recv_chan1:
        async for i in recv_chan1:
            async with agen() as recv_chan:
                jj = 0
                async for j in recv_chan:
                    assert (i, j) == (ii, jj)
                    jj += 1
            ii += 1
