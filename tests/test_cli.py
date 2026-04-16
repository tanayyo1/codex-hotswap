from pathlib import Path

from codex_hotswap.cli import main


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
