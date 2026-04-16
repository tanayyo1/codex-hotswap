# codex-hotswap

[![CI](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml/badge.svg)](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml)
[![version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/tanayyo1/codex-hotswap)

Use multiple Codex accounts in the terminal without breaking your normal repo history or `/resume` flow.

## What It Does

`codex-hotswap` keeps one shared Codex home for normal work and `/resume`, then swaps the active account auth underneath when a limit hits.

That means:

- your chats stay organized per repo
- `/resume` still shows the right sessions for the current directory
- each account only needs to be logged in once
- when one account hits a limit, it rotates to the next configured account

## The Mental Model

There are two kinds of storage:

- shared Codex home: `~/.codex`
- per-account auth vaults: `~/.codex-acc1`, `~/.codex-acc2`, and so on

The shared home holds the session/history data that makes `/resume` work normally.

The per-account vaults hold only the auth data for each account.

When `codex-hot` starts, it copies the chosen account's auth into the shared home, then launches Codex as usual.

When a matched usage-limit or rate-limit failure appears, it copies the next account's auth into the shared home and resumes.

If you used an older per-account-only version of this tool, those old session stores stay in the vaults; the new shared-home flow uses `~/.codex` going forward.

## Quick Start

For four accounts named `acc1`, `acc2`, `acc3`, `acc4`:

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

After that, keep working in your repo the normal way:

```bash
cd ~/tonr
codex-hot
```

## Install

Recommended:

```bash
pipx install git+https://github.com/tanayyo1/codex-hotswap.git
```

This installs:

- `codex-hotswap`
- `codex-hot`

If `pipx` is missing on Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Restart your shell after `pipx ensurepath`, then install again.

### Optional: Make `codex` Go Through Hotswap

If you want plain `codex` to route through `codex-hotswap` automatically:

```bash
codex-hotswap install-shim
```

That installs a small shim at `~/.local/bin/codex` so normal terminal usage keeps working, but account failover still happens underneath.

## Setup

### Named Accounts

```bash
codex-hotswap setup --force --accounts main,work,backup,extra
```

This creates auth vaults like:

- `main` -> `~/.codex-main`
- `work` -> `~/.codex-work`
- `backup` -> `~/.codex-backup`
- `extra` -> `~/.codex-extra`

Then log in once to each one:

```bash
codex-hotswap login main
codex-hotswap login work
codex-hotswap login backup
codex-hotswap login extra
```

### Numbered Accounts

```bash
codex-hotswap setup --force --count 4 --prefix acc
```

This creates:

- `acc1` -> `~/.codex-acc1`
- `acc2` -> `~/.codex-acc2`
- `acc3` -> `~/.codex-acc3`
- `acc4` -> `~/.codex-acc4`

Then log in once to each account:

```bash
codex-hotswap login acc1
codex-hotswap login acc2
codex-hotswap login acc3
codex-hotswap login acc4
```

If you rerun `setup` with the same names, the generated targets are updated instead of failing on duplicates.

## Daily Use

Pick the account you want to start on:

```bash
codex-hotswap use acc1
```

Then work normally:

```bash
codex-hot
```

If you installed the shim, you can type `codex` instead.

Examples:

```bash
codex-hot "fix the failing tests"
codex-hot --search
```

## What `login` Does

```bash
codex-hotswap login acc2
```

is effectively:

```bash
CODEX_HOME=~/.codex-acc2 codex login
```

That stores the auth for `acc2` in its own vault.

If the target is already logged in, `codex-hotswap login <target>` skips the browser flow unless you pass `--relogin`.

## What `codex-hot` Does

When you run `codex-hot`:

1. the selected account auth is copied into the shared `~/.codex`
2. Codex launches normally in the current repo
3. if a matched usage-limit or rate-limit style failure appears, that account is marked exhausted
4. the wrapper rotates to the next configured account
5. the next account auth is copied into the shared home
6. `codex resume --last` is attempted

## Useful Commands

```bash
codex-hotswap status
codex-hotswap list
codex-hotswap current
codex-hotswap use <target>
codex-hotswap next
codex-hotswap install-shim
codex-hotswap uninstall-shim
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

Restart your shell and install again.

### `codex-hotswap: Config file not found`

Create a config first:

```bash
codex-hotswap setup --force --count 4 --prefix acc
```

or:

```bash
codex-hotswap init
```

### Login did not finish

Rerun the login:

```bash
codex-hotswap login acc3
```

### It is not switching automatically

Check:

- you are using `codex-hot`
- each account was logged in successfully
- the account order is correct in `codex-hotswap status`
- not all accounts are already exhausted

The live detector is conservative on purpose. If Codex changes its failure banner, the detector may need an update before it swaps automatically.

### Resume did not continue where expected

`codex-hotswap` uses:

```bash
codex resume --last
```

So resume behavior still depends on Codex itself.

Run `codex-hot` from the repo where you want `/resume` to keep working.

## Guarantees And Limits

What it does well:

- keeps repo/session history in a shared Codex home
- isolates multiple account logins
- swaps account auth without changing your workspace
- resumes with `codex resume --last`

What it does not guarantee:

- perfect detection of every future failure message
- a real usage meter from Codex
- perfect resume behavior if Codex changes its session internals

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

GitHub Actions checks:

- tests on Python `3.11`, `3.12`, and `3.13`
- package build
