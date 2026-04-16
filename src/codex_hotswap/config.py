from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import tomllib


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "codex-hotswap" / "config.toml"


class ConfigError(ValueError):
    pass


@dataclass(slots=True)
class Target:
    name: str
    profile: str | None = None
    model: str | None = None
    oss: bool = False
    local_provider: str | None = None
    config_overrides: list[str] = field(default_factory=list)
    extra_args: list[str] = field(default_factory=list)
    active: bool = True
    note: str | None = None

    def codex_args(self) -> list[str]:
        args: list[str] = []
        if self.profile:
            args += ["--profile", self.profile]
        if self.model:
            args += ["--model", self.model]
        if self.oss:
            args.append("--oss")
        if self.local_provider:
            args += ["--local-provider", self.local_provider]
        for value in self.config_overrides:
            args += ["--config", value]
        args.extend(self.extra_args)
        return args


@dataclass(slots=True)
class Settings:
    max_swaps: int = 3
    swap_delay_seconds: float = 1.5


@dataclass(slots=True)
class Config:
    path: Path
    settings: Settings
    targets: list[Target]

    def get_target(self, name: str) -> Target:
        for target in self.targets:
            if target.name == name:
                return target
        raise ConfigError(f"Unknown target: {name}")

    def active_targets(self) -> list[Target]:
        return [target for target in self.targets if target.active]


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    raw = tomllib.loads(path.read_text())
    version = raw.get("version")
    if version != 1:
        raise ConfigError("Config version must be set to 1")

    settings = _load_settings(raw.get("settings", {}))
    targets_raw = raw.get("targets")
    if not isinstance(targets_raw, list) or not targets_raw:
        raise ConfigError("Config must define at least one target")

    targets = [_load_target(item, seen_names=set()) for item in targets_raw]
    _validate_unique_names(targets)
    if not any(target.active for target in targets):
        raise ConfigError("Config must define at least one active target")
    return Config(path=path, settings=settings, targets=targets)


def write_default_config(path: Path = DEFAULT_CONFIG_PATH, force: bool = False) -> Path:
    if path.exists() and not force:
        raise ConfigError(f"Config already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """version = 1

[settings]
max_swaps = 3
swap_delay_seconds = 1.5

[[targets]]
name = "primary"
profile = "default"
note = "Your primary Codex profile"

[[targets]]
name = "backup"
profile = "backup"
note = "A second Codex profile or provider"
"""
    )
    return path


def _load_settings(raw: Any) -> Settings:
    if not isinstance(raw, dict):
        raise ConfigError("[settings] must be a table")

    max_swaps = raw.get("max_swaps", 3)
    delay = raw.get("swap_delay_seconds", 1.5)
    if not isinstance(max_swaps, int) or max_swaps < 1:
        raise ConfigError("settings.max_swaps must be a positive integer")
    if not isinstance(delay, (int, float)) or delay < 0:
        raise ConfigError("settings.swap_delay_seconds must be a non-negative number")
    return Settings(max_swaps=max_swaps, swap_delay_seconds=float(delay))


def _load_target(raw: Any, seen_names: set[str]) -> Target:
    if not isinstance(raw, dict):
        raise ConfigError("Each target must be a table")

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ConfigError("Each target must have a non-empty name")
    if name in seen_names:
        raise ConfigError(f"Duplicate target name: {name}")
    seen_names.add(name)

    profile = _optional_string(raw, "profile")
    model = _optional_string(raw, "model")
    local_provider = _optional_string(raw, "local_provider")
    note = _optional_string(raw, "note")
    oss = raw.get("oss", False)
    active = raw.get("active", True)
    if not isinstance(oss, bool):
        raise ConfigError(f"Target {name}: oss must be true or false")
    if not isinstance(active, bool):
        raise ConfigError(f"Target {name}: active must be true or false")

    config_overrides = _string_list(raw.get("config_overrides", []), name, "config_overrides")
    extra_args = _string_list(raw.get("extra_args", []), name, "extra_args")

    return Target(
        name=name,
        profile=profile,
        model=model,
        oss=oss,
        local_provider=local_provider,
        config_overrides=config_overrides,
        extra_args=extra_args,
        active=active,
        note=note,
    )


def _optional_string(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key} must be a non-empty string when provided")
    return value


def _string_list(value: Any, target_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ConfigError(f"Target {target_name}: {field_name} must be a list of strings")
    return value


def _validate_unique_names(targets: list[Target]) -> None:
    seen: set[str] = set()
    for target in targets:
        if target.name in seen:
            raise ConfigError(f"Duplicate target name: {target.name}")
        seen.add(target.name)

