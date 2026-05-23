# LLM Provider Layer — Module 5.0

## Overview

Module 5.0 introduces a clean LLM provider abstraction layer that supports
multiple AI providers behind a unified interface. All agent and workflow modules
(planned for Module 6+) will call `LLMService` rather than SDK clients directly.

---

## Supported Providers

| Provider | Identifier | Default |
|----------|-----------|---------|
| Google Gemini | `gemini` | ✅ Yes |
| OpenAI / GPT | `openai` | No |
| Mock (tests/dev) | `mock` | No |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | Active provider: `gemini`, `openai`, or `mock` |
| `GEMINI_API_KEY` | _(empty)_ | Google AI API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `LLM_TEMPERATURE` | `0.7` | Sampling temperature (0.0–2.0) |
| `LLM_MAX_OUTPUT_TOKENS` | `4000` | Max tokens in model response |
| `LLM_TIMEOUT_SECONDS` | `60` | HTTP timeout for API calls |

---

## Usage Examples

### Use Gemini (default)

```dotenv
# backend/.env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.5-flash
```

```python
from app.services.llm_service import LLMService
from app.llm.schemas import LLMMessage, LLMRequest

service = LLMService()  # reads LLM_PROVIDER=gemini from env

request = LLMRequest(messages=[
    LLMMessage(role="system", content="You are a book-writing assistant."),
    LLMMessage(role="user",   content="Write an introduction for Chapter 1."),
])

response = service.generate_text(request)
print(response.content)
```

### Switch to OpenAI

```dotenv
# backend/.env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4o-mini
```

No code changes needed — the factory picks up the new provider automatically.

### Use Mock provider (tests / offline dev)

```dotenv
# backend/.env  (or set in conftest.py)
LLM_PROVIDER=mock
```

```python
from app.llm.providers import MockLLMProvider
from app.services.llm_service import LLMService
from app.llm.schemas import LLMMessage, LLMRequest

service = LLMService(provider=MockLLMProvider())  # inject explicitly

request = LLMRequest(messages=[LLMMessage(role="user", content="Hello.")])
response = service.generate_text(request)
# response.content == "Mock response for: Hello."
```

### Use the factory directly

```python
from app.llm.factory import get_llm_provider

provider = get_llm_provider("mock")   # explicit override
provider = get_llm_provider()         # uses LLM_PROVIDER env var
```

---

## API Endpoints

### `GET /api/llm/provider`

Returns the current provider configuration. **No model call is made.**

```json
{
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "configured": true,
  "supports_streaming": false
}
```

### `POST /api/llm/mock-generate`

Always uses `MockLLMProvider`. Use to verify the API contract without any real
API calls.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Write a chapter outline."}
  ]
}
```

**Response:**
```json
{
  "provider": "mock",
  "model": "mock-llm",
  "content": "Mock response for: Write a chapter outline.",
  "input_tokens": 5,
  "output_tokens": 6,
  "total_tokens": 11
}
```

---

## Architecture

```
app/llm/
├── __init__.py     ← public re-exports
├── schemas.py      ← LLMMessage, LLMRequest, LLMResponse, LLMProviderInfo
├── exceptions.py   ← LLMError, LLMConfigurationError, LLMProviderError
├── base.py         ← BaseLLMProvider (abstract)
├── providers.py    ← MockLLMProvider, GeminiLLMProvider, OpenAILLMProvider
└── factory.py      ← get_llm_provider(), get_default_llm_provider()

app/services/
└── llm_service.py  ← LLMService (wrapper for business logic)

app/api/
└── routes_llm.py   ← GET /api/llm/provider, POST /api/llm/mock-generate
```

---

## Design Decisions

### Provider isolation

SDK clients (`genai.Client`, `openai.OpenAI`) are instantiated inside
`generate()`, not in `__init__`. This means:
- Providers can be imported and introspected in tests without network access.
- `GeminiLLMProvider(api_key="fake")` works in tests as long as `.generate()`
  is not called.

### No startup-time provider creation

`get_llm_provider()` is called **on demand** (inside route handlers / service
calls), never at app startup. Missing API keys won't block `uvicorn app.main:app`.

### Token counts are optional

Both Gemini and OpenAI responses may not always return token usage. All
`input_tokens`, `output_tokens`, `total_tokens` fields in `LLMResponse` are
`int | None`. Code consuming responses should handle `None` gracefully.

---

## Important Notes

- **No agent workflow yet.** Real generation will be triggered by
  Planner / Researcher / Writer / Humanizer / Editor / FactChecker agents
  (Module 6+).
- **No LangGraph.** Graph-based orchestration is not part of this module.
- **No real generation endpoint.** The only generation endpoint currently
  (`/api/llm/mock-generate`) always uses `MockLLMProvider`.
- **Tests use mock only.** All tests pass offline with no API keys.
- **No database migrations.** This module adds no new ORM models.
