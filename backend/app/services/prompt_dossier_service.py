"""
AIuthor Backend — Prompt Dossier Service.
Generates an inventory and rendered examples of all agent prompts.
"""
from __future__ import annotations

import re
from app.agents.prompt_registry import PromptRegistry
from app.workflows.schemas import PromptDossierRequest, PromptDossierResponse

class PromptDossierService:
    """
    Generates assessment-ready prompt dossier documenting all agent systems.
    """

    def __init__(self) -> None:
        self.prompt_registry = PromptRegistry()

    def generate_prompt_dossier(self, request: PromptDossierRequest) -> PromptDossierResponse:
        agent_names = [
            "planner",
            "researcher",
            "writer",
            "humanizer",
            "editor",
            "fact_checker",
            "memory_keeper",
            "assembler",
        ]

        prompts_list = []
        markdown_sections = []

        # 1. Header & Overview
        markdown_sections.append("# AIuthor Prompt Dossier\n")
        markdown_sections.append("## Overview")
        markdown_sections.append(
            "This dossier compiles and documents the agent prompt templates utilized by the AIuthor "
            "Agentic Long-Form Book Generation System. AIuthor leverages a multi-agent orchestration "
            "architecture where each specialized agent performs tasks governed by structured templates.\n"
        )

        # 2. Agent Prompt Inventory
        markdown_sections.append("## Agent Prompt Inventory")
        markdown_sections.append(
            "The following table summarizes the active agent roles and versions maintained in the system:\n"
        )
        markdown_sections.append("| Agent Name | Version | Role Excerpt |")
        markdown_sections.append("| :--- | :--- | :--- |")

        # Collect information for all agents first
        for name in agent_names:
            template = self.prompt_registry.get_template(name)
            version = self.prompt_registry.get_version(name)

            # Extract role excerpt: find "Role:" block
            role_match = re.search(r"Role:\s*(.*?)(?=\n\n|\n[A-Z][a-z]+:|\Z)", template, re.IGNORECASE | re.DOTALL)
            role_excerpt = role_match.group(1).strip().replace("\n", " ") if role_match else "Specialized Agent"
            # Keep role excerpt short for the table
            table_role = role_excerpt[:80] + "..." if len(role_excerpt) > 80 else role_excerpt

            markdown_sections.append(f"| {name} | {version} | {table_role} |")

            # Prepare sample rendered user prompt
            rendered_user_prompt = None
            if request.include_render_examples:
                dummy_task = f"Execute standard {name} pipeline task."
                dummy_context = {
                    "genre": "Non-Fiction",
                    "tone": "Informative",
                    "core_concept": "Continuous Learning"
                }
                dummy_metadata = {"word_count_target": 1500, "run_id": "00000000-0000-0000-0000-000000000000"}
                _, rendered_user_prompt = self.prompt_registry.render_prompt(
                    name, task=dummy_task, context=dummy_context, metadata=dummy_metadata
                )

            prompts_list.append({
                "agent_name": name,
                "version": version,
                "role_excerpt": role_excerpt,
                "template": template if request.include_templates else None,
                "render_example": rendered_user_prompt if request.include_render_examples else None,
            })

        markdown_sections.append("")  # Empty line after inventory table

        # 3. Add Agent Details sections
        for item in prompts_list:
            display_name = item["agent_name"].replace("_", " ").title()
            markdown_sections.append(f"## {display_name} Prompt")
            markdown_sections.append(f"- **Agent ID**: `{item['agent_name']}`")
            markdown_sections.append(f"- **Version**: `{item['version']}`")
            markdown_sections.append(f"- **Role Excerpt**: {item['role_excerpt']}")
            markdown_sections.append("")

            if request.include_templates:
                markdown_sections.append("### Template")
                markdown_sections.append("```markdown")
                markdown_sections.append(item["template"])
                markdown_sections.append("```\n")

            if request.include_render_examples:
                markdown_sections.append("### Render Example (User Prompt)")
                markdown_sections.append("```")
                markdown_sections.append(item["render_example"])
                markdown_sections.append("```\n")

        # 4. Humanizer Rules
        markdown_sections.append("## Humanizer Rules")
        markdown_sections.append(
            "The Humanizer agent is dedicated to transforming AI-sounding drafts into naturally flowing, "
            "emotionally resonant prose. Its core parameters mandate:\n"
            "- Strict preservation of all inline academic/factual citations (e.g. `[C1]`, `[C2]`).\n"
            "- Adherence to custom `Tone Fingerprints` retrieved from the MemoryKeeper DB.\n"
            "- Enhancing sentence length variety and voice rhythm without adding external hallucinated details.\n"
        )

        # 5. Safety Rules
        markdown_sections.append("## Safety Rules")
        markdown_sections.append(
            "To prevent leakage and maintain system security, the prompt system enforces:\n"
            "- Sanitization of prompt variables: System configuration parameters, secrets, and database "
            "credentials are never exposed in user prompt variables.\n"
            "- Execution sandboxing: Agents do not execute arbitrary code inputs directly.\n"
            "- Structured JSON schemas for all output contracts, validated programmatically upon return.\n"
        )

        # 6. Versioning Notes
        markdown_sections.append("## Versioning Notes")
        markdown_sections.append(
            "All templates in `prompts/agents/` carry a header line declaring their active version "
            "(e.g., `Version: v1`). The `PromptRegistry` parses this version dynamically to log version-specific "
            "trace metrics. Updates to prompts follow semantic tag bumps and are verified using offline regression tests."
        )

        markdown_dossier = "\n".join(markdown_sections)

        return PromptDossierResponse(
            status="success",
            agent_count=len(agent_names),
            template_count=len(agent_names),
            markdown_dossier=markdown_dossier,
            prompts=prompts_list,
            metadata=request.metadata,
        )
