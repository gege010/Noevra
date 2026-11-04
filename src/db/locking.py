"""One process owns a local research database and its in-memory job runtime."""
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def local_database_lock(database: str | None):
    """Release automatically even after a crash; never infer ownership from a PID file."""
    if not database or database == ":memory:":
        yield
        return
    path = Path(database).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.with_name(path.name + ".lock").open("a+b")
    try:
        if handle.seek(0, 2) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if __import__("os").name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("This database is already used by another Noevra process. Stop it or select a different NOEVRA_DATA_DIR.") from None
        yield
    finally:
        # Closing the descriptor releases the OS lock on all supported platforms.
        handle.close()
