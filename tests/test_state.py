from pathlib import Path

from codex_hotswap.config import Config, Settings, Target
from codex_hotswap.state import StateStore


def build_config() -> Config:
    return Config(
        path=Path("/tmp/config.toml"),
        settings=Settings(),
        targets=[
            Target(name="primary"),
            Target(name="backup"),
            Target(name="disabled", active=False),
        ],
    )


def test_next_available_target_skips_exhausted_and_inactive(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    config = build_config()
    state = store.load()
    store.ensure_current_target(config, state)
    store.mark_exhausted(state, "primary", "rate limit")

    assert store.next_available_target(config, state) == "backup"


def test_reset_clears_exhaustion(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    config = build_config()
    state = store.load()
    store.ensure_current_target(config, state)
    store.mark_exhausted(state, "primary", "rate limit")
    store.reset(state, "primary")

    assert store.next_available_target(config, state) == "backup"


def test_ensure_runnable_target_skips_exhausted_current(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    config = build_config()
    state = store.load()
    store.ensure_current_target(config, state)
    store.mark_exhausted(state, "primary", "rate limit")

    assert store.ensure_runnable_target(config, state) == "backup"
