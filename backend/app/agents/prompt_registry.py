"""
AIuthor Backend — Prompt Registry (Module 7.0A).
"""
from __future__ import annotations

import os
import re
import json
from app.agents.exceptions import AgentPromptError


class PromptRegistry:
    """
    Manages loading, version extraction, and rendering of agent prompt templates.
    """

    def __init__(self, prompts_dir: str | None = None) -> None:
        if prompts_dir:
            self.prompts_dir = prompts_dir
        else:
            # Resolve relative path: app/agents/ -> prompts/agents/
            self.prompts_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "agents")
            )

    def list_templates(self) -> list[str]:
        """
        Scan templates directory and return sorted list of agent template base names.
        """
        if not os.path.exists(self.prompts_dir):
            return []
        templates = []
        for filename in os.listdir(self.prompts_dir):
            if filename.endswith(".md"):
                templates.append(filename[:-3])
        return sorted(templates)

    def get_template(self, agent_name: str) -> str:
        """
        Load markdown template content for the specified agent name.
        Raises AgentPromptError if template is missing or unreadable.
        """
        template_path = os.path.join(self.prompts_dir, f"{agent_name}.md")
        if not os.path.exists(template_path):
            raise AgentPromptError(
                message=f"Prompt template for agent '{agent_name}' not found.",
                agent_name=agent_name,
                details={"path": template_path},
            )
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as exc:
            raise AgentPromptError(
                message=f"Failed to read prompt template for agent '{agent_name}': {exc}",
                agent_name=agent_name,
                details={"path": template_path, "error": str(exc)},
            )

    def get_version(self, agent_name: str) -> str:
        """
        Parse the 'Version: <val>' line from the agent's prompt template.
        Falls back to 'v1' if missing.
        """
        template_content = self.get_template(agent_name)
        # Search for a line stating "Version: vX" or similar
        match = re.search(r"^\s*Version:\s*(\S+)", template_content, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "v1"

    def render_prompt(
        self,
        agent_name: str,
        task: str,
        context: dict | None = None,
        metadata: dict | None = None,
    ) -> tuple[str, str]:
        """
        Compiles the agent system prompt and user prompt.
        system_prompt: contains the exact prompt template markdown string.
        user_prompt: contains the task, context JSON, and metadata JSON.
        """
        system_prompt = self.get_template(agent_name)

        # Deterministic serialization using sorted keys and standard indentation
        context_str = json.dumps(context or {}, sort_keys=True, indent=2)
        metadata_str = json.dumps(metadata or {}, sort_keys=True, indent=2)

        user_prompt = (
            f"Task:\n{task}\n\n"
            f"Context:\n{context_str}\n\n"
            f"Metadata:\n{metadata_str}"
        )

        return system_prompt, user_prompt
