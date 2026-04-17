# Architecture Diagrams

All diagrams are Mermaid — they render natively on GitHub. Copy-paste into your own docs as needed.

---

## Top-level Hermes architecture

```mermaid
flowchart LR
  subgraph Inputs[16 Inputs]
    CLI[CLI]
    Telegram
    Discord
    Slack
    iMessage
    WeChat
    Email
    SMS
    Webhooks
    Cron
    Voice
  end

  subgraph Core[Hermes Agent]
    Gateway[Gateway Router]
    Context[Context Engine]
    Approval[Approval Layer]
    Router[Model Router]
    SkillLoader[Skill Loader]
    MemoryR[Memory Read]
    MemoryW[Memory Write]
  end

  subgraph Providers[Model Providers]
    Anthropic
    OpenAI
    Google
    Cerebras
    Moonshot
    ZAI[z.ai]
    xAI
    Local
  end

  subgraph Tools[Tools]
    NativeTools[Native tools]
    Gateway2[Nous Tool Gateway]
    MCP[MCP Servers]
    Subagents[Subagents / Delegation]
    Coding[Coding Agents<br/>Claude Code / Codex / Gemini CLI]
  end

  subgraph Storage[Storage]
    Vector[(Vector DB)]
    LightRAG[(LightRAG KG)]
    Mem0[(mem0 cloud)]
    Skills[(Skills)]
    Logs[(Audit logs)]
  end

  Inputs --> Gateway
  Gateway --> Context
  Context --> SkillLoader
  SkillLoader --> MemoryR
  MemoryR --> Vector
  MemoryR --> LightRAG
  MemoryR --> Mem0
  Context --> Router
  Router --> Providers
  Router --> Approval
  Approval --> Tools
  Tools --> MemoryW
  MemoryW --> Vector
  MemoryW --> LightRAG
  MemoryW --> Mem0
  MemoryW --> Logs
```

---

## MCP integration flow

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant H as Hermes
  participant M as MCP Server
  participant E as External API

  U->>H: "open a PR for this fix"
  H->>H: Load skill + config
  H->>M: tools/list
  M-->>H: [create_pull_request, ...]
  H->>H: Select tool
  H->>H: Approval layer (denylist, allowlist, channel)
  H->>M: tools/call create_pull_request
  M->>E: HTTPS to GitHub
  E-->>M: {html_url, number}
  M-->>H: result
  H->>H: Write to audit log
  H-->>U: "PR opened: #342 — approve?"
```

---

## Coding-agent delegation (OpenClaw pattern)

```mermaid
flowchart TB
  subgraph Telegram[Telegram Topic "feature-x"]
    Msg1[msg: implement foo]
    Msg2[msg: add tests]
    Msg3[msg: fix the null check]
  end

  subgraph Hermes[Hermes]
    Bind[bind-thread mapping]
  end

  subgraph Runtime[Persistent Claude Code]
    Sess[session state: cwd, branch, env]
  end

  Msg1 --> Bind
  Msg2 --> Bind
  Msg3 --> Bind
  Bind --> Sess

  Sess --> Git[(git repo)]
  Sess --> Bash[bash tool]
  Sess --> Read[Read tool]
  Sess --> Edit[Edit tool]
```

---

## Remote-sandbox sync flow (PR #8018)

```mermaid
sequenceDiagram
  autonumber
  participant L as Local Hermes ($5 VPS)
  participant R as Remote Sandbox (Modal)
  participant G as Git Remote

  L->>R: Spin up (if not running)
  L->>R: tar-pipe push (new files + deltas)
  R->>R: Do the work (Claude Code / build / tests)
  R-->>L: Stream stdout/stderr
  Note over L,R: On teardown (or /sync):
  R->>R: Compute SHA-256 of each changed file
  L->>L: Compare hashes
  R->>L: tar-pipe pull of diffed files
  L->>G: git commit & push (only if user approves)
```

---

## Observability stack

```mermaid
flowchart LR
  Hermes --> L1[Level 1: journald logs]
  Hermes --> L2[Level 2: /usage + dashboard]
  Hermes -- OTLP / OpenAI-compatible proxy --> L3
  subgraph L3[Level 3: external]
    Langfuse
    Helicone
    Phoenix
  end
  L3 --> Alerts[PagerDuty / Discord / Webhook]
  L2 --> Alerts
```

---

## Security layers (Part 19)

```mermaid
flowchart LR
  Input[Input<br/>Telegram/Discord/Email/Webhook] --> L1[Layer 1<br/>Origin labeling]
  L1 --> L2[Layer 2<br/>Approval + denylist]
  L2 --> L3[Layer 3<br/>Secrets redaction]
  L3 --> L4[Layer 4<br/>Webhook sig validation]
  L4 --> L5[Layer 5<br/>SSRF / redirect guard]
  L5 --> L6[Layer 6<br/>MCP trust levels]
  L6 --> L7[Layer 7<br/>Quarantine profile]
  L7 --> Exec[Tool execution]
  Exec --> Audit[(Audit log)]
```
