"""Descriptor-relative, bounded capture of untrusted project files."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable


_MAX_FILE_BYTES = 16 * 1024 * 1024
_MAX_TOTAL_BYTES = 128 * 1024 * 1024
_MAX_ENTRIES = 100_000
_MAX_DEPTH = 128


class SafeCaptureError(OSError):
    """A source path could not be captured without following unsafe state."""


@dataclass(frozen=True)
class CapturedFile:
    identity: str
    mode: int
    size: int
    content_hash: str


CaptureHook = Callable[[str, str], None]


def _digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _parts(identity: str) -> tuple[str, ...]:
    path = PurePosixPath(identity)
    if (
        not identity
        or identity != path.as_posix()
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise SafeCaptureError("unsafe project-relative identity")
    return path.parts


def _required_flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int):
        raise SafeCaptureError(f"platform lacks required {name}")
    return value


def _is_missing(error: BaseException) -> bool:
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, FileNotFoundError):
            return True
        current = current.__cause__
    return False


def _safe_entry_name(name: object) -> bool:
    if (
        not isinstance(name, str)
        or name in {"", ".", ".."}
        or "/" in name
        or "\\" in name
        or any(ord(character) < 32 or ord(character) == 127 for character in name)
    ):
        return False
    try:
        name.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


class SafeProjectReader:
    """Hold one project dirfd while capturing files by relative identity."""

    def __init__(
        self,
        root: Path,
        *,
        hook: CaptureHook | None = None,
        max_file_bytes: int = _MAX_FILE_BYTES,
        max_total_bytes: int = _MAX_TOTAL_BYTES,
        max_entries: int = _MAX_ENTRIES,
        max_depth: int = _MAX_DEPTH,
    ) -> None:
        self.root = root.expanduser().absolute()
        self.hook = hook
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.max_entries = max_entries
        self.max_depth = max_depth
        self._root_fd = -1
        self._total_bytes = 0
        self._entries = 0

    def __enter__(self) -> "SafeProjectReader":
        flags = (
            _required_flag("O_RDONLY")
            | _required_flag("O_DIRECTORY")
            | _required_flag("O_NOFOLLOW")
            | _required_flag("O_CLOEXEC")
        )
        try:
            self._root_fd = os.open(self.root, flags)
            metadata = os.fstat(self._root_fd)
            if not stat.S_ISDIR(metadata.st_mode):
                raise SafeCaptureError("project root is not a directory")
            self._notify("after_dir_fd_open", ".")
        except SafeCaptureError:
            self.close()
            raise
        except OSError as error:
            self.close()
            raise SafeCaptureError("project root is missing or unsafe") from error
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._root_fd >= 0:
            os.close(self._root_fd)
            self._root_fd = -1

    def _notify(self, stage: str, identity: str) -> None:
        if self.hook is not None:
            self.hook(stage, identity)

    def _count_entry(self) -> None:
        self._entries += 1
        if self._entries > self.max_entries:
            raise SafeCaptureError("capture entry limit exceeded")

    def _open_directory(self, parent_fd: int, name: str, identity: str) -> int:
        flags = (
            _required_flag("O_RDONLY")
            | _required_flag("O_DIRECTORY")
            | _required_flag("O_NOFOLLOW")
            | _required_flag("O_CLOEXEC")
        )
        descriptor = -1
        try:
            descriptor = os.open(name, flags, dir_fd=parent_fd)
            metadata = os.fstat(descriptor)
            if not stat.S_ISDIR(metadata.st_mode):
                raise SafeCaptureError("path component is not a directory")
            self._notify("after_dir_fd_open", identity)
            return descriptor
        except SafeCaptureError:
            if descriptor >= 0:
                os.close(descriptor)
            raise
        except OSError as error:
            if descriptor >= 0:
                os.close(descriptor)
            raise SafeCaptureError("directory component is missing or unsafe") from error
        except BaseException:
            if descriptor >= 0:
                os.close(descriptor)
            raise

    def _open_parent(self, parts: tuple[str, ...]) -> tuple[int, list[int]]:
        if self._root_fd < 0:
            raise SafeCaptureError("reader is not open")
        parent = self._root_fd
        opened: list[int] = []
        traversed: list[str] = []
        try:
            for part in parts:
                traversed.append(part)
                parent = self._open_directory(
                    parent,
                    part,
                    "/".join(traversed),
                )
                opened.append(parent)
        except BaseException:
            for descriptor in reversed(opened):
                os.close(descriptor)
            raise
        return parent, opened

    def _open_entry(self, parent_fd: int, name: str, identity: str) -> tuple[int, os.stat_result]:
        self._notify("before_final_open", identity)
        flags = (
            _required_flag("O_RDONLY")
            | _required_flag("O_NOFOLLOW")
            | _required_flag("O_NONBLOCK")
            | _required_flag("O_CLOEXEC")
        )
        descriptor = -1
        try:
            descriptor = os.open(name, flags, dir_fd=parent_fd)
            metadata = os.fstat(descriptor)
            self._notify("after_file_fd_open", identity)
            return descriptor, metadata
        except OSError as error:
            if descriptor >= 0:
                os.close(descriptor)
            raise SafeCaptureError("entry is missing or unsafe") from error
        except BaseException:
            if descriptor >= 0:
                os.close(descriptor)
            raise

    def _read_regular(self, descriptor: int, metadata: os.stat_result) -> bytes:
        if not stat.S_ISREG(metadata.st_mode):
            raise SafeCaptureError("entry is not a regular file")
        if metadata.st_size > self.max_file_bytes:
            raise SafeCaptureError("capture file limit exceeded")
        chunks: list[bytes] = []
        remaining = self.max_file_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > self.max_file_bytes:
            raise SafeCaptureError("capture file limit exceeded")
        self._total_bytes += len(content)
        if self._total_bytes > self.max_total_bytes:
            raise SafeCaptureError("capture total byte limit exceeded")
        return content

    def read_file(self, identity: str) -> tuple[bytes, CapturedFile]:
        parts = _parts(identity)
        parent, opened = self._open_parent(parts[:-1])
        descriptor = -1
        try:
            descriptor, metadata = self._open_entry(parent, parts[-1], identity)
            self._count_entry()
            content = self._read_regular(descriptor, metadata)
            return content, CapturedFile(
                identity=identity,
                mode=stat.S_IMODE(metadata.st_mode),
                size=len(content),
                content_hash=_digest(content),
            )
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            for item in reversed(opened):
                os.close(item)

    def read_bytes(self, identity: str) -> bytes:
        content, _ = self.read_file(identity)
        return content

    def read_optional_file(
        self,
        identity: str,
    ) -> tuple[bytes, CapturedFile] | None:
        """Read a file relative to the held root, returning None only for ENOENT."""
        try:
            return self.read_file(identity)
        except SafeCaptureError as error:
            if _is_missing(error):
                return None
            raise

    def _read_tree_directory(
        self,
        descriptor: int,
        identity: str,
        suffixes: tuple[str, ...],
        include: Callable[[str], bool] | None,
        captured: list[tuple[bytes, CapturedFile]],
        depth: int,
    ) -> None:
        if depth > self.max_depth:
            raise SafeCaptureError("capture directory depth limit exceeded")
        try:
            names = sorted(os.listdir(descriptor))
        except OSError as error:
            raise SafeCaptureError("capture directory cannot be listed") from error
        for name in names:
            if not _safe_entry_name(name):
                raise SafeCaptureError("capture directory contains an unsafe name")
            child_identity = f"{identity}/{name}"
            child_fd = -1
            try:
                child_fd, metadata = self._open_entry(
                    descriptor,
                    name,
                    child_identity,
                )
                self._count_entry()
                if stat.S_ISDIR(metadata.st_mode):
                    self._notify("after_tree_dir_open", child_identity)
                    self._read_tree_directory(
                        child_fd,
                        child_identity,
                        suffixes,
                        include,
                        captured,
                        depth + 1,
                    )
                elif stat.S_ISREG(metadata.st_mode):
                    if name.endswith(suffixes) and (
                        include is None or include(child_identity)
                    ):
                        content = self._read_regular(child_fd, metadata)
                        captured.append(
                            (
                                content,
                                CapturedFile(
                                    identity=child_identity,
                                    mode=stat.S_IMODE(metadata.st_mode),
                                    size=len(content),
                                    content_hash=_digest(content),
                                ),
                            )
                        )
                else:
                    raise SafeCaptureError("capture tree contains an unsafe file type")
            finally:
                if child_fd >= 0:
                    os.close(child_fd)

    def read_tree_files(
        self,
        identity: str,
        *,
        suffixes: tuple[str, ...],
        include: Callable[[str], bool] | None = None,
    ) -> tuple[tuple[bytes, CapturedFile], ...]:
        """Capture matching regular files through one no-follow dirfd traversal."""
        if (
            not isinstance(suffixes, tuple)
            or not suffixes
            or not all(isinstance(item, str) and item for item in suffixes)
        ):
            raise ValueError("suffixes must be a non-empty tuple of strings")
        parts = _parts(identity)
        parent, opened = self._open_parent(parts[:-1])
        descriptor = -1
        try:
            descriptor, metadata = self._open_entry(parent, parts[-1], identity)
            self._count_entry()
            if not stat.S_ISDIR(metadata.st_mode):
                raise SafeCaptureError("capture tree root is not a directory")
            self._notify("after_tree_dir_open", identity)
            captured: list[tuple[bytes, CapturedFile]] = []
            self._read_tree_directory(
                descriptor,
                identity,
                suffixes,
                include,
                captured,
                0,
            )
            return tuple(captured)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            for item in reversed(opened):
                os.close(item)

    def read_optional_tree_files(
        self,
        identity: str,
        *,
        suffixes: tuple[str, ...],
        include: Callable[[str], bool] | None = None,
    ) -> tuple[tuple[bytes, CapturedFile], ...] | None:
        """Return None only when the tree root itself is absent."""
        if (
            not isinstance(suffixes, tuple)
            or not suffixes
            or not all(isinstance(item, str) and item for item in suffixes)
        ):
            raise ValueError("suffixes must be a non-empty tuple of strings")
        parts = _parts(identity)
        try:
            parent, opened = self._open_parent(parts[:-1])
        except SafeCaptureError as error:
            if _is_missing(error):
                return None
            raise
        descriptor = -1
        try:
            try:
                descriptor, metadata = self._open_entry(
                    parent,
                    parts[-1],
                    identity,
                )
            except SafeCaptureError as error:
                if _is_missing(error):
                    return None
                raise
            self._count_entry()
            if not stat.S_ISDIR(metadata.st_mode):
                raise SafeCaptureError("capture tree root is not a directory")
            self._notify("after_tree_dir_open", identity)
            captured: list[tuple[bytes, CapturedFile]] = []
            self._read_tree_directory(
                descriptor,
                identity,
                suffixes,
                include,
                captured,
                0,
            )
            return tuple(captured)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            for item in reversed(opened):
                os.close(item)

    def copy_entry(self, identity: str, destination: Path) -> tuple[CapturedFile, ...]:
        parts = _parts(identity)
        parent, opened = self._open_parent(parts[:-1])
        descriptor = -1
        try:
            descriptor, metadata = self._open_entry(parent, parts[-1], identity)
            self._count_entry()
            return self._copy_open_entry(
                descriptor,
                metadata,
                identity,
                destination,
            )
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            for item in reversed(opened):
                os.close(item)

    def _copy_open_entry(
        self,
        descriptor: int,
        metadata: os.stat_result,
        identity: str,
        destination: Path,
        depth: int = 0,
    ) -> tuple[CapturedFile, ...]:
        if depth > self.max_depth:
            raise SafeCaptureError("capture directory depth limit exceeded")
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISREG(metadata.st_mode):
            content = self._read_regular(descriptor, metadata)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as stream:
                stream.write(content)
            os.chmod(destination, mode)
            return (
                CapturedFile(identity, mode, len(content), _digest(content)),
            )
        if not stat.S_ISDIR(metadata.st_mode):
            raise SafeCaptureError("capture entry has an unsafe file type")
        destination.mkdir(parents=True, exist_ok=True)
        captured: list[CapturedFile] = []
        try:
            names = sorted(os.listdir(descriptor))
        except OSError as error:
            raise SafeCaptureError("capture directory cannot be listed") from error
        for name in names:
            if not _safe_entry_name(name):
                raise SafeCaptureError("capture directory contains an unsafe name")
            child_identity = f"{identity}/{name}"
            child_destination = destination / name
            child_fd = -1
            try:
                child_fd, child_metadata = self._open_entry(
                    descriptor,
                    name,
                    child_identity,
                )
                self._count_entry()
                captured.extend(
                    self._copy_open_entry(
                        child_fd,
                        child_metadata,
                        child_identity,
                        child_destination,
                        depth + 1,
                    )
                )
            finally:
                if child_fd >= 0:
                    os.close(child_fd)
        os.chmod(destination, mode)
        return tuple(captured)

    def capture(
        self,
        identities: Iterable[str],
        destination_root: Path,
    ) -> tuple[CapturedFile, ...]:
        captured: dict[str, CapturedFile] = {}
        for identity in identities:
            destination = destination_root / Path(*PurePosixPath(identity).parts)
            for item in self.copy_entry(identity, destination):
                previous = captured.get(item.identity)
                if previous is not None and previous != item:
                    raise SafeCaptureError("capture identity changed during snapshot")
                captured[item.identity] = item
        return tuple(captured[key] for key in sorted(captured))


__all__ = [
    "CapturedFile",
    "SafeCaptureError",
    "SafeProjectReader",
]
