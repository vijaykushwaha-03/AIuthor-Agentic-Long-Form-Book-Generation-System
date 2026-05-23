"""
AIuthor Backend — Memory Service.

Encapsulates all database operations for the memory resources: FactRegistry,
ConceptBible, CharacterBible, CallbackIndex, ToneFingerprint, DecisionLog,
and Memory Envelope read/write operations.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

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
    MemoryReadRequest,
    MemoryReadResponse,
    MemoryWriteRequest,
    MemoryWriteResponse,
)
from app.services.exceptions import NotFoundError, ValidationServiceError, ConflictError

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service layer for memory database operations.

    All write operations commit + refresh; any DB error causes a rollback before re-raising.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Private helpers ───────────────────────────────────────────────────────

    def _commit(self) -> None:
        """Commit the current transaction; rollback and re-raise on failure."""
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _verify_book(self, book_id: UUID) -> BookProject:
        """Confirm BookProject exists, else raise NotFoundError."""
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    def _verify_chapter_optional(self, book_id: UUID, chapter_id: UUID | None) -> Chapter | None:
        """If chapter_id is provided, verify it exists for this book."""
        if chapter_id is None:
            return None
        chapter = (
            self.db.query(Chapter)
            .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
            .first()
        )
        if chapter is None:
            raise NotFoundError(
                message="Chapter not found",
                code="chapter_not_found",
                details={"chapter_id": str(chapter_id), "book_id": str(book_id)},
            )
        return chapter

    def _enum_to_str(self, value: Any) -> str | None:
        """Convert enum values to string where needed."""
        if value is None:
            return None
        if hasattr(value, "value"):
            return value.value
        return str(value)

    # ── Fact Registry methods ──────────────────────────────────────────────────

    def create_fact(self, payload: FactRegistryCreate, book_id: UUID | None = None) -> FactRegistry:
        """Create a new fact claim."""
        effective_book_id = book_id if book_id is not None else payload.book_id
        self._verify_book(effective_book_id)
        self._verify_chapter_optional(effective_book_id, payload.chapter_id)

        fact = FactRegistry(
            book_id=effective_book_id,
            chapter_id=payload.chapter_id,
            claim=payload.claim,
            source_document_id=payload.source_document_id,
            source_chunk_id=payload.source_chunk_id,
            confidence=payload.confidence,
            status=payload.status or "unverified",
            used_in_chapters=payload.used_in_chapters,
            fact_metadata=payload.fact_metadata,
        )
        self.db.add(fact)
        self._commit()
        self.db.refresh(fact)
        logger.info("Created Fact id=%s for book_id=%s", fact.id, effective_book_id)
        return fact

    def get_fact(self, book_id: UUID, fact_id: UUID) -> FactRegistry:
        """Fetch a fact by id and book_id."""
        fact = (
            self.db.query(FactRegistry)
            .filter(FactRegistry.id == fact_id, FactRegistry.book_id == book_id)
            .first()
        )
        if fact is None:
            raise NotFoundError(
                message="Fact registry entry not found",
                code="fact_not_found",
                details={"fact_id": str(fact_id), "book_id": str(book_id)},
            )
        return fact

    def list_facts(
        self,
        book_id: UUID,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        chapter_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[FactRegistry], int]:
        """Return a paginated list of fact claims."""
        self._verify_book(book_id)
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = self.db.query(FactRegistry).filter(FactRegistry.book_id == book_id)
        if status is not None:
            query = query.filter(FactRegistry.status == status)
        if chapter_id is not None:
            query = query.filter(FactRegistry.chapter_id == chapter_id)
        if search is not None:
            query = query.filter(FactRegistry.claim.ilike(f"%{search}%"))

        query = query.order_by(desc(FactRegistry.created_at))
        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    def update_fact(self, book_id: UUID, fact_id: UUID, payload: FactRegistryUpdate) -> FactRegistry:
        """Apply a partial update to a fact claim."""
        fact = self.get_fact(book_id, fact_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "chapter_id" in update_data:
            self._verify_chapter_optional(book_id, update_data["chapter_id"])

        for field, value in update_data.items():
            setattr(fact, field, value)

        self._commit()
        self.db.refresh(fact)
        logger.info("Updated Fact id=%s", fact_id)
        return fact

    def delete_fact(self, book_id: UUID, fact_id: UUID) -> bool:
        """Permanently delete a fact claim."""
        fact = self.get_fact(book_id, fact_id)
        self.db.delete(fact)
        self._commit()
        logger.info("Deleted Fact id=%s", fact_id)
        return True

    # ── Concept Bible methods ──────────────────────────────────────────────────

    def create_concept(self, payload: ConceptBibleCreate, book_id: UUID | None = None) -> ConceptBible:
        """Create a new concept/glossary entry."""
        effective_book_id = book_id if book_id is not None else payload.book_id
        self._verify_book(effective_book_id)

        # Check unique constraint
        existing = (
            self.db.query(ConceptBible)
            .filter(ConceptBible.book_id == effective_book_id, ConceptBible.concept == payload.concept)
            .first()
        )
        if existing:
            raise ConflictError(
                message=f"Concept '{payload.concept}' already exists for this book.",
                code="duplicate_concept",
                details={"concept": payload.concept, "book_id": str(effective_book_id)},
            )

        concept = ConceptBible(
            book_id=effective_book_id,
            concept=payload.concept,
            definition=payload.definition,
            first_chapter=payload.first_chapter,
            related_terms=payload.related_terms,
            appears_in_chapters=payload.appears_in_chapters,
            concept_metadata=payload.concept_metadata,
        )
        self.db.add(concept)
        self._commit()
        self.db.refresh(concept)
        logger.info("Created Concept id=%s concept=%s", concept.id, concept.concept)
        return concept

    def get_concept(self, book_id: UUID, concept_id: UUID) -> ConceptBible:
        """Fetch a concept by id and book_id."""
        concept = (
            self.db.query(ConceptBible)
            .filter(ConceptBible.id == concept_id, ConceptBible.book_id == book_id)
            .first()
        )
        if concept is None:
            raise NotFoundError(
                message="Concept not found in book",
                code="concept_not_found",
                details={"concept_id": str(concept_id), "book_id": str(book_id)},
            )
        return concept

    def list_concepts(
        self,
        book_id: UUID,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
    ) -> tuple[list[ConceptBible], int]:
        """Return a paginated list of concepts sorted alphabetically."""
        self._verify_book(book_id)
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = self.db.query(ConceptBible).filter(ConceptBible.book_id == book_id)
        if search is not None:
            query = query.filter(
                or_(
                    ConceptBible.concept.ilike(f"%{search}%"),
                    ConceptBible.definition.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(asc(ConceptBible.concept))
        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    def update_concept(self, book_id: UUID, concept_id: UUID, payload: ConceptBibleUpdate) -> ConceptBible:
        """Apply a partial update to a concept."""
        concept = self.get_concept(book_id, concept_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "concept" in update_data and update_data["concept"] != concept.concept:
            existing = (
                self.db.query(ConceptBible)
                .filter(ConceptBible.book_id == book_id, ConceptBible.concept == update_data["concept"])
                .first()
            )
            if existing:
                raise ConflictError(
                    message=f"Concept '{update_data['concept']}' already exists for this book.",
                    code="duplicate_concept",
                    details={"concept": update_data["concept"], "book_id": str(book_id)},
                )

        for field, value in update_data.items():
            setattr(concept, field, value)

        self._commit()
        self.db.refresh(concept)
        logger.info("Updated Concept id=%s", concept_id)
        return concept

    def delete_concept(self, book_id: UUID, concept_id: UUID) -> bool:
        """Permanently delete a concept."""
        concept = self.get_concept(book_id, concept_id)
        self.db.delete(concept)
        self._commit()
        logger.info("Deleted Concept id=%s", concept_id)
        return True

    # ── Character Bible methods ──────────────────────────────────────────────────

    def create_character(self, payload: CharacterBibleCreate, book_id: UUID | None = None) -> CharacterBible:
        """Create a new character continuity record."""
        effective_book_id = book_id if book_id is not None else payload.book_id
        self._verify_book(effective_book_id)

        # Check unique constraint
        existing = (
            self.db.query(CharacterBible)
            .filter(CharacterBible.book_id == effective_book_id, CharacterBible.character_name == payload.character_name)
            .first()
        )
        if existing:
            raise ConflictError(
                message=f"Character '{payload.character_name}' already exists for this book.",
                code="duplicate_character",
                details={"character_name": payload.character_name, "book_id": str(effective_book_id)},
            )

        character = CharacterBible(
            book_id=effective_book_id,
            character_name=payload.character_name,
            role=payload.role,
            traits=payload.traits,
            relationships=payload.relationships,
            arc_summary=payload.arc_summary,
            appears_in_chapters=payload.appears_in_chapters,
            character_metadata=payload.character_metadata,
        )
        self.db.add(character)
        self._commit()
        self.db.refresh(character)
        logger.info("Created Character id=%s name=%s", character.id, character.character_name)
        return character

    def get_character(self, book_id: UUID, character_id: UUID) -> CharacterBible:
        """Fetch a character by id and book_id."""
        character = (
            self.db.query(CharacterBible)
            .filter(CharacterBible.id == character_id, CharacterBible.book_id == book_id)
            .first()
        )
        if character is None:
            raise NotFoundError(
                message="Character not found in book",
                code="character_not_found",
                details={"character_id": str(character_id), "book_id": str(book_id)},
            )
        return character

    def list_characters(
        self,
        book_id: UUID,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
    ) -> tuple[list[CharacterBible], int]:
        """Return a paginated list of characters sorted alphabetically."""
        self._verify_book(book_id)
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = self.db.query(CharacterBible).filter(CharacterBible.book_id == book_id)
        if search is not None:
            query = query.filter(
                or_(
                    CharacterBible.character_name.ilike(f"%{search}%"),
                    CharacterBible.role.ilike(f"%{search}%"),
                    CharacterBible.arc_summary.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(asc(CharacterBible.character_name))
        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    def update_character(self, book_id: UUID, character_id: UUID, payload: CharacterBibleUpdate) -> CharacterBible:
        """Apply a partial update to a character."""
        character = self.get_character(book_id, character_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "character_name" in update_data and update_data["character_name"] != character.character_name:
            existing = (
                self.db.query(CharacterBible)
                .filter(CharacterBible.book_id == book_id, CharacterBible.character_name == update_data["character_name"])
                .first()
            )
            if existing:
                raise ConflictError(
                    message=f"Character '{update_data['character_name']}' already exists for this book.",
                    code="duplicate_character",
                    details={"character_name": update_data["character_name"], "book_id": str(book_id)},
                )

        for field, value in update_data.items():
            setattr(character, field, value)

        self._commit()
        self.db.refresh(character)
        logger.info("Updated Character id=%s", character_id)
        return character

    def delete_character(self, book_id: UUID, character_id: UUID) -> bool:
        """Permanently delete a character."""
        character = self.get_character(book_id, character_id)
        self.db.delete(character)
        self._commit()
        logger.info("Deleted Character id=%s", character_id)
        return True

    # ── Callback Index methods ─────────────────────────────────────────────────

    def create_callback(self, payload: CallbackIndexCreate, book_id: UUID | None = None) -> CallbackIndex:
        """Create a new callback reference."""
        effective_book_id = book_id if book_id is not None else payload.book_id
        self._verify_book(effective_book_id)

        callback = CallbackIndex(
            book_id=effective_book_id,
            source_chapter=payload.source_chapter,
            target_chapter=payload.target_chapter,
            concept=payload.concept,
            callback_text=payload.callback_text,
            status=payload.status or "active",
            callback_metadata=payload.callback_metadata,
        )
        self.db.add(callback)
        self._commit()
        self.db.refresh(callback)
        logger.info("Created Callback id=%s for book_id=%s", callback.id, effective_book_id)
        return callback

    def get_callback(self, book_id: UUID, callback_id: UUID) -> CallbackIndex:
        """Fetch a callback by id and book_id."""
        callback = (
            self.db.query(CallbackIndex)
            .filter(CallbackIndex.id == callback_id, CallbackIndex.book_id == book_id)
            .first()
        )
        if callback is None:
            raise NotFoundError(
                message="Callback not found",
                code="callback_not_found",
                details={"callback_id": str(callback_id), "book_id": str(book_id)},
            )
        return callback

    def list_callbacks(
        self,
        book_id: UUID,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        source_chapter: int | None = None,
        target_chapter: int | None = None,
        search: str | None = None,
    ) -> tuple[list[CallbackIndex], int]:
        """Return a paginated list of callbacks sorted by source then target chapter."""
        self._verify_book(book_id)
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = self.db.query(CallbackIndex).filter(CallbackIndex.book_id == book_id)
        if status is not None:
            query = query.filter(CallbackIndex.status == status)
        if source_chapter is not None:
            query = query.filter(CallbackIndex.source_chapter == source_chapter)
        if target_chapter is not None:
            query = query.filter(CallbackIndex.target_chapter == target_chapter)
        if search is not None:
            query = query.filter(
                or_(
                    CallbackIndex.concept.ilike(f"%{search}%"),
                    CallbackIndex.callback_text.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(
            asc(CallbackIndex.source_chapter),
            asc(CallbackIndex.target_chapter),
            asc(CallbackIndex.created_at),
        )
        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    def update_callback(self, book_id: UUID, callback_id: UUID, payload: CallbackIndexUpdate) -> CallbackIndex:
        """Apply a partial update to a callback."""
        callback = self.get_callback(book_id, callback_id)
        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(callback, field, value)

        self._commit()
        self.db.refresh(callback)
        logger.info("Updated Callback id=%s", callback_id)
        return callback

    def delete_callback(self, book_id: UUID, callback_id: UUID) -> bool:
        """Permanently delete a callback."""
        callback = self.get_callback(book_id, callback_id)
        self.db.delete(callback)
        self._commit()
        logger.info("Deleted Callback id=%s", callback_id)
        return True

    # ── Tone Fingerprint methods ────────────────────────────────────────────────

    def create_tone_fingerprint(self, payload: ToneFingerprintCreate, book_id: UUID | None = None) -> ToneFingerprint:
        """Create a new tone fingerprint record."""
        effective_book_id = book_id if book_id is not None else payload.book_id
        self._verify_book(effective_book_id)

        tone_name_str = self._enum_to_str(payload.tone_name)

        tone = ToneFingerprint(
            book_id=effective_book_id,
            tone_name=tone_name_str,
            sentence_rhythm=payload.sentence_rhythm,
            lexical_rules=payload.lexical_rules,
            banned_phrases=payload.banned_phrases,
            example_phrases=payload.example_phrases,
            fingerprint_metadata=payload.fingerprint_metadata,
        )
        self.db.add(tone)
        self._commit()
        self.db.refresh(tone)
        logger.info("Created ToneFingerprint id=%s tone_name=%s", tone.id, tone.tone_name)
        return tone

    def get_tone_fingerprint(self, book_id: UUID, tone_id: UUID) -> ToneFingerprint:
        """Fetch a tone fingerprint by id and book_id."""
        tone = (
            self.db.query(ToneFingerprint)
            .filter(ToneFingerprint.id == tone_id, ToneFingerprint.book_id == book_id)
            .first()
        )
        if tone is None:
            raise NotFoundError(
                message="Tone fingerprint not found",
                code="tone_fingerprint_not_found",
                details={"tone_id": str(tone_id), "book_id": str(book_id)},
            )
        return tone

    def list_tone_fingerprints(
        self,
        book_id: UUID,
        page: int = 1,
        page_size: int = 50,
        tone_name: str | None = None,
    ) -> tuple[list[ToneFingerprint], int]:
        """Return a paginated list of tone fingerprints sorted newest first."""
        self._verify_book(book_id)
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = self.db.query(ToneFingerprint).filter(ToneFingerprint.book_id == book_id)
        if tone_name is not None:
            query = query.filter(ToneFingerprint.tone_name == self._enum_to_str(tone_name))

        query = query.order_by(desc(ToneFingerprint.created_at))
        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    def update_tone_fingerprint(self, book_id: UUID, tone_id: UUID, payload: ToneFingerprintUpdate) -> ToneFingerprint:
        """Apply a partial update to a tone fingerprint."""
        tone = self.get_tone_fingerprint(book_id, tone_id)
        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "tone_name":
                value = self._enum_to_str(value)
            setattr(tone, field, value)

        self._commit()
        self.db.refresh(tone)
        logger.info("Updated ToneFingerprint id=%s", tone_id)
        return tone

    def delete_tone_fingerprint(self, book_id: UUID, tone_id: UUID) -> bool:
        """Permanently delete a tone fingerprint."""
        tone = self.get_tone_fingerprint(book_id, tone_id)
        self.db.delete(tone)
        self._commit()
        logger.info("Deleted ToneFingerprint id=%s", tone_id)
        return True

    # ── Decision Log methods ──────────────────────────────────────────────────

    def create_decision(self, payload: DecisionLogCreate, book_id: UUID | None = None) -> DecisionLog:
        """Create a new decision log entry."""
        effective_book_id = book_id if book_id is not None else payload.book_id
        if effective_book_id is not None:
            self._verify_book(effective_book_id)

        decision = DecisionLog(
            book_id=effective_book_id,
            decision=payload.decision,
            reason=payload.reason,
            impact=payload.impact,
            decision_metadata=payload.decision_metadata,
        )
        self.db.add(decision)
        self._commit()
        self.db.refresh(decision)
        logger.info("Created DecisionLog id=%s for book_id=%s", decision.id, effective_book_id)
        return decision

    def get_decision(self, decision_id: UUID) -> DecisionLog:
        """Fetch a decision by id."""
        decision = self.db.get(DecisionLog, decision_id)
        if decision is None:
            raise NotFoundError(
                message="Decision log entry not found",
                code="decision_log_not_found",
                details={"decision_id": str(decision_id)},
            )
        return decision

    def list_decisions(
        self,
        book_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
    ) -> tuple[list[DecisionLog], int]:
        """Return a paginated list of decisions sorted newest first."""
        if book_id is not None:
            self._verify_book(book_id)

        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = self.db.query(DecisionLog)
        if book_id is not None:
            query = query.filter(DecisionLog.book_id == book_id)

        if search is not None:
            query = query.filter(
                or_(
                    DecisionLog.decision.ilike(f"%{search}%"),
                    DecisionLog.reason.ilike(f"%{search}%"),
                    DecisionLog.impact.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(desc(DecisionLog.created_at))
        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    def update_decision(self, decision_id: UUID, payload: DecisionLogUpdate) -> DecisionLog:
        """Apply a partial update to a decision."""
        decision = self.get_decision(decision_id)
        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(decision, field, value)

        self._commit()
        self.db.refresh(decision)
        logger.info("Updated DecisionLog id=%s", decision_id)
        return decision

    def delete_decision(self, decision_id: UUID) -> bool:
        """Permanently delete a decision."""
        decision = self.get_decision(decision_id)
        self.db.delete(decision)
        self._commit()
        logger.info("Deleted DecisionLog id=%s", decision_id)
        return True

    # ── Memory Envelope methods ───────────────────────────────────────────────

    def read_memory(self, request: MemoryReadRequest) -> MemoryReadResponse:
        """Query the memory system for a specific book."""
        self._verify_book(request.book_id)

        types = request.memory_types
        if not types:
            types = ["facts", "concepts", "characters", "callbacks", "tone_fingerprints", "decisions"]

        limit = request.limit
        query_str = request.query
        chapter_num = request.chapter_number

        res: dict[str, list[Any]] = {
            "facts": [],
            "concepts": [],
            "characters": [],
            "callbacks": [],
            "tone_fingerprints": [],
            "decisions": [],
        }

        # Resolve chapter_id if chapter_number is provided
        chapter_id = None
        if chapter_num is not None:
            ch = (
                self.db.query(Chapter)
                .filter(Chapter.book_id == request.book_id, Chapter.chapter_number == chapter_num)
                .first()
            )
            if ch:
                chapter_id = ch.id

        if "facts" in types:
            q = self.db.query(FactRegistry).filter(FactRegistry.book_id == request.book_id)
            if query_str:
                q = q.filter(FactRegistry.claim.ilike(f"%{query_str}%"))
            q = q.order_by(desc(FactRegistry.created_at))
            facts_list = q.all()

            filtered_facts = []
            for fact in facts_list:
                if chapter_num is not None:
                    used_ch = fact.used_in_chapters
                    in_used = isinstance(used_ch, list) and chapter_num in used_ch
                    in_ch = (fact.chapter_id == chapter_id) if chapter_id else False
                    if not (in_used or in_ch):
                        continue
                filtered_facts.append(fact)
            res["facts"] = filtered_facts[:limit]

        if "concepts" in types:
            q = self.db.query(ConceptBible).filter(ConceptBible.book_id == request.book_id)
            if query_str:
                q = q.filter(
                    or_(
                        ConceptBible.concept.ilike(f"%{query_str}%"),
                        ConceptBible.definition.ilike(f"%{query_str}%"),
                    )
                )
            q = q.order_by(asc(ConceptBible.concept))
            res["concepts"] = q.limit(limit).all()

        if "characters" in types:
            q = self.db.query(CharacterBible).filter(CharacterBible.book_id == request.book_id)
            if query_str:
                q = q.filter(
                    or_(
                        CharacterBible.character_name.ilike(f"%{query_str}%"),
                        CharacterBible.role.ilike(f"%{query_str}%"),
                        CharacterBible.arc_summary.ilike(f"%{query_str}%"),
                    )
                )
            q = q.order_by(asc(CharacterBible.character_name))
            res["characters"] = q.limit(limit).all()

        if "callbacks" in types:
            q = self.db.query(CallbackIndex).filter(CallbackIndex.book_id == request.book_id)
            if chapter_num is not None:
                q = q.filter(
                    or_(
                        CallbackIndex.source_chapter == chapter_num,
                        CallbackIndex.target_chapter == chapter_num,
                    )
                )
            if query_str:
                q = q.filter(
                    or_(
                        CallbackIndex.concept.ilike(f"%{query_str}%"),
                        CallbackIndex.callback_text.ilike(f"%{query_str}%"),
                    )
                )
            q = q.order_by(
                asc(CallbackIndex.source_chapter),
                asc(CallbackIndex.target_chapter),
                asc(CallbackIndex.created_at),
            )
            res["callbacks"] = q.limit(limit).all()

        if "tone_fingerprints" in types:
            q = self.db.query(ToneFingerprint).filter(ToneFingerprint.book_id == request.book_id)
            if query_str:
                q = q.filter(ToneFingerprint.tone_name.ilike(f"%{query_str}%"))
            q = q.order_by(desc(ToneFingerprint.created_at))
            res["tone_fingerprints"] = q.limit(limit).all()

        if "decisions" in types:
            q = self.db.query(DecisionLog).filter(DecisionLog.book_id == request.book_id)
            if query_str:
                q = q.filter(
                    or_(
                        DecisionLog.decision.ilike(f"%{query_str}%"),
                        DecisionLog.reason.ilike(f"%{query_str}%"),
                        DecisionLog.impact.ilike(f"%{query_str}%"),
                    )
                )
            q = q.order_by(desc(DecisionLog.created_at))
            res["decisions"] = q.limit(limit).all()

        total_items = sum(len(res[k]) for k in res)

        return MemoryReadResponse(
            book_id=request.book_id,
            facts=res["facts"],
            concepts=res["concepts"],
            characters=res["characters"],
            callbacks=res["callbacks"],
            tone_fingerprints=res["tone_fingerprints"],
            decisions=res["decisions"],
            total_items=total_items,
        )

    def write_memory(self, request: MemoryWriteRequest) -> MemoryWriteResponse:
        """Write collections of memory records."""
        self._verify_book(request.book_id)

        created_counts = {
            "facts": 0,
            "concepts": 0,
            "characters": 0,
            "callbacks": 0,
            "tone_fingerprints": 0,
            "decisions": 0,
        }

        # 1. Validation & Safety Checks
        for fact_in in request.facts:
            if fact_in.book_id != request.book_id:
                raise ValidationServiceError(
                    message=f"Fact book_id {fact_in.book_id} does not match request book_id {request.book_id}",
                    code="book_id_mismatch",
                )
            self._verify_chapter_optional(request.book_id, fact_in.chapter_id)

        for concept_in in request.concepts:
            if concept_in.book_id != request.book_id:
                raise ValidationServiceError(
                    message=f"Concept book_id {concept_in.book_id} does not match request book_id {request.book_id}",
                    code="book_id_mismatch",
                )
            existing = (
                self.db.query(ConceptBible)
                .filter(ConceptBible.book_id == request.book_id, ConceptBible.concept == concept_in.concept)
                .first()
            )
            if existing:
                raise ConflictError(
                    message=f"Concept '{concept_in.concept}' already exists for this book.",
                    code="duplicate_concept",
                )

        for char_in in request.characters:
            if char_in.book_id != request.book_id:
                raise ValidationServiceError(
                    message=f"Character book_id {char_in.book_id} does not match request book_id {request.book_id}",
                    code="book_id_mismatch",
                )
            existing = (
                self.db.query(CharacterBible)
                .filter(CharacterBible.book_id == request.book_id, CharacterBible.character_name == char_in.character_name)
                .first()
            )
            if existing:
                raise ConflictError(
                    message=f"Character '{char_in.character_name}' already exists for this book.",
                    code="duplicate_character",
                )

        for cb_in in request.callbacks:
            if cb_in.book_id != request.book_id:
                raise ValidationServiceError(
                    message=f"Callback book_id {cb_in.book_id} does not match request book_id {request.book_id}",
                    code="book_id_mismatch",
                )

        for tone_in in request.tone_fingerprints:
            if tone_in.book_id != request.book_id:
                raise ValidationServiceError(
                    message=f"Tone fingerprint book_id {tone_in.book_id} does not match request book_id {request.book_id}",
                    code="book_id_mismatch",
                )

        for dec_in in request.decisions:
            if dec_in.book_id is not None and dec_in.book_id != request.book_id:
                raise ValidationServiceError(
                    message=f"Decision book_id {dec_in.book_id} does not match request book_id {request.book_id}",
                    code="book_id_mismatch",
                )

        # 2. Add records
        for fact_in in request.facts:
            fact = FactRegistry(
                book_id=request.book_id,
                chapter_id=fact_in.chapter_id,
                claim=fact_in.claim,
                source_document_id=fact_in.source_document_id,
                source_chunk_id=fact_in.source_chunk_id,
                confidence=fact_in.confidence,
                status=fact_in.status or "unverified",
                used_in_chapters=fact_in.used_in_chapters,
                fact_metadata=fact_in.fact_metadata,
            )
            self.db.add(fact)
            created_counts["facts"] += 1

        for concept_in in request.concepts:
            concept = ConceptBible(
                book_id=request.book_id,
                concept=concept_in.concept,
                definition=concept_in.definition,
                first_chapter=concept_in.first_chapter,
                related_terms=concept_in.related_terms,
                appears_in_chapters=concept_in.appears_in_chapters,
                concept_metadata=concept_in.concept_metadata,
            )
            self.db.add(concept)
            created_counts["concepts"] += 1

        for char_in in request.characters:
            char = CharacterBible(
                book_id=request.book_id,
                character_name=char_in.character_name,
                role=char_in.role,
                traits=char_in.traits,
                relationships=char_in.relationships,
                arc_summary=char_in.arc_summary,
                appears_in_chapters=char_in.appears_in_chapters,
                character_metadata=char_in.character_metadata,
            )
            self.db.add(char)
            created_counts["characters"] += 1

        for cb_in in request.callbacks:
            cb = CallbackIndex(
                book_id=request.book_id,
                source_chapter=cb_in.source_chapter,
                target_chapter=cb_in.target_chapter,
                concept=cb_in.concept,
                callback_text=cb_in.callback_text,
                status=cb_in.status or "active",
                callback_metadata=cb_in.callback_metadata,
            )
            self.db.add(cb)
            created_counts["callbacks"] += 1

        for tone_in in request.tone_fingerprints:
            tone = ToneFingerprint(
                book_id=request.book_id,
                tone_name=self._enum_to_str(tone_in.tone_name),
                sentence_rhythm=tone_in.sentence_rhythm,
                lexical_rules=tone_in.lexical_rules,
                banned_phrases=tone_in.banned_phrases,
                example_phrases=tone_in.example_phrases,
                fingerprint_metadata=tone_in.fingerprint_metadata,
            )
            self.db.add(tone)
            created_counts["tone_fingerprints"] += 1

        for dec_in in request.decisions:
            dec = DecisionLog(
                book_id=request.book_id,  # force override
                decision=dec_in.decision,
                reason=dec_in.reason,
                impact=dec_in.impact,
                decision_metadata=dec_in.decision_metadata,
            )
            self.db.add(dec)
            created_counts["decisions"] += 1

        self._commit()

        return MemoryWriteResponse(
            book_id=request.book_id,
            operation=self._enum_to_str(request.operation) or "write",
            created_counts=created_counts,
            updated_counts={k: 0 for k in created_counts},
            status="completed",
            message=f"Successfully wrote {sum(created_counts.values())} memories.",
        )
