"""
AIuthor Backend — Workflow Node Functions (Module 7.2A).

Each node wraps an agent via execute_agent_node to capture traces,
prompts, durations, and outputs into the workflow state.
"""
from __future__ import annotations

import logging
import time
from app.agents.schemas import AgentInput, AgentPromptRenderRequest
from app.services.agent_execution_service import AgentExecutionService
from app.workflows.state import AIuthorWorkflowState
from app.workflows.exceptions import WorkflowExecutionError

logger = logging.getLogger(__name__)


def execute_agent_node(
    state: AIuthorWorkflowState,
    *,
    step_name: str,
    agent_name: str,
    task: str,
) -> dict:
    """
    Orchestrates rendering, timing, and invoking the agent in the specified execution mode.
    """
    svc = AgentExecutionService(db=None)

    # 1. Render prompt before execution (does not invoke LLM)
    context = {
        "run_id": state.get("run_id"),
        "book_id": state.get("book_id"),
        "chapter_id": state.get("chapter_id"),
        "context_pack": state.get("context_pack"),
        "memory_context": state.get("memory_context"),
        "payload": state.get("payload"),
    }
    render_req = AgentPromptRenderRequest(
        agent_name=agent_name,
        task=task,
        context=context,
        metadata=state.get("metadata"),
    )
    render_resp = svc.render_agent_prompt(render_req)

    # 2. Record start time
    start_time = time.perf_counter()

    # 3. Create AgentInput with IDs from state
    inp = AgentInput(
        agent_name=agent_name,
        task=task,
        context_pack=state.get("context_pack"),
        memory_context=state.get("memory_context"),
        payload=state.get("payload"),
        metadata=state.get("metadata"),
        run_id=state.get("run_id"),
        book_id=state.get("book_id"),
        chapter_id=state.get("chapter_id"),
    )

    execution_mode = state.get("execution_mode", "mock")
    output = None
    error_message = None
    status = "completed"

    try:
        if execution_mode == "mock":
            output = svc.run_agent_mock(inp)
        elif execution_mode == "real_dev":
            output = svc.run_agent_once(inp)
        else:
            raise WorkflowExecutionError(
                message=f"Unsupported execution_mode '{execution_mode}' in node for '{agent_name}'.",
                workflow_name=state.get("workflow_name"),
            )
    except Exception as exc:
        status = "failed"
        error_message = str(exc)

    # 4. Record stop time
    duration_ms = int((time.perf_counter() - start_time) * 1000)

    if output:
        output_dict = {
            "agent_name": agent_name,
            "status": output.status,
            "content": output.content,
            "structured_output": output.structured_output,
            "error_message": output.error_message or error_message,
            "input_tokens": output.input_tokens,
            "output_tokens": output.output_tokens,
            "total_tokens": output.total_tokens,
            "metadata": output.metadata or {},
        }
    else:
        output_dict = {
            "agent_name": agent_name,
            "status": status,
            "content": None,
            "structured_output": None,
            "error_message": error_message,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "metadata": {},
        }

    return {
        "step_name": step_name,
        "agent_name": agent_name,
        "task": task,
        "system_prompt": render_resp.system_prompt,
        "user_prompt": render_resp.user_prompt,
        "status": output_dict["status"],
        "content": output_dict["content"],
        "structured_output": output_dict["structured_output"],
        "duration_ms": duration_ms,
        "input_tokens": output_dict["input_tokens"],
        "output_tokens": output_dict["output_tokens"],
        "total_tokens": output_dict["total_tokens"],
        "error_message": output_dict["error_message"],
        "metadata": output_dict["metadata"],
    }


