import os
from pathlib import Path

from codex_hotswap.config import Config, Settings, Target
from codex_hotswap.runner import CodexRunner
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

    assert env["CODEX_HOME"] == "~/.codex-primary"
    assert env["PATH"] == os.environ["PATH"]
