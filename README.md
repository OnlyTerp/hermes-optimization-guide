# Hermes Optimization Guide

> **Tested on Hermes Agent (latest) — April 2026** · 5 parts · Battle-tested on a live production deployment

### Make Your Hermes Agent Actually Work — Setup, Migration, Knowledge Graphs, Telegram, and Self-Improving Skills
#### Full setup walkthrough, OpenClaw migration, LightRAG graph RAG, Telegram bot integration, and on-the-fly skill creation

*By Terp - [Terp AI Labs](https://x.com/OnlyTerp)*

---

## Table of Contents

1. [Setup](./part1-setup.md) — Install Hermes, configure your provider, first-run walkthrough
2. [OpenClaw Migration](./part2-openclaw-migration.md) — Move your OpenClaw data, config, skills, and memory into Hermes
3. [LightRAG — Graph RAG](./part3-lightrag-setup.md) — Set up a knowledge graph that actually understands relationships, not just text similarity
4. [Telegram Bot](./part4-telegram-setup.md) — Connect Hermes to Telegram for mobile access, voice memos, and group chats
5. [On-the-Fly Skills](./part5-creating-skills.md) — Ask Hermes to create new skills that optimize your workflow automatically

---

## The Problem

If you're running a stock Hermes setup (or migrating from OpenClaw), you're probably dealing with:

- **Installation confusion.** The docs cover the basics but don't tell you what to configure first or what matters.
- **Lost knowledge from OpenClaw.** You spent weeks building memory, skills, and workflows — now they're stuck in the old system.
- **Basic memory that can't reason.** Vector search finds similar text but can't answer "what decisions led to X and who was involved?"
- **No mobile access.** Sitting at a terminal is fine until you need to check something from your phone.
- **Repetitive prompting.** You keep asking the agent to do the same multi-step task the same way, every time.

## What This Fixes

After this guide:

| Problem | Solution | Result |
|---------|----------|--------|
| Fresh install | Step-by-step setup | Working agent in under 5 minutes |
| OpenClaw data stuck | Automated migration | Skills, memory, config all transferred |
| Shallow memory | LightRAG graph RAG | Entities + relationships, not just text chunks |
| Desktop only | Telegram integration | Chat from anywhere, voice memos, group support |
| Repetitive prompts | Agent-created skills | Agent saves workflows as reusable skills automatically |

---

## Prerequisites

- A Linux/macOS machine (or WSL2 on Windows)
- Python 3.11+ and Git
- An API key for at least one LLM provider (Anthropic, OpenAI, OpenRouter, etc.)
- Optional: Ollama for local embeddings (free vector search)

---

## How the Pieces Fit Together

```
You (any device)
    ↓
Hermes Agent (lean context, ~5KB injected per message)
    ↓
┌──────────────────────────────────────────┐
│  Skills (loaded on demand, 0 cost idle) │
│  Memory (compact, vector-searched)       │
│  LightRAG (entity graph, deep recall)    │
│  Telegram (mobile + group access)        │
└──────────────────────────────────────────┘
    ↓
LLM Provider (Claude, GPT, local models)
```

**The key insight:** Everything is modular. Install what you need, skip what you don't. The agent adapts.

---

## Quick Start

```bash
# 1. Install Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. Configure
hermes setup

# 3. Start chatting
hermes
```

For the full walkthrough including optimization, read each part in order.

---

> **Note:** Based on the official Hermes Agent documentation and real production usage. No private credentials, API keys, or personal data included.