def planner_node(state: AIuthorWorkflowState) -> AIuthorWorkflowState:
    """
    Planner node: creates the book outline from topic, genre, reader_profile, and tone.
    """
    topic = state.get("topic", "")
    genre = state.get("genre", "general non-fiction")
    reader_profile = state.get("reader_profile", "general audience")
    tone = state.get("tone", "informative")

    task = (
        f"Create a concise 3-chapter book outline for the following:\n"
        f"Topic: {topic}\n"
        f"Genre: {genre}\n"
        f"Reader profile: {reader_profile}\n"
        f"Tone: {tone}\n"
        f"Output the outline in structured form with chapter titles and brief descriptions."
    )

    try:
        step_data = execute_agent_node(state, step_name="planner", agent_name="planner", task=task)
        if step_data["status"] == "failed":
            raise RuntimeError(step_data["error_message"])
    except Exception as exc:
        logger.error("planner_node failed: %s", exc)
        failed_step = {
            "step_name": "planner",
            "agent_name": "planner",
            "task": task,
            "system_prompt": None,
            "user_prompt": None,
            "status": "failed",
            "content": None,
            "structured_output": None,
            "duration_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": str(exc),
            "metadata": {},
        }
        new_steps = list(state.get("steps", [])) + [failed_step]
        new_trace_steps = list(state.get("trace_steps", [])) + [failed_step]
        return {
            **state,
            "planner_output": None,
            "steps": new_steps,
            "trace_steps": new_trace_steps,
            "status": "failed",
            "error_message": str(exc),
        }

    output_dict = {
        "agent_name": "planner",
        "status": step_data["status"],
        "content": step_data["content"],
        "structured_output": step_data["structured_output"],
        "error_message": step_data["error_message"],
        "input_tokens": step_data["input_tokens"],
        "output_tokens": step_data["output_tokens"],
        "total_tokens": step_data["total_tokens"],
        "metadata": step_data["metadata"],
    }
    new_steps = list(state.get("steps", [])) + [step_data]
    new_trace_steps = list(state.get("trace_steps", [])) + [step_data]
    return {
        **state,
        "planner_output": output_dict,
        "steps": new_steps,
        "trace_steps": new_trace_steps,
    }


def researcher_node(state: AIuthorWorkflowState) -> AIuthorWorkflowState:
    """
    Researcher node: summarizes context_pack evidence for the planned book.
    """
    planner_out = state.get("planner_output") or {}
    planner_content = planner_out.get("content", "No outline available.")
    context_pack = state.get("context_pack") or {}
    context_text = context_pack.get("context_text", "No context provided.")

    task = (
        f"Summarize and extract key evidence from the following context for a book outline.\n"
        f"Book Outline:\n{planner_content}\n\n"
        f"Available Context:\n{context_text}\n\n"
        f"List the key facts, citations, and relevant evidence that support the planned chapters."
    )

    try:
        step_data = execute_agent_node(state, step_name="researcher", agent_name="researcher", task=task)
        if step_data["status"] == "failed":
            raise RuntimeError(step_data["error_message"])
    except Exception as exc:
        logger.error("researcher_node failed: %s", exc)
        failed_step = {
            "step_name": "researcher",
            "agent_name": "researcher",
            "task": task,
            "system_prompt": None,
            "user_prompt": None,
            "status": "failed",
            "content": None,
            "structured_output": None,
            "duration_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": str(exc),
            "metadata": {},
        }
        new_steps = list(state.get("steps", [])) + [failed_step]
        new_trace_steps = list(state.get("trace_steps", [])) + [failed_step]
        return {
            **state,
            "researcher_output": None,
            "steps": new_steps,
            "trace_steps": new_trace_steps,
            "status": "failed",
            "error_message": str(exc),
        }

    output_dict = {
        "agent_name": "researcher",
        "status": step_data["status"],
        "content": step_data["content"],
        "structured_output": step_data["structured_output"],
        "error_message": step_data["error_message"],
        "input_tokens": step_data["input_tokens"],
        "output_tokens": step_data["output_tokens"],
        "total_tokens": step_data["total_tokens"],
        "metadata": step_data["metadata"],
    }
    new_steps = list(state.get("steps", [])) + [step_data]
    new_trace_steps = list(state.get("trace_steps", [])) + [step_data]
    return {
        **state,
        "researcher_output": output_dict,
        "steps": new_steps,
        "trace_steps": new_trace_steps,
    }


