# 09 · Tools, MCP & Plugins

> Decide what your agent can actually do (run commands, search, browse, drive your desktop, call outside services), and give each surface only what it needs.

**TL;DR**
- **Keep each surface's tool list short.** `hermes tools disable --platform <name> …` trims one surface, and `agent.disabled_toolsets` removes a toolset everywhere. Every enabled toolset is paid for on every call ([chapter 05](./05-token-budget.md#lever-1-send-fewer-tool-schemas)).
- **Choose where commands run.** `local` is fine when you're at the keyboard. A bot other people can message belongs in `docker` or a cloud sandbox. Container backends skip the dangerous-command prompts (unless you mount host paths), because the container is the security boundary.
- **Web search works with zero keys**, through a free keyless ring and a 20-minute result cache. Pick a keyed backend once you depend on it.
- **Treat MCP servers and plugins as code you're installing.** Prefer the curated catalogs, filter each server down to the tools you use, pin package versions so `hermes security audit` can check them, and mark servers you don't control `trust: untrusted`.
- **Turn on checkpoints before the agent edits a repo.** `/rollback` then undoes its file changes and keeps yours.

## The toolset menu

A toolset is a named bundle of tools, and you switch whole toolsets on or off per platform. This is what a fresh v0.21.4 install enables in the CLI (`hermes tools list`):

