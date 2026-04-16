# codex-hotswap

Automatically rotate between Codex launch targets when a run hits a rate limit, quota issue, or provider error, then resume the most recent session in the same working directory.

`codex-hotswap` is inspired by the hotswap workflow people use with Claude Code, but it is implemented for the Codex CLI and its actual constraints. The first version focuses on:

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

[[targets]]
name = "primary"
profile = "default"

[[targets]]
name = "backup"
profile = "work"
model = "gpt-5.4"
```

Run Codex through the wrapper:

```bash
codex-hot
codex-hot "fix the failing tests"
codex-hot --search
```

If a run exits non-zero and matches one of the trigger patterns, `codex-hot` will:

1. mark the current target as exhausted
2. rotate to the next available target
3. wait briefly
4. run `codex ... resume --last`

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
codex-hotswap reset [target]
codex-hotswap run [codex args...]
```

## Target Model

Each target represents a way to launch `codex`. The current implementation supports:

- `profile`
- `model`
- `oss`
- `local_provider`
- `config_overrides`
- `extra_args`

This means you can rotate between:

- different Codex profiles
- hosted and local OSS providers
- models with different quotas
- custom config overrides

## Detection

Because Codex does not expose the same stop-hook mechanism as Claude Code, this project detects swap-worthy failures by inspecting the live terminal output from non-zero exits. The default trigger set is intentionally conservative and looks for phrases such as:

- `rate limit`
- `rate_limit`
- `quota`
- `429`
- `capacity`
- `too many requests`

You should treat this as output-driven recovery, not a guarantee that every upstream failure mode can be recognized perfectly.

## Development

```bash
python -m pytest
```
