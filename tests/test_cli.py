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


def test_setup_can_login_and_install_shim_in_one_command(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    state_path = tmp_path / "state.json"
    shim_path = tmp_path / "bin" / "codex"
    logged_targets: list[str] = []
    installed_paths: list[Path] = []

    def fake_login(self, target, login_args, relogin=False):
        logged_targets.append(target.name)
        return 0

    def fake_install(path, real_bin=None, force=False):
        installed_paths.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# codex-hotswap shim\n")
        return path

    monkeypatch.setattr("codex_hotswap.cli.CodexRunner.login", fake_login)
    monkeypatch.setattr("codex_hotswap.cli._install_codex_shim", fake_install)
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
            "--count",
            "2",
            "--prefix",
            "acc",
            "--login",
            "--install-shim",
            "--shim-path",
            str(shim_path),
        ],
    )

    assert main() == 0
    assert logged_targets == ["acc1", "acc2"]
    assert installed_paths == [shim_path]
    assert shim_path.exists()
    assert 'shared_codex_home = "~/.codex"' in config_path.read_text()


def test_codex_hot_passthrough_preserves_unknown_codex_flags(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    state_path = tmp_path / "state.json"
    config_path.write_text(
        """version = 1

[settings]
shared_codex_home = "~/.codex"

[[targets]]
name = "acc1"
codex_home = "~/.codex-acc1"
"""
    )
    received: list[str] = []

    def fake_run(self, user_args):
        received.extend(user_args)
        return 0

    monkeypatch.setattr("codex_hotswap.cli.CodexRunner.run", fake_run)
    monkeypatch.setattr(
        "sys.argv",
        [
            "codex-hot",
            "--config-path",
            str(config_path),
            "--state-path",
            str(state_path),
            "--version",
        ],
    )

    assert main() == 0
    assert received == ["--version"]


def test_setup_rejects_login_arg_without_login(tmp_path: Path, monkeypatch) -> None:
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
            "--count",
            "2",
            "--login-arg=--device-auth",
        ],
    )

    assert main() == 1


def test_setup_rejects_shim_force_without_install_shim(tmp_path: Path, monkeypatch) -> None:
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
            "--count",
            "2",
            "--shim-force",
        ],
    )

    assert main() == 1


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


def test_install_codex_shim_refuses_to_replace_non_shim_without_force(tmp_path: Path) -> None:
    shim_path = tmp_path / "bin" / "codex"
    shim_path.parent.mkdir(parents=True)
    shim_path.write_text("#!/bin/sh\nexit 0\n")
    real_bin = tmp_path / "real" / "codex"
    real_bin.parent.mkdir(parents=True)
    real_bin.write_text("#!/bin/sh\nexit 0\n")

    try:
        _install_codex_shim(shim_path, real_bin=real_bin, force=False)
    except ConfigError as exc:
        assert "Refusing to overwrite non-shim file" in str(exc)
    else:
        raise AssertionError("expected ConfigError")


def test_install_codex_shim_refuses_to_replace_non_shim_with_force(tmp_path: Path) -> None:
    shim_path = tmp_path / "bin" / "codex"
    shim_path.parent.mkdir(parents=True)
    shim_path.write_text("#!/bin/sh\nexit 0\n")
    real_bin = tmp_path / "real" / "codex"
    real_bin.parent.mkdir(parents=True)
    real_bin.write_text("#!/bin/sh\nexit 0\n")

    try:
        _install_codex_shim(shim_path, real_bin=real_bin, force=True)
    except ConfigError as exc:
        assert "Refusing to overwrite non-shim file" in str(exc)
    else:
        raise AssertionError("expected ConfigError")


def test_setup_install_shim_failure_returns_error(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    state_path = tmp_path / "state.json"

    def fake_install(path, real_bin=None, force=False):
        raise ConfigError("shim failed")

    monkeypatch.setattr("codex_hotswap.cli._install_codex_shim", fake_install)
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
            "--count",
            "2",
            "--prefix",
            "acc",
            "--install-shim",
        ],
    )

    assert main() == 1


