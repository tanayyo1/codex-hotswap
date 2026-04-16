# codex-hotswap

Automatically rotate between Codex launch targets when a run hits a rate limit, quota issue, or provider error, then resume the most recent session in the same working directory.

`codex-hotswap` is inspired by the hotswap workflow people use with Claude Code, but it is implemented for the Codex CLI and its actual constraints. The first version focuses on:

- isolated Codex accounts via `CODEX_HOME`
- explicit target rotation
- safe local state
- wrapper-level trigger detection
- `codex resume --last` recovery

It does not depend on private hooks or undocumented transcript formats.

## Status

The project is early, but the architecture is production-oriented:

- Python 3.11+
- minimal dependencies
- unit tests around config, detection, and rotation logic
- interactive wrapper based on a PTY so `codex` still runs in a terminal session

## Install

```bash
pip install .
```

This provides two commands:

- `codex-hotswap` for management commands
- `codex-hot` as the wrapper you use instead of `codex`

## Quick Start

Create a starter config:

```bash
codex-hotswap init
```

Edit the generated file:

```bash
~/.config/codex-hotswap/config.toml
```

Example:

```toml
version = 1

[settings]
max_swaps = 3
swap_delay_seconds = 1.5
default_cooldown_minutes = 240

[[targets]]
name = "primary"
codex_home = "~/.codex-primary"
profile = "default"

[[targets]]
name = "backup"
codex_home = "~/.codex-backup"
profile = "default"
model = "gpt-5.4"
```

Log each account into its own Codex home once:

```bash
CODEX_HOME=~/.codex-primary codex login
CODEX_HOME=~/.codex-backup codex login
```

Run Codex through the wrapper:

```bash
codex-hot
codex-hot "fix the failing tests"
codex-hot --search
```

If a run exits non-zero and matches one of the trigger patterns, `codex-hot` will:

1. mark the current target as exhausted
2. assign it a cooldown window if configured
3. rotate to the next available target
4. wait briefly
5. run `codex ... resume --last`

Because `resume --last` is directory-aware, recovery is scoped to the current working tree.

## Commands

```bash
codex-hotswap init
codex-hotswap status
codex-hotswap list
codex-hotswap current
codex-hotswap use <target>
codex-hotswap next
codex-hotswap exhaust <target> [--reason <text>]
codex-hotswap exhaust <target> [--reason <text>] [--cooldown-minutes <n>]
codex-hotswap reset [target]
codex-hotswap run [codex args...]
```

## Target Model

Each target represents a way to launch `codex`. The current implementation supports:

- `codex_home`
- `profile`
- `model`
- `oss`
- `local_provider`
- `config_overrides`
- `extra_args`

This means you can rotate between:

- different logged-in Codex accounts
- different Codex profiles
- hosted and local OSS providers
- models with different quotas
- custom config overrides

`codex_home` is the account-isolation mechanism. Each target can point at a different Codex home directory with its own login state, config, and local session data.

## Detection

Because Codex does not expose the same stop-hook mechanism as Claude Code, this project detects swap-worthy failures by inspecting the live terminal output from non-zero exits. The default trigger set is intentionally conservative and looks for phrases such as:

- `rate limit`
- `rate_limit`
- `quota`
- `429`
- `capacity`
- `too many requests`

You should treat this as output-driven recovery, not a guarantee that every upstream failure mode can be recognized perfectly.

## Exhaustion Tracking

`codex-hotswap` does not read a real usage counter from Codex. Instead, it tracks local exhaustion state when a target fails with a swap-worthy error.

With `settings.default_cooldown_minutes`, exhausted targets re-enter rotation automatically after the cooldown expires. Without a cooldown, a target stays exhausted until you reset it manually.

## Development

```bash
python -m pytest
```
