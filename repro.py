import trio
import signal
import threading

def run_in_trio_thread_ki_inner() -> None:
    # if we get a control-C during a run_in_trio_thread, then it propagates
    # back to the caller (slick!)
    record = set()

    async def check_run_in_trio_thread() -> None:
        token = trio.lowlevel.current_trio_token()

        def trio_thread_fn() -> None:
            print("in Trio thread")
            assert not trio.lowlevel.currently_ki_protected()
            print("ki_self")
            try:
                signal.raise_signal(signal.SIGINT)
            finally:
                import sys

                print("finally", sys.exc_info())

        async def trio_thread_afn() -> None:
            trio_thread_fn()

        def external_thread_fn() -> None:
            try:
                print("running")
                trio.from_thread.run_sync(trio_thread_fn, trio_token=token)
            except KeyboardInterrupt:
                print("ok1")
                record.add("ok1")
            try:
                trio.from_thread.run(trio_thread_afn, trio_token=token)
            except KeyboardInterrupt:
                print("ok2")
                record.add("ok2")

        thread = threading.Thread(target=external_thread_fn)
        thread.start()
        print("waiting")
        while thread.is_alive():  # noqa: ASYNC110
            await trio.sleep(0.01)  # Fine to poll in tests.
        print("waited, joining")
        thread.join()
        print("done")

    trio.run(check_run_in_trio_thread)
    assert record == {"ok1", "ok2"}

run_in_trio_thread_ki_inner()
