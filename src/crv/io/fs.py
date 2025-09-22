"""
Filesystem helpers for crv.io (file protocol baseline).

Responsibilities
- Provide a minimal stdlib-only abstraction for basic filesystem operations used by crv.io:
  existence checks, directory creation, safe write handles, fsync, and atomic renames.
- Establish clear semantics for the atomic write path: tmp write → fsync → atomic rename.

Source of truth
- Schema/table details and IDs live in crv.core (grammar/tables/ids/versioning); this module
  does not redefine any of those concepts and focuses solely on file operations.

Import DAG discipline
- stdlib-only; remote backends (via fsspec) can be layered later behind the same interface.

Notes
- Atomicity via os.replace is guaranteed only when src and dst reside on the same filesystem.
- All helpers are synchronous; callers decide on concurrency/locking if/when needed.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import BinaryIO


def exists(path: str) -> bool:
    """
    Check whether a path exists.

    Args:
        path (str): Filesystem path.

    Returns:
        bool: True if the path exists, False otherwise.
    """
    return os.path.exists(path)


def makedirs(path: str, exist_ok: bool = True) -> None:
    """
    Create directories recursively.

    Args:
        path (str): Directory path to create.
        exist_ok (bool): Do not error if the directory already exists.

    Notes:
        Thin wrapper around os.makedirs to centralize IO-layer usage.
    """
    os.makedirs(path, exist_ok=exist_ok)


@contextmanager
def open_write(path: str) -> Iterator[BinaryIO]:
    """
    Open a file for binary write as a context manager.

    Args:
        path (str): Destination path to open in write-binary mode.

    Yields:
        object: A writable file-like handle supporting .flush() and .fileno().

    Notes:
        - Useful when writing small JSON files (e.g., manifest) where explicit fsync
          can be applied prior to atomic rename of a temporary file.
        - Caller is responsible for atomic os.replace of the temporary file to final path.
    """
    fh = open(path, "wb")
    try:
        yield fh
    finally:
        fh.close()


def fsync_file(fh: BinaryIO) -> None:
    """
    Flush and fsync an open file handle.

    Args:
        fh (object): A file-like object with .fileno() and optionally .flush().

    Notes:
        Ensures file contents reach the storage device (subject to OS/filesystem semantics).
    """
    try:
        fh.flush()
    except Exception:
        # Not all file-like objects support flush; ignore.
        pass
    os.fsync(fh.fileno())


def fsync_path(path: str) -> None:
    """
    Open a path read-only and fsync its file descriptor.

    Args:
        path (str): Path to an already-written file.

    Notes:
        Useful when a library wrote to a path directly (e.g., polars.write_parquet),
        and you want to ensure data hits the disk before an atomic rename operation.
    """
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def rename_atomic(src: str, dst: str) -> None:
    """
    Atomically rename src -> dst on the same filesystem.

    Args:
        src (str): Existing source path (typically a temporary file).
        dst (str): Final destination path.

    Notes:
        Uses os.replace, which is atomic only if src and dst reside on the same filesystem.
        Callers must ensure tmp and final are placed under the same mount/volume.
    """
    os.replace(src, dst)


def listdir(path: str) -> list[str]:
    """
    List entries in a directory (non-recursive) as full paths.

    Args:
        path (str): Directory to list.

    Returns:
        list[str]: Full paths of entries; [] if directory does not exist.
    """
    try:
        names = os.listdir(path)
    except FileNotFoundError:
        return []
    return [os.path.join(path, name) for name in names]


def is_parquet(path: str) -> bool:
    """
    Check if a path appears to be a parquet file by extension.

    Args:
        path (str): File path.

    Returns:
        bool: True if path ends with ".parquet".
    """
    return path.endswith(".parquet")


def walk_parquet_files(root: str) -> list[str]:
    """
    Recursively collect all *.parquet under a root directory.

    Args:
        root (str): Directory to walk.

    Returns:
        list[str]: Full paths to parquet files found beneath root.
    """
    out: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".parquet"):
                out.append(os.path.join(dirpath, name))
    return out
