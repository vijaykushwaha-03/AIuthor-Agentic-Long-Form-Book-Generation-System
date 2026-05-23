# Sample API JSON Payloads

This document lists realistic sample JSON payloads for request and update contracts configured within the schema package.

> [!NOTE]
> **Implementation Status**: These payloads represent the verified schema structures. Actual endpoints are not yet implemented.

---

## 1. BookProjectCreate
* **Route**: `POST /api/books`
```json
{
  "topic": "Personal Finance for Beginners",
  "reader_profile": "Adults with no prior finance background",
  "genre": "non-fiction guide",
  "tone": "conversational",
  "target_chapters": 10,
  "words_per_chapter": 2500,
  "project_metadata": {
    "test_case": "A"
  }
}
```

## 2. BookProjectUpdate
* **Route**: `PATCH /api/books/{book_id}`
```json
{
  "topic": "Personal Finance for Young Adults",
  "target_chapters": 12,
  "status": "planning"
}
```

## 3. BookRunStartRequest
* **Route**: `POST /api/books/{book_id}/runs`
```json
{
  "run_metadata": {
    "run_mode": "dry_run",
    "debug": true
  }
}
```

## 4. ChapterContract
* **Agent Flow**: Generated dynamically by the Planner Agent.
```json
{
  "chapter_number": 1,
  "title": "Understanding Your Income",
  "purpose": "Explain the difference between gross and net income.",
  "key_concepts": [
    "gross income",
    "net income",
    "withholding taxes"
  ],
  "required_facts": [
    "Net income is income after taxes and deductions."
  ],
  "callback_opportunities": [
    "Reference net income when discussing budgeting in Chapter 2."
  ],
  "estimated_word_count": 1500,
  "metadata": {
    "difficulty_rating": "beginner"
  }
}
```

## 5. ChapterCreate
* **Database/Agent Flow**: Populating database columns based on planner output.
```json
{
  "book_id": "4a71c110-85f0-4375-81a1-9dc36f7842e4",
  "chapter_number": 1,
  "title": "Understanding Your Income",
  "summary": "This chapter introduces basic income terminology.",
  "chapter_contract": {
    "chapter_number": 1,
    "title": "Understanding Your Income",
    "purpose": "Explain the difference between gross and net income."
  },
  "tone": "conversational",
  "status": "planned"
}
```

## 6. ChapterUpdate (with final_text)
* **Route**: `PATCH /api/books/{book_id}/chapters/{chapter_id}`
```json
{
  "final_text": "Income is the starting point of all personal finance. When we speak of gross income...",
  "word_count": 1420,
  "status": "completed"
}
```

## 7. ChapterInsertRequest (Test D Style)
* **Route**: `POST /api/books/{book_id}/chapters/insert`
```json
{
  "after_chapter": 4,
  "title": "Understanding Credit Without Fear",
  "purpose": "Bridge budgeting and long-term planning",
  "tone": "conversational",
  "metadata": {
    "repair_required": true
  }
}
```

## 8. BookSectionCreate (for TOC)
* **Database/Assembler Flow**: Populating book front/back matter tables.
```json
{
  "book_id": "4a71c110-85f0-4375-81a1-9dc36f7842e4",
  "section_type": "toc",
  "title": "Table of Contents",
  "content": "1. Understanding Your Income\n2. Creating Your First Budget",
  "sort_order": 5,
  "status": "generated",
  "section_metadata": {
    "auto_generated": true
  }
}
```

## 9. BookSectionUpdate (for Glossary)
* **Route/Assembler Flow**: Updating glossaries during repair or compile cycles.
```json
{
  "content": "Gross Income: Total pay before taxes.\nNet Income: Take-home pay after deductions.",
  "status": "completed"
}
```
