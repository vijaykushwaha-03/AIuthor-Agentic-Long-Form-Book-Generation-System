from __future__ import annotations

import pytest
from pydantic import ValidationError
from uuid import uuid4
from datetime import datetime

from app.schemas import (
    FactRegistryCreate,
    FactRegistryUpdate,
    FactRegistryResponse,
    ConceptBibleCreate,
    ConceptBibleUpdate,
    ConceptBibleResponse,
    CharacterBibleCreate,
    CharacterBibleUpdate,
    CharacterBibleResponse,
    CallbackIndexCreate,
    CallbackIndexUpdate,
    CallbackIndexResponse,
    ToneFingerprintCreate,
    ToneFingerprintUpdate,
    ToneFingerprintResponse,
    DecisionLogCreate,
    DecisionLogUpdate,
    DecisionLogResponse,
    MemoryReadRequest,
    MemoryReadResponse,
    MemoryWriteRequest,
    MemoryWriteResponse,
    TonePreset,
    MemoryOperation,
)


# ── 28. Package Exports Verification ──────────────────────────────────────────

def test_package_exports_memory():
    """Verify all memory schemas and types are properly imported from the schemas package."""
    assert FactRegistryCreate is not None
    assert FactRegistryUpdate is not None
    assert FactRegistryResponse is not None
    assert ConceptBibleCreate is not None
    assert ConceptBibleUpdate is not None
    assert ConceptBibleResponse is not None
    assert CharacterBibleCreate is not None
    assert CharacterBibleUpdate is not None
    assert CharacterBibleResponse is not None
    assert CallbackIndexCreate is not None
    assert CallbackIndexUpdate is not None
    assert CallbackIndexResponse is not None
    assert ToneFingerprintCreate is not None
    assert ToneFingerprintUpdate is not None
    assert ToneFingerprintResponse is not None
    assert DecisionLogCreate is not None
    assert DecisionLogUpdate is not None
    assert DecisionLogResponse is not None
    assert MemoryReadRequest is not None
    assert MemoryReadResponse is not None
    assert MemoryWriteRequest is not None
    assert MemoryWriteResponse is not None


# ── FactRegistry Tests ────────────────────────────────────────────────────────

def test_fact_registry_create_valid():
    """1. Valid data passes validation for FactRegistryCreate."""
    book_id = uuid4()
    schema = FactRegistryCreate(
        book_id=book_id,
        claim="The sun rises in the east.",
        confidence=0.95,
        status="verified",
        used_in_chapters=[1, 2, 3]
    )
    assert schema.book_id == book_id
    assert schema.claim == "The sun rises in the east."
    assert schema.confidence == 0.95
    assert schema.status == "verified"
    assert schema.used_in_chapters == [1, 2, 3]


def test_fact_registry_create_claim_too_short():
    """2. claim too short fails validation."""
    book_id = uuid4()
    # claim must be min_length=3. "ab" is 2.
    with pytest.raises(ValidationError):
        FactRegistryCreate(book_id=book_id, claim="ab")

    # Claim is stripped. "  ab  " is stripped to "ab", failing validation.
    with pytest.raises(ValidationError):
        FactRegistryCreate(book_id=book_id, claim="  ab  ")


def test_fact_registry_create_confidence_below_0():
    """3. confidence below 0 fails validation."""
    book_id = uuid4()
    with pytest.raises(ValidationError):
        FactRegistryCreate(
            book_id=book_id,
            claim="Valid claim",
            confidence=-0.1
        )


def test_fact_registry_create_confidence_above_1():
    """4. confidence above 1 fails validation."""
    book_id = uuid4()
    with pytest.raises(ValidationError):
        FactRegistryCreate(
            book_id=book_id,
            claim="Valid claim",
            confidence=1.01
        )


def test_fact_registry_create_used_in_chapters_zero():
    """5. used_in_chapters with 0 fails validation."""
    book_id = uuid4()
    with pytest.raises(ValidationError):
        FactRegistryCreate(
            book_id=book_id,
            claim="Valid claim",
            used_in_chapters=[0, 1]
        )


