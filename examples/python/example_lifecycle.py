"""Example-only ownership and cooperative POSIX signal handling."""
from contextlib import contextmanager
import signal


class ExampleInterrupted(Exception):
    def __init__(self, signum):
        super().__init__(f"interrupted by signal {signum}")
        self.signum = signum


@contextmanager
def managed_engine(factory, *args, **kwargs):
    """Wait for synchronous native work before explicitly closing its handle.

    A handler must not raise during ctypes creation: the native handle may exist
    before Python has received it. The caller checks between synchronous calls.
    """
    requested = None
    engine = None

    def request_stop(signum, _frame):
        nonlocal requested
        if requested is None:
            requested = signum

    def check_interrupted():
        if requested is not None:
            raise ExampleInterrupted(requested)

    previous = {sig: signal.signal(sig, request_stop)
                for sig in (signal.SIGTERM, signal.SIGINT)}
    # Python signal.signal() disables syscall restart. Keep native FastRPC
    # waits restartable so a stop request cannot abort an in-flight DSP call.
    for sig in previous:
        signal.siginterrupt(sig, False)
    try:
        engine = factory(*args, **kwargs)
        check_interrupted()
        yield engine, check_interrupted
        check_interrupted()
    finally:
        try:
            if engine is not None:
                engine.close()
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
