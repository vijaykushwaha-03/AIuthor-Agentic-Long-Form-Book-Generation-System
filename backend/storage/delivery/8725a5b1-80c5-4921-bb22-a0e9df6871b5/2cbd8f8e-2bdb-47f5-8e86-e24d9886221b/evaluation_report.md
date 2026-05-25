# AIuthor Evaluation Report

## Summary
- **Book Project ID**: `8725a5b1-80c5-4921-bb22-a0e9df6871b5`
- **Workflow Run ID**: `2cbd8f8e-2bdb-47f5-8e86-e24d9886221b`
- **Overall Status**: **WARNING**
- **Total Checks Evaluated**: 17
- **Passed Checks**: 12
- **Warnings**: 2
- **Failures**: 0
- **Skipped Checks**: 3

## Scorecard
| Check Name | Status | Score | Message |
| :--- | :--- | :--- | :--- |
| chapter_count | PASS | 1.00 | Book project contains 3 chapter(s). |
| chapter_numbering | PASS | 1.00 | Chapter numbers are sequential and start at 1. |
| chapter_content_presence | PASS | 1.00 | All chapters have generated final_text. |
| chapter_statuses | PASS | 1.00 | No chapters are in failed status. |
| chapter_word_count | PASS | 1.00 | Total word count is 815. All chapters meet minimum word count requirements. |
| chapter_repair_metadata | SKIPPED | N/A | No insert-repair operations detected or metadata not set. |
| docx_export_record | PASS | 1.00 | Valid DOCX export record exists. |
| export_file_integrity | PASS | 1.00 | All exported files successfully found on disk. |
| pdf_export_record | WARNING | 0.00 | No PDF export record found. |
| agent_traces_presence | PASS | 1.00 | Found 24 agent trace execution steps. |
| agent_coverage | PASS | 1.00 | All 8 agents have executed and logged traces successfully. |
| prompt_logs_presence | PASS | 1.00 | Found 16 prompt logs in the database. |
| token_ledger_presence | PASS | 1.00 | Found 16 billing or token cost entries in database. |
| continuity_memory | WARNING | 0.00 | Memory lists are completely empty. Continuity cannot be verified. |
| ai_tells_score | PASS | 0.80 | LLM-as-Judge AI-Tells score: 0.80 across 2 chapter(s). |
| tone_consistency_score | SKIPPED | N/A | LLM Judge failed or no chapter text available. |
| fact_grounding_score | SKIPPED | N/A | No facts in FactRegistry to evaluate. |

## Chapter Checks
- **chapter_count** (PASS): Book project contains 3 chapter(s).
- **chapter_numbering** (PASS): Chapter numbers are sequential and start at 1.
- **chapter_content_presence** (PASS): All chapters have generated final_text.
- **chapter_statuses** (PASS): No chapters are in failed status.
- **chapter_word_count** (PASS): Total word count is 815. All chapters meet minimum word count requirements.
- **chapter_repair_metadata** (SKIPPED): No insert-repair operations detected or metadata not set.

## Export Checks
- **docx_export_record** (PASS): Valid DOCX export record exists.
- **export_file_integrity** (PASS): All exported files successfully found on disk.
- **pdf_export_record** (WARNING): No PDF export record found.

## Trace Checks
- **agent_traces_presence** (PASS): Found 24 agent trace execution steps.
- **prompt_logs_presence** (PASS): Found 16 prompt logs in the database.
- **token_ledger_presence** (PASS): Found 16 billing or token cost entries in database.

## Memory Checks
- **continuity_memory** (WARNING): Memory lists are completely empty. Continuity cannot be verified.

## Quality Scores
- **ai_tells_score** (PASS) score=0.800: LLM-as-Judge AI-Tells score: 0.80 across 2 chapter(s).
- **tone_consistency_score** (SKIPPED) score=N/A: LLM Judge failed or no chapter text available.
- **fact_grounding_score** (SKIPPED) score=N/A: No facts in FactRegistry to evaluate.

## Recommendations
> [!WARNING]
> Warnings exist. Word counts might be low, PDF records missing, or traces incomplete. Consider review before assessment submission.