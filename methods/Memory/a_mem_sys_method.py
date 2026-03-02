"""
A-mem-sys method: wrap DaVinciBench/baseline/Memory/A-mem-sys for 2D_exploration evaluation.
Uses the original A-mem-sys package via import (no reimplementation).
Memory module LLM is fixed to deepseek-v3.2 by default (not the solver agent).
"""
import os
import sys
from typing import Optional, Tuple, Any

# Ensure A-mem-sys package is importable (same repo, relative to this file)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# methods/Memory -> methods -> scripts -> 2D_exploration -> DaVinciBench
_DAVINCI_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", "..", ".."))
_A_MEM_SYS_ROOT = os.path.join(_DAVINCI_ROOT, "baseline", "Memory", "A-mem-sys")
if os.path.isdir(_A_MEM_SYS_ROOT) and _A_MEM_SYS_ROOT not in sys.path:
    sys.path.insert(0, _A_MEM_SYS_ROOT)

# Default LLM for memory processing (metadata, evolution) — not the solver agent
DEFAULT_MEMORY_LLM_MODEL = "deepseek-v3.2"
# Load embedding model from local path (no HuggingFace download)
DEFAULT_EMBEDDING_MODEL_PATH = "/home/test/testdata/models/all-MiniLM-L6-v2"


def get_memory_system(
    llm_backend: str = "openai",
    llm_model: str = DEFAULT_MEMORY_LLM_MODEL,
    api_key: Optional[str] = None,
    embedding_model_name: str = DEFAULT_EMBEDDING_MODEL_PATH,
    base_url: Optional[str] = None,
):
    """
    Create and return an AgenticMemorySystem from A-mem-sys.
    Memory processing LLM defaults to deepseek-v3.2 (independent of solver).
    base_url: optional custom API base (e.g. https://yeysai.com/v1) when using same gateway as solver.
    """
    # Lazy import so module loads without A-mem-sys deps (sentence_transformers, chromadb, etc.)
    from agentic_memory.memory_system import AgenticMemorySystem
    kwargs = dict(
        model_name=embedding_model_name,
        llm_backend=llm_backend,
        llm_model=llm_model,
        api_key=api_key,
    )
    if base_url is not None:
        kwargs["base_url"] = base_url
    return AgenticMemorySystem(**kwargs)


def retrieve_for_prompt(
    task_prompt: Any,
    last_feedback: Optional[str],
    memory_system: Any,
    k: int = 5,
) -> str:
    """
    Retrieve related memories for the current round. Uses find_related_memories from A-mem-sys.
    task_prompt: dict with at least task_description (or str).
    Returns the formatted memory string to prepend to the prompt (empty if no memories).
    """
    if task_prompt is None:
        task_desc = ""
    elif isinstance(task_prompt, dict):
        task_desc = task_prompt.get("task_description") or ""
    else:
        task_desc = str(task_prompt)
    query = task_desc.strip()
    if last_feedback and last_feedback.strip():
        query = (query + "\n" + (last_feedback or "").strip()).strip()
    if not query:
        query = "task and feedback"
    memory_str, _ = memory_system.find_related_memories(query, k=k)
    return memory_str or ""


def store_after_iteration(
    task_name: str,
    iteration: int,
    score: float,
    feedback_snippet: str,
    code_snippet: Optional[str],
    memory_system: Any,
) -> str:
    """
    Store this iteration's full solution (code) and feedback in memory so that when we
    retrieve, we can put that round's solution+feedback in the prompt for revision.
    No truncation: full code and feedback are stored.
    Returns the content string that was stored (for logging in JSON).
    """
    feedback = (feedback_snippet or "").strip()
    code = (code_snippet or "").strip()
    content = (
        f"## Past attempt | Task: {task_name} | Iteration: {iteration} | Score: {score:.1f}\n\n"
        "### Code\n```python\n"
        f"{code}\n"
        "```\n\n"
        "### Feedback\n"
        f"{feedback}\n"
    )
    try:
        memory_system.add_note(content)
        return content
    except Exception as e:
        return f"(store failed: {e})"


def restore_memory_from_base_log(
    memory_system: Any,
    base_log: Any,
) -> None:
    """
    Restore memory state from a base task log so that mutated tasks start with
    the same memory the agent had after the initial task (T0). Used when
    running mutation sequence: each mutated task (T1, T2, ...) gets T0's
    memory replayed into a fresh memory system (so T1 and T2 do not share
    each other's updates, only T0's).
    """
    if not base_log or not memory_system:
        return
    history = base_log.get("iteration_history") or []
    for item in history:
        content = item.get("memory_stored")
        if not content or not isinstance(content, str) or content.strip() == "":
            continue
        try:
            memory_system.add_note(content.strip())
        except Exception:
            continue
