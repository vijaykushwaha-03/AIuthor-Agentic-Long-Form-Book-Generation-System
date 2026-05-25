"""
AIuthor Backend — Manuscript Content Cleaning Utilities.

Provides functions to strip code fences, parse JSON, validate against debug/mock output,
and extract clean chapter content.
"""
from __future__ import annotations

import json
import re

# Ordered preference for prose field keys when LLM returns a dict or JSON object
_PROSE_FIELD_PRIORITY = (
    "final_text",
    "chapter_text",
    "prose",
    "content",
    "draft_text",
    "text",
    "body",
    "passage",
)


def extract_prose_from_llm_response(raw):
    """
    Sanitize a raw LLM output string into clean book-style prose.

    Handles three cases:

    1. **JSON string / code-fence JSON**: Parse and extract the first matching
       prose field (`final_text` > `chapter_text` > `prose` >
       `content` > `draft_text` > `text` > `body` > `passage`).
    2. **Plain string**: Return as-is after stripping outer whitespace.

    Never raises -- always returns the best available string.

    Args:
        raw: Raw LLM response text (may be JSON, fenced JSON, or plain prose).

    Returns:
        Clean prose string ready for storing and exporting.
    """
    if not raw:
        return raw or ""

    stripped = raw.strip()

    # Attempt JSON parse (with or without code fence)
    parsed = try_parse_json_text(stripped)

    if isinstance(parsed, dict):
        for key in _PROSE_FIELD_PRIORITY:
            val = parsed.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        for val in parsed.values():
            if isinstance(val, str) and val.strip():
                return val.strip()
        return stripped

    if isinstance(parsed, list) and parsed:
        for item in parsed:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if isinstance(item, dict):
                for key in _PROSE_FIELD_PRIORITY:
                    val = item.get(key)
                    if val and isinstance(val, str) and val.strip():
                        return val.strip()

    return stripped



def strip_markdown_code_fence(text: str) -> str:
    """
    Remove ```json ... ``` or generic ``` ... ``` fences, preserving the inner content.
    If no fences are found, returns the original text.
    """
    if not text:
        return ""
    text_stripped = text.strip()
    
    # 1. Check if the entire string is wrapped in a fence block
    match = re.match(r'^```(?:json)?\s*\n?(.*?)\n?```$', text_stripped, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # 2. Check if a fence block is embedded inside the text
    match_embedded = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL | re.IGNORECASE)
    if match_embedded:
        return match_embedded.group(1).strip()
        
    return text


def try_parse_json_text(text: str) -> dict | list | None:
    """
    Try to parse text as JSON. Strips markdown fences first.
    If direct parsing fails, tries to locate the first valid {...} or [...] inside the text.
    Never raises an exception; returns None on failure.
    """
    if not text:
        return None
        
    # Strip fences
    cleaned = strip_markdown_code_fence(text).strip()
    
    try:
        return json.loads(cleaned)
    except Exception:
        pass
        
    # Try locating JSON bounds within the text
    first_brace = cleaned.find('{')
    first_bracket = cleaned.find('[')
    
    start_idx = -1
    end_char = ''
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_idx = first_brace
        end_char = '}'
    elif first_bracket != -1:
        start_idx = first_bracket
        end_char = ']'
        
    if start_idx != -1:
        last_idx = cleaned.rfind(end_char)
        while last_idx > start_idx:
            candidate = cleaned[start_idx:last_idx+1]
            try:
                return json.loads(candidate)
            except Exception:
                last_idx = cleaned.rfind(end_char, start_idx, last_idx)
                
    return None