# ── ConceptBible Tests ────────────────────────────────────────────────────────

def test_concept_bible_create_valid():
    """6. Valid data passes validation for ConceptBibleCreate."""
    book_id = uuid4()
    schema = ConceptBibleCreate(
        book_id=book_id,
        concept="FTL Drive",
        definition="Faster-than-light propulsion system.",
        first_chapter=1,
        related_terms=["Hyperdrive", "Warp Engine"],
        appears_in_chapters=[1, 2]
    )
    assert schema.book_id == book_id
    assert schema.concept == "FTL Drive"
    assert schema.definition == "Faster-than-light propulsion system."
    assert schema.first_chapter == 1


def test_concept_bible_create_concept_too_short():
    """7. concept too short fails validation."""
    book_id = uuid4()
    # min_length is 2. "a" is 1.
    with pytest.raises(ValidationError):
        ConceptBibleCreate(book_id=book_id, concept="a")

    # Stripped check: "  a  " is stripped to "a", which fails.
    with pytest.raises(ValidationError):
        ConceptBibleCreate(book_id=book_id, concept="  a  ")


def test_concept_bible_create_first_chapter_below_1():
    """8. first_chapter below 1 fails validation."""
    book_id = uuid4()
    with pytest.raises(ValidationError):
        ConceptBibleCreate(
            book_id=book_id,
            concept="Valid Concept",
            first_chapter=0
        )


# ── CharacterBible Tests ──────────────────────────────────────────────────────

def test_character_bible_create_valid():
    """9. Valid data passes validation for CharacterBibleCreate."""
    book_id = uuid4()
    schema = CharacterBibleCreate(
        book_id=book_id,
        character_name="John Doe",
        role="Protagonist",
        traits=["brave", "honest"],
        relationships={"Jane Doe": "sister"},
        arc_summary="Saves the world.",
        appears_in_chapters=[1, 2, 3]
    )
    assert schema.book_id == book_id
    assert schema.character_name == "John Doe"
    assert schema.traits == ["brave", "honest"]


def test_character_bible_create_name_too_short():
    """10. character_name too short fails validation."""
    book_id = uuid4()
    # min_length is 2. "x" is 1.
    with pytest.raises(ValidationError):
        CharacterBibleCreate(book_id=book_id, character_name="x")

    # Stripped check: "  x  " is stripped to "x", which fails.
    with pytest.raises(ValidationError):
        CharacterBibleCreate(book_id=book_id, character_name="  x  ")


# ── CallbackIndex Tests ───────────────────────────────────────────────────────

def test_callback_index_create_valid():
    """11. Valid data passes validation for CallbackIndexCreate."""
    book_id = uuid4()
    schema = CallbackIndexCreate(
        book_id=book_id,
        source_chapter=2,
        target_chapter=5,
        concept="The Red Ring",
        callback_text="He glanced down at the red ring on his finger, remembering...",
        status="active"
    )
    assert schema.book_id == book_id
    assert schema.source_chapter == 2
    assert schema.target_chapter == 5
    assert schema.callback_text == "He glanced down at the red ring on his finger, remembering..."


def test_callback_index_create_source_chapter_below_1():
    """12. source_chapter below 1 fails validation."""
    book_id = uuid4()
    with pytest.raises(ValidationError):
        CallbackIndexCreate(
            book_id=book_id,
            source_chapter=0,
            callback_text="Valid callback text"
        )


def test_callback_index_create_callback_text_too_short():
    """13. callback_text too short fails validation."""
    book_id = uuid4()
    # min_length is 3. "ab" is 2.
    with pytest.raises(ValidationError):
        CallbackIndexCreate(
            book_id=book_id,
            callback_text="ab"
        )

    # Stripped check: "  ab  " is stripped to "ab", which fails.
    with pytest.raises(ValidationError):
        CallbackIndexCreate(
            book_id=book_id,
            callback_text="  ab  "
        )


# ── ToneFingerprint Tests ─────────────────────────────────────────────────────

