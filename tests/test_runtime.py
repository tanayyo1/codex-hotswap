from pathlib import Path

from codex_hotswap.auth import AuthManager
from codex_hotswap.config import Config, Settings, Target
from codex_hotswap.runtime import RuntimeHome


def test_runtime_home_links_shared_store_and_keeps_private_auth(tmp_path: Path) -> None:
    shared_home = tmp_path / "shared"
    shared_home.mkdir()
    (shared_home / "history.jsonl").write_text('{"session_id":"abc"}\n')
    (shared_home / "session_index.jsonl").write_text('{"id":"abc"}\n')
    (shared_home / "sessions").mkdir()
    (shared_home / "shell_snapshots").mkdir()

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "auth.json").write_text('{"account":"primary"}\n')

    config = Config(
        path=tmp_path / "config.toml",
        settings=Settings(shared_codex_home=str(shared_home)),
        targets=[Target(name="primary", codex_home=str(vault))],
    )

    with RuntimeHome(config=config, auth_manager=AuthManager(config)) as runtime:
        assert runtime.path is not None
        assert (runtime.path / "history.jsonl").is_symlink()
        assert (runtime.path / "sessions").is_symlink()

        runtime.activate(config.targets[0])

        runtime_auth = runtime.path / "auth.json"
        assert runtime_auth.exists()
        assert not runtime_auth.is_symlink()
        assert runtime_auth.read_text() == '{"account":"primary"}\n'
        assert not (shared_home / "auth.json").exists()


def test_runtime_home_syncs_new_local_entries_back_to_shared_home(tmp_path: Path) -> None:
    shared_home = tmp_path / "shared"
    shared_home.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "auth.json").write_text("{}\n")
    config = Config(
        path=tmp_path / "config.toml",
        settings=Settings(shared_codex_home=str(shared_home)),
        targets=[Target(name="primary", codex_home=str(vault))],
    )

    with RuntimeHome(config=config, auth_manager=AuthManager(config)) as runtime:
        assert runtime.path is not None
        (runtime.path / "state_5.sqlite").write_text("sqlite-data")

    assert (shared_home / "state_5.sqlite").read_text() == "sqlite-data"


def test_multiple_runtime_homes_can_activate_different_accounts(tmp_path: Path) -> None:
    shared_home = tmp_path / "shared"
    shared_home.mkdir()
    (shared_home / "history.jsonl").write_text("")
    (shared_home / "session_index.jsonl").write_text("")

    vault_one = tmp_path / "vault-one"
    vault_one.mkdir()
    (vault_one / "auth.json").write_text('{"account":"one"}\n')
    vault_two = tmp_path / "vault-two"
    vault_two.mkdir()
    (vault_two / "auth.json").write_text('{"account":"two"}\n')

    config = Config(
        path=tmp_path / "config.toml",
        settings=Settings(shared_codex_home=str(shared_home)),
        targets=[
            Target(name="one", codex_home=str(vault_one)),
            Target(name="two", codex_home=str(vault_two)),
        ],
    )
    manager = AuthManager(config)

    with RuntimeHome(config=config, auth_manager=manager) as runtime_one, RuntimeHome(config=config, auth_manager=manager) as runtime_two:
        runtime_one.activate(config.get_target("one"))
        runtime_two.activate(config.get_target("two"))

        assert runtime_one.path is not None
        assert runtime_two.path is not None
        assert runtime_one.path != runtime_two.path
        assert (runtime_one.path / "auth.json").read_text() == '{"account":"one"}\n'
        assert (runtime_two.path / "auth.json").read_text() == '{"account":"two"}\n'
        assert (runtime_one.path / "history.jsonl").resolve() == (runtime_two.path / "history.jsonl").resolve()
