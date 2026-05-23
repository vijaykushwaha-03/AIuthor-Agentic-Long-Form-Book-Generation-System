"""
AIuthor Backend — Continuity Pack Service (Module 9.0).
"""
from __future__ import annotations

import json
import logging
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

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
from app.workflows.schemas import (
    ContinuityPackRequest,
    ContinuityPackResponse,
)
from app.services.exceptions import NotFoundError
from app.services import MemoryService

logger = logging.getLogger(__name__)


class ContinuityPackService:
    """
    Service responsible for building book context packages for consumption by writing agents.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.memory_service = MemoryService(db)

    def build_continuity_pack(self, request: ContinuityPackRequest) -> ContinuityPackResponse:
        """
        Gathers memory records from tables and constructs a stable Markdown pack.
        """
        # Validate BookProject exists
        book = self.db.get(BookProject, request.book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(request.book_id)},
            )

        facts_data = []
        concepts_data = []
        characters_data = []
        callbacks_data = []
        tone_data = []
        decisions_data = []

        # 1. Facts
        if request.include_facts:
            q = self.db.query(FactRegistry).filter(FactRegistry.book_id == request.book_id)
            if request.chapter_id:
                # Include facts connected to this chapter or global/book-level (null chapter_id)
                q = q.filter(
                    or_(
                        FactRegistry.chapter_id == request.chapter_id,
                        FactRegistry.chapter_id.is_(None)
                    )
                )
            q = q.order_by(desc(FactRegistry.created_at)).limit(request.max_items_per_type)
            for f in q.all():
                facts_data.append({
                    "id": str(f.id),
                    "claim": f.claim,
                    "confidence": f.confidence,
                    "status": f.status,
                    "used_in_chapters": f.used_in_chapters,
                    "metadata": f.fact_metadata
                })

        # 2. Concepts
        if request.include_concepts:
            q = self.db.query(ConceptBible).filter(ConceptBible.book_id == request.book_id)
            q = q.order_by(asc(ConceptBible.concept)).limit(request.max_items_per_type)
            for c in q.all():
                concepts_data.append({
                    "id": str(c.id),
                    "concept": c.concept,
                    "definition": c.definition,
                    "first_chapter": c.first_chapter,
                    "related_terms": c.related_terms,
                    "appears_in_chapters": c.appears_in_chapters,
                    "metadata": c.concept_metadata
                })

        # 3. Characters
        if request.include_characters:
            q = self.db.query(CharacterBible).filter(CharacterBible.book_id == request.book_id)
            q = q.order_by(asc(CharacterBible.character_name)).limit(request.max_items_per_type)
            for ch in q.all():
                characters_data.append({
                    "id": str(ch.id),
                    "character_name": ch.character_name,
                    "role": ch.role,
                    "traits": ch.traits,
                    "relationships": ch.relationships,
                    "arc_summary": ch.arc_summary,
                    "appears_in_chapters": ch.appears_in_chapters,
                    "metadata": ch.character_metadata
                })

        # 4. Callbacks
        if request.include_callbacks:
            q = self.db.query(CallbackIndex).filter(CallbackIndex.book_id == request.book_id)
            if request.chapter_id:
                ch = self.db.get(Chapter, request.chapter_id)
                if ch:
                    ch_num = ch.chapter_number
                    q = q.filter(
                        or_(
                            CallbackIndex.source_chapter == ch_num,
                            CallbackIndex.target_chapter == ch_num
                        )
                    )
            q = q.order_by(asc(CallbackIndex.source_chapter), asc(CallbackIndex.target_chapter)).limit(request.max_items_per_type)
            for cb in q.all():
                callbacks_data.append({
                    "id": str(cb.id),
                    "source_chapter": cb.source_chapter,
                    "target_chapter": cb.target_chapter,
                    "concept": cb.concept,
                    "callback_text": cb.callback_text,
                    "status": cb.status,
                    "metadata": cb.callback_metadata
                })

        # 5. Tone Fingerprints
        if request.include_tone:
            q = self.db.query(ToneFingerprint).filter(ToneFingerprint.book_id == request.book_id)
            q = q.order_by(desc(ToneFingerprint.created_at)).limit(request.max_items_per_type)
            for t in q.all():
                tone_data.append({
                    "id": str(t.id),
                    "tone_name": t.tone_name,
                    "sentence_rhythm": t.sentence_rhythm,
                    "lexical_rules": t.lexical_rules,
                    "banned_phrases": t.banned_phrases,
                    "example_phrases": t.example_phrases,
                    "metadata": t.fingerprint_metadata
                })

        # 6. Decisions
        if request.include_decisions:
            q = self.db.query(DecisionLog).filter(DecisionLog.book_id == request.book_id)
            q = q.order_by(desc(DecisionLog.created_at)).limit(request.max_items_per_type)
            for d in q.all():
                decisions_data.append({
                    "id": str(d.id),
                    "decision": d.decision,
                    "reason": d.reason,
                    "impact": d.impact,
                    "metadata": d.decision_metadata
                })

        # Build stable continuity text markdown
        header = "# Continuity Pack\n\n"
        current_text = header

        section_configs = [
            ("Facts", facts_data, lambda f: f"- {f['claim']} (Confidence: {f['confidence'] or 1.0})"),
            ("Concepts", concepts_data, lambda c: f"- {c['concept']}: {c['definition'] or 'No definition'}"),
            ("Characters", characters_data, lambda ch: f"- {ch['character_name']} (Role: {ch['role'] or 'Unknown'}): {ch['arc_summary'] or 'No arc summary'}" + (f" Traits: {', '.join(ch['traits'])}" if isinstance(ch['traits'], list) else "")),
            ("Callbacks", callbacks_data, lambda cb: f"- Callback (Concept: {cb['concept'] or 'None'}): {cb['callback_text']} (Ch {cb['source_chapter'] or '?'} -> Ch {cb['target_chapter'] or '?'})"),
            ("Tone Fingerprints", tone_data, lambda t: f"- Tone: {t['tone_name']} (Rhythm: {json.dumps(t['sentence_rhythm'] or {})})"),
            ("Decisions", decisions_data, lambda d: f"- Decision: {d['decision']} (Reason: {d['reason'] or 'None'})")
        ]

        for sec_title, sec_items, formatter in section_configs:
            if not sec_items:
                continue
            sec_header = f"## {sec_title}\n"
            if len(current_text) + len(sec_header) + 1 > request.max_chars:
                break

            sec_text = sec_header
            added_any = False
            for item in sec_items:
                item_text = formatter(item) + "\n"
                if len(current_text) + len(sec_text) + len(item_text) + 1 > request.max_chars:
                    break
                sec_text += item_text
                added_any = True

            if added_any:
                current_text += sec_text + "\n"

        continuity_text = current_text.strip()
        total_items = len(facts_data) + len(concepts_data) + len(characters_data) + len(callbacks_data) + len(tone_data) + len(decisions_data)

        return ContinuityPackResponse(
            book_id=request.book_id,
            chapter_id=request.chapter_id,
            continuity_text=continuity_text,
            facts=facts_data,
            concepts=concepts_data,
            characters=characters_data,
            callbacks=callbacks_data,
            tone_fingerprints=tone_data,
            decisions=decisions_data,
            total_items=total_items,
            total_chars=len(continuity_text),
        )