def test_tone_fingerprint_create_valid():
    """14. Valid conversational tone passes validation."""
    book_id = uuid4()
    # Test using TonePreset
    schema_preset = ToneFingerprintCreate(
        book_id=book_id,
        tone_name=TonePreset.CONVERSATIONAL,
        sentence_rhythm={"avg_length": 15},
        lexical_rules={"use_contractions": True},
        banned_phrases=["utilize", "furthermore"],
        example_phrases=["Hey there!", "Let's find out."]
    )
    assert schema_preset.book_id == book_id
    assert schema_preset.tone_name == TonePreset.CONVERSATIONAL

    # Test using a valid string tone name <= 50 characters
    schema_str = ToneFingerprintCreate(
        book_id=book_id,
        tone_name="Noir-Mystery-Fiction",
        sentence_rhythm={"avg_length": 10}
    )
    assert schema_str.tone_name == "Noir-Mystery-Fiction"

    # Test too-long string tone name fails (> 50 chars)
    with pytest.raises(ValidationError):
        ToneFingerprintCreate(
            book_id=book_id,
            tone_name="a" * 51
        )


def test_tone_fingerprint_create_empty_banned_phrase():
    """15. empty banned phrase in list fails validation."""
    book_id = uuid4()
    # Empty string inside list fails
    with pytest.raises(ValidationError):
        ToneFingerprintCreate(
            book_id=book_id,
            tone_name="conversational",
            banned_phrases=["", "fine"]
        )

    # Whitespace-only string inside list fails
    with pytest.raises(ValidationError):
        ToneFingerprintCreate(
            book_id=book_id,
            tone_name="conversational",
            banned_phrases=["   "]
        )


# ── DecisionLog Tests ─────────────────────────────────────────────────────────

def test_decision_log_create_valid():
    """16. Valid data passes validation for DecisionLogCreate."""
    schema = DecisionLogCreate(
        decision="Using a first-person narrator.",
        reason="To build intimacy with the reader.",
        impact="Changes chapter outline generation strategy."
    )
    assert schema.book_id is None
    assert schema.decision == "Using a first-person narrator."
    assert schema.reason == "To build intimacy with the reader."


def test_decision_log_create_decision_too_short():
    """17. decision too short fails validation."""
    # min_length is 3. "ab" is 2.
    with pytest.raises(ValidationError):
        DecisionLogCreate(decision="ab")

    # Stripped check: "  ab  " is stripped to "ab", which fails.
    with pytest.raises(ValidationError):
        DecisionLogCreate(decision="  ab  ")


# ── MemoryReadRequest Tests ───────────────────────────────────────────────────

def test_memory_read_request_valid():
    """18. Valid data passes validation for MemoryReadRequest."""
    book_id = uuid4()
    schema = MemoryReadRequest(
        book_id=book_id,
        memory_types=["facts", "concepts"],
        chapter_number=3,
        query="The golden ring",
        limit=50
    )
    assert schema.book_id == book_id
    assert schema.chapter_number == 3
    assert schema.limit == 50


def test_memory_read_request_limit_above_100():
    """19. limit above 100 fails validation."""
    book_id = uuid4()
    with pytest.raises(ValidationError):
        MemoryReadRequest(
            book_id=book_id,
            limit=101
        )


# ── MemoryWriteRequest Tests ──────────────────────────────────────────────────

def test_memory_write_request_valid():
    """20. Valid data with one fact and one concept passes validation."""
    book_id = uuid4()
    fact = FactRegistryCreate(
        book_id=book_id,
        claim="Earth is round."
    )
    concept = ConceptBibleCreate(
        book_id=book_id,
        concept="Gravity",
        definition="The force that pulls things together."
    )
    schema = MemoryWriteRequest(
        book_id=book_id,
        operation=MemoryOperation.WRITE,
        facts=[fact],
        concepts=[concept]
    )
    assert schema.book_id == book_id
    assert schema.operation == MemoryOperation.WRITE
    assert len(schema.facts) == 1
    assert len(schema.concepts) == 1


# ── MemoryReadResponse Tests ──────────────────────────────────────────────────

