import os
from pathlib import Path
from types import SimpleNamespace

from codex_hotswap.config import Config, Settings, Target
from codex_hotswap.runner import CodexRunner, InteractiveResult
from codex_hotswap.state import StateStore


def build_runner(tmp_path: Path) -> CodexRunner:
    config = Config(
        path=tmp_path / "config.toml",
        settings=Settings(shared_codex_home=str(tmp_path / "shared-codex")),
        targets=[Target(name="primary", codex_home="~/.codex-primary", profile="default")],
    )
    return CodexRunner(config=config, state_store=StateStore(tmp_path / "state.json"))


def test_build_command_uses_target_args(tmp_path: Path) -> None:
    runner = build_runner(tmp_path)
    target = runner.config.targets[0]

    command = runner.build_command(target, ["resume", "--last"])

    assert command[1:] == [
        "--profile",
        "default",
        "resume",
        "--last",
    ]
    assert Path(command[0]).name == "codex"


def test_build_runtime_env_uses_shared_codex_home(tmp_path: Path) -> None:
    runner = build_runner(tmp_path)

    env = runner.build_runtime_env()

    assert env["CODEX_HOME"] == str(tmp_path / "shared-codex")
    assert env["PATH"] == os.environ["PATH"]


def test_build_login_env_creates_target_vault_directory(tmp_path: Path) -> None:
    codex_home = tmp_path / "account-home"
    runner = CodexRunner(
        config=Config(
            path=tmp_path / "config.toml",
            settings=Settings(shared_codex_home=str(tmp_path / "shared-codex")),
            targets=[Target(name="primary", codex_home=str(codex_home))],
        ),
        state_store=StateStore(tmp_path / "state.json"),
    )

    env = runner.build_login_env(runner.config.targets[0])

    assert env["CODEX_HOME"] == str(codex_home)
    assert codex_home.is_dir()


def test_login_status_detects_logged_in(monkeypatch, tmp_path: Path) -> None:
    runner = build_runner(tmp_path)

    def fake_run(command, env, capture_output, text):
        return SimpleNamespace(returncode=0, stdout="Logged in using ChatGPT\n", stderr="")

    monkeypatch.setattr("codex_hotswap.runner.subprocess.run", fake_run)

    logged_in, status_text = runner.login_status(runner.config.targets[0])

    assert logged_in is True
    assert "Logged in" in status_text


def test_invoke_returns_triggered_for_live_detection(monkeypatch, tmp_path: Path) -> None:
    runner = build_runner(tmp_path)

    def fake_activate(target):
        return None

    def fake_run_runtime_passthrough(target, user_args, announce=False):
        return InteractiveResult(
            output=bytearray(b"usage limit"),
            exit_code=0,
            live_trigger_pattern=r"\brate[_ -]?limit\b",
        )

    monkeypatch.setattr(runner.auth_manager, "activate", fake_activate)
    monkeypatch.setattr(runner, "_run_runtime_passthrough", fake_run_runtime_passthrough)

    outcome = runner._invoke(runner.config.targets[0], [])

    assert outcome.triggered is True
    assert outcome.trigger_pattern == r"\brate[_ -]?limit\b"


def test_login_status_handles_missing_codex_binary(monkeypatch, tmp_path: Path) -> None:
    runner = build_runner(tmp_path)

    def fake_run(command, env, capture_output, text):
        raise FileNotFoundError

    monkeypatch.setattr("codex_hotswap.runner.subprocess.run", fake_run)

    logged_in, status_text = runner.login_status(runner.config.targets[0])

    assert logged_in is False
    assert "not found" in status_text


def test_signal_helpers_ignore_missing_process(tmp_path: Path) -> None:
    runner = build_runner(tmp_path)

    assert runner._signal_process(999999, 2) is False
    assert runner._signal_process_group(999999, 2) is False


def test_invoke_activates_target_before_runtime_run(monkeypatch, tmp_path: Path) -> None:
    runner = build_runner(tmp_path)
    activated = []

    def fake_activate(target):
        activated.append(target.name)
        return None

    def fake_run_runtime_passthrough(target, user_args, announce=False):
        return InteractiveResult(output=bytearray(b"ok"), exit_code=0)

    monkeypatch.setattr(runner.auth_manager, "activate", fake_activate)
    monkeypatch.setattr(runner, "_run_runtime_passthrough", fake_run_runtime_passthrough)

    outcome = runner._invoke(runner.config.targets[0], [])

    assert activated == ["primary"]
    assert outcome.triggered is False


def test_codex_binary_peels_back_to_real_binary_from_shim(tmp_path: Path, monkeypatch) -> None:
    shim = tmp_path / "codex"
    real = tmp_path / "real-codex"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        "# codex-hotswap shim\n"
        f'export CODEX_HOTSWAP_REAL_BIN="{real}"\n'
        'exec codex-hot "$@"\n'
    )

    runner = build_runner(tmp_path)
    monkeypatch.setattr("codex_hotswap.runner.shutil.which", lambda name: str(shim) if name == "codex" else None)

    assert runner.codex_binary() == str(real)


def test_run_returns_error_when_shared_home_lock_is_busy(monkeypatch, tmp_path: Path, capsys) -> None:
    runner = build_runner(tmp_path)
    lock = runner.runtime_lock_path()
    lock.parent.mkdir(parents=True, exist_ok=True)
    handle = lock.open("a+", encoding="utf-8")

    try:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        exit_code = runner.run([])
    finally:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()

    assert exit_code == 1
    assert "another codex-hotswap session is already using the shared CODEX_HOME" in capsys.readouterr().out
