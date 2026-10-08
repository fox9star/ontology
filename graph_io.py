"""Atomic file writes and reentrant file locks shared by graph/job writers."""

from __future__ import annotations

import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

_registry_lock = threading.Lock()
_thread_locks = {}
_held_by_thread = threading.local()


@contextmanager
def graph_file_lock(path, timeout=30.0):
    """Lock any file path across processes and threads, even before it exists.

    Lock files intentionally persist: unlinking them would let another process
    lock a different inode. Nested calls in the same thread share one OS lock.
    Use around the full read/modify/write transaction, not just the final write.
    """
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = os.path.normcase(str(path))
    with _registry_lock:
        local_lock = _thread_locks.setdefault(key, threading.RLock())
    started = time.monotonic()
    if timeout is None:
        acquired = local_lock.acquire()
    else:
        if timeout < 0:
            raise ValueError("Lock timeout must be nonnegative or None")
        acquired = local_lock.acquire(timeout=timeout)
    if not acquired:
        raise TimeoutError(f"Timed out waiting for file lock: {path}")
    held = getattr(_held_by_thread, "locks", None)
    if held is None:
        held = _held_by_thread.locks = {}
    nested = key in held
    handle = None
    locked = False
    try:
        if not nested:
            lock_path = path.with_name(f".{path.name}.lock")
            handle = open(lock_path, "a+b")
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            while True:
                try:
                    if os.name == "nt":
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except OSError:
                    if timeout is not None and time.monotonic() - started >= timeout:
                        raise TimeoutError(f"Timed out waiting for file lock: {path}")
                    time.sleep(0.025)
            held[key] = handle
        yield path
    finally:
        if not nested and handle is not None:
            try:
                if locked:
                    if os.name == "nt":
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                held.pop(key, None)
                handle.close()
        local_lock.release()


def write_bytes_atomic(payload, path):
    """Replace a file with complete bytes using a flushed adjacent temporary."""
    if not isinstance(payload, bytes):
        raise TypeError("Atomic payload must be bytes")
    path = Path(path).resolve()
    with graph_file_lock(path):
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists():
                os.chmod(temporary, path.stat().st_mode)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return str(path)


def write_graph_atomic(graph, path, format="turtle"):
    """Serialize before replacing the file. Works within graph_file_lock."""
    payload = graph.serialize(format=format, encoding="utf-8")
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return write_bytes_atomic(payload, path)
