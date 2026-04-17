from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

from .config import Config, ConfigError, Target

ACTIVE_TARGET_METADATA = ".codex-hotswap-active-target.json"


@dataclass
class AuthManager:
    config: Config

    def activate(self, target: Target, *, destination_home: Path | None = None) -> Path:
        source_home = target.expanded_codex_home()
        if source_home is None:
            raise ConfigError(f"Target {target.name} does not define a login vault")

        source_auth = Path(source_home) / "auth.json"
        if not source_auth.exists():
            raise ConfigError(f"Target {target.name} has no auth.json at {source_auth}")

        target_home = destination_home or self.config.shared_codex_home_path()
        target_home.mkdir(parents=True, exist_ok=True)
        destination_auth = target_home / "auth.json"

        if source_auth.resolve() == destination_auth.resolve(strict=False):
            return destination_auth

        with tempfile.NamedTemporaryFile(dir=target_home, prefix=".auth-", suffix=".json", delete=False) as handle:
            temp_path = Path(handle.name)

        try:
            shutil.copy2(source_auth, temp_path)
            os.replace(temp_path, destination_auth)
            self._write_activation_metadata(self.config.shared_codex_home_path(), target)
        except Exception:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return destination_auth

    def activation_metadata_path(self) -> Path:
        return self.config.shared_codex_home_path() / ACTIVE_TARGET_METADATA

    def _write_activation_metadata(self, shared_home: Path, target: Target) -> None:
        payload = {
            "target": target.name,
            "auth_vault": target.expanded_codex_home(),
            "activated_at": datetime.now(UTC).isoformat(),
            "copied_files": ["auth.json"],
        }
        with tempfile.NamedTemporaryFile(
            dir=shared_home,
            prefix=".active-target-",
            suffix=".json",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write((json.dumps(payload, indent=2) + "\n").encode("utf-8"))

        metadata_path = shared_home / ACTIVE_TARGET_METADATA
        try:
            os.replace(temp_path, metadata_path)
        except Exception:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