def extract_chapter_content_from_json(
    data: dict | list | None,
    chapter_number: int | None = None,
    chapter_title: str | None = None,
) -> str | None:
    """
    Extracts chapter content from parsed JSON data.
    Supports list of chapters (matching by chapter_number or title, falling back to first),
    direct dict content/text/body/etc. fields, and nested chapter.content.
    """
    if not data:
        return None
        
    if isinstance(data, dict):
        # Case: {"chapter": {"content": "..."}} or other priority fields
        if "chapter" in data and isinstance(data["chapter"], dict):
            ch_data = data["chapter"]
            for key in _PROSE_FIELD_PRIORITY:
                if key in ch_data and not isinstance(ch_data[key], (dict, list)):
                    return str(ch_data[key])
                
        # Case: priority keys directly in data (e.g. {"body": "..."} or {"content": "..."})
        for key in _PROSE_FIELD_PRIORITY:
            if key in data and not isinstance(data[key], (dict, list)):
                return str(data[key])
            
        # Case: {"chapters": [...]}
        chapters = data.get("chapters")
        
        # Fallback for nested front_matter/back_matter if chapters is empty or missing
        if not chapters or (isinstance(chapters, list) and len(chapters) == 0):
            # Check front_matter
            front = data.get("front_matter")
            if isinstance(front, dict):
                is_intro = False
                if chapter_number == 1:
                    is_intro = True
                elif chapter_title and any(k in chapter_title.lower() for k in ["intro", "preface", "foreword"]):
                    is_intro = True
                
                if is_intro:
                    for key in ["introduction", "preface", "foreword", "content", "body", "text"]:
                        val = front.get(key)
                        if val and isinstance(val, str) and val.strip():
                            return val
                            
            # Check back_matter
            back = data.get("back_matter")
            if isinstance(back, dict):
                is_conclusion = False
                if chapter_title and any(k in chapter_title.lower() for k in ["conclusion", "epilogue", "summary"]):
                    is_conclusion = True
                    
                if is_conclusion:
                    for key in ["conclusion", "summary", "epilogue", "content", "body", "text"]:
                        val = back.get(key)
                        if val and isinstance(val, str) and val.strip():
                            return val
                            
            # Ultimate fallback to any non-empty introduction in front_matter
            if isinstance(front, dict) and "introduction" in front and isinstance(front["introduction"], str) and front["introduction"].strip():
                return front["introduction"]
    elif isinstance(data, list):
        # Case: [...]
        chapters = data
    else:
        return None
        
    if isinstance(chapters, list) and len(chapters) > 0:
        matched_chapter = None
        
        # 1. Match by chapter_number
        if chapter_number is not None:
            for ch in chapters:
                if isinstance(ch, dict):
                    ch_num = ch.get("chapter_number")
                    if ch_num is not None and str(ch_num) == str(chapter_number):
                        matched_chapter = ch
                        break
                        
        # 2. Match by chapter_title
        if matched_chapter is None and chapter_title is not None:
            for ch in chapters:
                if isinstance(ch, dict):
                    title = ch.get("title")
                    if title and (chapter_title.lower() in title.lower() or title.lower() in chapter_title.lower()):
                        matched_chapter = ch
                        break
                        
        # 3. Fallback to first chapter
        if matched_chapter is None:
            matched_chapter = chapters[0]
            
        if isinstance(matched_chapter, dict):
            for key in _PROSE_FIELD_PRIORITY:
                if key in matched_chapter and not isinstance(matched_chapter[key], (dict, list)):
                    return str(matched_chapter[key])
            if "content" in matched_chapter:
                return matched_chapter["content"]
            if "text" in matched_chapter:
                return matched_chapter["text"]
                
    return None