def writer_node(state: AIuthorWorkflowState) -> AIuthorWorkflowState:
    """
    Writer node: drafts a short section using planner outline and researcher evidence.
    """
    planner_out = state.get("planner_output") or {}
    researcher_out = state.get("researcher_output") or {}
    planner_content = planner_out.get("content", "No outline available.")
    researcher_content = researcher_out.get("content", "No research available.")
    tone = state.get("tone", "informative")
    reader_profile = state.get("reader_profile", "general audience")

    task = (
        f"Write a short draft introduction section (2-3 paragraphs) based on:\n"
        f"Outline:\n{planner_content}\n\n"
        f"Research:\n{researcher_content}\n\n"
        f"Tone: {tone}\n"
        f"Target reader: {reader_profile}\n"
        f"Keep it concise and engaging. Do not write the full book."
    )

    try:
        step_data = execute_agent_node(state, step_name="writer", agent_name="writer", task=task)
        if step_data["status"] == "failed":
            raise RuntimeError(step_data["error_message"])
    except Exception as exc:
        logger.error("writer_node failed: %s", exc)
        failed_step = {
            "step_name": "writer",
            "agent_name": "writer",
            "task": task,
            "system_prompt": None,
            "user_prompt": None,
            "status": "failed",
            "content": None,
            "structured_output": None,
            "duration_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": str(exc),
            "metadata": {},
        }
        new_steps = list(state.get("steps", [])) + [failed_step]
        new_trace_steps = list(state.get("trace_steps", [])) + [failed_step]
        return {
            **state,
            "writer_output": None,
            "steps": new_steps,
            "trace_steps": new_trace_steps,
            "status": "failed",
            "error_message": str(exc),
        }

    output_dict = {
        "agent_name": "writer",
        "status": step_data["status"],
        "content": step_data["content"],
        "structured_output": step_data["structured_output"],
        "error_message": step_data["error_message"],
        "input_tokens": step_data["input_tokens"],
        "output_tokens": step_data["output_tokens"],
        "total_tokens": step_data["total_tokens"],
        "metadata": step_data["metadata"],
    }
    new_steps = list(state.get("steps", [])) + [step_data]
    new_trace_steps = list(state.get("trace_steps", [])) + [step_data]
    # If fact_checker_output already exists we are on a retry — increment counter
    retry_count = state.get("retry_count", 0)
    if state.get("fact_checker_output") is not None:
        retry_count += 1
    return {
        **state,
        "writer_output": output_dict,
        "steps": new_steps,
        "trace_steps": new_trace_steps,
        "retry_count": retry_count,
    }


def humanizer_node(state: AIuthorWorkflowState) -> AIuthorWorkflowState:
    """
    Humanizer node: improves naturalness, rhythm, emotional flow, and tone of the draft.
    """
    writer_out = state.get("writer_output") or {}
    writer_content = writer_out.get("content", "No draft available.")

    task = (
        f"Humanize the following text to make it feel natural, emotionally engaging, and human:\n\n"
        f"{writer_content}\n\n"
        f"Preserve all facts, citations, and core meaning. Do not add unverified claims."
    )

    try:
        step_data = execute_agent_node(state, step_name="humanizer", agent_name="humanizer", task=task)
        if step_data["status"] == "failed":
            raise RuntimeError(step_data["error_message"])
    except Exception as exc:
        logger.error("humanizer_node failed: %s", exc)
        failed_step = {
            "step_name": "humanizer",
            "agent_name": "humanizer",
            "task": task,
            "system_prompt": None,
            "user_prompt": None,
            "status": "failed",
            "content": None,
            "structured_output": None,
            "duration_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": str(exc),
            "metadata": {},
        }
        new_steps = list(state.get("steps", [])) + [failed_step]
        new_trace_steps = list(state.get("trace_steps", [])) + [failed_step]
        return {
            **state,
            "humanizer_output": None,
            "steps": new_steps,
            "trace_steps": new_trace_steps,
            "status": "failed",
            "error_message": str(exc),
        }

    output_dict = {
        "agent_name": "humanizer",
        "status": step_data["status"],
        "content": step_data["content"],
        "structured_output": step_data["structured_output"],
        "error_message": step_data["error_message"],
        "input_tokens": step_data["input_tokens"],
        "output_tokens": step_data["output_tokens"],
        "total_tokens": step_data["total_tokens"],
        "metadata": step_data["metadata"],
    }
    new_steps = list(state.get("steps", [])) + [step_data]
    new_trace_steps = list(state.get("trace_steps", [])) + [step_data]
    return {
        **state,
        "humanizer_output": output_dict,
        "steps": new_steps,
        "trace_steps": new_trace_steps,
    }


def editor_node(state: AIuthorWorkflowState) -> AIuthorWorkflowState:
    """
    Editor node: improves structure, clarity, and flow of the writer or humanizer's draft.
    """
    # Prefer humanizer_output; fall back to writer_output
    draft_source = state.get("humanizer_output") or state.get("writer_output") or {}
    writer_content = draft_source.get("content", "No draft available.")

    task = (
        f"Edit the following draft for clarity, structure, and flow:\n\n"
        f"{writer_content}\n\n"
        f"Improve transitions, remove redundancies, and ensure consistent tone. "
        f"Do not add new facts or change the core meaning."
    )

    try:
        step_data = execute_agent_node(state, step_name="editor", agent_name="editor", task=task)
        if step_data["status"] == "failed":
            raise RuntimeError(step_data["error_message"])
    except Exception as exc:
        logger.error("editor_node failed: %s", exc)
        failed_step = {
            "step_name": "editor",
            "agent_name": "editor",
            "task": task,
            "system_prompt": None,
            "user_prompt": None,
            "status": "failed",
            "content": None,
            "structured_output": None,
            "duration_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": str(exc),
            "metadata": {},
        }
        new_steps = list(state.get("steps", [])) + [failed_step]
        new_trace_steps = list(state.get("trace_steps", [])) + [failed_step]
        return {
            **state,
            "editor_output": None,
            "steps": new_steps,
            "trace_steps": new_trace_steps,
            "status": "failed",
            "error_message": str(exc),
        }

    output_dict = {
        "agent_name": "editor",
        "status": step_data["status"],
        "content": step_data["content"],
        "structured_output": step_data["structured_output"],
        "error_message": step_data["error_message"],
        "input_tokens": step_data["input_tokens"],
        "output_tokens": step_data["output_tokens"],
        "total_tokens": step_data["total_tokens"],
        "metadata": step_data["metadata"],
    }
    new_steps = list(state.get("steps", [])) + [step_data]
    new_trace_steps = list(state.get("trace_steps", [])) + [step_data]
    return {
        **state,
        "editor_output": output_dict,
        "steps": new_steps,
        "trace_steps": new_trace_steps,
    }


