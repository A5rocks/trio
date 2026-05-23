from __future__ import annotations
import attrs
import time

EventResult = None

@attrs.frozen(eq=False)
class _BrowserStatistics:
    backend: Literal["browser"] = attrs.field(init=False, default="browser")

class BrowserIOManager:
    def __init__(self) -> None:
        pass

    def close(self) -> None:
        pass

    def process_events(self, events) -> None:
        # there are no events
        assert events is None

    def get_events(self, timeout) -> None:
        # TODO: somehow suspend execution... you can use
        # `pyodide.ffi.wrappers.set_timeout` with the loop generator
        # but that doesn't allow returning a result from `trio.run` :/
        #
        # but as is, you *cannot* run_sync_soon anything else,
        # rendering this completely impractical! well, WASM is
        # impractical anyways.
        time.sleep(timeout)
        return None
