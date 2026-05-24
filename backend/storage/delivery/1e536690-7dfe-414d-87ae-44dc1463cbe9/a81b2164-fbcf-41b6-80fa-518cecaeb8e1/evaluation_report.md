# AIuthor Evaluation Report

## Summary
- **Book Project ID**: `1e536690-7dfe-414d-87ae-44dc1463cbe9`
- **Workflow Run ID**: `a81b2164-fbcf-41b6-80fa-518cecaeb8e1`
- **Overall Status**: **WARNING**
- **Total Checks Evaluated**: 14
- **Passed Checks**: 10
- **Warnings**: 3
- **Failures**: 0
- **Skipped Checks**: 1

## Scorecard
| Check Name | Status | Score | Message |
| :--- | :--- | :--- | :--- |
| chapter_count | PASS | 1.00 | Book project contains 3 chapter(s). |
| chapter_numbering | PASS | 1.00 | Chapter numbers are sequential and start at 1. |
| chapter_content_presence | WARNING | 0.50 | Some chapters have content but lack final_text. Chapters: [2, 3] |
| chapter_statuses | PASS | 1.00 | No chapters are in failed status. |
| chapter_word_count | WARNING | 0.70 | Total word count is 196, but some chapters are extremely short (< 200 words): [(1, 196), (2, 0), (3, 0)] |
| chapter_repair_metadata | SKIPPED | N/A | No insert-repair operations detected or metadata not set. |
| docx_export_record | PASS | 1.00 | Valid DOCX export record exists. |
| export_file_integrity | PASS | 1.00 | All exported files successfully found on disk. |
| pdf_export_record | WARNING | 0.50 | PDF export failed, but DOCX is available. |
| agent_traces_presence | PASS | 1.00 | Found 8 agent trace execution steps. |
| agent_coverage | PASS | 1.00 | All 8 agents have executed and logged traces successfully. |
| prompt_logs_presence | PASS | 1.00 | Found 8 prompt logs in the database. |
| token_ledger_presence | PASS | 1.00 | Found 8 billing or token cost entries in database. |
| continuity_memory | PASS | 1.00 | Continuity memory populated with 22 total records across tables. |

## Chapter Checks
- **chapter_count** (PASS): Book project contains 3 chapter(s).
- **chapter_numbering** (PASS): Chapter numbers are sequential and start at 1.
- **chapter_content_presence** (WARNING): Some chapters have content but lack final_text. Chapters: [2, 3]
- **chapter_statuses** (PASS): No chapters are in failed status.
- **chapter_word_count** (WARNING): Total word count is 196, but some chapters are extremely short (< 200 words): [(1, 196), (2, 0), (3, 0)]
- **chapter_repair_metadata** (SKIPPED): No insert-repair operations detected or metadata not set.

## Export Checks
- **docx_export_record** (PASS): Valid DOCX export record exists.
- **export_file_integrity** (PASS): All exported files successfully found on disk.
- **pdf_export_record** (WARNING): PDF export failed, but DOCX is available.

## Trace Checks
- **agent_traces_presence** (PASS): Found 8 agent trace execution steps.
- **prompt_logs_presence** (PASS): Found 8 prompt logs in the database.
- **token_ledger_presence** (PASS): Found 8 billing or token cost entries in database.

## Memory Checks
- **continuity_memory** (PASS): Continuity memory populated with 22 total records across tables.

## Recommendations
> [!WARNING]
> Warnings exist. Word counts might be low, PDF records missing, or traces incomplete. Consider review before assessment submission.