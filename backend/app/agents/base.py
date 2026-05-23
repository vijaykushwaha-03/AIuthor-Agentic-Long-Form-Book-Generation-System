"""
AIuthor Backend — Base Agent (Module 7.0A).
"""
from __future__ import annotations

import abc
import json
import logging
from app.services.llm_service import LLMService
from app.llm.schemas import LLMMessage, LLMRequest
from app.agents.schemas import AgentInput, AgentOutput, AgentInfo
from app.agents.prompt_registry import PromptRegistry
from app.agents.exceptions import AgentExecutionError

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    """
    Abstract base class providing prompt rendering and LLM generation wrappers
    shared across all AIuthor pipeline agents.
    """

    agent_name: str
    display_name: str
    description: str
    requires_context_pack: bool = False
    requires_memory: bool = False

    def __init__(
        self,
        llm_service: LLMService | None = None,
        prompt_registry: PromptRegistry | None = None,
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.prompt_registry = prompt_registry or PromptRegistry()

    def get_info(self) -> AgentInfo:
        """
        Return the agent description metadata, including active prompt text and version.
        """
        template = self.prompt_registry.get_template(self.agent_name)
        version = self.prompt_registry.get_version(self.agent_name)
        return AgentInfo(
            agent_name=self.agent_name,
            display_name=self.display_name,
            description=self.description,
            prompt_template=template,
            version=version,
            requires_context_pack=self.requires_context_pack,
            requires_memory=self.requires_memory,
        )

    def build_messages(self, input: AgentInput) -> list[LLMMessage]:
        """
        Compile agent-specific system and user prompts into a standard chat message list.
        """
        context = {
            "run_id": str(input.run_id) if input.run_id else None,
            "book_id": str(input.book_id) if input.book_id else None,
            "chapter_id": str(input.chapter_id) if input.chapter_id else None,
            "context_pack": input.context_pack,
            "memory_context": input.memory_context,
            "payload": input.payload,
        }

        system_prompt, user_prompt = self.prompt_registry.render_prompt(
            agent_name=self.agent_name,
            task=input.task,
            context=context,
            metadata=input.metadata,
        )

        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

    def run(self, input: AgentInput) -> AgentOutput:
        """
        Executes the agent task using the configured production LLM provider.
        Attempts to parse responses containing JSON block structures.
        """
        messages = self.build_messages(input)
        req = LLMRequest(
            messages=messages,
            metadata={
                "agent_name": self.agent_name,
                "run_id": str(input.run_id) if input.run_id else None,
                "book_id": str(input.book_id) if input.book_id else None,
                "chapter_id": str(input.chapter_id) if input.chapter_id else None,
            },
        )

        try:
            resp = self.llm_service.generate_text(req)
        except Exception as exc:
            raise AgentExecutionError(
                message=f"Agent '{self.agent_name}' execution failed: {exc}",
                agent_name=self.agent_name,
                details={"error": str(exc)},
            )

        # Attempt to parse json structure if output represents a JSON block
        structured_output = None
        try:
            content_str = resp.content.strip()
            if content_str.startswith("```json"):
                content_str = content_str[7:]
            if content_str.endswith("```"):
                content_str = content_str[:-3]
            content_str = content_str.strip()
            structured_output = json.loads(content_str)
        except Exception:
            pass

        return AgentOutput(
            agent_name=self.agent_name,
            status="completed",
            content=resp.content,
            structured_output=structured_output,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            total_tokens=resp.total_tokens,
            metadata=resp.metadata or {},
        )

    def run_mock(self, input: AgentInput) -> AgentOutput:
        """
        Runs the agent task forcing the offline MockLLMProvider wrapper.
        Guarantees no Gemini or OpenAI keys or networks are used.
        """
        from app.llm.providers import MockLLMProvider
        orig_service = self.llm_service
        self.llm_service = LLMService(provider=MockLLMProvider())
        try:
            return self.run(input)
        finally:
            self.llm_service = orig_service
