# codex-hotswap

[![CI](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml/badge.svg)](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml)
[![version](https://img.shields.io/badge/version-0.2.5-blue.svg)](https://github.com/tanayyo1/codex-hotswap)

`codex-hotswap` lets you keep using Codex in the terminal with your normal repo history and `/resume`, while automatically swapping to another logged-in account when the current one hits a limit.

Current platform status:

- Linux: supported
- macOS: expected to work, but less field-tested
- Windows native: not supported yet
- Windows users should use WSL for now

## In One Sentence

If one Codex account runs out of usage, `codex-hotswap` automatically switches to another account you already logged in, so you can keep working in the same repo.

## Who This Is For

This tool is for people who:

- use Codex in the terminal a lot
- have more than one Codex account available
- do not want to manually log out, log back in, and recover the session every time one account hits limits

## Why This Exists

Heavy Codex users hit an annoying problem:

- you are deep in a repo
- your current account hits a usage limit
- you stop working
- you manually switch accounts
- you try to recover the session

`codex-hotswap` turns that into:

- log each account in once
- keep one shared `~/.codex` for normal history and `/resume`
- swap only the active auth when a limit banner appears
- continue with `codex resume --last`

## Start Here

If `pipx` is not installed on Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Restart your shell after `pipx ensurepath`.

Then run this:

```bash
pipx install git+https://github.com/tanayyo1/codex-hotswap.git
codex-hotswap setup --force --count 4 --prefix acc --login --install-shim
codex-hotswap use acc1
codex
```

That is the shortest real setup path.

What happens:

- installs the tool
- creates 4 account slots: `acc1`, `acc2`, `acc3`, `acc4`
- asks you to log in to each account
- makes normal `codex` go through `codex-hotswap`

After setup, daily use is just:

```bash
cd ~/your-repo
codex
```

## Super Simple Explanation

Think of it like this:

- your chats and repo history stay in one normal Codex home
- each account login is saved separately
- when one account is exhausted, this tool swaps to the next saved account

You keep using Codex in the same repo. The account changes underneath.

## How It Works

There are two storage layers:

- shared runtime home: `~/.codex`
- per-account auth vaults: `~/.codex-acc1`, `~/.codex-acc2`, and so on

The shared home keeps the normal Codex session history, so `/resume` stays organized by repo the same way Codex already does.

Each auth vault stores a separate account login. When `codex-hotswap` launches Codex, it copies the selected account's `auth.json` into the shared home first, then runs Codex normally in your current directory.

If Codex emits a matched usage-limit or rate-limit failure, `codex-hotswap`:

1. marks that account exhausted
2. activates the next account's auth
3. runs `codex resume --last`

What you should see in practice:

- the repo and session stay the same
- the `Account:` line in Codex changes to the next logged-in account
- work continues in the same repo/thread unless the next account is also exhausted

## What You Actually Do Every Day

After setup, most people only need this:

```bash
cd ~/your-repo
codex
```

That is the whole point of the project.

## Install

Recommended:

```bash
pipx install git+https://github.com/tanayyo1/codex-hotswap.git
```

If `pipx` is missing on Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Restart your shell after `pipx ensurepath`, then install again.

Installed commands:

- `codex-hotswap`
- `codex-hot`

## If You Are Not Technical

Here is the simplest way to think about the commands:

- `codex-hotswap setup ...` = prepare multiple accounts
- `codex-hotswap login acc1` = log in one account
- `codex-hotswap use acc1` = choose which account to start with
- `codex` = use Codex normally after setup
- `codex-hotswap doctor` = check if everything is set up correctly
- `codex-hotswap reset` = clear “account exhausted” markers

## Setup

### Default Setup

```bash
codex-hotswap setup --force --count 4 --prefix acc --login --install-shim
```

This creates:

- `acc1` -> `~/.codex-acc1`
- `acc2` -> `~/.codex-acc2`
- `acc3` -> `~/.codex-acc3`
- `acc4` -> `~/.codex-acc4`

If you want named accounts instead:

```bash
codex-hotswap setup --force --accounts main,work,backup,extra --login --install-shim
```

For headless or remote login flows:

```bash
codex-hotswap setup --force --count 4 --prefix acc --login --device-auth --install-shim
```

If you rerun `setup` with the same names, the generated targets are updated instead of failing on duplicates.

Each account login is still interactive. The setup command walks you through them in sequence.

### What `login` Does

```bash
codex-hotswap login acc2
```

is effectively:

```bash
CODEX_HOME=~/.codex-acc2 codex login
```

If a target already appears logged in, `codex-hotswap login <target>` skips the browser flow unless you pass `--relogin`.

## Daily Use

Pick the account you want to start on once:

```bash
codex-hotswap use acc1
```

Then work normally:

```bash
cd ~/tonr
codex
```

If you did not install the shim, use:

```bash
codex-hot
```

Examples:

```bash
codex "fix the failing tests"
codex-hot --search
```

### What A Real Swap Looks Like

When a swap works, the important signal is not a new repo or a new `/resume` list.

The important signal is:

- same repo directory
- same Codex session or thread
- different logged-in account underneath

If account `acc1` hits a limit and `acc2` is available, a normal swap should feel like:

1. Codex hits a usage-limit banner
2. `codex-hotswap` rotates to the next target
3. `codex resume --last` runs
4. the session continues, but the `Account:` line now shows the next account

## Example Real-Life Flow

Example:

1. you are working in `~/tonr`
2. you run `codex`
3. Codex shows account `acc1`
4. `acc1` hits its limit
5. `codex-hotswap` switches to `acc2`
6. Codex continues in the same repo

What should stay the same:

- repo directory
- normal `/resume` behavior
- your general session flow

What changes:

- the logged-in account

## The `codex` Shim

The shim is a tiny script placed at `~/.local/bin/codex`.

Its only job is to make this:

```bash
codex
```

run through `codex-hotswap` automatically.

Install it:

```bash
codex-hotswap install-shim
```

Remove it:

```bash
codex-hotswap uninstall-shim
```

If `codex-hotswap doctor` says the shim is installed but not active on `PATH`, your shell is still finding some other `codex` binary first.

## Useful Commands

```bash
codex-hotswap doctor
codex-hotswap status
codex-hotswap list
codex-hotswap current
codex-hotswap use <target>
codex-hotswap next
codex-hotswap login <target>
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

Restart your shell, then install again.

### `codex-hotswap: Config file not found`

Create it first:

```bash
codex-hotswap setup --force --count 4 --prefix acc
```

or:

```bash
codex-hotswap init
```

### Check Everything

```bash
codex-hotswap doctor
```

`doctor` checks:

- shared `~/.codex`
- shared `auth.json`
- current target
- each auth vault
- each target's login status
- shim presence and whether it is the `codex` currently found on `PATH`
- whether the shared runtime lock is idle or busy

If `doctor status: ok` appears, your setup is healthy.

### It Is Not Swapping Automatically

Check:

- you are using `codex` through the shim or `codex-hot`
- each account really logged in successfully
- the target order in `codex-hotswap status`
- not all accounts are already exhausted

The live detector is conservative on purpose. If Codex changes its failure banner, `codex-hotswap` may need an update before automatic rotation works again.

### `codex-hotswap: no non-exhausted targets remain`

This means `codex-hotswap` believes every configured target is currently exhausted.

Common reasons:

- the current account hit a limit
- the next account also hit a limit immediately after rotation
- other accounts were already marked exhausted from earlier tests

Check state:

```bash
codex-hotswap status
```

Clear exhaustion markers:

```bash
codex-hotswap reset
```

Or start directly from a specific account:

```bash
codex-hotswap use acc3
codex
```

### `/resume` Looks Wrong

Make sure you are starting through `codex-hotswap`, not a separate unmanaged `codex` flow using some other `CODEX_HOME`.

The intended shared-history model is:

- one shared `~/.codex` for runtime history
- one auth vault per account

Run from the repo you care about:

```bash
cd ~/your-repo
codex
```

If a swap succeeds, `/resume` should still behave like normal Codex for that repo because the shared runtime home stays the same. The account changes underneath; the shared session store does not.

### Another Wrapped Session Is Already Running

`codex-hotswap` now locks the shared `~/.codex` while a wrapped session is active.

That is intentional. The active auth inside the shared home is mutable, so running two wrapped sessions against the same shared home at once is unsafe.

If you need parallel wrapped sessions, use separate configs with separate `shared_codex_home` values.

## Guarantees And Limits

What it does well:

- keeps normal repo/session history in a shared Codex home
- preserves the usual `/resume` workflow by repo
- isolates multiple account logins
- swaps account auth without changing your workspace
- preserves the same repo/session flow across account swaps
- checks setup health with `doctor`

What it does not guarantee:

- perfect detection of every future Codex failure banner
- a real upstream usage meter from Codex
- perfect resume behavior if Codex changes its session internals
- concurrent wrapped sessions against the same shared home

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
codex-hotswap install-shim
codex-hotswap uninstall-shim
codex-hotswap doctor
codex-hotswap run [codex args...]
codex-hot [codex args...]
```

## Short FAQ

### Do I need to keep using `codex-hot` forever?

No. If you install the shim, you can just use normal `codex`.

### Will my repo chats stay separate?

Yes. The shared runtime home keeps normal Codex history, so `/resume` should still stay organized by repo.

### Does it magically log into all accounts by itself?

No. You still log into each account once. After that, switching is automatic.

### Does it track real Codex usage counters?

No. It reacts to the failure/limit output that Codex shows.

### Can I run multiple wrapped sessions at the same time in the same shared home?

No. That is intentionally blocked because auth swapping in one shared home must stay serialized.

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
