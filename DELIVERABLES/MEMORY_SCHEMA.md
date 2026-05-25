# AIuthor Memory Schema and Concrete Data Models

This document details the persistent database tables used to store memory, continuity, RAG document chunks, and observability metrics outside the LLM context window.

## 1. Core Book Project Tables

### `book_projects`
Stores the high-level configuration of each book brief.
- `id` (UUID, Primary Key)
- `topic` (Text, NOT NULL): The central subject of the book.
- `reader_profile` (Text, NOT NULL): Intended audience description.
- `genre` (Text, NOT NULL): Genre of the manuscript.
- `tone` (String, NOT NULL): Style parameter (conversational, academic, storyteller, motivational, witty).
- `target_chapters` (Integer, NOT NULL): Planned length.
- `status` (String): High-level state (created, planning, in_progress, completed, failed).
- `created_at` (Timestamp), `updated_at` (Timestamp)

### `chapters`
Stores the chapter metadata and drafts.
- `id` (UUID, Primary Key)
- `book_id` (UUID, ForeignKey to `book_projects.id`)
- `chapter_number` (Integer, NOT NULL)
- `title` (Text, NOT NULL)
- `summary` (Text)
- `chapter_contract` (JSON): The structured outline, required facts, and callbacks.
- `draft_text` (Text), `humanized_text` (Text), `edited_text` (Text), `final_text` (Text)
- `status` (String)

---

## 2. Memory System Tables (Continuity & Lore)

### `fact_registry`
Tracks factual claims to ensure no hallucination in non-fiction chapters.
- `id` (UUID, Primary Key)
- `book_id` (UUID, ForeignKey)
- `chapter_id` (UUID, ForeignKey, nullable): The chapter where this fact was extracted or verified.
- `claim` (Text, NOT NULL): The factual assertion.
- `source_document_id` (UUID, ForeignKey): Source PDF/Doc.
- `source_chunk_id` (UUID, ForeignKey): Reference block.
- `confidence` (Float): AI extraction confidence score.
- `status` (String): verification status (unverified, verified, disputed).
- `used_in_chapters` (JSON): List of chapter integers using this fact.

#### Example Record:
```json
{
  "id": "e30cf2f6-3d23-424a-97a3-832140bb0f82",
  "book_id": "1e536690-7dfe-414d-87ae-44dc1463cbe9",
  "chapter_id": "42abef88-29bc-4ef1-893f-a39bdcf29bcf",
  "claim": "Retrieval-Augmented Generation (RAG) combines search engines with generative large language models.",
  "source_document_id": "55fbe9a1-8d2b-4fc4-bbcb-c3dbeea12ef1",
  "source_chunk_id": "fa80c10a-39fc-48ad-8d9b-a3d2efba4128",
  "confidence": 0.98,
  "status": "verified",
  "used_in_chapters": [1, 2]
}
```

### `concept_bible`
Stores technical terms, vocabulary, or jargon to build the glossary.
- `id` (UUID, Primary Key)
- `book_id` (UUID, ForeignKey)
- `concept` (Text, NOT NULL): The term.
- `definition` (Text): Meaning of the term.
- `first_chapter` (Integer): Chapter where it first appeared.
- `related_terms` (JSON): List of related terms.
- `appears_in_chapters` (JSON): List of chapter indices.

#### Example Record:
```json
{
  "id": "b3f02ea2-9d32-4bf1-a8cf-8d9beeab0f8c",
  "book_id": "1e536690-7dfe-414d-87ae-44dc1463cbe9",
  "concept": "Vector Embedding",
  "definition": "A dense mathematical representation of text capture semantic meaning in high-dimensional space.",
  "first_chapter": 1,
  "related_terms": ["vector space", "cosine similarity"],
  "appears_in_chapters": [1, 2, 3]
}
```

### `character_bible`
Tracks characters, attributes, and relationships for storytelling.
- `id` (UUID, Primary Key)
- `book_id` (UUID, ForeignKey)
- `character_name` (Text, NOT NULL)
- `role` (Text): Role in narrative (e.g. protagonist).
- `traits` (JSON): Character traits.
- `relationships` (JSON): Mapping to other characters.
- `arc_summary` (Text): Character development path.
- `appears_in_chapters` (JSON): Chapters they appear in.