def test_memory_read_response_valid_empty():
    """21. Valid empty response passes validation."""
    book_id = uuid4()
    schema = MemoryReadResponse(
        book_id=book_id,
        total_items=0
    )
    assert schema.book_id == book_id
    assert schema.total_items == 0
    assert schema.facts == []
    assert schema.concepts == []


# ── ORM Responses Tests ───────────────────────────────────────────────────────

def test_fact_registry_response_orm():
    """22. FactRegistryResponse validates from ORM-like object."""
    class MockFactModel:
        def __init__(self):
            self.id = uuid4()
            self.book_id = uuid4()
            self.chapter_id = uuid4()
            self.claim = "Grounding fact claim."
            self.source_document_id = uuid4()
            self.source_chunk_id = uuid4()
            self.confidence = 0.8
            self.status = "verified"
            self.used_in_chapters = [1, 2]
            self.fact_metadata = {"tag": "geo"}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockFactModel()
    schema = FactRegistryResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.claim == "Grounding fact claim."
    assert schema.status == "verified"


def test_concept_bible_response_orm():
    """23. ConceptBibleResponse validates from ORM-like object."""
    class MockConceptModel:
        def __init__(self):
            self.id = uuid4()
            self.book_id = uuid4()
            self.concept = "Quantum Entanglement"
            self.definition = "A physical phenomenon."
            self.first_chapter = 3
            self.related_terms = ["Einstein-Podolsky-Rosen"]
            self.appears_in_chapters = [3, 4]
            self.concept_metadata = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockConceptModel()
    schema = ConceptBibleResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.concept == "Quantum Entanglement"
    assert schema.first_chapter == 3


def test_character_bible_response_orm():
    """24. CharacterBibleResponse validates from ORM-like object."""
    class MockCharacterModel:
        def __init__(self):
            self.id = uuid4()
            self.book_id = uuid4()
            self.character_name = "Alice"
            self.role = "Detective"
            self.traits = ["observant", "cynical"]
            self.relationships = {"Bob": "partner"}
            self.arc_summary = "Alice finds the truth."
            self.appears_in_chapters = [1, 2]
            self.character_metadata = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockCharacterModel()
    schema = CharacterBibleResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.character_name == "Alice"
    assert schema.role == "Detective"


def test_callback_index_response_orm():
    """25. CallbackIndexResponse validates from ORM-like object."""
    class MockCallbackModel:
        def __init__(self):
            self.id = uuid4()
            self.book_id = uuid4()
            self.source_chapter = 1
            self.target_chapter = 3
            self.concept = "The golden key"
            self.callback_text = "The key fit perfectly."
            self.status = "active"
            self.callback_metadata = {"relevance": "high"}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockCallbackModel()
    schema = CallbackIndexResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.callback_text == "The key fit perfectly."
    assert schema.status == "active"


def test_tone_fingerprint_response_orm():
    """26. ToneFingerprintResponse validates from ORM-like object."""
    class MockFingerprintModel:
        def __init__(self):
            self.id = uuid4()
            self.book_id = uuid4()
            self.tone_name = "Academic Prose"
            self.sentence_rhythm = {"avg_sentence_length": 25}
            self.lexical_rules = {"formal_terms_only": True}
            self.banned_phrases = ["gonna", "wanna"]
            self.example_phrases = ["Indeed, the results suggest..."]
            self.fingerprint_metadata = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockFingerprintModel()
    schema = ToneFingerprintResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.tone_name == "Academic Prose"
    assert schema.banned_phrases == ["gonna", "wanna"]


def test_decision_log_response_orm():
    """27. DecisionLogResponse validates from ORM-like object."""
    class MockDecisionModel:
        def __init__(self):
            self.id = uuid4()
            self.book_id = uuid4()
            self.decision = "Changing POV to third-person limited."
            self.reason = "Allows multiple perspectives."
            self.impact = "Requires rewriting chapter summaries."
            self.decision_metadata = {"approved_by": "lead_writer"}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockDecisionModel()
    schema = DecisionLogResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.decision == "Changing POV to third-person limited."
    assert schema.reason == "Allows multiple perspectives."
