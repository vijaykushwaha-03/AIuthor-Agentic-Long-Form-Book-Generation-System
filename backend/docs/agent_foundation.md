# Agent Foundation Integration

This document outlines the design, capabilities, APIs, and manual validation flows for the AIuthor multi-agent pipeline orchestration framework.

## Supported Agents

The system registers exactly eight distinct pipeline agents within the core registry:

1. **Planner**: Strategic book architect converting requirements (topic, tone, genre) into detailed structural outlines.
2. **Researcher**: Context-pack reader extracting facts, citations, and summaries from source documents.
3. **Writer**: Publisher-grade long-form text generator leveraging outlines, context-packs, and memories.
4. **Humanizer**: Style post-processor applying custom voice adjustments and enhancing natural flow.
5. **Editor**: Structural refiner focusing on transitions, readability, and structural pacing.
6. **Fact Checker**: Verification engine validating factual output and preserving citation IDs.
7. **Memory Keeper**: Knowledge aggregator updating the long-term project memory.
8. **Assembler**: Compilation agent assembling final sections into standard book chapters.

---

## Safe / Offline REST API Endpoints

These endpoints operate completely offline using mock structures, requiring no external LLM access key. They are safe for automated tests.

* **`GET /api/agents`**  
  List all registered pipeline agents with their display names, versions, and capability descriptors.

* **`GET /api/agents/{agent_name}`**  
  Get details and system prompt template for a specific agent. Returns `404 Not Found` for unrecognized agents.

* **`POST /api/agents/render-prompt`**  
  Locally compile and inspect system and user prompt strings without invoking LLM text generation.  
  *Payload:* `AgentPromptRenderRequest`  
  *Response:* `AgentPromptRenderResponse`

* **`POST /api/agents/mock-run`**  
  Run execution through a deterministic mock generator (`MockLLMProvider`). Used to test schema contracts and routing behavior offline.  
  *Payload:* `AgentInput`  
  *Response:* `AgentOutput`

---

## Dev-Only Real Endpoint

* **`POST /api/agents/dev-run-real`**  
  Runs a single-agent invocation against configured real model providers.
  * Default behavior is disabled: returns `403 Forbidden` unless specifically enabled via environment variables.

### Enabling Real Provider Testing

To enable real provider execution locally, update the testing flags in your `backend/.env` file:
* Set `ENABLE_REAL_AGENT_TEST_API=true`.
* Configure the active `LLM_PROVIDER` and corresponding model parameters as documented in the LLM provider layer configuration.

---

## Example Request Structure

**`POST http://127.0.0.1:8000/api/agents/dev-run-real`**

**Request Body:**
```json
{
  "agent_name": "planner",
  "task": "Create a 5 chapter outline for a beginner-friendly book about RAG systems.",
  "payload": {
    "topic": "RAG systems",
    "genre": "technical guide",
    "reader_profile": "junior AI engineers",
    "tone": "clear and practical"
  }
}
```

**Expected Response Shape:**
```json
{
  "agent_name": "planner",
  "status": "completed",
  "content": "Real model output text here...",
  "structured_output": null,
  "error_message": null,
  "input_tokens": 120,
  "output_tokens": 450,
  "total_tokens": 570,
  "metadata": {
    "execution_mode": "real_dev",
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "warning": "Manual dev-only single-agent execution. Not full workflow."
  }
}
```

---

## Safety Guidelines

> [!CAUTION]
> * **No LangGraph Workflow**: This test endpoint does NOT run multi-agent workflows, state management, or background loops. It executes the specified agent once as a standalone query.
> * **Cost Warning**: Invoking `dev-run-real` makes real API calls and may incur costs on your OpenAI/Gemini accounts.
> * **Production Restriction**: Never enable `ENABLE_REAL_AGENT_TEST_API=true` in a public production deployment.
