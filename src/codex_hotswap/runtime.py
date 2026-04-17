from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile

from .auth import ACTIVE_TARGET_METADATA, AuthManager
from .config import Config, Target


DEFAULT_RUNTIME_ROOT = Path.home() / ".local" / "state" / "codex-hotswap" / "runtime"

REQUIRED_SHARED_DIRS = (
    "sessions",
    "shell_snapshots",
    "skills",
    "rules",
    "memories",
)

REQUIRED_SHARED_FILES = (
    "history.jsonl",
    "session_index.jsonl",
)

SHARED_ENTRY_EXCLUDES = {
    "auth.json",
    ACTIVE_TARGET_METADATA,
    ".codex-hotswap.lock",
}

LOCAL_ONLY_ENTRIES = {
    "auth.json",
    ACTIVE_TARGET_METADATA,
}


@dataclass(slots=True)
class RuntimeHome:
    config: Config
    auth_manager: AuthManager
    path: Path | None = None

    def __enter__(self) -> "RuntimeHome":
        runtime_root = DEFAULT_RUNTIME_ROOT
        runtime_root.mkdir(parents=True, exist_ok=True)

        shared_home = self.shared_home
        shared_home.mkdir(parents=True, exist_ok=True)
        _ensure_required_shared_entries(shared_home)

        self.path = Path(tempfile.mkdtemp(prefix="codex-hotswap-", dir=runtime_root))
        _populate_runtime_home(shared_home, self.path)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.path is None:
            return
        try:
            _sync_runtime_home(self.shared_home, self.path)
        finally:
            shutil.rmtree(self.path, ignore_errors=True)
            self.path = None

    @property
    def shared_home(self) -> Path:
        return self.config.shared_codex_home_path()

    def activate(self, target: Target) -> Path:
        if self.path is None:
            raise RuntimeError("runtime home has not been created yet")
        return self.auth_manager.activate(target, destination_home=self.path)


def _ensure_required_shared_entries(shared_home: Path) -> None:
    for name in REQUIRED_SHARED_DIRS:
        (shared_home / name).mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_SHARED_FILES:
        (shared_home / name).touch(exist_ok=True)


def _populate_runtime_home(shared_home: Path, runtime_home: Path) -> None:
    for entry in shared_home.iterdir():
        if entry.name in SHARED_ENTRY_EXCLUDES:
            continue
        _symlink(entry, runtime_home / entry.name)


def _sync_runtime_home(shared_home: Path, runtime_home: Path) -> None:
    for entry in runtime_home.iterdir():
        if entry.name in LOCAL_ONLY_ENTRIES:
            continue
        if entry.is_symlink():
            continue
        destination = shared_home / entry.name
        if destination.exists():
            continue
        if entry.is_dir():
            shutil.copytree(entry, destination, symlinks=True)
        else:
            shutil.copy2(entry, destination)


def _symlink(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        destination.unlink()
    os.symlink(source, destination, target_is_directory=source.is_dir())