def looks_like_debug_or_prompt_dump(text: str) -> bool:
    """
    Returns True if the text contains workflow debug markers or internal prompts.
    Rejects immediately on Mock response or Mock execution mode.
    Rejects on 2 or more other debug markers.
    """
    if not text:
        return False
        
    # Immediate rejection cases
    if "Mock response for:" in text:
        return True
    if re.search(r'execution_mode\s*[:=]\s*["\']mock["\']', text, re.IGNORECASE):
        return True
    if 'execution_mode: "mock"' in text or "execution_mode: \"mock\"" in text or "execution_mode: 'mock'" in text:
        return True
        
    # Count other markers
    markers = [
        "execution_mode",
        "workflow_name",
        "payload",
        "book_id",
        "chapter_id",
        "run_id",
        "Context:",
        "Task:",
        "Metadata:",
        "real_dev"
    ]
    
    count = 0
    for marker in markers:
        if marker in text:
            count += 1
            if count >= 2:
                return True
                
    return False


def clean_manuscript_text(text: str) -> str:
    """
    Strips markdown code fences, normalizes line endings, limits excessive
    blank lines to maximum of 1 blank line (2 newlines), and trims outer whitespace.
    """
    if not text:
        return ""
        
    # Strip fences
    cleaned = strip_markdown_code_fence(text)
    
    # Normalize newlines
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    
    # Replace 3 or more consecutive newlines with 2 newlines (preserves paragraph breaks, removes excess)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned.strip()


def validate_manuscript_export_text(text: str) -> list[str]:
    """
    Checks if the text contains any forbidden debug/workflow markers.
    Returns a list of warnings if found, or empty list if clean.
    """
    forbidden_markers = [
        "Mock response for:",
        'execution_mode: "mock"',
        "execution_mode: \"mock\"",
        "execution_mode",
        "workflow_name",
        "payload",
        "book_id",
        "chapter_id",
        "run_id",
        "Context:",
        "Task:",
        "Metadata:"
    ]
    
    warnings = []
    if not text:
        return warnings
        
    for marker in forbidden_markers:
        if marker in text:
            warnings.append(f"Forbidden marker '{marker}' detected in manuscript body.")
            
    return warnings


def extract_clean_chapter_manuscript(
    *,
    final_text: str | None,
    edited_text: str | None,
    humanized_text: str | None,
    draft_text: str | None,
    summary: str | None,
    chapter_number: int | None,
    chapter_title: str | None,
    prefer_final_text: bool = True,
) -> tuple[str, str, list[str]]:
    """
    Runs text extraction across candidate fields in priority order, resolving JSON
    contents if available, cleaning the text, and rejecting debug dumps.
    
    Returns:
        tuple[clean_content, source_field, warnings]
    """
    if prefer_final_text:
        candidates = [
            ("final_text", final_text),
            ("edited_text", edited_text),
            ("humanized_text", humanized_text),
            ("draft_text", draft_text),
            ("summary", summary),
        ]
    else:
        candidates = [
            ("draft_text", draft_text),
            ("humanized_text", humanized_text),
            ("edited_text", edited_text),
            ("final_text", final_text),
            ("summary", summary),
        ]
        
    warnings = []
    
    for field_name, val in candidates:
        if val is not None and val.strip():
            # Try to parse as JSON first
            parsed = try_parse_json_text(val)
            extracted = None
            if parsed:
                extracted = extract_chapter_content_from_json(parsed, chapter_number, chapter_title)
                
            content_to_clean = extracted if extracted is not None else val
            
            # Clean text
            cleaned = clean_manuscript_text(content_to_clean)
            
            # Strict rejection checks
            if looks_like_debug_or_prompt_dump(cleaned):
                warnings.append(f"Field '{field_name}' was rejected: looks like a debug or prompt dump.")
                continue
                
            forbidden = validate_manuscript_export_text(cleaned)
            if forbidden:
                warnings.extend(forbidden)
                warnings.append(f"Field '{field_name}' was rejected: contains forbidden markers.")
                continue
                
            if not cleaned.strip():
                warnings.append(f"Field '{field_name}' was rejected: resolved to empty text.")
                continue
                
            return cleaned, field_name, warnings
            
    # All candidates failed
    warnings.append("All available text fields were empty, rejected, or contained debug dumps.")
    return "Content not available for this chapter.", "placeholder", warnings

