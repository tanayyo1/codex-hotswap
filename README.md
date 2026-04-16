# codex-hotswap

[![CI](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml/badge.svg)](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml)
[![version](https://img.shields.io/badge/version-0.1.4-blue.svg)](https://github.com/tanayyo1/codex-hotswap)

Run Codex in the terminal with multiple accounts and automatically switch to the next configured account when the current one hits a matched usage-limit or rate-limit style failure.

## What This Is

`codex-hotswap` is a wrapper around the `codex` CLI.

Instead of running:

```bash
codex
```

you run:

```bash
codex-hot
```

The wrapper starts Codex with your current account target, watches for matched limit failures, marks that target exhausted, rotates to the next available target, and runs:

```bash
codex resume --last
```

## Why This Exists

Without this tool, the usual flow looks like this:

1. you are working in Codex
2. one account hits a usage limit
3. your session stops being useful
4. you manually change accounts
5. you manually try to resume

With `codex-hotswap`:

1. each account is logged into its own separate `CODEX_HOME`
2. you use `codex-hot`
3. when the current target hits a matched failure, the wrapper rotates automatically
4. the wrapper attempts `codex resume --last` on the next target

## The Core Idea

Each Codex account lives in its own isolated folder.

Example:

- `acc1` -> `~/.codex-acc1`
- `acc2` -> `~/.codex-acc2`
- `acc3` -> `~/.codex-acc3`
- `acc4` -> `~/.codex-acc4`

Each folder keeps that account's own:

- login state
- config
- local Codex state
- session history managed by Codex

`codex-hotswap` does not copy tokens between accounts.

It simply launches `codex` with a different `CODEX_HOME`.

## 5-Minute Setup

If you want 4 accounts named `acc1`, `acc2`, `acc3`, `acc4`:

```bash
pipx install git+https://github.com/tanayyo1/codex-hotswap.git
codex-hotswap setup --force --count 4 --prefix acc
codex-hotswap login acc1
codex-hotswap login acc2
codex-hotswap login acc3
codex-hotswap login acc4
codex-hotswap use acc1
codex-hot
```

After setup, your normal workflow is just:

```bash
codex-hot
```

## Install

### Recommended: `pipx`

Install globally:

```bash
pipx install git+https://github.com/tanayyo1/codex-hotswap.git
```

This gives you:

- `codex-hotswap`
- `codex-hot`

### If `pipx` Is Missing

If your shell says:

```bash
Command 'pipx' not found
```

On Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Then restart your shell and install:

```bash
pipx install git+https://github.com/tanayyo1/codex-hotswap.git
```

### Local Dev Install

If you are working from a local clone:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## Setup Options

### Option A: Named Accounts

If you want readable names:

```bash
codex-hotswap setup --force --accounts main,work,backup,extra
```

This creates:

- `main` -> `~/.codex-main`
- `work` -> `~/.codex-work`
- `backup` -> `~/.codex-backup`
- `extra` -> `~/.codex-extra`

Then log in once:

```bash
codex-hotswap login main
codex-hotswap login work
codex-hotswap login backup
codex-hotswap login extra
codex-hotswap use main
codex-hot
```

### Option B: Numbered Accounts

If you just want `acc1`, `acc2`, `acc3`, `acc4`:

```bash
codex-hotswap setup --force --count 4 --prefix acc
```

This creates:

- `acc1` -> `~/.codex-acc1`
- `acc2` -> `~/.codex-acc2`
- `acc3` -> `~/.codex-acc3`
- `acc4` -> `~/.codex-acc4`

Then:

```bash
codex-hotswap login acc1
codex-hotswap login acc2
codex-hotswap login acc3
codex-hotswap login acc4
codex-hotswap use acc1
codex-hot
```

If you rerun `setup` later with the same names, `codex-hotswap` updates those generated targets instead of failing on duplicate names.

## What `login` Does

This command:

```bash
codex-hotswap login acc2
```

is effectively:

```bash
CODEX_HOME=~/.codex-acc2 codex login
```

So each account is authenticated into its own isolated Codex home.

You usually do this once per account. If the target is already logged in, `codex-hotswap login <target>` skips reopening the login flow.

If you want to force a fresh login:

```bash
codex-hotswap login acc2 --relogin
```

## What `codex-hot` Does

When you run:

```bash
codex-hot
```

the wrapper:

1. launches Codex using the current target
2. watches the live terminal session
3. if it sees a matched usage-limit or rate-limit style failure, it marks that target exhausted
4. switches to the next available target
5. runs `codex resume --last`

Simple example:

- start on `acc1`
- `acc1` hits a usage limit
- rotate to `acc2`
- run `codex resume --last`
- later rotate to `acc3` if needed

## Normal Use

After setup, use `codex-hot` instead of raw `codex` whenever you want automatic account rotation.

Examples:

```bash
cd /your/project
codex-hot
```

```bash
codex-hot "fix the failing tests"
```

```bash
codex-hot --search
```

## Useful Commands

```bash
codex-hotswap status
codex-hotswap list
codex-hotswap current
codex-hotswap use <target>
codex-hotswap next
codex-hotswap reset
codex-hotswap reset <target>
codex-hotswap exhaust <target> --reason manual --cooldown-minutes 120
```

## Troubleshooting

### `pipx: command not found`

On Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Restart your shell after `pipx ensurepath`.

### `codex-hotswap: Config file not found`

Run setup first:

```bash
codex-hotswap setup --force --count 4 --prefix acc
```

or create a starter config:

```bash
codex-hotswap init
```

### Login did not finish

Just rerun login for that target:

```bash
codex-hotswap login acc3
```

### It is not switching automatically

Check these first:

- you ran `codex-hot`, not plain `codex`
- each target was logged in successfully
- the target order looks right in `codex-hotswap status`
- not all targets are already exhausted

Check current state:

```bash
codex-hotswap status
```

The live detector is intentionally conservative. It is designed to avoid rotating accounts because of random text in the chat, so a brand-new upstream failure banner may need a detector update before it swaps automatically.

### Resume did not continue where expected

`codex-hotswap` uses:

```bash
codex resume --last
```

So resume behavior still depends on Codex itself.

Run `codex-hot` from the same project directory where you want resume to continue.

## Guarantees And Limits

What it does well:

- isolates multiple Codex accounts with separate `CODEX_HOME`
- automates fallback to the next configured target
- stays terminal-native
- resumes with `codex resume --last`

What it does not guarantee:

- perfect detection of every future upstream failure message
- a real usage meter from Codex
- perfect resume behavior if Codex changes session behavior

## Commands

```bash
codex-hotswap init
codex-hotswap setup --force --accounts main,work,backup
codex-hotswap setup --force --count 4 --prefix acc
codex-hotswap login <target> [-- <codex login args...>]
codex-hotswap add-target <name> [options]
codex-hotswap remove-target <target>
codex-hotswap status
codex-hotswap list
codex-hotswap current
codex-hotswap use <target>
codex-hotswap next
codex-hotswap exhaust <target> [--reason <text>] [--cooldown-minutes <n>]
codex-hotswap reset [target]
codex-hotswap run [codex args...]
```

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest
python -m build
```

## CI

GitHub Actions currently checks:

- tests on Python `3.11`, `3.12`, and `3.13`
- package build
