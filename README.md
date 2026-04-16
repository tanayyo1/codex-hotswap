# codex-hotswap

Automatically rotate between Codex launch targets when a run hits a rate limit, quota issue, or provider error, then resume the most recent session in the same working directory.

`codex-hotswap` is for people who use Codex in the terminal and do not want to stop working every time one account, profile, or provider hits a limit.

## What This Does

You configure multiple Codex targets, for example:

- one Codex account in `~/.codex-main`
- another Codex account in `~/.codex-work`
- an optional local OSS fallback

Then you run:

```bash
codex-hot
```

If the current target fails with a matched rate-limit, quota, or provider-style error, `codex-hotswap` will:

1. mark that target exhausted
2. optionally put it on cooldown
3. switch to the next available target
4. run `codex resume --last`

So the core value is simple:

`keep Codex work moving in the terminal without manual account switching.`

## Who This Is For

This is mainly for terminal Codex users who have one or more of:

- multiple paid Codex accounts
- multiple Codex profiles
- different model/provider setups
- a hosted setup plus a local OSS fallback

## How It Works

A `target` is one way to launch Codex.

A target can include:

- `codex_home` for isolated login state
- `profile`
- `model`
- `oss`
- `local_provider`
- extra config overrides and args

The most important piece for multi-account setups is `codex_home`.

Each target can point to a different `CODEX_HOME`, which means each target can keep its own:

- login state
- config
- local Codex session data

That is how `codex-hotswap` supports separate logged-in accounts cleanly.

## Install

```bash
pip install .
```

This provides:

- `codex-hotswap` for setup and management
- `codex-hot` as the wrapper you run instead of `codex`

## Quick Start

### 1. Create a config

```bash
codex-hotswap init
```

This writes:

```bash
~/.config/codex-hotswap/config.toml
```

### 2. Edit the config

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
note = "Main Codex account"

[[targets]]
name = "backup"
codex_home = "~/.codex-backup"
profile = "default"
note = "Backup Codex account"
```

### 3. Log into each target once

```bash
codex-hotswap login primary
codex-hotswap login backup
```

You can also pass extra login flags through:

```bash
codex-hotswap login backup -- --device-auth
```

### 4. Start using the wrapper

```bash
codex-hot
codex-hot "fix the failing tests"
codex-hot --search
```

### 5. Let it rotate when needed

If a run exits non-zero and matches a swap-worthy trigger, `codex-hot` will:

1. mark the current target exhausted
2. apply cooldown if configured
3. rotate to the next available target
4. resume with `codex resume --last`

Because `resume --last` is directory-aware, recovery stays scoped to the current working tree.

## Example Multi-Account Setup

```toml
version = 1

[settings]
max_swaps = 3
swap_delay_seconds = 2
default_cooldown_minutes = 240

[[targets]]
name = "main"
codex_home = "~/.codex-main"
profile = "default"
note = "Main account"

[[targets]]
name = "work"
codex_home = "~/.codex-work"
profile = "default"
note = "Second paid account"

[[targets]]
name = "oss"
profile = "local"
oss = true
local_provider = "ollama"
active = false
note = "Optional local fallback"
```

Setup flow:

```bash
codex-hotswap login main
codex-hotswap login work
codex-hotswap use main
codex-hot
```

## Commands

```bash
codex-hotswap init
codex-hotswap login <target> [-- <codex login args...>]
codex-hotswap status
codex-hotswap list
codex-hotswap current
codex-hotswap use <target>
codex-hotswap next
codex-hotswap exhaust <target> [--reason <text>] [--cooldown-minutes <n>]
codex-hotswap reset [target]
codex-hotswap run [codex args...]
```

## Detection

Codex does not expose the same stop-hook mechanism Claude Code does, so `codex-hotswap` currently detects swap-worthy failures by inspecting live terminal output from non-zero exits.

The default trigger set looks for phrases like:

- `rate limit`
- `rate_limit`
- `quota`
- `429`
- `capacity`
- `too many requests`
- `provider error`
- `model unavailable`

This is useful and practical, but it is not a perfect upstream signal.

## Exhaustion Tracking

`codex-hotswap` does not currently read a real usage counter from Codex.

Instead, it keeps local target state:

- which target is current
- which targets are exhausted
- when an exhausted target should become available again

With `settings.default_cooldown_minutes`, exhausted targets re-enter rotation automatically after their cooldown expires. Without a cooldown, a target stays exhausted until you reset it manually.

## Current Boundaries

What this tool does well:

- isolate multiple Codex accounts with separate `CODEX_HOME` values
- automate fallback to the next configured target
- keep the workflow terminal-native
- resume with `codex resume --last`

What it does not guarantee:

- perfect detection of every failure mode
- a real usage meter from Codex
- perfect resume behavior if Codex changes internals
- magic recovery outside the normal Codex resume model

## Development

```bash
python -m pytest
```
