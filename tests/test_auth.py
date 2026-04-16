from pathlib import Path
import json

from codex_hotswap.auth import ACTIVE_TARGET_METADATA, AuthManager
from codex_hotswap.config import Config, Settings, Target


def test_auth_manager_activates_target_auth_into_shared_home(tmp_path: Path) -> None:
    shared_home = tmp_path / "shared"
    vault_home = tmp_path / "vault"
    vault_home.mkdir()
    (vault_home / "auth.json").write_text('{"tokens": {"account_id": "abc"}}')

    config = Config(
        path=tmp_path / "config.toml",
        settings=Settings(shared_codex_home=str(shared_home)),
        targets=[Target(name="primary", codex_home=str(vault_home))],
    )

    manager = AuthManager(config)
    destination = manager.activate(config.targets[0])

    assert destination == shared_home / "auth.json"
    assert destination.read_text() == '{"tokens": {"account_id": "abc"}}'
    metadata = json.loads((shared_home / ACTIVE_TARGET_METADATA).read_text())
    assert metadata["target"] == "primary"
    assert metadata["auth_vault"] == str(vault_home)
    assert metadata["copied_files"] == ["auth.json"]