def fact_checker_node(state: AIuthorWorkflowState) -> AIuthorWorkflowState:
    """
    Fact-checker node: validates edited output against context_pack citations.
    """
    editor_out = state.get("editor_output") or {}
    editor_content = editor_out.get("content", "No edited draft available.")
    context_pack = state.get("context_pack") or {}
    context_text = context_pack.get("context_text", "No context provided.")
    citations = context_pack.get("citations", [])

    task = (
        f"Fact-check the following edited text against the available context and citations:\n\n"
        f"Edited Text:\n{editor_content}\n\n"
        f"Context:\n{context_text}\n\n"
        f"Citations: {citations}\n\n"
        f"List any factual claims that cannot be verified. "
        f"If everything checks out, confirm the text is consistent with the sources."
    )

    try:
        step_data = execute_agent_node(state, step_name="fact_checker", agent_name="fact_checker", task=task)
        if step_data["status"] == "failed":
            raise RuntimeError(step_data["error_message"])
    except Exception as exc:
        logger.error("fact_checker_node failed: %s", exc)
        failed_step = {
            "step_name": "fact_checker",
            "agent_name": "fact_checker",
            "task": task,
            "system_prompt": None,
            "user_prompt": None,
            "status": "failed",
            "content": None,
            "structured_output": None,
            "duration_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": str(exc),
            "metadata": {},
        }
        new_steps = list(state.get("steps", [])) + [failed_step]
        new_trace_steps = list(state.get("trace_steps", [])) + [failed_step]
        return {
            **state,
            "fact_checker_output": None,
            "steps": new_steps,
            "trace_steps": new_trace_steps,
            "status": "failed",
            "error_message": str(exc),
        }

    output_dict = {
        "agent_name": "fact_checker",
        "status": step_data["status"],
        "content": step_data["content"],
        "structured_output": step_data["structured_output"],
        "error_message": step_data["error_message"],
        "input_tokens": step_data["input_tokens"],
        "output_tokens": step_data["output_tokens"],
        "total_tokens": step_data["total_tokens"],
        "metadata": step_data["metadata"],
    }
    new_steps = list(state.get("steps", [])) + [step_data]
    new_trace_steps = list(state.get("trace_steps", [])) + [step_data]

    # Dynamically mark overall status completed only if running mini_book_pipeline
    workflow_name = state.get("workflow_name", "mini_book_pipeline")
    final_status = "completed" if workflow_name == "mini_book_pipeline" else "running"

    return {
        **state,
        "fact_checker_output": output_dict,
        "steps": new_steps,
        "trace_steps": new_trace_steps,
        "status": final_status,
    }