| Toolset | Tools | Use it for | Notes |
|---|---|---|---|
| `terminal` | `terminal`, `process_manage` | Shell commands and background processes | Runs on the [terminal backend](#where-commands-run-terminal-backends) you choose |
| `file` | `read_file`, `write_file`, `patch`, `search_files` | Reading and editing files | Edits in git repos get [LSP diagnostics](#lsp) |
| `code_execution` | `execute_code` | Python that calls other tools in one step | [Stateful per session](#execute_code-one-script-instead-of-forty-calls) |
| `web` | `web_search`, `web_extract` | Searching and reading pages | [Works without keys](#web-search-and-extract) |
| `browser` | `browser_*`, or one `browser_exec` | Logins, forms, JavaScript-heavy sites | About 7.9 KB of schemas, the largest of any toolset |
| `vision` | `vision_analyze` | Looking at images and screenshots | A model that can see gets the raw pixels |
| `image_gen` | `image_generate` | Text-to-image | Deferred behind tool search |
| `tts` | `text_to_speech` | Spoken audio | Edge TTS by default: free, no key |
| `skills`, `memory`, `session_search` | skill and memory tools | The learning loop | [07](./07-memory.md), [08](./08-skills.md) |
| `todo`, `clarify` | `todo_list`, `clarify` | Planning, asking you a question | `clarify` renders as buttons in chat apps |
| `delegation` | `delegate_task` | Subagents | [12](./12-multi-agent.md) |
| `cronjob` | `cronjob_manage` | Scheduling | [11](./11-automation.md) |
| `connections` | `manage_connections` | Connecting apps (catalog MCP servers, Nous Portal connectors) | |
| `computer_use` | `computer_use` | Clicking and typing in desktop apps | Deferred; needs `cua-driver` ([below](#computer-use)) |

Off by default: `video`, `video_gen`, `x_search`, `kanban`, `homeassistant` (needs `HASS_TOKEN`), `spotify`, `yuanbao`, and the `a2a` plugin toolset. Speech-to-text isn't a model toolset at all. Voice-note transcription has its own switch, `stt.enabled` ([chapter 10](./10-messaging.md#voice)).

### Turn toolsets on and off

```bash
hermes tools                                     # interactive checklist, per platform
hermes tools list --platform telegram            # what Telegram gets now
hermes tools disable --platform telegram browser code_execution delegation tts
hermes tools enable --platform cli homeassistant
hermes chat -t web,file,terminal                 # this session only
```

Measured on a fresh v0.21.4 home with `hermes prompt-size --platform telegram`: that `disable` line takes Telegram from 24 tools and 42,199 bytes of schemas to 15 tools and 24,642 bytes. That's about 10,000 → 5,900 tokens on every call (o200k_base tokenizer). Chapter 05 has the full [cost method](./05-token-budget.md#lever-1-send-fewer-tool-schemas).

For "off on every surface", one key beats editing each platform row:

```yaml
agent:
  disabled_toolsets: [tts]   # applied after per-platform config, so it always wins
```

Inside a CLI session, `/tools disable browser` saves the same change and starts a fresh session, so the new tool list never breaks a conversation's prompt cache halfway through.

## Where commands run: terminal backends

The `terminal` tool, the file tools, and `execute_code` all run on one backend, `terminal.backend`:

| Backend | Commands run in | Dangerous-command prompt | Pick it when | Needs |
|---|---|---|---|---|
| `local` (default) | Your machine, as your user | Yes | You're at the keyboard and trust the work | Nothing |
| `ssh` | A remote host | Yes | Bigger hardware, or keeping the agent off its own box | `TERMINAL_SSH_HOST`, `TERMINAL_SSH_USER` |
| `docker` | One long-lived hardened container (capabilities dropped, no privilege escalation, 256-process limit) | **Skipped**, unless host paths are mounted | Any bot other people can message, or untrusted code | Docker or Podman |
| `singularity` | An Apptainer container (`--containall --no-home`) | **Skipped** | HPC clusters without Docker | `apptainer` or `singularity` on `PATH` |
| `modal` | A Modal cloud sandbox | **Skipped** | Heavy or bursty compute | `MODAL_TOKEN_ID` + `MODAL_TOKEN_SECRET`, or `~/.modal.toml` |
| `daytona` | A Daytona cloud workspace (disk capped at 10 GiB) | **Skipped** | A managed, persistent cloud dev box | `DAYTONA_API_KEY` |
| `vercel_sandbox` | A Vercel Sandbox microVM | **Skipped** | Cloud execution with snapshot persistence | `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`, `VERCEL_TEAM_ID`, plus the `vercel` extra |

"Skipped" is deliberate. With a container backend, Hermes treats the container as the security boundary and doesn't ask before `rm -rf` inside it, so the container's settings *are* your policy. Two exceptions, both from `tools/approval.py`: your `approvals.deny` rules apply on every backend, and Docker keeps the prompts on when a host path is bind-mounted (a `docker_volumes` entry that starts with `/`, `~`, `./`, `../`, or a Windows drive letter, or `docker_mount_cwd_to_workspace: true`), because commands can then reach host files. For a bot that other people can reach:

```yaml
terminal:
  backend: docker
  container_persistent: false   # a fresh container per chat session; nothing carries between conversations
  docker_volumes:
    - "bot-data:/data"         # a named volume; a host path here would turn approval prompts back on
  docker_forward_env: []        # anything listed here is readable by every command in the container
```

The default Docker mode (`container_persistent: true`) is the opposite trade: one container shared across sessions, `/new`, and subagents, so installed packages and background servers survive. That suits your own coding work. Checkpoints don't work on container backends ([below](#checkpoints-and-rollback)).

Two more things change what a sandbox can leak. If code in the container needs provider keys, `hermes egress` gives the sandbox proxy tokens instead of the real keys, and it covers the Docker backend only ([chapter 13](./13-security.md)). The SSH, Modal, and Daytona backends copy your Hermes state (credential files, skills, cache) into the remote machine for the session and sync changes back on teardown, so treat those hosts as holding your credentials. Every `terminal:` key also has a `TERMINAL_<KEY>` environment override (for example `TERMINAL_DOCKER_IMAGE`), which is handy in containers and CI.

Switch with `hermes config set terminal.backend docker`, then run `hermes doctor`. If commands fail, test on `local` first. That isolates backend problems from everything else.

## execute_code: one script instead of forty calls

`execute_code` runs a Python script that imports Hermes tools (`web_search`, `web_extract`, `read_file`, `write_file`, `search_files`, `patch`, and foreground `terminal`) over a local RPC channel. Only what the script prints comes back to the model. A loop over 30 search results costs one tool call and one short result, not 30 round trips that each re-send the whole prompt.

Since v0.21.0 each session owns a **persistent kernel**: variables, imports, and loaded data survive between calls, so the agent can load a dataset once and query it for several turns. The agent passes `reset: true` to start clean. Kernels are reaped after `code_execution.kernel_idle_timeout` (1,800 s), and at most `code_execution.max_session_kernels` (4) stay alive.

The defaults are sane: 300 s timeout, 50 tool calls per script, and a scrubbed environment. Any variable whose name contains `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `CREDENTIAL`, `PASSWD`, or `AUTH` is stripped. Scripts can't call MCP tools, `delegate_task`, or `execute_code` itself. Allow a specific variable through with `terminal.env_passthrough`. `code_execution.mode: project` (the default) runs scripts in the session's working directory with your active virtualenv's Python. `strict` isolates them in a temp directory with Hermes' own interpreter.

## Web search and extract

With no keys at all, `web_search` and `web_extract` rotate across the free tiers of Exa, Parallel, Firecrawl, and Keenable, and a rate-limited request fails over to the next vendor. It's a fine start and flaky under load. Pick a backend once in `hermes tools` → Web Search & Extract. From then on the stored selection (`web.backend`) wins, and adding a key to `.env` never reroutes traffic. Exa, Parallel, and Keenable appear there twice, as Free (keyless) and Paid (API key), and your choice is stored in `web.provider_tier`.

| Backend | Search | Extract | Credential |
|---|---|---|---|
| Firecrawl (default) | yes | yes | `FIRECRAWL_API_KEY`, or a self-hosted `FIRECRAWL_API_URL` |
| SearXNG | yes | no | `SEARXNG_URL` (self-hosted, free) |
| Brave (free tier), DDGS | yes | no | `BRAVE_SEARCH_API_KEY`; DDGS needs none |
| Exa, Parallel, Keenable | yes | yes | Optional: keyless ring members |
| Tavily | yes | yes | Optional: keyless once selected |
| Perplexity | yes | snippets | `PERPLEXITY_API_KEY` |
| xAI, OpenAI native | yes | no | xAI key or login; Codex login |

A cheap, reliable combination is free search plus paid extraction:

```yaml
web:
  search_backend: searxng     # free, self-hosted search
  extract_backend: firecrawl  # full-page extraction
  cache_ttl_minutes: 20       # default: repeat searches/extracts inside the window cost nothing
  extract_char_limit: 15000   # default per-page budget; the full text is saved to disk for paging
```

Three defaults worth knowing. `web.keyless_rescue` retries one failed keyed call on the free ring, so an outage degrades instead of erroring. Set `web.keyless_fallback: false` if you don't want requests leaving through anonymous free tiers at all. Local and private URLs are never cached, and `web.cache_exempt_hosts` adds staging hosts to that list. Details: [Web Search](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-search#result-caching).

## Browsers

| You want | Use | Set up |
|---|---|---|
| Headless browsing on this machine | Local (default) | Nothing; `hermes tools` → Browser Automation installs Chromium if it's missing |
| Stealth, CAPTCHA solving, residential IPs | A cloud provider: Browser Use, Browserbase, Firecrawl, or the Nous Tool Gateway | `hermes tools` → Browser Automation, plus that provider's key |
| To watch it work in your own Chrome, Brave, or Edge | `/browser connect` (CLI only) | Start the browser with `--remote-debugging-port=9222` and a **dedicated** `--user-data-dir` |
| The agent logged in as you | Real-profile browsing | `browser.use_real_profile: true` |
| Browsing on a tiny VM | The Lightpanda engine | `browser.engine: lightpanda` |

When the `browser-use` CLI is runnable, the default driver replaces the individual browser tools with one `browser_exec` tool that writes Python against the page. It's only offered to sessions that also have terminal access. `browser.backend: "off"` forces the classic tools. With a cloud provider selected, URLs on localhost or your LAN automatically go to a local browser (`browser.auto_local_for_private_urls`), so the provider never sees them.

**Real-profile browsing** copies your default browser's active profile (cookies, saved logins) into `~/.hermes/browser-profile/` and drives your real browser binary headless on that copy. It's off by default, and turning it off deletes the copy on the next browser use. Pages the agent visits run with your real logins, which the docs call "a consent-gated convenience, not an isolation boundary." Only enable it for work you'd do yourself. Quit the browser before a session starts: Windows can't copy a profile the browser has open, and on macOS and Linux a running browser usually holds its login database locked. With `browser.real_profile_autoclose: true` Hermes offers to close it for you, and still asks first before it runs `hermes browser close-profile`, which loses unsaved tabs. Pin one of several browser profiles with `browser.real_profile_pin`.

## Vision, images, and speech

- **Vision.** When your main model can see and its provider accepts images in tool results (Anthropic, OpenAI, Azure OpenAI, Gemini 3.x), `vision_analyze` hands it the raw pixels and makes no extra call. Only a text-only main model gets a second model's text description. Setting an explicit `auxiliary.vision` backend forces that lossy describe-in-text path for every image, so leave it alone unless your main model is text-only ([chapter 05](./05-token-budget.md#lever-3-put-side-tasks-on-a-cheap-model)). `agent.image_input_mode` (`auto`, `native`, `text`) makes the choice explicit.
- **Images.** `image_generate` uses FAL by default (`FAL_KEY`). OpenAI, xAI, and others are selectable in `hermes tools`. It's deferred behind tool search, so leaving it on costs little.
- **Speech.** `text_to_speech` defaults to Edge TTS (free, no key). ElevenLabs, OpenAI, Gemini, and local Piper, KittenTTS, and NeuTTS are options (`tts.provider`). Transcription of voice notes defaults to local faster-whisper. Picking **Local Whisper** in `hermes tools` → Speech-to-Text installs it.
- **Nous Tool Gateway.** Paid Nous Portal subscribers can route web, image generation, TTS, and the cloud browser through one subscription: pick **Nous Subscription** for each tool in `hermes tools`. `hermes portal info` shows what's routed where.

Whatever you pick in `hermes tools` is stored (`web.backend`, `image_gen.provider`, `tts.provider`, `stt.provider`, `browser.cloud_provider`) and wins. A key sitting in `.env` doesn't silently switch providers.

## Computer use

`computer_use` drives desktop apps (clicking, typing, scrolling, dragging) in the background on macOS, Windows, and Linux, through the open-source `cua-driver`. Your cursor doesn't move and focus doesn't change. It works with any tool-calling model. A vision model is best, and text-only models fall back to accessibility-tree mode.

```bash
hermes computer-use install       # the installer usually did this already
hermes computer-use doctor        # the check matrix: permissions, identity, version
hermes computer-use permissions   # macOS: Accessibility + Screen Recording
```

The toolset is on by default in the CLI and only activates once `cua-driver` is present. Linux needs a display server (Xvfb on a headless host).

Safety defaults are sensible. Every click, keystroke, drag, and scroll goes through the same approval gate as dangerous shell commands. Where nobody can answer (cron, headless and unattended runs), the action is refused unless you run with `--yolo`. Emptying the trash, logging out, and typing `curl … | bash` are hard-blocked. For repeatable automation, `computer_use.permission_mode: bounded` plus a capability manifest you review once replaces per-action prompts. For anything that happens in a web page, use the browser toolset instead: it's faster, cheaper, and needs no desktop permissions.

## MCP done right

MCP servers add tools from outside Hermes: GitHub, Linear, databases, internal APIs. Adding one is easy. The work is keeping each server's surface small and its code trustworthy.

### Add a server

```bash
hermes mcp catalog                    # Nous-reviewed servers (65 at v2026.9.21)
hermes mcp install deepwiki           # install one; prompts for keys or OAuth, then a tool checklist
hermes mcp add linear --url https://mcp.linear.app/mcp --auth oauth
hermes mcp add codex --preset codex   # the Codex CLI's own MCP server
hermes mcp test linear                # connects and lists tools; exit 0 ok, 1 failed, 3 not configured
hermes mcp add project_fs --command npx --args -y @modelcontextprotocol/server-filesystem@<version> /home/you/code/app
```

`--args` must come last, because it takes the rest of the line. Put `--env KEY=VALUE` before it.

Or write it in `config.yaml`. Both kinds of server look like this:

```yaml
mcp_servers:
  project_fs:                    # stdio: Hermes spawns and supervises the process
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem@<version>", "/home/you/code/app"]
    idle_timeout_seconds: 900    # recycle it after 15 idle minutes (memory-hungry servers)
  linear:                        # HTTP: a remote endpoint
    url: https://mcp.linear.app/mcp
    auth: oauth
    trust: untrusted             # every write-capable tool call asks for approval
    tools:
      exclude: ["delete_*"]      # globs match the server's own tool names
```

- **stdio servers** get a minimal environment (`PATH`, `HOME`, `USER`, `LANG`, `LC_ALL`, `TERM`, `SHELL`, `TMPDIR`, `XDG_*`) plus whatever you list under `env`. Reference secrets as `${VAR}` and keep the values in `~/.hermes/.env`. Snippets copied from Cursor or Claude Code configs work unchanged, and `hermes import-agent` migrates a Claude Code setup.
- **HTTP servers** use Streamable HTTP. A 400 or 405 on the first request usually means the server only speaks SSE: add `transport: sse`.
- **OAuth** (`auth: oauth`) is automatic: discovery, PKCE, and refresh, with tokens cached per profile under `mcp-tokens/`. On a headless host, `hermes mcp login linear --flow device` works when the server supports device codes. Otherwise paste the redirect URL back at the prompt, or tunnel the callback port over SSH ([OAuth over SSH](https://hermes-agent.nousresearch.com/docs/guides/oauth-over-ssh)). When a refresh token dies, the gateway parks that server with a warning in `gateway.log` until you run `hermes mcp login <name>`, or `hermes mcp reauth --all` for every server.

### Filter what the model sees

`hermes mcp configure <name>` reopens the tool checklist and writes `mcp_servers.<name>.tools.include`. Filtering by hand works the same way. `include` and `exclude` take exact names or globs, and `include` wins when both are set. `tools.resources: false` and `tools.prompts: false` drop the extra wrapper tools. `enabled: false` parks a server without deleting it. `hermes tools disable <server>:<tool>` adds one tool to that server's `exclude` list, for every platform.

To keep a server off one platform entirely, list the MCP servers that platform may use, by bare name, in its toolset list. Listed servers become an allowlist, and the special entry `no_mcp` removes them all. This behavior comes from `hermes_cli/tools_config.py` at v0.21.4 (checked on a scratch install), not from the docs, and the `mcp-<server>` spelling does *not* act as an allowlist here:

```yaml
platform_toolsets:
  telegram: [web, memory, session_search, skills, cronjob, clarify, vision, linear]  # only Linear's MCP tools on Telegram
```

MCP tools register as `mcp__<server>__<tool>` (with hyphens and dots turned into underscores), but filters use the server's original tool names.

### What MCP costs you

- **Schemas: little.** Tool search defers MCP tools by default, so a 40-tool server costs a listing line per tool until the agent needs one ([chapter 05](./05-token-budget.md#tool-search-is-already-working-for-you)).
- **Reloads: a full cache miss.** `/reload-mcp` rebuilds the tool set, and so does editing `mcp_servers` in `config.yaml` while a CLI session runs (`mcp.auto_reload_on_config_change`, on by default). The next call re-sends the whole prefix at full price. `/reload-mcp` asks before it does that (`approvals.mcp_reload_confirm`, on by default). If other tools rewrite your config often, set the auto-reload key to `false` and reload deliberately between sessions.
- **Results.** Output above 50,000 characters (`tool_budget.mcp_result_size_chars`) spills to a file the agent can page through.
- **Your model, on the server's behalf.** MCP servers can ask Hermes to run LLM calls for them (sampling). It's on by default, capped at 10 requests a minute and 4,096 tokens each. Turn it off with `sampling: {enabled: false}` for any server that doesn't need it.

At startup Hermes connects at most 4 servers at a time (`mcp.discovery_concurrency`), so a long server list doesn't spawn every process at once.

### Vet before you trust

An MCP server is code you run with your credentials. Before adding one:

1. **Prefer the catalog, and still read the manifest.** Catalog entries live in `optional-mcps/` in the Hermes repo, and installing one runs its `install.bootstrap` commands. The picker prints the `source:` repo so you can check it. This isn't theoretical: the [v0.21.0 release notes](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.31) record removing a Blender MCP integration after its upstream was compromised.
2. **Pin versions:** `npx -y pkg@1.2.3` or `uvx pkg==1.2.3`. `hermes security audit` checks pinned `npx`/`uvx` servers against OSV.dev and silently skips unpinned ones (`hermes_cli/security_audit.py`).
3. **Shrink the surface:** an `include` list for anything that can write, and a narrow token for each server.
4. **Mark what you don't control `trust: untrusted`**, so every tool without a read-only annotation needs your approval. Unknown trust values fail closed. The same annotation decides retries: when a remote session expires mid-call, only read-only tools are replayed, and anything else returns `outcome_uncertain` rather than running twice.
5. **Audit on a schedule:** `hermes security audit --fail-on high` scans the Hermes venv, plugin requirements, and pinned MCP packages, and exits non-zero on a finding.

### Hermes as an MCP server

`hermes mcp serve` turns it around: Claude Code, Cursor, Codex, or any MCP client can list your Hermes conversations, read history, wait for new messages, send messages through your connected platforms, and answer pending approvals. That's 10 tools over stdio. Reads work without the gateway. Sends need it running, and they're text only.

```json
{ "mcpServers": { "hermes": { "command": "hermes", "args": ["mcp", "serve"] } } }
```

## Plugins from the catalog

Plugins are Python add-ons that register tools, hooks, slash commands, platforms, or providers. The curated catalog is the sane way to get them: each entry is human-reviewed at an exact 40-character commit SHA, and installs check out that commit, not a branch tip. At v2026.9.21 it holds 228 entries, 5 of them maintained by Nous.

```bash
hermes plugins search telegram
hermes plugins info snyk          # details for one catalog entry
hermes plugins install snyk       # shows declared tools/hooks/env vars, then checks out the reviewed pin and scans it
hermes plugins enable snyk        # installed is not enabled
hermes plugins list               # catalog installs show as catalog:<tier>@<sha>
hermes plugins update snyk        # re-pins only when the catalog pin moved (never a git pull)
```

- **The install-time scan** grades every install and update `safe`, `caution` (you confirm), or `dangerous` (blocked, and `--force` won't override it).
- **Custom sources** (`owner/repo` or a git URL) skip review and install the branch tip with a warning. For code you trust, pin it: `hermes plugins install owner/repo --ref <40-char-sha>`. Never use `--allow-removed`, which bypasses the blocklist of plugins pulled for security reasons.
- **Project plugins** in a repo's `.hermes/plugins/` load only with `HERMES_ENABLE_PROJECT_PLUGINS=true`. Leave that unset for repos you didn't write.
- **A catalog entry is a point-in-time review, not an audit.** Read the code of anything you hand credentials to.

**After upgrading: the compat cutoff.** Since 2026-09-14, plugins that import module paths removed in the September 2026 refactor are disabled at load, and `hermes plugins list` shows why. `hermes plugins compat` prints every offending `file:line` with the new path. If you can't wait for the author, `plugins.allow_deprecated_imports: true` keeps them loading until the old paths are deleted for good. Treat it as a stopgap.

**Bundled plugins** ship disabled. Enable them with `hermes plugins enable <name>`. The useful ones: `disk-cleanup` (tracks and removes the agent's temp files), `security-guidance` (warns when written code matches 25 dangerous patterns, and blocks it with `SECURITY_GUIDANCE_BLOCK=1`), and `observability/langfuse` (traces to Langfuse).

## Hooks, LSP, and checkpoints

### Hooks

Hooks run your code at lifecycle points and cost no tokens. **Shell hooks** are the one to reach for: a `hooks:` block in `config.yaml` runs any script, and a `pre_tool_call` hook that exits with code 2 blocks the call. That makes a policy gate a few lines of YAML:

```yaml
hooks:
  pre_tool_call:
    - matcher: "terminal"                          # regex on the tool name
      command: "~/.hermes/agent-hooks/policy.sh"   # gets JSON on stdin; exit 2 = block
      timeout: 5
      fail_closed: true                            # a crashed or timed-out gate blocks instead of allowing
```

Each new `(event, command)` pair needs your approval once, and under the gateway or cron a new hook stays silently unregistered until it has it. `hermes hooks test pre_tool_call --for-tool terminal` fires your hooks against a synthetic payload, and `hermes hooks doctor` flags scripts edited since you approved them. Consent, outbound webhooks, and gateway hooks are in [chapter 11](./11-automation.md#hooks-react-to-what-the-agent-does). Plugins register hooks too (`ctx.register_hook`), with the same events.

### LSP

Inside a git repository, every `write_file` and `patch` is followed by a check from a real language server (pyright, gopls, typescript-language-server, rust-analyzer: 28 in all, per `hermes lsp list`). The agent sees the type errors *its edit introduced*, not just syntax errors. Missing servers are installed on demand into Hermes' own directory (`lsp.install_strategy: auto`).

```bash
hermes lsp status              # which languages get semantic diagnostics today
hermes lsp install typescript  # install one now instead of on first edit
```

`lsp.exclude_roots` skips one huge monorepo whose server can't answer in time. `lsp.enabled: false` turns the layer off and falls back to syntax checks.

### Checkpoints and /rollback

Checkpoints are **off by default**. When enabled, Hermes snapshots a project into a shadow git store (your repo's own `.git` is untouched) before `write_file`, `patch`, and destructive terminal commands (`rm`, `mv`, `sed -i`, `git reset`, output redirects, and others), at most once per directory per turn.

```bash
hermes config set checkpoints.enabled true   # or per session: hermes chat --checkpoints
```

```text
/rollback              # list checkpoints with change stats
/rollback diff 2       # preview what restoring would change
/rollback 2            # restore; files you edited by hand afterwards are kept
/rollback 2 --all      # restore everything, including your hand edits
```

A restore also rewinds the last conversation turn, so the agent's context matches the files. Snapshots are skipped for `/`, `$HOME`, and trees over 50,000 files. `hermes checkpoints status` shows what the store costs you, and projects untouched for 7 days are pruned automatically.

## Starter kits

Starting points, not rules. Measure each with `hermes prompt-size --platform <name>`.

| Kit | Keep | Drop | Worth adding | Backend |
|---|---|---|---|---|
| **Coding** (CLI) | `terminal`, `file`, `code_execution`, `web`, `skills`, `memory`, `session_search`, `delegation`, `todo`, `clarify` | `tts`, `image_gen`, `computer_use`; `browser` unless you test web UIs | Catalog MCP: `context7` (library docs, no key), `deepwiki`; `sentry` or `gitlab` if you use them. LSP on. Checkpoints on. | `local`, with `docker` for untrusted repos |
| **Research** | `web`, `browser`, `vision`, `code_execution`, `memory`, `session_search`, `delegation`, `skills`, `clarify` | `tts`, `computer_use`, `cronjob` | `deepwiki`, `microsoft-learn`, `aws-knowledge` (all keyless); a keyed search backend | `local` |
| **Personal assistant** (Telegram) | `web`, `memory`, `session_search`, `skills`, `cronjob`, `clarify`, `vision` | `browser`, `code_execution`, `delegation`, `computer_use` | `todoist`, `notion`, or `linear` (OAuth), allowlisted to this platform as shown above | `docker` if anyone else can message it |
| **Homelab ops** | `terminal`, `file`, `code_execution`, `cronjob`, `web`, `memory`, `skills` | `browser`, `tts`, `image_gen`, `vision`, `computer_use` | `homeassistant` (`HASS_TOKEN`); `grafana` or `betterstack` from the catalog | `ssh` to the box it manages, as a dedicated user |

## Verify it

```bash
hermes tools list --platform telegram    # the toolsets each surface really gets
hermes prompt-size --platform telegram   # what those toolsets cost per call
hermes mcp list                          # configured servers
hermes mcp test <name>                   # connect + tool discovery for one server
hermes plugins list                      # enabled / disabled / not enabled, with provenance
hermes plugins compat                    # exit 1 means a plugin still uses removed paths
hermes security audit                    # OSV check of venv, plugins, pinned MCP servers
hermes lsp status
hermes checkpoints status
```

In a session, `/context` shows the tool-definition tokens you're paying for and `/plugins` shows what actually loaded. The MCP startup line in `agent.log` names every server that failed and why, for example `MCP: registered 116 tool(s) from 4 server(s) (2 failed: github (Connection closed); …)`.

## Gotchas

- **Container backends skip approval prompts and checkpoints.** `docker` (without host mounts), `singularity`, `modal`, `daytona`, and `vercel_sandbox` don't ask before destructive commands, and `/rollback` refuses to restore on them ([Security](https://hermes-agent.nousresearch.com/docs/user-guide/security#terminal-backend-security-comparison), [Checkpoints](https://hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback)).
- **Agent commands hang or time out, but work in your own terminal.** A slow or interactive `.bashrc` (nvm, prompts, `tmux` attach) runs on every agent shell. Add the standard non-interactive guard at the top ([Tools](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools#shell-startup-files-and-non-interactive-commands)).
- **`/browser connect` is CLI-only.** Sent from Telegram or Discord, it goes to the agent as plain text. On Chrome 136 and later, `--remote-debugging-port` is ignored for your default profile, so always pass a dedicated `--user-data-dir` ([Browser](https://hermes-agent.nousresearch.com/docs/user-guide/features/browser#local-chromium-family-browser-via-cdp-browser-connect)).
- **An MCP OAuth login times out when you add the server mid-session.** The config watcher's reload allows 30 seconds. Add the entry, then run `hermes mcp login <name>` from a fresh terminal, which waits up to 5 minutes ([MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp#oauth-authenticated-http-servers)).
- **OAuth MCP servers kept asking you to log in again.** A refresh bug fixed in v0.21.2 erased the refresh token ([release notes](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.9.11)). Update.
- **Windows desktop: `command: npx` fails with `WinError 2` and "0 tool(s) from 0 server(s)".** Fixed in v0.21.4 ([#111937](https://github.com/NousResearch/hermes-agent/issues/111937), [PR #112242](https://github.com/NousResearch/hermes-agent/pull/112242)).
- **Plugins vanished after an upgrade.** That's the 2026-09-14 compat cutoff. Run `hermes plugins compat` ([Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)).
- **A new shell hook does nothing under the gateway or cron.** It's waiting for consent it can't ask for ([Hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks#consent-model)).
- **`web_extract` output ends with `[TRUNCATED]`.** That's the 15,000-character budget working. The full text is on disk, and the footer tells the agent how to page it. Raise `web.extract_char_limit` if you need more inline.

## Go deeper

- Official: [Tools & Toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools) · [Toolsets Reference](https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference) · [Code Execution](https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution) · [Web Search](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-search) · [Browser](https://hermes-agent.nousresearch.com/docs/user-guide/features/browser) · [Computer Use](https://hermes-agent.nousresearch.com/docs/user-guide/features/computer-use) · [MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) · [MCP Config Reference](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference) · [Use MCP with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes) · [Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins) · [Plugin Catalog](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugin-catalog) · [Built-in Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/built-in-plugins) · [LSP](https://hermes-agent.nousresearch.com/docs/user-guide/features/lsp) · [Checkpoints](https://hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback) · [Tool Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway)
- In this guide: [05 · The Token Budget](./05-token-budget.md) · [10 · Messaging](./10-messaging.md) · [13 · Security](./13-security.md)

---
[← Previous: 08 · Skills](./08-skills.md) · [Guide index](../README.md#the-guide) · [Next: 10 · Messaging: Chat From Anywhere →](./10-messaging.md)
