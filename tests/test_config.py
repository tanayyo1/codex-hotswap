from pathlib import Path

import pytest

from codex_hotswap.config import ConfigError, load_config


def test_load_config_builds_target_args(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """version = 1

[settings]
max_swaps = 4
swap_delay_seconds = 2
default_cooldown_minutes = 90

[[targets]]
name = "primary"
codex_home = "~/.codex-primary"
profile = "default"
model = "gpt-5.4"
oss = true
local_provider = "ollama"
config_overrides = ["model_reasoning_effort=\\"high\\""]
extra_args = ["--search"]
"""
    )

    config = load_config(path)
    assert config.settings.max_swaps == 4
    assert config.settings.default_cooldown_minutes == 90
    assert config.targets[0].env_overrides() == {"CODEX_HOME": "~/.codex-primary"}
    assert config.targets[0].codex_args() == [
        "--profile",
        "default",
        "--model",
        "gpt-5.4",
        "--oss",
        "--local-provider",
        "ollama",
        "--config",
        'model_reasoning_effort="high"',
        "--search",
    ]


def test_load_config_requires_target() -> None:
    with pytest.raises(ConfigError):
        load_config(Path("/does/not/exist"))


def test_load_config_rejects_duplicate_names(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """version = 1

[[targets]]
name = "same"

[[targets]]
name = "same"
"""
    )

    with pytest.raises(ConfigError, match="Duplicate target name"):
        load_config(path)


def test_write_default_config_contains_codex_home(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    from codex_hotswap.config import write_default_config

    write_default_config(path)

    text = path.read_text()
    assert 'codex_home = "~/.codex-primary"' in text
    assert "default_cooldown_minutes = 240" in text
