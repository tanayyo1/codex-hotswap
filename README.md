# codex-hotswap

[![CI](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml/badge.svg)](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml)
[![version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/tanayyo1/codex-hotswap)

Use multiple Codex accounts in the terminal and automatically switch to the next one when the current one hits a limit or similar failure.

## In One Sentence

`codex-hotswap` lets you log in to several Codex accounts once, then use `codex-hot` instead of `codex` so it can automatically move to the next account and run `codex resume --last` when needed.

## What Problem This Solves

Without this tool:

1. you are using Codex in the terminal
2. one account hits a limit or provider failure
3. your work stops
4. you manually switch accounts
5. you try to resume manually

With this tool:

1. you log each Codex account into its own separate folder once
2. you run `codex-hot`
3. if the current account fails with a matched limit/quota/provider error
4. `codex-hotswap` switches to the next configured account
5. it runs `codex resume --last`

## The Core Idea

Each Codex account is stored in its own separate `CODEX_HOME`.

Example:

- account 1 -> `~/.codex-acc1`
- account 2 -> `~/.codex-acc2`
- account 3 -> `~/.codex-acc3`
- account 4 -> `~/.codex-acc4`

That means each account keeps its own:

- login state
- config
- local Codex state

This tool does not copy tokens between accounts.

It simply launches Codex with a different `CODEX_HOME` when it needs to switch.

## If You Just Want The Commands

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

After that, use `codex-hot` instead of `codex`.

## Install

### Best Option: `pipx`

Install globally with `pipx`:

```bash
pipx install git+https://github.com/tanayyo1/codex-hotswap.git
```

This gives you two commands:

- `codex-hotswap`
- `codex-hot`

### If `pipx` Is Not Installed

If you see:

```bash
Command 'pipx' not found
```

On Ubuntu or Debian, run:

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Then restart your shell and install:

```bash
pipx install git+https://github.com/tanayyo1/codex-hotswap.git
```

### Local Development Install

If you are working from a clone of this repo:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## Easiest Setup For Most Users

### Option A: Named Accounts

If you want names like `main`, `work`, `backup`, `extra`:

```bash
codex-hotswap setup --force --accounts main,work,backup,extra
```

This creates:

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

Pick your first account:

```bash
codex-hotswap use main
```

Start working:

```bash
codex-hot
```

### Option B: Numbered Accounts

If you just want 4 simple accounts:

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

## What `login` Actually Does

This:

```bash
codex-hotswap login acc2
```

is basically:

```bash
CODEX_HOME=~/.codex-acc2 codex login
```

So each account gets logged into its own isolated Codex home.

You only need to do this once per account unless the login expires or you want to re-authenticate.

If a target is already logged in, `codex-hotswap login <target>` now detects that and skips reopening the login flow.

## What `codex-hot` Actually Does

When you run:

```bash
codex-hot
```

it does this:

1. launches Codex using your current target
2. watches the terminal output
3. if Codex exits with a matched limit/quota/provider-style failure
4. marks that target exhausted
5. switches to the next available target
6. runs `codex resume --last`

Example flow:

- try `acc1`
- `acc1` hits limit
- switch to `acc2`
- run `codex resume --last`
- if needed later, move to `acc3`
- then `acc4`

## Normal Daily Use

After setup, your normal workflow should be:

```bash
cd /your/project
codex-hot
```

Or:

```bash
codex-hot "fix the failing tests"
codex-hot --search
```

Use `codex-hot` instead of raw `codex` if you want auto-switching.

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

or:

```bash
codex-hotswap init
```

### `login` did not finish for an account

Just rerun the login for that target:

```bash
codex-hotswap login acc3
```

### It is not switching automatically

Possible reasons:

- you ran `codex` instead of `codex-hot`
- the account was never logged in
- Codex changed its output and the failure was not matched
- all configured targets are exhausted

Check:

```bash
codex-hotswap status
```

### Resume did not continue where expected

`codex-hotswap` uses:

```bash
codex resume --last
```

So resume behavior depends on how Codex itself handles the latest session in that directory.

Run `codex-hot` from the same project directory where you want resume to work.

## What The Tool Guarantees, And What It Does Not

What it does well:

- isolate multiple Codex accounts with separate `CODEX_HOME`
- automate fallback to the next configured target
- keep the workflow terminal-native
- resume with `codex resume --last`

What it does not guarantee:

- perfect detection of every possible upstream failure
- a real usage meter from Codex
- perfect resume behavior if Codex changes internal behavior

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
