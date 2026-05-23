"""
AIuthor Backend — Memory Extraction Service (Module 9.0).
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, or_

from app.models import (
    BookProject,
    Chapter,
    FactRegistry,
    ConceptBible,
    CharacterBible,
    CallbackIndex,
    ToneFingerprint,
    DecisionLog,
)
from app.schemas import (
    FactRegistryCreate,
    FactRegistryUpdate,
    ConceptBibleCreate,
    ConceptBibleUpdate,
    CharacterBibleCreate,
    CharacterBibleUpdate,
    CallbackIndexCreate,
    CallbackIndexUpdate,
    ToneFingerprintCreate,
    ToneFingerprintUpdate,
    DecisionLogCreate,
    DecisionLogUpdate,
)
from app.workflows.schemas import (
    MemoryExtractionRequest,
    MemoryCandidate,
    MemoryWriteResult,
    MemoryExtractionResponse,
)
from app.agents.schemas import AgentInput
from app.services.exceptions import NotFoundError, ValidationServiceError
from app.services import (
    MemoryService,
    AgentExecutionService,
    ChapterService,
    BookProjectService,
    WorkflowObservabilityService,
)

logger = logging.getLogger(__name__)


def parse_json_safely(content: str) -> dict | list | None:
    """Attempt to parse JSON safely, handling markdown code blocks and partial blocks."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    try:
        return json.loads(content)
    except Exception:
        # Search for any JSON block inside { ... } or [ ... ]
        match = re.search(r"(\{.*\}|\[.*\])", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
    return None


class MemoryExtractionService:
    """
    Coordinates extraction of story elements via MemoryKeeper and saves them to the DB.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.memory_service = MemoryService(db)
        self.agent_service = AgentExecutionService(db=db)
        self.chapter_service = ChapterService(db)
        self.book_service = BookProjectService(db)
        self.workflow_observability_service = WorkflowObservabilityService(db)

    def _get_book(self, book_id: uuid.UUID) -> BookProject:
        """Fetch BookProject or raise NotFoundError."""
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    def _get_chapter_if_needed(self, book_id: uuid.UUID, chapter_id: uuid.UUID | None) -> Chapter | None:
        """If chapter_id is provided, verify ownership and return Chapter."""
        if chapter_id is None:
            return None
        chapter = self.db.get(Chapter, chapter_id)
        if chapter is None or chapter.book_id != book_id:
            raise NotFoundError(
                message="Chapter not found or does not belong to this book",
                code="chapter_not_found",
                details={"chapter_id": str(chapter_id), "book_id": str(book_id)},
            )
        return chapter

    def _build_source_text(self, request: MemoryExtractionRequest, chapter: Chapter | None = None) -> str:
        """Build source text to extract memories from based on source_type."""
        if request.source_type == "text":
            return request.source_text or ""

        elif request.source_type == "chapter":
            if chapter is None:
                raise ValueError("Chapter must be loaded for source_type='chapter'")
            # Priority: final_text -> edited_text -> humanized_text -> draft_text -> summary -> title
            text_sources = [
                chapter.final_text,
                chapter.edited_text,
                chapter.humanized_text,
                chapter.draft_text,
                chapter.summary,
                chapter.title,
            ]
            for src in text_sources:
                if src and src.strip():
                    return src.strip()
            return ""

        elif request.source_type == "workflow_output":
            if not request.workflow_output:
                return ""
            return json.dumps(request.workflow_output, sort_keys=True, indent=2)

        elif request.source_type == "trace_bundle":
            if not request.trace_bundle:
                return ""
            # Extract useful outputs/traces
            traces = request.trace_bundle.get("traces", [])
            if isinstance(traces, list):
                lines = []
                for t in traces:
                    if isinstance(t, dict):
                        agent = t.get("agent_name", "unknown")
                        content = t.get("content") or ""
                        if content:
                            lines.append(f"--- Agent: {agent} Output ---")
                            lines.append(content)
                if lines:
                    return "\n\n".join(lines)
            return json.dumps(request.trace_bundle, sort_keys=True, indent=2)

        return ""

    def _extract_candidates_mock(self, source_text: str, request: MemoryExtractionRequest) -> list[MemoryCandidate]:
        """Deterministic mock memory candidate extractor (no LLM, safe for offline tests)."""
        candidates = []
        text_lower = source_text.lower()
        ch_id = request.chapter_id

        # 1. Fact
        if request.include_facts:
            # extract first sentence or fallback
            sentences = [s.strip() for s in source_text.split(".") if s.strip()]
            claim = sentences[0] if sentences else "Factual claim from source text."
            if len(claim) > 200:
                claim = claim[:200] + "..."
            candidates.append(MemoryCandidate(
                memory_type="fact",
                key="factual_claim",
                value=claim,
                confidence=0.9,
                source_agent="memory_keeper_mock",
                chapter_id=ch_id
            ))

        # 2. Concept
        if request.include_concepts:
            detected = []
            if "rag" in text_lower:
                detected.append(("RAG", "Retrieval-Augmented Generation concept."))
            if "embeddings" in text_lower:
                detected.append(("Embeddings", "Dense vector embeddings for semantic search."))
            if "vector search" in text_lower or "vector" in text_lower:
                detected.append(("Vector Search", "Cosine similarity retrieval over vectors."))
            if "concept" in text_lower:
                detected.append(("Technical Concept", "Capitalized concept found in source text."))
            if not detected:
                detected.append(("General Concept", "A generic technical concept from mock."))

            for concept, defn in detected:
                candidates.append(MemoryCandidate(
                    memory_type="concept",
                    key=concept,
                    value=defn,
                    confidence=0.85,
                    source_agent="memory_keeper_mock",
                    chapter_id=ch_id
                ))

        # 3. Character
        if request.include_characters:
            chars = []
            if "character" in text_lower or "john" in text_lower:
                chars.append(("John Doe", "Main protagonist introduced in chapter."))
            if "jane" in text_lower or "protagonist" in text_lower:
                chars.append(("Jane Smith", "Deuteragonist with high intelligence."))
            if request.metadata and "character_name" in request.metadata:
                char_name = request.metadata["character_name"]
                char_role = request.metadata.get("character_role", "Supporting character.")
                chars.append((char_name, char_role))

            for char_name, role_desc in chars:
                candidates.append(MemoryCandidate(
                    memory_type="character",
                    key=char_name,
                    value=role_desc,
                    confidence=0.95,
                    source_agent="memory_keeper_mock",
                    chapter_id=ch_id
                ))

        # 4. Callback
        if request.include_callbacks:
            keywords = ["later", "previous", "recall", "callback", "chapter"]
            if any(k in text_lower for k in keywords):
                candidates.append(MemoryCandidate(
                    memory_type="callback",
                    key="Narrative Callback",
                    value="Callback index referencing previous event or setting up later chapter.",
                    confidence=0.8,
                    source_agent="memory_keeper_mock",
                    chapter_id=ch_id,
                    metadata={"source_chapter": 1, "target_chapter": 2}
                ))

        # 5. Tone
        if request.include_tone:
            tone_name = "conversational"
            if "academic" in text_lower:
                tone_name = "academic"
            elif "storyteller" in text_lower:
                tone_name = "storyteller"
            if request.metadata and "tone" in request.metadata:
                tone_name = request.metadata["tone"]

            candidates.append(MemoryCandidate(
                memory_type="tone",
                key=tone_name,
                value=f"Style fingerprint for {tone_name} tone.",
                confidence=0.9,
                source_agent="memory_keeper_mock",
                chapter_id=ch_id,
                metadata={"sentence_rhythm": {"average_sentence_length": 15}}
            ))

        # 6. Decision
        if request.include_decisions:
            decision_text = "Standard generation pathway selected."
            if request.metadata and "decision" in request.metadata:
                decision_text = request.metadata["decision"]

            candidates.append(MemoryCandidate(
                memory_type="decision",
                key="generation_pathway",
                value=decision_text,
                confidence=1.0,
                source_agent="memory_keeper_mock",
                chapter_id=ch_id
            ))

        return candidates

    def _extract_candidates_real_dev(self, source_text: str, request: MemoryExtractionRequest) -> list[MemoryCandidate]:
        """Extract memory candidates using Gemini/OpenAI through the MemoryKeeper Agent."""
        inp = AgentInput(
            agent_name="memory_keeper",
            task="Extract stable memory records from this source text for long-book continuity.",
            book_id=request.book_id,
            run_id=request.run_id,
            chapter_id=request.chapter_id,
            payload={
                "source_text": source_text,
                "include_facts": request.include_facts,
                "include_concepts": request.include_concepts,
                "include_characters": request.include_characters,
                "include_callbacks": request.include_callbacks,
                "include_tone": request.include_tone,
                "include_decisions": request.include_decisions,
            },
            metadata=request.metadata,
        )
        agent_out = self.agent_service.run_agent_once(inp)
        content = agent_out.content or ""
        return self._parse_memorykeeper_output(content, request)

    def _parse_memorykeeper_output(self, content: str, request: MemoryExtractionRequest) -> list[MemoryCandidate]:
        """Parse structured MemoryKeeper LLM responses with fallback modes."""
        candidates = []
        if not content or not content.strip():
            return candidates

        parsed = parse_json_safely(content)
        if isinstance(parsed, dict):
            def get_list_by_normalized_key(d, possible_keys):
                for pk in possible_keys:
                    if pk in d:
                        val = d[pk]
                        if isinstance(val, list):
                            return val
                        elif isinstance(val, dict):
                            return [val]
                return []

            facts_list = get_list_by_normalized_key(parsed, ["facts", "fact", "fact_registry"])
            concepts_list = get_list_by_normalized_key(parsed, ["concepts", "concept", "concept_bible"])
            characters_list = get_list_by_normalized_key(parsed, ["characters", "character", "character_bible"])
            callbacks_list = get_list_by_normalized_key(parsed, ["callbacks", "callback", "callback_index"])
            tone_list = get_list_by_normalized_key(parsed, ["tone", "tone_rules", "tone_fingerprints", "tone_fingerprint", "tone_rules_list"])
            decisions_list = get_list_by_normalized_key(parsed, ["decisions", "decision", "decision_log"])

            # Map Facts
            for f in facts_list:
                if isinstance(f, dict):
                    claim = f.get("claim") or f.get("value") or f.get("key")
                    if claim:
                        candidates.append(MemoryCandidate(
                            memory_type="fact",
                            key="factual_claim",
                            value=claim,
                            confidence=float(f.get("confidence", 1.0)),
                            source_agent="memory_keeper",
                            chapter_id=request.chapter_id,
                            metadata=f.get("metadata")
                        ))
                elif isinstance(f, str):
                    candidates.append(MemoryCandidate(
                        memory_type="fact",
                        key="factual_claim",
                        value=f,
                        confidence=1.0,
                        source_agent="memory_keeper",
                        chapter_id=request.chapter_id
                    ))

            # Map Concepts
            for c in concepts_list:
                if isinstance(c, dict):
                    concept = c.get("concept") or c.get("key")
                    defn = c.get("definition") or c.get("value") or "Concept defined in text."
                    if concept:
                        candidates.append(MemoryCandidate(
                            memory_type="concept",
                            key=concept,
                            value=defn,
                            confidence=float(c.get("confidence", 1.0)),
                            source_agent="memory_keeper",
                            chapter_id=request.chapter_id,
                            metadata=c.get("metadata")
                        ))
                elif isinstance(c, str):
                    candidates.append(MemoryCandidate(
                        memory_type="concept",
                        key=c,
                        value="Defined concept.",
                        confidence=1.0,
                        source_agent="memory_keeper",
                        chapter_id=request.chapter_id
                    ))

            # Map Characters
            for char in characters_list:
                if isinstance(char, dict):
                    name = char.get("character_name") or char.get("name") or char.get("key")
                    role = char.get("role") or char.get("value") or "Character role."
                    if name:
                        candidates.append(MemoryCandidate(
                            memory_type="character",
                            key=name,
                            value=role,
                            confidence=float(char.get("confidence", 1.0)),
                            source_agent="memory_keeper",
                            chapter_id=request.chapter_id,
                            metadata=char
                        ))
                elif isinstance(char, str):
                    candidates.append(MemoryCandidate(
                        memory_type="character",
                        key=char,
                        value="Character role.",
                        confidence=1.0,
                        source_agent="memory_keeper",
                        chapter_id=request.chapter_id
                    ))

            # Map Callbacks
            for cb in callbacks_list:
                if isinstance(cb, dict):
                    text = cb.get("callback_text") or cb.get("value")
                    concept = cb.get("concept") or cb.get("key") or "callback"
                    if text:
                        candidates.append(MemoryCandidate(
                            memory_type="callback",
                            key=concept,
                            value=text,
                            confidence=float(cb.get("confidence", 1.0)),
                            source_agent="memory_keeper",
                            chapter_id=request.chapter_id,
                            metadata=cb
                        ))
                elif isinstance(cb, str):
                    candidates.append(MemoryCandidate(
                        memory_type="callback",
                        key="callback",
                        value=cb,
                        confidence=1.0,
                        source_agent="memory_keeper",
                        chapter_id=request.chapter_id
                    ))

            # Map Tone Rules
            for t in tone_list:
                if isinstance(t, dict):
                    tone_name = t.get("tone_name") or t.get("key") or "conversational"
                    desc = t.get("description") or t.get("value") or "Tone guideline."
                    candidates.append(MemoryCandidate(
                        memory_type="tone",
                        key=tone_name,
                        value=desc,
                        confidence=float(t.get("confidence", 1.0)),
                        source_agent="memory_keeper",
                        chapter_id=request.chapter_id,
                        metadata=t
                    ))
                elif isinstance(t, str):
                    candidates.append(MemoryCandidate(
                        memory_type="tone",
                        key=t,
                        value="Tone guideline.",
                        confidence=1.0,
                        source_agent="memory_keeper",
                        chapter_id=request.chapter_id
                    ))

            # Map Decisions
            for d in decisions_list:
                if isinstance(d, dict):
                    decision = d.get("decision") or d.get("key")
                    reason = d.get("reason") or d.get("value") or "Decision logged."
                    if decision:
                        candidates.append(MemoryCandidate(
                            memory_type="decision",
                            key=decision,
                            value=reason,
                            confidence=float(d.get("confidence", 1.0)),
                            source_agent="memory_keeper",
                            chapter_id=request.chapter_id,
                            metadata=d
                        ))
                elif isinstance(d, str):
                    candidates.append(MemoryCandidate(
                        memory_type="decision",
                        key=d,
                        value="Decision logged.",
                        confidence=1.0,
                        source_agent="memory_keeper",
                        chapter_id=request.chapter_id
                    ))

        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    mtype = item.get("memory_type")
                    key = item.get("key") or item.get("claim") or item.get("concept") or item.get("character_name") or item.get("name") or item.get("tone_name") or item.get("decision")
                    val = item.get("value") or item.get("definition") or item.get("role") or item.get("callback_text") or item.get("reason")
                    if mtype and key and val:
                        candidates.append(MemoryCandidate(
                            memory_type=mtype,
                            key=key,
                            value=val,
                            confidence=float(item.get("confidence", 1.0)),
                            source_agent="memory_keeper",
                            chapter_id=request.chapter_id,
                            metadata=item
                        ))

        else:
            # Line-based parser fallback
            lines = content.splitlines()
            current_type = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                lower_line = line.lower()
                if "fact" in lower_line and ":" in lower_line:
                    current_type = "fact"
                    continue
                elif "concept" in lower_line and ":" in lower_line:
                    current_type = "concept"
                    continue
                elif "character" in lower_line and ":" in lower_line:
                    current_type = "character"
                    continue
                elif "callback" in lower_line and ":" in lower_line:
                    current_type = "callback"
                    continue
                elif "tone" in lower_line and ":" in lower_line:
                    current_type = "tone"
                    continue
                elif "decision" in lower_line and ":" in lower_line:
                    current_type = "decision"
                    continue

                if line.startswith("-") or line.startswith("*"):
                    text_content = line[1:].strip()
                    if current_type and text_content:
                        parts = text_content.split(":", 1)
                        if len(parts) == 2:
                            k, v = parts[0].strip(), parts[1].strip()
                        else:
                            k, v = current_type, text_content
                        candidates.append(MemoryCandidate(
                            memory_type=current_type,
                            key=k or "extracted_key",
                            value=v or "extracted_value",
                            confidence=0.7,
                            source_agent="memory_keeper_fallback",
                            chapter_id=request.chapter_id
                        ))

        return candidates

    def _write_candidate(self, candidate: MemoryCandidate, request: MemoryExtractionRequest) -> MemoryWriteResult:
        """Write a single MemoryCandidate into the corresponding database-backed memory record."""
        try:
            mtype = candidate.memory_type
            book_id = request.book_id
            ch_id = candidate.chapter_id or request.chapter_id

            if mtype == "fact":
                # Check duplicate by claim
                existing = self.db.query(FactRegistry).filter_by(book_id=book_id, claim=candidate.value).first()
                meta = {
                    "source_agent": candidate.source_agent or "memory_keeper",
                    "source_citation_id": candidate.source_citation_id,
                    **(candidate.metadata or {}),
                    **(request.metadata or {}),
                }
                if existing:
                    if not request.overwrite_existing:
                        return MemoryWriteResult(
                            memory_type=mtype,
                            key=candidate.key,
                            status="skipped",
                            record_id=existing.id,
                            skipped_reason="duplicate"
                        )
                    # Update
                    payload = FactRegistryUpdate(
                        chapter_id=ch_id,
                        confidence=candidate.confidence,
                        fact_metadata=meta
                    )
                    self.memory_service.update_fact(book_id, existing.id, payload)
                    return MemoryWriteResult(
                        memory_type=mtype,
                        key=candidate.key,
                        status="updated",
                        record_id=existing.id,
                        metadata=meta
                    )
                # Create
                payload = FactRegistryCreate(
                    book_id=book_id,
                    chapter_id=ch_id,
                    claim=candidate.value,
                    confidence=candidate.confidence,
                    fact_metadata=meta
                )
                fact = self.memory_service.create_fact(payload)
                return MemoryWriteResult(
                    memory_type=mtype,
                    key=candidate.key,
                    status="written",
                    record_id=fact.id,
                    metadata=meta
                )

            elif mtype == "concept":
                # Check duplicate by concept name
                existing = self.db.query(ConceptBible).filter_by(book_id=book_id, concept=candidate.key).first()
                meta = {
                    "source_agent": candidate.source_agent or "memory_keeper",
                    **(candidate.metadata or {}),
                    **(request.metadata or {}),
                }
                if existing:
                    if not request.overwrite_existing:
                        return MemoryWriteResult(
                            memory_type=mtype,
                            key=candidate.key,
                            status="skipped",
                            record_id=existing.id,
                            skipped_reason="duplicate"
                        )
                    # Update
                    payload = ConceptBibleUpdate(
                        definition=candidate.value,
                        concept_metadata=meta
                    )
                    self.memory_service.update_concept(book_id, existing.id, payload)
                    return MemoryWriteResult(
                        memory_type=mtype,
                        key=candidate.key,
                        status="updated",
                        record_id=existing.id,
                        metadata=meta
                    )
                # Create
                payload = ConceptBibleCreate(
                    book_id=book_id,
                    concept=candidate.key,
                    definition=candidate.value,
                    concept_metadata=meta
                )
                concept = self.memory_service.create_concept(payload)
                return MemoryWriteResult(
                    memory_type=mtype,
                    key=candidate.key,
                    status="written",
                    record_id=concept.id,
                    metadata=meta
                )

            elif mtype == "character":
                # Check duplicate by character name
                existing = self.db.query(CharacterBible).filter_by(book_id=book_id, character_name=candidate.key).first()
                meta = {
                    "source_agent": candidate.source_agent or "memory_keeper",
                    **(candidate.metadata or {}),
                    **(request.metadata or {}),
                }
                if existing:
                    if not request.overwrite_existing:
                        return MemoryWriteResult(
                            memory_type=mtype,
                            key=candidate.key,
                            status="skipped",
                            record_id=existing.id,
                            skipped_reason="duplicate"
                        )
                    # Update
                    payload = CharacterBibleUpdate(
                        role=candidate.value,
                        character_metadata=meta
                    )
                    self.memory_service.update_character(book_id, existing.id, payload)
                    return MemoryWriteResult(
                        memory_type=mtype,
                        key=candidate.key,
                        status="updated",
                        record_id=existing.id,
                        metadata=meta
                    )
                # Create
                payload = CharacterBibleCreate(
                    book_id=book_id,
                    character_name=candidate.key,
                    role=candidate.value,
                    character_metadata=meta
                )
                char = self.memory_service.create_character(payload)
                return MemoryWriteResult(
                    memory_type=mtype,
                    key=candidate.key,
                    status="written",
                    record_id=char.id,
                    metadata=meta
                )

            elif mtype == "callback":
                # Check duplicate by callback text
                existing = self.db.query(CallbackIndex).filter_by(book_id=book_id, callback_text=candidate.value).first()
                meta = {
                    "source_agent": candidate.source_agent or "memory_keeper",
                    **(candidate.metadata or {}),
                    **(request.metadata or {}),
                }
                source_ch = candidate.metadata.get("source_chapter") if candidate.metadata else None
                target_ch = candidate.metadata.get("target_chapter") if candidate.metadata else None
                if existing:
                    if not request.overwrite_existing:
                        return MemoryWriteResult(
                            memory_type=mtype,
                            key=candidate.key,
                            status="skipped",
                            record_id=existing.id,
                            skipped_reason="duplicate"
                        )
                    # Update
                    payload = CallbackIndexUpdate(
                        concept=candidate.key,
                        source_chapter=source_ch,
                        target_chapter=target_ch,
                        callback_metadata=meta
                    )
                    self.memory_service.update_callback(book_id, existing.id, payload)
                    return MemoryWriteResult(
                        memory_type=mtype,
                        key=candidate.key,
                        status="updated",
                        record_id=existing.id,
                        metadata=meta
                    )
                # Create
                payload = CallbackIndexCreate(
                    book_id=book_id,
                    concept=candidate.key,
                    callback_text=candidate.value,
                    source_chapter=source_ch,
                    target_chapter=target_ch,
                    callback_metadata=meta
                )
                cb = self.memory_service.create_callback(payload)
                return MemoryWriteResult(
                    memory_type=mtype,
                    key=candidate.key,
                    status="written",
                    record_id=cb.id,
                    metadata=meta
                )

            elif mtype == "tone":
                # Check duplicate by tone_name
                existing = self.db.query(ToneFingerprint).filter_by(book_id=book_id, tone_name=candidate.key).first()
                meta = {
                    "source_agent": candidate.source_agent or "memory_keeper",
                    **(candidate.metadata or {}),
                    **(request.metadata or {}),
                }
                rhythm = candidate.metadata.get("sentence_rhythm") if candidate.metadata else None
                lexical = candidate.metadata.get("lexical_rules") if candidate.metadata else None
                banned = candidate.metadata.get("banned_phrases") if candidate.metadata else None
                examples = candidate.metadata.get("example_phrases") if candidate.metadata else None

                if existing:
                    if not request.overwrite_existing:
                        return MemoryWriteResult(
                            memory_type=mtype,
                            key=candidate.key,
                            status="skipped",
                            record_id=existing.id,
                            skipped_reason="duplicate"
                        )
                    # Update
                    payload = ToneFingerprintUpdate(
                        sentence_rhythm=rhythm,
                        lexical_rules=lexical,
                        banned_phrases=banned,
                        example_phrases=examples,
                        fingerprint_metadata=meta
                    )
                    self.memory_service.update_tone_fingerprint(book_id, existing.id, payload)
                    return MemoryWriteResult(
                        memory_type=mtype,
                        key=candidate.key,
                        status="updated",
                        record_id=existing.id,
                        metadata=meta
                    )
                # Create
                payload = ToneFingerprintCreate(
                    book_id=book_id,
                    tone_name=candidate.key,
                    sentence_rhythm=rhythm,
                    lexical_rules=lexical,
                    banned_phrases=banned,
                    example_phrases=examples,
                    fingerprint_metadata=meta
                )
                tone = self.memory_service.create_tone_fingerprint(payload)
                return MemoryWriteResult(
                    memory_type=mtype,
                    key=candidate.key,
                    status="written",
                    record_id=tone.id,
                    metadata=meta
                )

            elif mtype == "decision":
                # Check duplicate by decision
                existing = self.db.query(DecisionLog).filter_by(book_id=book_id, decision=candidate.key).first()
                meta = {
                    "source_agent": candidate.source_agent or "memory_keeper",
                    **(candidate.metadata or {}),
                    **(request.metadata or {}),
                }
                if existing:
                    if not request.overwrite_existing:
                        return MemoryWriteResult(
                            memory_type=mtype,
                            key=candidate.key,
                            status="skipped",
                            record_id=existing.id,
                            skipped_reason="duplicate"
                        )
                    # Update
                    payload = DecisionLogUpdate(
                        reason=candidate.value,
                        decision_metadata=meta
                    )
                    self.memory_service.update_decision(existing.id, payload)
                    return MemoryWriteResult(
                        memory_type=mtype,
                        key=candidate.key,
                        status="updated",
                        record_id=existing.id,
                        metadata=meta
                    )
                # Create
                payload = DecisionLogCreate(
                    book_id=book_id,
                    decision=candidate.key,
                    reason=candidate.value,
                    decision_metadata=meta
                )
                dec = self.memory_service.create_decision(payload)
                return MemoryWriteResult(
                    memory_type=mtype,
                    key=candidate.key,
                    status="written",
                    record_id=dec.id,
                    metadata=meta
                )

            return MemoryWriteResult(
                memory_type=candidate.memory_type,
                key=candidate.key,
                status="failed",
                error_message=f"Unsupported memory type '{candidate.memory_type}'."
            )

        except Exception as exc:
            logger.exception("Error writing memory candidate %s", candidate)
            return MemoryWriteResult(
                memory_type=candidate.memory_type,
                key=candidate.key,
                status="failed",
                error_message=str(exc)
            )

    def extract_memory(self, request: MemoryExtractionRequest) -> MemoryExtractionResponse:
        """Core endpoint method for memory extraction flow execution."""
        # 1. Validate Book & Chapter
        self._get_book(request.book_id)
        chapter = self._get_chapter_if_needed(request.book_id, request.chapter_id)

        # 2. Build Text Content
        source_text = self._build_source_text(request, chapter)

        # 3. Extract Candidates
        if request.execution_mode == "mock":
            candidates = self._extract_candidates_mock(source_text, request)
        elif request.execution_mode == "real_dev":
            candidates = self._extract_candidates_real_dev(source_text, request)
        else:
            raise ValidationServiceError(
                message=f"Execution mode '{request.execution_mode}' is not supported.",
                code="unsupported_execution_mode",
            )

        # Filter candidates by flags
        filtered_candidates = []
        for c in candidates:
            mtype = c.memory_type
            if mtype == "fact" and not request.include_facts:
                continue
            if mtype == "concept" and not request.include_concepts:
                continue
            if mtype == "character" and not request.include_characters:
                continue
            if mtype == "callback" and not request.include_callbacks:
                continue
            if mtype == "tone" and not request.include_tone:
                continue
            if mtype == "decision" and not request.include_decisions:
                continue
            filtered_candidates.append(c)

        # 4. Write Candidates
        write_results = []
        written_count = 0
        skipped_count = 0
        failed_count = 0

        if request.persist_memory:
            for cand in filtered_candidates:
                res = self._write_candidate(cand, request)
                write_results.append(res)
                if res.status in ("written", "updated"):
                    written_count += 1
                elif res.status == "skipped":
                    skipped_count += 1
                elif res.status == "failed":
                    failed_count += 1

        return MemoryExtractionResponse(
            book_id=request.book_id,
            run_id=request.run_id,
            chapter_id=request.chapter_id,
            source_type=request.source_type,
            execution_mode=request.execution_mode,
            status="completed",
            candidates=filtered_candidates,
            write_results=write_results,
            total_candidates=len(filtered_candidates),
            written_count=written_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            metadata=request.metadata,
        )
