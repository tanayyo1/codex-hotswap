import os
from pathlib import Path
from types import SimpleNamespace

from codex_hotswap.config import Config, Settings, Target
from codex_hotswap.runner import CodexRunner, InteractiveResult
from codex_hotswap.state import StateStore


def build_runner(tmp_path: Path) -> CodexRunner:
    config = Config(
        path=tmp_path / "config.toml",
        settings=Settings(),
        targets=[Target(name="primary", codex_home="~/.codex-primary", profile="default")],
    )
    return CodexRunner(config=config, state_store=StateStore(tmp_path / "state.json"))


def test_build_command_uses_target_args(tmp_path: Path) -> None:
    runner = build_runner(tmp_path)
    target = runner.config.targets[0]

    assert runner.build_command(target, ["resume", "--last"]) == [
        "codex",
        "--profile",
        "default",
        "resume",
        "--last",
    ]


def test_build_env_includes_codex_home(tmp_path: Path) -> None:
    runner = build_runner(tmp_path)
    target = runner.config.targets[0]

    env = runner.build_env(target)

    assert env["CODEX_HOME"] == os.path.expanduser("~/.codex-primary")
    assert env["PATH"] == os.environ["PATH"]


def test_build_env_creates_codex_home_directory(tmp_path: Path) -> None:
    codex_home = tmp_path / "account-home"
    runner = CodexRunner(
        config=Config(
            path=tmp_path / "config.toml",
            settings=Settings(),
            targets=[Target(name="primary", codex_home=str(codex_home))],
        ),
        state_store=StateStore(tmp_path / "state.json"),
    )

    env = runner.build_env(runner.config.targets[0])

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

    def fake_run_passthrough(target, user_args, announce=False):
        return InteractiveResult(
            output=bytearray(b"usage limit"),
            exit_code=0,
            live_trigger_pattern=r"\brate[_ -]?limit\b",
        )

    monkeypatch.setattr(runner, "_run_passthrough", fake_run_passthrough)

    outcome = runner._invoke(runner.config.targets[0], [])

    assert outcome.triggered is True
    assert outcome.trigger_pattern == r"\brate[_ -]?limit\b"
