from pathlib import Path

from codex_hotswap.cli import (
    _build_setup_targets,
    _resolve_setup_target_names,
    main,
)
from codex_hotswap.config import ConfigError


def test_add_and_remove_target_updates_config(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"

    monkeypatch.setattr(
        "sys.argv",
        ["codex-hotswap", "init", "--config-path", str(config_path), "--force"],
    )
    assert main() == 0

    monkeypatch.setattr(
        "sys.argv",
        [
            "codex-hotswap",
            "add-target",
            "work",
            "--config-path",
            str(config_path),
            "--codex-home",
            "~/.codex-work",
            "--profile",
            "default",
            "--note",
            "Work account",
        ],
    )
    assert main() == 0
    text = config_path.read_text()
    assert 'name = "work"' in text
    assert 'codex_home = "~/.codex-work"' in text

    monkeypatch.setattr(
        "sys.argv",
        ["codex-hotswap", "remove-target", "work", "--config-path", str(config_path)],
    )
    assert main() == 0
    text = config_path.read_text()
    assert 'name = "work"' not in text


def test_resolve_setup_target_names_from_accounts() -> None:
    assert _resolve_setup_target_names("main, work, backup", None, "acc") == ["main", "work", "backup"]


def test_resolve_setup_target_names_from_count() -> None:
    assert _resolve_setup_target_names(None, 3, "acc") == ["acc1", "acc2", "acc3"]


def test_resolve_setup_target_names_rejects_duplicates() -> None:
    try:
        _resolve_setup_target_names("main,main", None, "acc")
    except ConfigError as exc:
        assert "duplicate" in str(exc).lower()
    else:
        raise AssertionError("expected ConfigError")


def test_build_setup_targets_uses_prefix_and_profile() -> None:
    targets = _build_setup_targets(
        target_names=["main", "work"],
        codex_home_prefix="~/.codex-",
        profile="default",
    )

    assert targets[0].codex_home == "~/.codex-main"
    assert targets[1].codex_home == "~/.codex-work"
    assert all(target.profile == "default" for target in targets)


def test_setup_creates_config_and_targets(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    state_path = tmp_path / "state.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "codex-hotswap",
            "setup",
            "--config-path",
            str(config_path),
            "--state-path",
            str(state_path),
            "--force",
            "--accounts",
            "main,work,backup",
        ],
    )
    assert main() == 0

    text = config_path.read_text()
    assert 'name = "main"' in text
    assert 'codex_home = "~/.codex-main"' in text
    assert 'name = "work"' in text
    assert 'name = "backup"' in text
