# AIuthor Evaluation Report

## Summary
- **Book Project ID**: `1d1285fa-6290-4076-a29d-780e3a84d08a`
- **Overall Status**: **FAIL**
- **Total Checks Evaluated**: 17
- **Passed Checks**: 6
- **Warnings**: 5
- **Failures**: 2
- **Skipped Checks**: 4

## Scorecard
| Check Name | Status | Score | Message |
| :--- | :--- | :--- | :--- |
| chapter_count | PASS | 1.00 | Book project contains 3 chapter(s). |
| chapter_numbering | PASS | 1.00 | Chapter numbers are sequential and start at 1. |
| chapter_content_presence | FAIL | 0.00 | No chapters have generated content. |
| chapter_statuses | FAIL | 0.00 | Chapters [1] have a failed status. |
| chapter_word_count | WARNING | 0.00 | Total book word count is 0. |
| chapter_repair_metadata | SKIPPED | N/A | No insert-repair operations detected or metadata not set. |
| docx_export_record | PASS | 1.00 | Valid DOCX export record exists. |
| export_file_integrity | PASS | 1.00 | All exported files successfully found on disk. |
| pdf_export_record | WARNING | 0.00 | No PDF export record found. |
| agent_traces_presence | PASS | 1.00 | Found 8 agent trace execution steps. |
| agent_coverage | PASS | 1.00 | All 8 agents have executed and logged traces successfully. |
| prompt_logs_presence | WARNING | 0.00 | No prompt logs found in database. |
| token_ledger_presence | WARNING | 0.00 | No token ledger or billing costs recorded in database. |
| continuity_memory | WARNING | 0.00 | Memory lists are completely empty. Continuity cannot be verified. |
| ai_tells_score | SKIPPED | N/A | LLM Judge failed or no text evaluated. |
| tone_consistency_score | SKIPPED | N/A | LLM Judge failed or no chapter text available. |
| fact_grounding_score | SKIPPED | N/A | No facts in FactRegistry to evaluate. |

## Chapter Checks
- **chapter_count** (PASS): Book project contains 3 chapter(s).
- **chapter_numbering** (PASS): Chapter numbers are sequential and start at 1.
- **chapter_content_presence** (FAIL): No chapters have generated content.
- **chapter_statuses** (FAIL): Chapters [1] have a failed status.
- **chapter_word_count** (WARNING): Total book word count is 0.
- **chapter_repair_metadata** (SKIPPED): No insert-repair operations detected or metadata not set.

## Export Checks
- **docx_export_record** (PASS): Valid DOCX export record exists.
- **export_file_integrity** (PASS): All exported files successfully found on disk.
- **pdf_export_record** (WARNING): No PDF export record found.

## Trace Checks
- **agent_traces_presence** (PASS): Found 8 agent trace execution steps.
- **prompt_logs_presence** (WARNING): No prompt logs found in database.
- **token_ledger_presence** (WARNING): No token ledger or billing costs recorded in database.

## Memory Checks
- **continuity_memory** (WARNING): Memory lists are completely empty. Continuity cannot be verified.

## Quality Scores
- **ai_tells_score** (SKIPPED) score=N/A: LLM Judge failed or no text evaluated.
- **tone_consistency_score** (SKIPPED) score=N/A: LLM Judge failed or no chapter text available.
- **fact_grounding_score** (SKIPPED) score=N/A: No facts in FactRegistry to evaluate.

## Recommendations
> [!CAUTION]
> Critical failures detected. Please address chapter numbering, missing files, or missing structural requirements before finalizing delivery.