#### Example Record:
```json
{
  "id": "11abcb9e-fa3e-46cf-ab2a-97abf0cbefca",
  "book_id": "d894c477-5f7a-41bb-b3e3-6e7bee7663fe",
  "character_name": "Master Benjamin",
  "role": "Protagonist, clockmaker of Silent City",
  "traits": ["dedicated", "elderly", "quiet"],
  "relationships": {
    "Eliza": "apprentice"
  },
  "arc_summary": "Discovers the mist falls when the clock stops and must keep it ticking.",
  "appears_in_chapters": [1, 2, 3, 4, 5]
}
```

### `callback_index`
Stores callbacks and cross-chapter reference points (TOC shifting repairs).
- `id` (UUID, Primary Key)
- `book_id` (UUID, ForeignKey)
- `source_chapter` (Integer): The chapter referencing the concept.
- `target_chapter` (Integer): The chapter where the concept was originally defined.
- `concept` (Text)
- `callback_text` (Text): Exact text hook back.
- `status` (String): (active, broken).

#### Example Record:
```json
{
  "id": "fc3ab92d-9bc2-4ef8-aef0-be39dcfb01ef",
  "book_id": "1e536690-7dfe-414d-87ae-44dc1463cbe9",
  "source_chapter": 3,
  "target_chapter": 1,
  "concept": "RAG Pipelines",
  "callback_text": "Recall from Chapter 1 that a basic RAG pipeline retrieves documents prior to calling the LLM.",
  "status": "active"
}
```

### `tone_fingerprints`
Stores stylistic rules, sentence rhythm patterns, and banned vocabulary.
- `id` (UUID, Primary Key)
- `book_id` (UUID, ForeignKey)
- `tone_name` (String, NOT NULL)
- `sentence_rhythm` (JSON): Varied lengths parameters.
- `lexical_rules` (JSON): Metaphors, voice descriptors.
- `banned_phrases` (JSON): AI Tells list ("In today's fast-paced world", etc.).
- `example_phrases` (JSON): Exemplar sentences.

#### Example Record:
```json
{
  "id": "fb2ab81c-cbcd-49d9-ad3f-e39dcf28a21f",
  "book_id": "1e536690-7dfe-414d-87ae-44dc1463cbe9",
  "tone_name": "conversational",
  "sentence_rhythm": {
    "short_sentence_target_percent": 30,
    "long_sentence_max_words": 25
  },
  "lexical_rules": {
    "perspective": "second-person"
  },
  "banned_phrases": [
    "it is important to note",
    "delve into",
    "not only, but also",
    "in today's fast-paced world",
    "testament to"
  ],
  "example_phrases": [
    "Think of vector embeddings as coordinates on a map.",
    "Let's trace how a prompt changes through the pipeline."
  ]
}
```

### `decision_log`
Engineering + runtime log detailing AI choices.
- `id` (UUID, Primary Key)
- `book_id` (UUID, ForeignKey)
- `decision` (Text)
- `reason` (Text)
- `impact` (Text)

---

## 3. RAG Storage Tables

### `source_documents`
- `id` (UUID)
- `book_id` (UUID)
- `title` (Text)
- `source_type` (String)
- `status` (String)

### `document_chunks`
- `id` (UUID)
- `document_id` (UUID)
- `book_id` (UUID)
- `chunk_index` (Integer)
- `chunk_text` (Text)
- `embedding` (Vector(768)) -- pgvector 768-dimension column.
- `token_count` (Integer)
- `embedding_status` (String)

---

## 4. Observability Tables

### `agent_traces`
- `id` (UUID)
- `run_id` (UUID)
- `book_id` (UUID)
- `agent_name` (String)
- `status` (String)
- `input_summary` (JSON)
- `output_summary` (JSON)
- `started_at` (Timestamp), `completed_at` (Timestamp)

### `prompt_logs`
- `id` (UUID)
- `run_id` (UUID)
- `book_id` (UUID)
- `agent_name` (String)
- `prompt_name` (String)
- `model_name` (String)
- `prompt_text` (Text)
- `response_text` (Text)

### `token_cost_ledger`
- `id` (UUID)
- `run_id` (UUID)
- `book_id` (UUID)
- `agent_name` (String)
- `model_name` (String)
- `input_tokens` (Integer)
- `output_tokens` (Integer)
- `total_tokens` (Integer)
- `estimated_cost` (Float)