def memory_keeper_node(state: AIuthorWorkflowState) -> AIuthorWorkflowState:
    """
    MemoryKeeper node: extracts stable facts, concepts, callbacks, and tone fingerprints.
    """
    planner_content = (state.get("planner_output") or {}).get("content", "")
    researcher_content = (state.get("researcher_output") or {}).get("content", "")
    writer_content = (state.get("writer_output") or {}).get("content", "")
    humanizer_content = (state.get("humanizer_output") or {}).get("content", "")
    editor_content = (state.get("editor_output") or {}).get("content", "")
    fact_checker_content = (state.get("fact_checker_output") or {}).get("content", "")

    task = (
        f"Extract stable facts, concepts, continuity callbacks, tone fingerprints, "
        f"and key decisions from the following workflow artifacts:\n\n"
        f"Planner Outline: {planner_content[:1000]}\n"
        f"Research: {researcher_content[:1000]}\n"
        f"Writer Draft: {writer_content[:1000]}\n"
        f"Humanizer Output: {humanizer_content[:1000]}\n"
        f"Editor Edited: {editor_content[:1000]}\n"
        f"Fact-Checker Verification: {fact_checker_content[:1000]}\n\n"
        f"Compile a structured summary of continuity rules and memory candidates to preserve."
    )

    try:
        step_data = execute_agent_node(state, step_name="memory_keeper", agent_name="memory_keeper", task=task)
        if step_data["status"] == "failed":
            raise RuntimeError(step_data["error_message"])
    except Exception as exc:
        logger.error("memory_keeper_node failed: %s", exc)
        failed_step = {
            "step_name": "memory_keeper",
            "agent_name": "memory_keeper",
            "task": task,
            "system_prompt": None,
            "user_prompt": None,
            "status": "failed",
            "content": None,
            "structured_output": None,
            "duration_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": str(exc),
            "metadata": {},
        }
        new_steps = list(state.get("steps", [])) + [failed_step]
        new_trace_steps = list(state.get("trace_steps", [])) + [failed_step]
        return {
            **state,
            "memory_keeper_output": None,
            "steps": new_steps,
            "trace_steps": new_trace_steps,
            "status": "failed",
            "error_message": str(exc),
        }

    output_dict = {
        "agent_name": "memory_keeper",
        "status": step_data["status"],
        "content": step_data["content"],
        "structured_output": step_data["structured_output"],
        "error_message": step_data["error_message"],
        "input_tokens": step_data["input_tokens"],
        "output_tokens": step_data["output_tokens"],
        "total_tokens": step_data["total_tokens"],
        "metadata": step_data["metadata"],
    }
    new_steps = list(state.get("steps", [])) + [step_data]
    new_trace_steps = list(state.get("trace_steps", [])) + [step_data]
    return {
        **state,
        "memory_keeper_output": output_dict,
        "steps": new_steps,
        "trace_steps": new_trace_steps,
    }


def assembler_node(state: AIuthorWorkflowState) -> AIuthorWorkflowState:
    """
    Assembler node: packages suggested outline, draft introduction, memory, and checklists.
    """
    planner_content = (state.get("planner_output") or {}).get("content", "")
    researcher_content = (state.get("researcher_output") or {}).get("content", "")
    editor_content = (state.get("editor_output") or {}).get("content", "")
    fact_checker_content = (state.get("fact_checker_output") or {}).get("content", "")
    memory_content = (state.get("memory_keeper_output") or {}).get("content", "")

    task = (
        f"Assemble a final compact book package structure using all execution outputs:\n\n"
        f"Outline: {planner_content[:500]}\n"
        f"Research: {researcher_content[:500]}\n"
        f"Draft introduction: {editor_content[:1000]}\n"
        f"Fact check status: {fact_checker_content[:500]}\n"
        f"Memory continuity preserved: {memory_content[:500]}\n\n"
        f"Output a cohesive compact book draft package with suggested title, outline, introduction preview, "
        f"and export/matter checklists."
    )

    try:
        step_data = execute_agent_node(state, step_name="assembler", agent_name="assembler", task=task)
        if step_data["status"] == "failed":
            raise RuntimeError(step_data["error_message"])
    except Exception as exc:
        logger.error("assembler_node failed: %s", exc)
        failed_step = {
            "step_name": "assembler",
            "agent_name": "assembler",
            "task": task,
            "system_prompt": None,
            "user_prompt": None,
            "status": "failed",
            "content": None,
            "structured_output": None,
            "duration_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "error_message": str(exc),
            "metadata": {},
        }
        new_steps = list(state.get("steps", [])) + [failed_step]
        new_trace_steps = list(state.get("trace_steps", [])) + [failed_step]
        return {
            **state,
            "assembler_output": None,
            "steps": new_steps,
            "trace_steps": new_trace_steps,
            "status": "failed",
            "error_message": str(exc),
        }

    output_dict = {
        "agent_name": "assembler",
        "status": step_data["status"],
        "content": step_data["content"],
        "structured_output": step_data["structured_output"],
        "error_message": step_data["error_message"],
        "input_tokens": step_data["input_tokens"],
        "output_tokens": step_data["output_tokens"],
        "total_tokens": step_data["total_tokens"],
        "metadata": step_data["metadata"],
    }
    new_steps = list(state.get("steps", [])) + [step_data]
    new_trace_steps = list(state.get("trace_steps", [])) + [step_data]
    return {
        **state,
        "assembler_output": output_dict,
        "steps": new_steps,
        "trace_steps": new_trace_steps,
        "status": "completed",
    }
