# 14 · Running 24/7

> Turn Hermes into a service people can depend on: the right host, a supervised gateway, backups you've actually restored, updates that don't wake you at night, and monitoring that tells you before your users do.

**TL;DR**
- **Run the gateway under the service Hermes installs** (`hermes setup` does it for you), not tmux or a hand-written unit. Cron only fires while the gateway runs, and the native unit carries restart and drain behavior that hand-written units get wrong.
- **A small Linux box and a dedicated, unprivileged user** is the default production setup. Bots on Telegram, Discord, or Slack need no open inbound ports.
- **Back up nightly with `hermes backup`, keep copies off the box and encrypted, and test a restore.** Never copy a live `state.db` by hand.
- **Updates follow `main`.** Preview them with `hermes update --plan`, and pin a release tag if you run Docker.
- **Watch it from outside.** `hermes gateway status --deep` for a quick look, and the built-in OTLP health export if you want alerts.
- **One gateway serves every profile.** Separate tenants need separate OS users or containers, because profiles aren't a security boundary.

## Pick a host

| Host | Good for | Watch out for |
|---|---|---|
| Laptop or desktop | Interactive use | It sleeps, and the gateway and cron stop with it |
| Home server or mini PC | A personal always-on agent, LAN services, local models | Your uplink and power |
| Small Linux VPS | A 24/7 bot, scheduled jobs, team access | A public IP: firewall it and keep services on loopback |
| Docker on any of these | Isolation, reproducible upgrades, NAS boxes | Image-based updates, UID mapping on bind mounts ([Docker](#docker)) |

Model inference happens at your provider, so the agent itself is light. The Docker guide's [resource table](https://hermes-agent.nousresearch.com/docs/user-guide/docker#resource-limits) is a fair sizing guide for any install:

| Resource | Minimum | Recommended |
|---|---|---|
| Memory | 1 GB | 2–4 GB. Browser automation is the hungriest feature, so allow at least 2 GB with browser tools. |
| CPU | 1 core | 2 cores |
| Disk for Hermes' data | 500 MB | 2 GB or more. It grows with sessions and skills. |

Local models are a different sizing exercise ([chapter 04](./04-local-models.md)). Disk growth is mostly `state.db`, which prunes ended sessions after 90 days by default ([below](#keep-statedb-healthy)). Log files rotate on their own at 5 MB, keeping 3 old copies (`logging.max_size_mb`, `logging.backup_count`). Budget space for the backups you keep.

**Inbound ports.** Telegram (long polling by default), Discord, and Slack (Socket Mode) connect outbound, so a bot on those platforms needs nothing open except SSH. Webhook-driven platforms, Telegram's webhook mode (`TELEGRAM_WEBHOOK_URL`), and `hermes webhook` routes need an inbound HTTPS path.

## A VPS, end to end

A Debian or Ubuntu box, from nothing to a gateway that survives reboots. Step 1 needs an admin account with sudo. Everything else runs as a dedicated `hermes` user that has none.

1. **Prepare the box** (as the admin):

   ```bash
   sudo apt update && sudo apt install -y git curl xz-utils
   sudo useradd --create-home --shell /bin/bash hermes
   sudo loginctl enable-linger hermes   # its user services start at boot and survive logout
   sudo ufw allow OpenSSH               # keep SSH reachable (use your port if sshd isn't on 22)
   sudo ufw enable                      # nothing else inbound for Telegram/Discord/Slack bots
   sudo apt install -y unattended-upgrades
   sudo dpkg-reconfigure --priority=low unattended-upgrades   # automatic OS security updates
   ```

   Want browser tools? Chromium's system libraries are the one install step that needs root: `sudo npx playwright install-deps chromium` (the admin needs Node.js for `npx`). If you don't, pass `--skip-browser` to the installer in the next step ([official split](https://hermes-agent.nousresearch.com/docs/getting-started/installation#non-sudo--system-service-user-installs)).

2. **Install and set up** (as `hermes`):

   ```bash
   sudo -iu hermes
   curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash   # no browser: ... | bash -s -- --skip-browser
   source ~/.bashrc
   hermes setup                      # provider, model, messaging, then the gateway service
   hermes doctor
   hermes -z "Reply with exactly: OK"
   ```

   When it installs the browser, the installer notices there's no sudo, puts Chromium in the `hermes` user's own cache, skips the system-library step, and prints the command an admin would need. `hermes setup` always ends by installing and starting the gateway as a **user service**, even with no messaging platform configured, because cron needs a running gateway. Linger from step 1 is what starts it at boot.

3. **Configure it for unattended use** (still as `hermes`):

   ```bash
   mkdir -p ~/work
   hermes config set terminal.cwd /home/hermes/work     # where gateway and cron commands start
   hermes config set timezone Europe/Berlin             # so "every day at 9" means your 9
   hermes config set updates.pre_update_backup full     # zip the whole home before each update
   hermes gateway restart                               # make sure the running gateway uses them
   ```

   Then lock down who can talk to it and what it may run: allowlists or pairing, approvals, and ideally a container backend ([chapter 13](./13-security.md)). Messaging setup is in [chapter 10](./10-messaging.md#set-it-up).

4. **Prove it survives a reboot.** As the admin, `sudo reboot`. Reconnect, run `sudo -iu hermes`, then `hermes gateway status` (service running, "Systemd linger is enabled") and `hermes cron status`. Cron jobs only fire while a gateway runs.

### Or run it as a system service

A system unit suits a box an admin owns, and it's the one you can sandbox with a drop-in ([below](#optional-harden-the-unit-with-a-drop-in)). Remove the user service that `hermes setup` installed first. Both units would compete for the same bot tokens, and Hermes' commands keep picking the user unit while its file exists.

```bash
hermes gateway uninstall                # as hermes: remove the user service
exit                                    # back to the admin account
sudo ln -s /home/hermes/.hermes/hermes-agent/venv/bin/hermes /usr/local/bin/hermes
sudo hermes gateway install --system --run-as-user hermes
sudo hermes gateway start --system
sudo hermes gateway status --system     # "Configured to run as: hermes"
```

The symlink makes the `hermes` user's install callable through `sudo`, as the install docs suggest for service accounts. The unit lands in `/etc/systemd/system/hermes-gateway.service` and runs as `hermes`.

| Scope | Pick it when | Tradeoff |
|---|---|---|
| User service plus linger (what `hermes setup` installs) | The service account manages itself | No root needed after setup. Fewer sandboxing options in the unit. |
| System (`--system --run-as-user`) | An admin owns the box, or you want to harden the unit | Manual restarts need root. `hermes update` still drain-restarts it without root: it signals the gateway, and systemd relaunches it. |

## What the native service gives you

`hermes gateway install` generates the unit from your actual install (`hermes_cli/gateway_service_unit.py`), and that unit is part of how the gateway recovers:

- **It always comes back.** `Restart=always`, `RestartSec=5`, and no start-rate cap (`StartLimitIntervalSec=0`).
- **An exit-code contract.** The watchdogs below exit with code 75 to ask for a restart, and the unit honors it. A fatal config error exits with a code the unit won't restart, so a broken `config.yaml` doesn't loop forever.
- **Drain-aware stops.** `KillMode=mixed` with `SIGTERM`, an `ExecStop` step that marks the stop as planned (so a plain `systemctl restart` exits cleanly), `ExecReload` mapped to `SIGUSR1` (drain, exit, relaunch), and a `TimeoutStopSec` sized to the drain budget so systemd doesn't kill a turn mid-drain.
- **The right environment.** The venv's `PATH`, Node, `VIRTUAL_ENV`, `HERMES_HOME`, and `HERMES_SUPERVISED_CHILD=1`, which stops the agent from killing or restarting its own gateway from the terminal tool.
- **Correct ordering.** It waits for `network-online.target`. The system unit also starts the user's systemd manager, so restart-safe cron workers can run in their own scopes.
- **It keeps itself current.** `start` and `restart` rewrite the installed unit when Hermes would now generate a different one, and `status` warns when it's outdated.
- **An optional systemd watchdog.** Set `gateway.systemd_watchdog_seconds: 120` and reinstall the unit with `--force` (`hermes gateway install --force` for the user service). The unit switches to `Type=notify` with `WatchdogSec`, so systemd restarts a process whose event loop stops making progress.

Inside the process, these guards are on by default:

| Guard | Catches | Response |
|---|---|---|
| `gateway.startup_watchdog` | A gateway that never reaches a live event loop (default timeout 300 s) | Thread dump to `logs/gateway-startup-watchdog.log`, exit 75 |
| `gateway.loop_watchdog` | An event loop that stopped dispatching (3 failed probes, 30 s apart) | Thread dump, `gateway_state.json` marked degraded, exit 75 |
| Heartbeat check | Alive, but housekeeping stopped refreshing state for more than 120 s | `hermes gateway status` and the dashboard badge say "heartbeat stale" |
| `gateway.respawn_storm` | A crash loop (5 starts in 120 s) | Exponential backoff before booting |
| `gateway.restart_loop_guard` | A resumed turn that keeps killing the gateway | Skips auto-resume after 3 quick restarts. Inbound messages are still served. |

A hand-written unit misses parts of this contract and never gets regenerated when Hermes changes it. Keep your own units for things Hermes doesn't install, like [`hermes serve`](#the-desktop-app-on-your-server). If another process manager must own the gateway (supervisord, runit, a wrapper script), run `hermes gateway run --external-supervisor` under it and have it relaunch after any non-zero exit. Restarts and updates then exit with code 75 and leave the relaunch to it ([CLI reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands#hermes-gateway)).

**Operating it** (as `hermes`):

```bash
hermes gateway restart          # drains in-flight turns, then waits for the new process
hermes gateway status --deep    # unit state, warnings, recent journal lines
hermes logs gateway -f          # Hermes' own gateway.log
```

`systemctl --user reload hermes-gateway` runs the same drain and relaunch without waiting. Plain `systemctl --user` and `journalctl --user` need `XDG_RUNTIME_DIR`, which a `sudo -iu hermes` shell may not set. If they can't reach the bus, add `export XDG_RUNTIME_DIR=/run/user/$(id -u)` to the `hermes` user's `~/.profile` ([#43748](https://github.com/NousResearch/hermes-agent/issues/43748)). Hermes' own commands set it themselves. For the system service, use `sudo hermes gateway restart --system`, `sudo systemctl reload hermes-gateway`, and `journalctl -u hermes-gateway -f`. For a gateway that looks alive but does nothing, `kill -USR2 <pid>` appends every thread's stack to `logs/gateway_faulthandler.log` without stopping it.

> [!WARNING]
> Never add `ExecStopPost=/bin/kill -9 $MAINPID` or similar. It fires on every stop, including clean restarts, and kills the replacement, which causes an endless restart loop ([messaging docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging#service-management)). The unit's own `ExecStopPost` line is different: it runs after the gateway has exited and only kills helper processes left behind in the service's cgroup.

## Optional: harden the unit with a drop-in

systemd can sandbox the gateway. This section assumes the [system service](#or-run-it-as-a-system-service), because user units get fewer sandboxing options. Use a drop-in, not an edit to the unit file itself: Hermes rewrites `hermes-gateway.service` on start or restart when it's outdated, but it leaves drop-in files alone.

```bash
sudo systemctl edit hermes-gateway     # opens an override file; paste the block below
```

<!-- drift-guard: ignore -->
```ini
[Service]
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
MemoryMax=3G
```

Then `sudo hermes gateway restart --system`, and check the result with `systemd-analyze security hermes-gateway`.

The catch: **the agent's terminal runs inside this unit**, so every restriction applies to the agent's own commands too. That's the point, and it's also what breaks things:

| Directive | Protects | Costs |
|---|---|---|
| `NoNewPrivileges=yes` | No privilege gain through `sudo` or other setuid tools | Those tools stop working for the agent. It couldn't answer a sudo prompt from chat anyway. |
| `PrivateTmp=yes` | The agent's `/tmp` is private to the service | Other programs can't see what it leaves in `/tmp` |
| `ProtectSystem=full` | `/usr`, `/boot`, and `/etc` become read-only | Little extra protection for a non-root user, and little breakage |
| `MemoryMax=` | Caps a runaway gateway | Hitting it kills the gateway, and it restarts. Background commands and cron workers run in their own scopes, each capped at the smaller of this limit, half your RAM, or 4 GiB, so `MemoryMax=` doesn't bound them in total. |
| `ProtectSystem=strict`, `ProtectHome=` | Everything outside `ReadWritePaths=` becomes read-only | Breaks real work: project checkouts, `~/.cache`, `~/.npm`, `~/.local`, `npx`/`uvx` MCP servers, and Playwright's browser cache |

Start with the first four. Treat the strict pair as a project: list every path the agent legitimately writes in `ReadWritePaths=`, then test browser tools, MCP servers, and your cron jobs.

## Docker

The official image is the easiest way to run the whole process in a box, which is upstream's supported posture for agents that read untrusted input ([chapter 13](./13-security.md#layer-3-where-it-runs)).

- **Pin a release tag.** Releases are published as `nousresearch/hermes-agent:<release tag>`, for example `v2026.9.21`. `:latest` and `:main` are rebuilt from every push to `main` (`.github/workflows/docker.yml`), so they aren't release builds.
- **Supervised by default.** s6-overlay runs as PID 1, restarts a crashed gateway within seconds, and reaps zombie processes. Don't override the entrypoint, or you lose both.
- **Runs as UID 10000.** Set `HERMES_UID`/`HERMES_GID` (or `PUID`/`PGID`) to the host user that owns the data directory. `docker exec hermes hermes <command>` already drops to that user.
- **Immutable install.** `/opt/hermes` is read-only, and runtime package installs are off. Features that need extra Python packages must be baked into a derived image.

First run is interactive, then the gateway runs in the background:

```bash
mkdir -p ~/.hermes
docker run -it --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent:v2026.9.21 setup
```

<!-- drift-guard: ignore -->
```yaml
# docker-compose.yml
services:
  hermes:
    image: nousresearch/hermes-agent:v2026.9.21   # a release tag; :latest tracks main
    container_name: hermes
    restart: unless-stopped
    command: gateway run
    shm_size: 1g                  # only needed for browser tools
    volumes:
      - ~/.hermes:/opt/data
    environment:
      - HERMES_UID=1000           # owner of the data directory on the host
      - HERMES_GID=1000
    deploy:
      resources:
        limits:
          memory: 4G
```

- **One container serves every profile.** At boot the root gateway multiplexes all of them. The per-profile s6 slots described in the Docker docs are registered but never started at v0.21.4 (`hermes_cli/container_boot.py`). Never point two containers at one data directory.
- **`state.db` on Docker Desktop, OrbStack, or Podman on macOS:** those bind mounts (virtiofs, 9p) can silently corrupt a WAL database. Use a named volume instead (`hermes-data:/opt/data`), or convert the database as described in [the Docker docs](https://hermes-agent.nousresearch.com/docs/user-guide/docker#filesystem-requirements-for-statedb-in-containers).
- **Logs:** `docker logs -f hermes` shows live output. The copy that survives restarts is `~/.hermes/logs/gateways/default/current`.
- **Updates are image updates.** `hermes update` refuses inside the image (exit 2). Change the tag, then `docker compose pull && docker compose up -d`. The container migrates `config.yaml` on start and writes timestamped backups first.
- **The dashboard** (`HERMES_DASHBOARD=1`) binds `0.0.0.0` inside the container, so it refuses to start until an auth provider is configured ([below](#the-dashboard-safely)).

## Several profiles on one host

Since v0.21.4, **one gateway process per host serves every profile** ([chapter 10](./10-messaging.md#several-bots-several-profiles)). A profile you create is served right away without a restart (a rescan every 30 seconds catches stragglers), and each profile keeps its own bot tokens, `.env`, allowlists, approval choices, sessions, and logs ([what's isolated](https://hermes-agent.nousresearch.com/docs/user-guide/multi-profile-gateways#what-is-isolated-per-profile)).

```bash
hermes gateway list                          # every profile and who serves it
hermes -p work gateway status                # "running via the default-profile multiplexer"
hermes gateway migrate --multiplex --dry-run # left over per-profile units from older versions? preview the fold
```

- Each profile needs **its own bot token**. A second profile reusing a token is parked with a `duplicate_credential` error instead of starting a second poller.
- Starting or installing a gateway for a served profile is refused (exit 78). `gateway.multiplex_profiles: false` is ignored, and the migration has no rollback. The multi-profile docs page still describes the old per-profile setup and a rollback; the v0.21.4 code no longer supports either.
- **Profiles share one OS user.** For separate tenants, use separate containers, or separate OS users with their own installs. Give each of those a user service with linger: the standard system-scope install names its unit `hermes-gateway` whichever user it runs as, so a second one would collide with the first.

## The desktop app on your server

The desktop app talks to a `hermes serve` backend, the headless twin of the dashboard with the same auth rules ([chapter 13](./13-security.md#exposing-the-dashboard-backend-and-api-server)). Three ways to connect, safest first:

1. **An SSH connection.** In the app: **Settings → Gateways → Add connection → SSH**, then `user@host:22`. The app opens the tunnel and starts the backend on demand, so nothing listens on the network.
2. **Tailscale.** Bind the backend to the machine's tailnet address and protect it with a password. Run `hermes dashboard --host <tailscale-ip> --no-open` once in a terminal: with no auth provider configured, it offers to create a username and password and saves them under `dashboard.basic_auth` (hashed, with a signing secret so sessions survive restarts). In the app, the remote URL is `http://<tailscale-ip>:9119`.
3. **The public internet.** Use Nous Portal OAuth (`hermes dashboard register`) behind TLS, as in [the next section](#the-dashboard-safely). A username and password alone isn't suitable here.

Hermes has no installer for `hermes serve`, so this is one unit worth writing yourself. Call it `hermes-serve.service`: `hermes update` restarts active `hermes-serve*` units in the same pass as the gateway (`hermes_cli/update_cmd_fleet.py`). A unit with another name is only restarted by a later cleanup step, which is skipped when the update's Node.js refresh fails (`hermes_cli/update_cmd_maint.py`).

<!-- drift-guard: ignore -->
```ini
# ~/.config/systemd/user/hermes-serve.service  (as the hermes user; needs linger)
[Unit]
Description=Hermes backend for the desktop app
After=network-online.target

[Service]
ExecStart=%h/.hermes/hermes-agent/venv/bin/hermes serve --host 100.64.0.10 --port 9119
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

Replace the address with your tailnet IP, then run `systemctl --user daemon-reload && systemctl --user enable --now hermes-serve`. Hermes reads `~/.hermes/.env` and `config.yaml` itself, so the unit needs no `EnvironmentFile=`. The app can register many gateways and update them all at once from **Settings → Gateways → Update all instances** ([multi-connection docs](https://hermes-agent.nousresearch.com/docs/user-guide/multi-connection-desktop)).

## The dashboard, safely

The dashboard can read and write your keys and run the agent. Pick the least exposure that works:

- **On demand over SSH (no login needed).** On the server, as `hermes`, run `hermes dashboard --no-open` (it binds `127.0.0.1:9119`). On your machine, run `ssh -N -L 9119:127.0.0.1:9119 hermes@your-server` and open `http://127.0.0.1:9119`.
- **On a tailnet or trusted LAN:** a password on a Tailscale address, as in the previous section.
- **On the public internet:** OAuth behind a TLS proxy. With Caddy on the same host:

  ```text
  hermes.example.com {
      reverse_proxy 127.0.0.1:9119
  }
  ```

  ```bash
  hermes dashboard register --redirect-uri https://hermes.example.com/auth/callback
  hermes config set dashboard.public_url https://hermes.example.com
  hermes dashboard --host 127.0.0.1 --no-open
  ```

  The dashboard stays on loopback. The public `public_url` engages the auth gate, and a proxy connecting from loopback is trusted automatically. A proxy on another host or container must be listed in `dashboard.trusted_proxies` ([public URL override](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard#public-url-override)). To keep it running, reuse the unit from the previous section as `hermes-dashboard.service`, with `hermes dashboard --host 127.0.0.1 --no-open` as the command (`hermes serve` has no web UI). That's the unit name Hermes looks for when it restarts a managed dashboard after an update. The desktop app can connect to this server too.

Check the gate with `curl -s https://hermes.example.com/api/status | jq '.auth_required, .auth_providers'`.

With a system service, the dashboard's **Restart gateway** button re-runs the Hermes CLI as root through `sudo -n` (`hermes_cli/web_server_gateway.py`), so it fails unless the dashboard's user has passwordless sudo for that command. Don't grant it: the `hermes` user owns the code that command runs, so the grant hands root to anything running as `hermes`, the agent included. Restart from a shell instead, or use the user service, which the button restarts without sudo.

## Backups

**What to back up:** the whole Hermes home, `~/.hermes`, including every profile under `profiles/`. It holds `config.yaml`, `.env`, `auth.json`, `state.db` (every session), memories, skills, cron jobs, pairing approvals, and the credential vault. You don't need the `hermes-agent/` code directory, caches, or virtualenvs, because a reinstall recreates them.

**`hermes backup` is the right tool.** It copies SQLite databases through SQLite's own backup API, so the snapshot is consistent while Hermes runs. It skips the code, caches, venvs, and live browser profiles, which contain cookies and saved logins. It **includes `.env` and `auth.json`**, and exits 1 if any file couldn't be added, so a timer never mistakes a partial archive for a good one (`hermes_cli/backup.py`).

```bash
install -d -m 700 ~/backups                  # create it first, private: the zip holds your keys
hermes backup -o ~/backups -k 7              # newest 7 hermes-backup-*.zip kept (default 3; 0 = keep all)
hermes backup --quick                        # critical state only, into ~/.hermes/state-snapshots/
```

Create the directory before the first run. If `-o` names a directory that doesn't exist, Hermes writes a single file called `backups.zip` next to it, overwrites it every night, and `-k` never prunes it (tested on v0.21.4).

Schedule it outside Hermes, so it runs even when the gateway is down ([system cron or Hermes cron](./11-automation.md#system-cron-or-hermes-cron)). The `hermes` user's crontab:

```text
15 3 * * * $HOME/.local/bin/hermes backup -o $HOME/backups -k 7 >> $HOME/backups/backup.log 2>&1
```

Then get a copy **off the box** with whatever you trust (rsync to another machine, restic, object storage), and **encrypt it**: the archive is as sensitive as your API keys. In Docker, run `docker exec hermes hermes backup -o /opt/data/backups -k 7` from the host's crontab. That folder already exists (Hermes keeps config backups there), and later backups skip it, so archives don't nest.

**Restore** with `hermes import <zip>` on a fresh install. It restores into the current Hermes home, re-applies owner-only permissions to `.env`, `auth.json`, and `state.db`, keeps this machine's runtime files (PIDs, gateway state), and warns you if older session data replaces newer. If no gateway is running, it installs and starts one as a user service. Then run `hermes doctor` and `hermes gateway status`.

**Test a restore** without touching the live install. Import into a scratch home:

```bash
HERMES_HOME=~/restore-test hermes import ~/backups/hermes-backup-<timestamp>.zip
HERMES_HOME=~/restore-test hermes sessions stats    # sessions and messages are there
rm -rf ~/restore-test
```

Hermes leaves the gateway service alone when you restore into a non-default home while a default install exists.

**Retention at a glance:**

| What | Where | Kept |
|---|---|---|
| Your backups | `-o` directory (default `~`) | Newest 3, or `-k N` |
| Pre-update full zips (`updates.pre_update_backup: full`) | `~/.hermes/backups/` | `updates.backup_keep` (5) |
| Quick snapshots (`hermes backup --quick`, and one before every update) | `~/.hermes/state-snapshots/` | 20, but each `hermes update` prunes the folder down to its own pre-update snapshot. Restore with `/snapshot` in the CLI. |

**A profile export is not a backup.** `hermes profile export work -o work.tar.gz` leaves out `.env` and `auth.json` and scrubs secrets from text files, and a default-profile export only includes an allow-list of files. Use it to share or move one profile (`hermes profile import work.tar.gz --name work`), not to recover a server ([backup vs export](https://hermes-agent.nousresearch.com/docs/reference/faq#hermes-backup-vs-hermes-profile-export)).

## Keep `state.db` healthy

`state.db` is SQLite in WAL mode. The gateway, dashboard, desktop app, cron, and CLI can all write to it at once safely. The one unsafe thing is **rewriting the store while another process writes to it**, and every maintenance command now refuses to do that.

- **Automatic upkeep.** Ended sessions inactive for 90 days are pruned (`sessions.auto_prune: true`, `sessions.retention_days`), and the file is VACUUMed only when enough of it is free space. Pin anything you'll need later with `hermes sessions pin <id>`.
- **Manual upkeep.** Stop every writer first: the gateway (`hermes gateway stop`, with `sudo` and `--system` for a system service), any dashboard or `hermes serve` backend (`hermes dashboard --stop` stops both), and the desktop app:

  ```bash
  hermes sessions stats                  # sessions, messages, database size
  hermes sessions prune --dry-run        # what the 90-day rule would delete
  hermes sessions optimize               # merge search-index segments and VACUUM
  hermes sessions optimize-storage       # rebuild the search index in the compact layout (resumable)
  ```

- **Network and cross-VM filesystems.** On NFS, SMB, and similar mounts, set `database.journal_mode: delete`, then convert the existing file once with everything stopped: `hermes sessions set-journal-mode delete`. Hermes never switches a live WAL database on its own.
- **`hermes doctor` warns about a SQLite library with the WAL-reset bug.** It prints the fix for your install type (`hermes update` on a git install, a new image on Docker).
- **When it breaks:** stop every process, run `hermes doctor` until it names no holder, and never delete `state.db-wal`. The full runbook is in [chapter 15](./15-troubleshooting.md#the-session-database-statedb) and the [recovery guide](https://hermes-agent.nousresearch.com/docs/user-guide/session-storage-recovery).

## Updating a server

The basics are in [chapter 02](./02-install.md#updating-without-breaking-things): snapshot, pull, compile-check, dependencies, config migration, then a drain-restart of the gateway. On servers, a few more things matter.

- **`hermes update` follows `main`, not release tags.** Every run brings whatever merged since your last one. If you want release-by-release upgrades, the Docker image with a pinned tag is the simple route.
- **Preview first.** `hermes update --plan` is read-only and lists every running Hermes service across profiles, its supervisor, its code version, and how it will be restarted.
- **Hold new work if you want a quiet window.** `hermes pause --reason "upgrade"` stops new cron fires, Kanban dispatch, and gateway turns without killing anything in flight. `hermes resume` after you've verified the upgrade, and due jobs catch up ([the emergency brake](./11-automation.md#the-emergency-brake)).
- **The drain can take a while.** The restart waits up to `agent.restart_after_turn_timeout` (30 minutes) for running turns and cron jobs, and prints what it's waiting on every 30 seconds.
- **System-scope services** get a graceful signal from the updater and are relaunched by systemd, which needs no root. Only a forced restart needs root, and the updater prints the `sudo` command when that happens.
- **Automating it:** from the host's crontab or a timer, a plain `hermes update` is fine. From *inside* Hermes (a Hermes cron job, `/update` in chat), use `hermes update --no-gateway-restart` and restart separately, because the gateway's restart would kill the updater.
- **Afterwards:** `hermes --version`, `hermes doctor`, and `hermes gateway status`. Each run writes a JSON record to `~/.hermes/logs/update_receipts/` (`latest.json` is the newest), and the update exits non-zero if any gateway is still running old code.
- **Several machines:** update one canary box, watch it for a day, then the rest. The desktop app's **Update all instances** runs `hermes update` on every registered gateway.
- **Rolling back** a git install means checking out the previous tag, reinstalling dependencies, and restarting ([rollback instructions](https://hermes-agent.nousresearch.com/docs/getting-started/updating#rollback-instructions)). The pre-update backup covers your data.

## Monitoring

**The quick look**, as the `hermes` user:

```bash
hermes gateway status --deep     # unit state, outdated-unit and degraded warnings, heartbeat, last 20 journal lines
hermes cron status               # scheduler health; warns loudly if the gateway runs stale code
hermes logs errors --since 1h    # anything that went wrong recently
hermes status                    # every component at a glance
```

**Alerts need something outside the gateway.** A job running inside Hermes can't report that Hermes is down. The built-in health export pushes gateway state to an OpenTelemetry Collector, Datadog, or any other OTLP receiver. It's content-free by design: no prompts, messages, tool arguments, or job names ([gateway monitoring](https://hermes-agent.nousresearch.com/docs/developer-guide/gateway-monitoring)).

```yaml
monitoring:
  gateway_health_export:
    enabled: true
  export:
    otlp:
      enabled: true
      endpoint: http://collector.internal:4318/v1/traces   # metrics and logs paths are derived from it
      headers_env:
        Authorization: OTLP_AUTH_HEADER                     # header name -> env var holding its value
```

`hermes monitoring status` shows what's being exported. The OpenTelemetry SDK installs on first use. If you've turned lazy installs off ([chapter 13](./13-security.md#layer-5-supply-chain)), install the `otlp` extra yourself. The alerts worth having, in PromQL form from the upstream guide:

```text
hermes_gateway_up == 0                                # gateway reports itself down
absent_over_time(hermes_gateway_up[5m])               # the box stopped reporting at all
hermes_platform_up == 0                               # a messaging platform is down
hermes_cron_scheduler_heartbeat_age_seconds > 180     # the scheduler thread is stuck
hermes_cron_jobs_overdue > 0                          # jobs past their grace window
```

No collector? A [zero-token watchdog](./16-recipes.md#2-zero-token-watchdogs) can check disk space and backup age from inside Hermes, as long as you remember it dies with the gateway.

**Tracing turns and cost:** the bundled Langfuse plugin sends turns, LLM calls, and tool calls to Langfuse. Set it up from `hermes tools` (**Langfuse Observability**), which installs the SDK, saves the `HERMES_LANGFUSE_*` keys, and enables `observability/langfuse` ([built-in plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/built-in-plugins#observabilitylangfuse)). Without the SDK the plugin silently does nothing. Unlike the health export, it ships conversation content (redacted for secrets) off the box, unless you set `HERMES_LANGFUSE_CAPTURE=metadata`. Other tracing vendors aren't built in at v0.21.4.

**When something is wrong,** use the diagnostic ladder in [chapter 15](./15-troubleshooting.md#the-diagnostic-ladder). `hermes dump` gives a pasteable setup summary. Run `hermes debug share --local` and read the report before you upload anything: uploads go to a public paste site, and only credentials are redacted.

## Production checklist

1. The gateway runs under the native service (a user service with linger, or a system service), and a reboot test passed.
2. Hermes runs as a dedicated user without sudo. The firewall allows SSH and nothing else the platforms don't need.
3. OS security updates install automatically.
4. `terminal.cwd` and `timezone` are set, and the security basics from [chapter 13](./13-security.md#security-checklist) are done.
5. `hermes cron status` is green, and a `--paused` test job or a manual `hermes cron run` delivered where you expected.
6. A nightly `hermes backup` runs outside Hermes, into a `700` directory, with an encrypted off-box copy.
7. You've restored a backup into a scratch home at least once.
8. `updates.pre_update_backup` is `full` on machines you'd hate to rebuild.
9. Docker installs pin a release tag rather than `:latest`, and use a named volume on Docker Desktop.
10. Every profile has its own bot token, and `hermes gateway list` shows one gateway serving them all.
11. The dashboard and `hermes serve` are loopback-only, on a tailnet with a password, or behind TLS with OAuth.
12. Your own backend units are named `hermes-serve.service` or `hermes-dashboard.service`, the names updates look for.
13. Health export or another outside check alerts you when the gateway disappears.
14. Maintenance commands (`hermes sessions optimize`, `set-journal-mode`) run only with every writer stopped.
15. Updates go to one machine first, and you read `hermes update --plan` before touching a busy one.

## Verify it

As `hermes`:

```bash
hermes gateway status --deep                      # running, linger on, no degraded or heartbeat warnings
systemctl --user show hermes-gateway -p Restart   # Restart=always
hermes cron status                                # the scheduler is ticking
ls -l ~/backups                                   # last night's zip exists
hermes monitoring status                          # export enabled and endpoint set, if you use it
```

For a system service, check with `sudo hermes gateway status --system` and drop `--user` from the `systemctl` line.

Then pull the plug on purpose: `systemctl --user kill -s KILL hermes-gateway` (system service: `sudo systemctl kill -s KILL hermes-gateway`) should bring a new gateway back within seconds. Separately, confirm your alert fires when the host stops reporting.

## Gotchas

- **A user service dies at logout** unless lingering is on: `sudo loginctl enable-linger <user>` ([installation docs](https://hermes-agent.nousresearch.com/docs/getting-started/installation#non-sudo--system-service-user-installs)).
- **Custom `ExecStopPost` kill lines cause restart loops.** Remove them with `systemctl edit` ([messaging docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging#service-management)).
- **Cron silently stopped after an update?** The gateway kept running old code. `hermes gateway restart` fixes it, and v0.21.4's `hermes cron status` warns about it ([PR #117501](https://github.com/NousResearch/hermes-agent/pull/117501)).
- **`:latest` isn't a release.** It tracks `main` (`.github/workflows/docker.yml`).
- **Quick snapshots aren't backups.** Every `hermes update` keeps only its own pre-update snapshot in `state-snapshots/` and deletes the older ones, and it skips any file over 1 GiB, which can include a large `state.db` (`hermes_cli/update_cmd_maint.py`).
- **Backup zips inherit your umask.** On a default system they're readable by other local users, and they contain your keys. Write them into a `700` directory.
- **Don't copy `state.db` by itself or while Hermes runs.** The `-wal` file holds committed conversations. Use `hermes backup` ([recovery guide](https://hermes-agent.nousresearch.com/docs/user-guide/session-storage-recovery)).
- **The FAQ's profile export example** (`hermes profile export work ./file.tar.gz`) predates the current CLI. The output path is `-o`, and import takes `--name`.
- **Two gateways on one bot token** (a stray `hermes gateway run` in tmux plus the service) cause Telegram `409 Conflict` errors. `hermes gateway run` refuses to start in the foreground when a service already supervises the profile, unless you add `--force`, so don't.

## Go deeper

- Official: [Messaging service management](https://hermes-agent.nousresearch.com/docs/user-guide/messaging#service-management) · [Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker) · [Updating](https://hermes-agent.nousresearch.com/docs/getting-started/updating) · [Session storage recovery](https://hermes-agent.nousresearch.com/docs/user-guide/session-storage-recovery) · [Sessions: expiry and cleanup](https://hermes-agent.nousresearch.com/docs/user-guide/sessions#session-expiry-and-cleanup) · [Web dashboard](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard) · [Desktop remote backend](https://hermes-agent.nousresearch.com/docs/user-guide/desktop#connecting-to-a-remote-backend) · [Gateway monitoring](https://hermes-agent.nousresearch.com/docs/developer-guide/gateway-monitoring)
- In this guide: [02 · Install](./02-install.md) · [10 · Messaging](./10-messaging.md) · [13 · Security](./13-security.md) · [15 · Troubleshooting](./15-troubleshooting.md)

---
[← Previous: 13 · Security](./13-security.md) · [Guide index](../README.md#the-guide) · [Next: 15 · Troubleshooting →](./15-troubleshooting.md)
