from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile

from .config import Config, ConfigError, Target


@dataclass
class AuthManager:
    config: Config

    def activate(self, target: Target) -> Path:
        source_home = target.expanded_codex_home()
        if source_home is None:
            raise ConfigError(f"Target {target.name} does not define a login vault")

        source_auth = Path(source_home) / "auth.json"
        if not source_auth.exists():
            raise ConfigError(f"Target {target.name} has no auth.json at {source_auth}")

        shared_home = self.config.shared_codex_home_path()
        shared_home.mkdir(parents=True, exist_ok=True)
        destination_auth = shared_home / "auth.json"

        if source_auth.resolve() == destination_auth.resolve(strict=False):
            return destination_auth

        with tempfile.NamedTemporaryFile(dir=shared_home, prefix=".auth-", suffix=".json", delete=False) as handle:
            temp_path = Path(handle.name)

        try:
            shutil.copy2(source_auth, temp_path)
            os.replace(temp_path, destination_auth)
        except Exception:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return destination_auth