def test_doctor_reports_ok(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "config.toml"
    state_path = tmp_path / "state.json"
    shared_home = tmp_path / "shared"
    shim_path = tmp_path / "bin" / "codex"
    shared_home.mkdir()
    (shared_home / "auth.json").write_text("{}")
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "auth.json").write_text("{}")
    config_path.write_text(
        f"""version = 1

[settings]
shared_codex_home = "{shared_home}"

[[targets]]
name = "acc1"
codex_home = "{vault}"
"""
    )

    monkeypatch.setattr("codex_hotswap.cli.shutil.which", lambda name: "/usr/bin/codex" if name == "codex" else None)
    monkeypatch.setattr("codex_hotswap.cli.CodexRunner.login_status", lambda self, target: (True, "Logged in using ChatGPT"))
    monkeypatch.setattr(
        "sys.argv",
        [
            "codex-hotswap",
            "doctor",
            "--config-path",
            str(config_path),
            "--state-path",
            str(state_path),
            "--shim-path",
            str(shim_path),
        ],
    )

    assert main() == 0
    output = capsys.readouterr().out
    assert "doctor status: ok" in output
    assert "target acc1 login status: ok" in output


def test_doctor_reports_missing_auth(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "config.toml"
    state_path = tmp_path / "state.json"
    shared_home = tmp_path / "shared"
    shared_home.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    config_path.write_text(
        f"""version = 1

[settings]
shared_codex_home = "{shared_home}"

[[targets]]
name = "acc1"
codex_home = "{vault}"
"""
    )

    monkeypatch.setattr("codex_hotswap.cli.shutil.which", lambda name: "/usr/bin/codex" if name == "codex" else None)
    monkeypatch.setattr(
        "sys.argv",
        [
            "codex-hotswap",
            "doctor",
            "--config-path",
            str(config_path),
            "--state-path",
            str(state_path),
            "--skip-login-status",
        ],
    )

    assert main() == 1
    output = capsys.readouterr().out
    assert "doctor status: issues found" in output
    assert "shared auth.json is missing" in output


def test_doctor_reports_inactive_shim_on_path(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "config.toml"
    state_path = tmp_path / "state.json"
    shared_home = tmp_path / "shared"
    shared_home.mkdir()
    (shared_home / "auth.json").write_text("{}")
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "auth.json").write_text("{}")
    shim_path = tmp_path / "bin" / "codex"
    shim_path.parent.mkdir(parents=True)
    shim_path.write_text(
        "#!/usr/bin/env bash\n"
        "# codex-hotswap shim\n"
        'export CODEX_HOTSWAP_REAL_BIN="/usr/bin/codex"\n'
        'exec codex-hot "$@"\n'
    )
    config_path.write_text(
        f"""version = 1

[settings]
shared_codex_home = "{shared_home}"

[[targets]]
name = "acc1"
codex_home = "{vault}"
"""
    )

    monkeypatch.setattr("codex_hotswap.cli.shutil.which", lambda name: "/usr/bin/codex" if name == "codex" else None)
    monkeypatch.setattr("codex_hotswap.cli.CodexRunner.login_status", lambda self, target: (True, "Logged in using ChatGPT"))
    monkeypatch.setattr(
        "sys.argv",
        [
            "codex-hotswap",
            "doctor",
            "--config-path",
            str(config_path),
            "--state-path",
            str(state_path),
            "--shim-path",
            str(shim_path),
        ],
    )

    assert main() == 1
    output = capsys.readouterr().out
    assert "shim active on PATH: no" in output
    assert "doctor status: issues found" in output


def test_status_reports_invalid_state_file_cleanly(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "config.toml"
    state_path = tmp_path / "state.json"
    config_path.write_text(
        """version = 1

[[targets]]
name = "acc1"
"""
    )
    state_path.write_text("not json\n")

    monkeypatch.setattr(
        "sys.argv",
        [
            "codex-hotswap",
            "status",
            "--config-path",
            str(config_path),
            "--state-path",
            str(state_path),
        ],
    )

    assert main() == 1
    assert "Invalid state file" in capsys.readouterr().err


def test_status_reports_invalid_config_file_cleanly(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("not toml\n")

    monkeypatch.setattr(
        "sys.argv",
        [
            "codex-hotswap",
            "status",
            "--config-path",
            str(config_path),
        ],
    )

    assert main() == 1
    assert "Invalid config file" in capsys.readouterr().err
