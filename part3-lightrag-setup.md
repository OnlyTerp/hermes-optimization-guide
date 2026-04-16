# Part 3: LightRAG — Graph RAG That Actually Works

*From "find similar text" to "reason about relationships." The single biggest intelligence upgrade you can make.*

---

## The Problem With Basic Memory

Hermes ships with vector-based memory search. It finds documents that are textually similar to your query. That works for simple lookups, but it has a fundamental ceiling: **it finds what's similar, not what's connected.**

Ask "what hardware decisions were made and why?" and vector search returns files that all mention GPUs. It can't traverse from a decision → the person who made it → the project it affected → the lesson learned afterward.

**Graph RAG fixes this.** It builds a knowledge graph (entities + relationships) alongside your vector database, then searches both simultaneously.

### Naive RAG vs Graph RAG

| | Naive RAG (Default) | Graph RAG (LightRAG) |
|---|---|---|
| **Indexes** | Text chunks as vectors | Entities, relationships, AND text chunks |
| **Retrieves** | Similar text (cosine similarity) | Connected knowledge (graph traversal + similarity) |
| **Answers** | "Here's what the docs say about X" | "Here's how X relates to Y, who decided Z, and why" |
| **Scales** | Degrades at 500+ docs (too many partial matches) | Improves with more docs (richer graph) |
| **Cost** | Cheap (embedding only) | More expensive upfront (LLM extracts entities) but cheaper at query time |

---

## LightRAG: The Best Graph RAG For Personal Use

