# RAG Hybrid Retrieval & Context Pack System (Module 6.1)

This document provides a comprehensive guide on the **Hybrid Retrieval Layer** and the **Context Pack Builder** in the AIuthor backend repository. These services prepare high-quality, citation-annotated context blocks for AIuthor agents (such as the Researcher, Writer, and Editor) to consume during long-form book generation.

---

## 1. Overview of Retrieval Strategies

AIuthor provides four distinct retrieval endpoints for reference material depending on the pipeline stage and consumption requirements:

| Endpoint | Mode | Mechanism | Output Type | Best Used For |
|---|---|---|---|---|
| `POST /api/rag/retrieve` | **Lexical** | SQL case-insensitive `LIKE` matching | List of chunks with raw score `1.0` | Simple keyword lookups |
| `POST /api/rag/semantic-retrieve` | **Semantic** | Vector search (pgvector <=> distance on Postgres, cosine fallback on SQLite) | List of chunks ranked by cosine similarity | Semantic/conceptual search |
| `POST /api/rag/hybrid-retrieve` | **Hybrid** | Score-merged combination of Vector + Keyword | List of chunks + `C1, C2` citations | Multi-aspect ranked retrieval |
| `POST /api/rag/context-pack` | **Context Pack** | Hybrid search + size-boundary grouping & formatting | Concatenated context string + citation mapping | Prompt injection for LLM/Agents |

---

## 2. Hybrid Retrieval Mechanics

The `HybridRetrievalService` implements a clean scoring layer combining keyword precision and vector semantics:

### A. Semantic Search Phase
Runs semantic retrieval over `DocumentChunk` records using `SemanticRetrievalService`.
- Queries `top_k * 2` internally to ensure a wide and deep candidate pool for merge.
- Yields a list of `RetrievalResultItem`s with their cosine similarity scores (typically between `0.0` and `1.0`).

### B. Lexical Search Phase
Runs custom SQL-backed lexical keyword search:
- Filters for chunks containing at least one query word.
- Evaluates scores locally:
  - If the **exact phrase** matches the query string: `score = 1.0`.
  - Otherwise, splits the query into unique terms and calculates:
    $$score = \frac{count(matched\_terms)}{total\_query\_terms}$$

### C. Score Merging and Deduplication
Calculates a unified combined score for each unique chunk ID:
$$combined\_score = (semantic\_score \times semantic\_weight) + (lexical\_score \times lexical\_weight)$$
- Default weights: **Semantic weight = 0.7**, **Lexical weight = 0.3** (customizable).
- If a chunk is only found in one retrieval mode, the score for the missing mode is treated as `0.0`.
- Filters out chunks below the optional `min_score` threshold.
- Sorts results by `combined_score` descending, resolving ties by `chunk_index` ascending.
- Caps results at the requested `top_k` and produces sequential citation tags: `C1`, `C2`, `C3` ...

---

## 3. Context Pack Builder & Format

The `ContextPackService` translates the ranked chunks returned from hybrid retrieval into a single, cohesive text block optimized for agent prompt context windows.

### stable Agent-Readable Format
The generated text block (`context_text`) follows a stable format that agents can easily parse and reference:

```text
[C1] Source: Reference Paper - Climate Change, Chunk 12
Greenhouse gas emissions from human activities are the primary driver of rapid global temperature rises...

[C2] Source: 4b1c8d5c-9c3f-4e00-8f96-33923f5eb41f, Chunk 0
Another key aspect of local conservation revolves around community forestry...
```

### Size Boundary Enforcement (`max_context_chars`)
To prevent exceeding LLM context windows or token budgets, the builder restricts size using a strict iterative approach:
1. Adds chunk blocks sequentially (`C1`, `C2`, `C3`...) until the character limit would be exceeded.
2. **Never** cuts a chunk text mid-way to fit the boundary, unless **that first chunk alone** is larger than the entire limit.
3. If the first chunk is too large, it truncates that chunk safely and sets the `"truncated": true` flag in the metadata.
4. Automatically filters and re-indexes citations (`C1`, `C2`...) so only those chunks actually included in the text block are in the citation output list.

---

## 4. No Runtime Agents / LangGraph Yet

This module operates purely on the **API and Service layers** of the AIuthor database.
- **No LLM prompts** are executed.
- **No background agents** (Planner, Researcher, Writer) run.
- **No LangGraph orchestrations** are initiated.
- **No automatic memory writing** takes place.

These database-backed services provide clean, structured data layers which the subsequent agent modules will utilize directly to feed the LLM accurate context with source attribution.
