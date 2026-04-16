from pathlib import Path

from codex_hotswap.cli import (
    _build_setup_targets,
    _install_codex_shim,
    _merge_setup_targets,
    _resolve_real_codex_binary,
    _resolve_setup_target_names,
    _uninstall_codex_shim,
    main,
)
from codex_hotswap.config import Config, ConfigError, Settings, Target


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
        auth_home_prefix="~/.codex-",
        profile="default",
    )

    assert targets[0].codex_home == "~/.codex-main"
    assert targets[1].codex_home == "~/.codex-work"
    assert all(target.profile == "default" for target in targets)


def test_build_setup_targets_allows_no_profile() -> None:
    targets = _build_setup_targets(
        target_names=["main"],
        auth_home_prefix="~/.codex-",
        profile=None,
    )

    assert targets[0].profile is None


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
    assert 'shared_codex_home = "~/.codex"' in text
    assert 'profile = "default"' not in text
    assert 'name = "work"' in text
    assert 'name = "backup"' in text


def test_merge_setup_targets_replaces_existing_generated_targets() -> None:
    config = Config(
        path=Path("/tmp/config.toml"),
        settings=Settings(shared_codex_home="~/.codex"),
        targets=[
            Target(name="main", codex_home="~/.codex-old-main", note="old"),
            Target(name="custom", codex_home="~/.codex-custom", note="keep"),
        ],
    )

    updated = _merge_setup_targets(
        config,
        [
            Target(name="main", codex_home="~/.codex-main", note="new"),
            Target(name="backup", codex_home="~/.codex-backup", note="new"),
        ],
        replace_targets=False,
    )

    assert [target.name for target in updated.targets] == ["main", "custom", "backup"]
    assert updated.get_target("main").codex_home == "~/.codex-main"
    assert updated.get_target("custom").codex_home == "~/.codex-custom"


def test_install_and_uninstall_codex_shim(tmp_path: Path) -> None:
    shim_path = tmp_path / "bin" / "codex"
    real_bin = tmp_path / "real" / "codex"
    real_bin.parent.mkdir(parents=True)
    real_bin.write_text("#!/bin/sh\nexit 0\n")

    installed = _install_codex_shim(shim_path, real_bin=real_bin, force=True)

    assert installed == shim_path
    assert shim_path.exists()
    assert "CODEX_HOTSWAP_REAL_BIN" in shim_path.read_text()
    assert _resolve_real_codex_binary(shim_path) == real_bin
    assert _uninstall_codex_shim(shim_path) is True
    assert not shim_path.exists()
