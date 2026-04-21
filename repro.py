import trio
import signal
import threading
import gc

async def check_run_in_trio_thread() -> None:
    token = trio.lowlevel.current_trio_token()

    def trio_thread_fn() -> None:
        signal.raise_signal(signal.SIGINT)

    def external_thread_fn() -> None:
        try:
            trio.from_thread.run_sync(trio_thread_fn, trio_token=token)
        except KeyboardInterrupt:
            pass

    thread = threading.Thread(target=external_thread_fn)
    thread.start()

    while thread.is_alive():  # noqa: ASYNC110
        await trio.sleep(0.01)  # Fine to poll in tests.

    thread.join()

for _ in range(100):
    trio.run(check_run_in_trio_thread)
    for _ in range(6):
        gc.collect()