[LightRAG](https://github.com/HKUDS/LightRAG) is an open-source graph RAG framework from HKU (EMNLP 2025 paper). It competes with Microsoft's GraphRAG at a fraction of the cost.

**Why LightRAG over alternatives:**

| Tool | Graph | Vector | Web UI | Self-Hosted | API | Cost |
|------|-------|--------|--------|-------------|-----|------|
| **LightRAG** | Yes | Yes | Yes | Yes | REST API | Free |
| Microsoft GraphRAG | Yes | Yes | No | Yes | No | 10-50x more |
| Graphiti + Neo4j | Yes | No (separate) | No (Neo4j browser) | Yes | Build your own | Free but manual |
| Plain vector search | No | Yes | No | Yes | Yes | Free |

LightRAG does vector DB + knowledge graph **in parallel** during ingestion. One system, both capabilities.

---

## Installation

### Prerequisites

- Python 3.11+
- An LLM API key for entity extraction during ingestion — we recommend **Kimi 2.5** (Moonshot AI) for quality or **Cerebras + Qwen 3** for speed. Any OpenAI-compatible provider works (OpenAI, Anthropic, OpenRouter, etc.)
- An embedding API key — **Fireworks + Qwen3-Embedding-8B** recommended for high-quality 4096-dim embeddings, or use **Ollama + nomic-embed-text** locally for free

### Install LightRAG

```bash
# Create a dedicated directory
mkdir -p ~/.hermes/lightrag
cd ~/.hermes/lightrag

# Clone LightRAG
git clone https://github.com/HKUDS/LightRAG.git
cd LightRAG

# Install dependencies
pip install -e ".[api]"
```

### Set Up Environment

Create `~/.hermes/lightrag/.env`:

**Option A — Kimi 2.5 + Fireworks (recommended):**

```bash
# --- LLM for entity extraction (during ingestion) ---
LLM_BINDING=openai
LLM_MODEL=kimi-2.5                    # Best quality/cost ratio for entity extraction
LLM_BINDING_HOST=https://api.moonshot.cn/v1   # Kimi uses an OpenAI-compatible API
LLM_BINDING_API_KEY=<your-moonshot-api-key>   # Get one at https://platform.moonshot.cn

# --- Embedding model (for vector storage) ---
EMBEDDING_BINDING=fireworks
EMBEDDING_MODEL=accounts/fireworks/models/qwen3-embedding-8b   # 4096-dim, excellent quality
EMBEDDING_API_KEY=<your-fireworks-api-key>   # Get one at https://fireworks.ai
```

**Option B — Cerebras + Qwen 3 (fastest ingestion):**

```bash
# --- LLM for entity extraction (during ingestion) ---
LLM_BINDING=openai
LLM_MODEL=qwen-3-32b                  # Cerebras runs Qwen 3 at 2000+ tok/s
LLM_BINDING_HOST=https://api.cerebras.ai/v1
LLM_BINDING_API_KEY=<your-cerebras-api-key>   # Get one at https://cloud.cerebras.ai

# --- Embedding model (for vector storage) ---
EMBEDDING_BINDING=fireworks
EMBEDDING_MODEL=accounts/fireworks/models/qwen3-embedding-8b
EMBEDDING_API_KEY=<your-fireworks-api-key>
```

**Option C — Free local setup (Ollama):**

```bash
# --- LLM for entity extraction (local, free, quality may vary) ---
LLM_BINDING=ollama
LLM_MODEL=qwen3:32b                   # Or any capable local model
# No API key needed

# --- Embedding model (local, free) ---
EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=nomic-embed-text       # 768-dim, good quality, 2GB VRAM
# No API key needed
```

> **Where to get API keys:**
> - **Kimi / Moonshot:** [platform.moonshot.cn](https://platform.moonshot.cn) — sign up, create an API key
> - **Cerebras:** [cloud.cerebras.ai](https://cloud.cerebras.ai) — free tier available, very generous limits
> - **Fireworks:** [fireworks.ai](https://fireworks.ai) — sign up for an API key

### Entity Extraction Model — What to Use

This is the LLM that reads your documents and pulls out entities and relationships during ingestion. Quality here directly determines how good your knowledge graph is.

| Model | Speed | Quality | Cost | Recommendation |
|-------|-------|---------|------|----------------|
| **Kimi 2.5** | Fast | Excellent | Cheap | **What we use.** Great balance of quality, speed, and cost for entity extraction |
| **Cerebras + Qwen 3** | Blazing fast | Very good | Very cheap | **Fastest option in the world.** Cerebras inference at 2000+ tok/s makes bulk ingestion fly |
| GPT-4.1-mini | Fast | Good | Cheap | Solid fallback, well-tested |
| Claude Sonnet 4 | Medium | Excellent | Mid-range | Overkill for ingestion but works great |
| **Ollama local** | Depends on GPU | Unpredictable | Free | Untested for this use case — might mess up entity extraction quality. Use at your own risk |

> **Our recommendation:** Use **Kimi 2.5** for the best quality-to-cost ratio — it produces clean, accurate entity graphs. Switch to **Cerebras + Qwen 3** if you're doing bulk ingestion and speed is the priority (2000+ tokens/sec means you can ingest hundreds of documents in minutes). Both are cheap and reliable. We haven't tested local Ollama for entity extraction — it's free but the extraction quality is unverified and you might get a messy graph.

> **Embedding quality matters.** If you have a GPU with 8GB+ VRAM, run `nomic-embed-text` locally via Ollama for free. If you want the best quality, use **Fireworks' Qwen3-Embedding-8B** (4096 dimensions) — the search accuracy difference is dramatic. This is the embedding model we recommend regardless of which LLM you choose for entity extraction.

---

## Running the Server

### Start the REST API

```bash
cd ~/.hermes/lightrag/LightRAG

# Start the API server (binds to localhost by default)
lightrag-server --host 127.0.0.1 --port 9623
```

The server starts on `http://localhost:9623` with:
- **REST API** for ingestion and querying
- **Web UI** at `http://localhost:9623/webui` for browsing the knowledge graph
- **Health check** at `http://localhost:9623/health`

> **Security warning:** The LightRAG REST API has **no built-in authentication**. Always bind to `127.0.0.1` (localhost only) — never `0.0.0.0`. If you need remote access, put it behind a reverse proxy (nginx, Caddy) with authentication, or use SSH tunneling. Anyone who can reach this port can query, ingest, or delete your knowledge graph data.

### Run as a Background Service

```bash
# Using nohup
nohup lightrag-server --port 9623 > ~/.hermes/lightrag/server.log 2>&1 &

# Or use hermes to manage it
hermes background "cd ~/.hermes/lightrag/LightRAG && lightrag-server --port 9623"
```

---

## Ingesting Your Knowledge

### How Ingestion Works

```
Document (markdown, text, PDF, etc.)
    ↓
Chunking (text split into segments)
    ↓
┌─────────────────┐    ┌──────────────────┐
│ Embedding Model │    │ LLM Entity       │
│ (vector storage)│    │ Extraction       │
└────────┬────────┘    └────────┬─────────┘
         ↓                      ↓
   Vector Database       Knowledge Graph
   (similarity search)   (entity relationships)
```

For each document, LightRAG:
1. Chunks the text and embeds it (standard vector RAG)
2. Uses an LLM to extract **entities** (people, tools, projects, concepts) and **relationships** (who decided what, what depends on what)
3. Stores both in parallel — vectors for similarity, graph for structure

### Ingest Documents via API

```bash
# Ingest a single file
curl -X POST http://localhost:9623/documents/upload \
  -F "file=@/path/to/your/document.md"

# Ingest a text string directly
curl -X POST http://localhost:9623/documents/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Your knowledge content here...", "description": "Source description"}'

# Ingest all files in a directory
for file in ~/.hermes/memories/*.md; do
  curl -X POST http://localhost:9623/documents/upload -F "file=@$file"
  echo "Ingested: $file"
done
```

### What to Ingest

Feed LightRAG everything your agent needs to "know":

- **Memory files** — `~/.hermes/memories/*.md`
- **Project docs** — README files, design docs, decision logs
- **Chat summaries** — Exported conversation summaries
- **Notes** — Any markdown/text knowledge you want searchable
- **Code comments** — Extracted from important codebases

> **Start with your memory files and project docs.** These give the graph the most value — decisions, people, projects, and their relationships.

---

## Querying the Graph

### Query Modes

LightRAG has four query modes:

| Mode | Best For | How It Works |
|------|----------|-------------|
| `naive` | Simple keyword lookups | Vector search only (like basic RAG) |
| `local` | Specific entity facts | Entity-focused graph traversal |
| `global` | Cross-document relationships | Relationship-focused traversal |
| `hybrid` | General questions (default) | Both local + global combined |

### Query via API

```bash
# Hybrid query (recommended default)
curl -X POST http://localhost:9623/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What infrastructure decisions were made and why?",
    "mode": "hybrid",
    "only_need_context": false
  }'

# Local mode — specific entity facts
curl -X POST http://localhost:9623/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tell me about the 5090 PC setup",
    "mode": "local"
  }'

# Global mode — relationship discovery
curl -X POST http://localhost:9623/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do the different projects relate to each other?",
    "mode": "global"
  }'
```

### Get Just the Context (for your own LLM)

```bash
curl -X POST http://localhost:9623/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What models are running on what hardware?",
    "mode": "hybrid",
    "only_need_context": true
  }'
```

This returns the raw context chunks without generating an answer — useful for feeding into your own pipeline or Hermes' LLM.

---

## Integrating With Hermes

### Create a LightRAG Skill

Create `~/.hermes/skills/research/lightrag/SKILL.md`:

```markdown
---
name: lightrag
description: Query the LightRAG knowledge graph for past decisions, infrastructure, projects, and lessons learned. Use before saying "I don't remember."
---

# LightRAG Knowledge Graph

Query the LightRAG knowledge graph for past decisions, infrastructure, projects, and lessons learned.

## When To Use
- User asks about past work, decisions, or "what happened with X"
- Need context on projects, hardware, or configurations
- Remembering lessons learned or past issues
- Any question where you'd say "I don't remember" — use this FIRST

## Usage
```bash
curl -s -X POST http://localhost:9623/query \
  -H "Content-Type: application/json" \
  -d '{"query": "YOUR QUERY", "mode": "hybrid", "only_need_context": true}'
```

## Search Modes
- `hybrid` (default): Combined vector + graph search
- `local`: Entity-focused (specific facts)
- `global`: Relationship-focused (how things connect)
- `naive`: Vector-only (simple lookups)

## Important
- ALWAYS search this before saying "I don't remember"
- Results supersede general knowledge about the setup
- Reference entity names when citing results
```

### Query from a Script

Create `~/.hermes/skills/research/lightrag/scripts/lightrag_search.py`:

```python
#!/usr/bin/env python3
"""LightRAG search script for Hermes skill integration."""
import json
import sys
import urllib.request

def search(query: str, mode: str = "hybrid") -> str:
    url = "http://localhost:9623/query"
    payload = json.dumps({
        "query": query,
        "mode": mode,
        "only_need_context": True
    }).encode()
    
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result.get("response", result.get("data", str(result)))
    except Exception as e:
        return f"LightRAG query failed: {e}"

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not query:
        print("Usage: lightrag_search.py <query>")
        sys.exit(1)
    print(search(query))
```

---

## Optimizing Search Quality

### 1. Tune Entity Extraction

The quality of your graph depends on entity extraction. In LightRAG's config:

```yaml
# More entities = richer graph, slower ingestion
entity_extract_max_gleaning: 5    # Default: 3. Higher = more thorough

# Chunk size affects entity density
chunk_token_size: 1200             # Default: 1200. Smaller = more entities per doc
chunk_overlap_token_size: 100      # Default: 100
```

### 2. Use High-Quality Embeddings

Embedding quality directly impacts vector search accuracy:

| Model | Dimensions | Quality | Cost |
|-------|-----------|---------|------|
| nomic-embed-text (Ollama) | 768 | Good | Free (local) |
| Qwen3-Embedding-8B (Fireworks) | 4096 | Excellent | ~$0.001/1K tokens |
| text-embedding-3-large (OpenAI) | 3072 | Very Good | ~$0.00013/1K tokens |

> **If search quality matters, use 4096-dimension embeddings.** The difference between 768 and 4096 dims is like the difference between 720p and 4K — you catch details you'd otherwise miss.

### 3. Reindex After Bulk Changes

After ingesting a large batch of new documents:

```bash
# Check entity count
curl http://localhost:9623/graph/label/list | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} entities')"
```

### 4. Use the Right Query Mode

Don't always default to `hybrid`. Use:
- `local` when asking about a specific thing ("Tell me about the GPU setup")
- `global` when asking about connections ("How do the projects relate?")
- `hybrid` for general questions ("What decisions were made last week?")

### 5. Monitor and Prune

The Web UI at `http://localhost:9623/webui` lets you:
- Browse the knowledge graph visually
- See entity relationships
- Identify orphaned or redundant entities

---

## Web UI

Once the server is running, open `http://localhost:9623/webui` in your browser. You can:

- **Search** the graph with any query mode
- **Visualize** entity relationships as a network graph
- **Browse** all entities and their connections
- **Inspect** raw chunks and their source documents

---

## Troubleshooting

### "Connection refused" on query

The server isn't running. Start it:
```bash
cd ~/.hermes/lightrag/LightRAG && lightrag-server --port 9623
```

### Slow ingestion

Entity extraction is LLM-bound. Speed it up:
- Use a faster model for ingestion (Cerebras + Qwen 3 is the fastest option, or Kimi 2.5)
- Process documents in parallel batches
- Use a local model if you have GPU capacity

### Empty or irrelevant results

- Check that documents were actually ingested (Web UI → entities)
- Try different query modes (`local` vs `global` vs `hybrid`)
- Rephrase your query — be more specific about entities
- Check embedding model is actually running (`curl http://localhost:11434/api/tags` for Ollama)

### Duplicate entities after re-ingestion

LightRAG merges similar entities automatically, but exact duplicates can happen. Use the Web UI to manually clean up, or reindex from scratch:
```bash
# Nuclear option: wipe and reingest
rm -rf ~/.hermes/lightrag/LightRAG/rag_storage/*
# Then re-ingest your documents
```

---

## What's Next

- **Need mobile access?** → [Part 4: Telegram Setup](./part4-telegram-setup.md)
- **Want the agent to self-improve?** → [Part 5: On-the-Fly Skills](./part5-creating-skills.md)
