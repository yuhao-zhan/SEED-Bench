"""
Memento non-parametric method: wrap DaVinciBench/baseline/Memory/Memento for 2D_exploration.
Uses Memento's memory/np_memory.py (load_jsonl, extract_pairs, retrieve) and Sup-SimCSE.
Prompt is built only from retrieved cases (in-context learning); context=all is not used as best+previous.
"""
import os
import sys
import json
from typing import Optional, Tuple, Any, List

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# methods/Memory -> methods -> scripts -> 2D_exploration -> DaVinciBench
_DAVINCI_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", "..", ".."))
_MEMENTO_ROOT = os.path.join(_DAVINCI_ROOT, "baseline", "Memory", "Memento")
if os.path.isdir(_MEMENTO_ROOT) and _MEMENTO_ROOT not in sys.path:
    sys.path.insert(0, _MEMENTO_ROOT)

# Same as Memento no_parametric_cbr (client/no_parametric_cbr.py uses MEMORY_TOP_K=8; memory/np_memory.retrieve default is 5)
MEMORY_KEY_FIELD = "task_description"
MEMORY_VALUE_FIELD = "code"
# Per round: retrieve top_k cases by similarity; default 5 (match np_memory.retrieve); override with env MEMORY_TOP_K
MEMORY_TOP_K = int(os.environ.get("MEMORY_TOP_K", "5"))
MEMORY_MAX_LENGTH = 256
MEMORY_MAX_POS_EXAMPLES = int(os.environ.get("MEMORY_MAX_POS_EXAMPLES", str(MEMORY_TOP_K)))
MEMORY_MAX_NEG_EXAMPLES = int(os.environ.get("MEMORY_MAX_NEG_EXAMPLES", str(MEMORY_TOP_K)))
# Reward: 1.0 = success; otherwise reward = score/100 (0..1). Cases with reward >= REWARD_POSITIVE_THRESHOLD are "positive".
REWARD_POSITIVE_THRESHOLD = 0.5

# Local embedding model path (no network). Set MEMENTO_EMBEDDING_MODEL_PATH or use default.
DEFAULT_LOCAL_EMBEDDING_PATH = "/home/test/testdata/models/sup-simcse-bert-base-uncased"
# Lazy-loaded embedding model (Sup-SimCSE)
_embedding_tokenizer = None
_embedding_model = None


def _get_embedding_model(device_str: str = "auto"):
    """Lazy load Sup-SimCSE tokenizer and model. Prefer local path to avoid network."""
    global _embedding_tokenizer, _embedding_model
    if _embedding_tokenizer is not None and _embedding_model is not None:
        return _embedding_tokenizer, _embedding_model
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch
        local_path = os.environ.get("MEMENTO_EMBEDDING_MODEL_PATH", DEFAULT_LOCAL_EMBEDDING_PATH)
        if local_path and os.path.isdir(local_path):
            _embedding_tokenizer = AutoTokenizer.from_pretrained(local_path, local_files_only=True)
            _embedding_model = AutoModel.from_pretrained(local_path, local_files_only=True)
        else:
            _embedding_tokenizer = AutoTokenizer.from_pretrained("princeton-nlp/sup-simcse-bert-base-uncased")
            _embedding_model = AutoModel.from_pretrained("princeton-nlp/sup-simcse-bert-base-uncased")
        if device_str == "cuda" and torch.cuda.is_available():
            _embedding_model = _embedding_model.to("cuda")
        elif device_str != "cpu" and torch.cuda.is_available():
            _embedding_model = _embedding_model.to("cuda")
        else:
            _embedding_model = _embedding_model.to("cpu")
        return _embedding_tokenizer, _embedding_model
    except Exception as e:
        raise RuntimeError(
            f"Memento non-parametric: failed to load Sup-SimCSE: {e}. "
            "Download to local: run scripts/download_sup_simcse.sh or set MEMENTO_EMBEDDING_MODEL_PATH."
        ) from e


def get_memory_path(
    output_dir: str,
    task_name: str,
    model_identifier: str,
    run_number: Optional[int] = None,
) -> str:
    """Path to JSONL memory file for this (task, model, run). Creates parent dir if needed."""
    method = "memento_nonparametric"
    base = os.path.join(output_dir, task_name, model_identifier, method)
    os.makedirs(base, exist_ok=True)
    run = run_number if run_number is not None else 1
    return os.path.join(base, f"memory_{run}.jsonl")


def load_memory(path: str) -> Tuple[List[dict], List[Tuple[str, Any, int]]]:
    """Load items and (key, value, index) pairs from JSONL. Returns ([], []) if path missing."""
    if not path or not os.path.exists(path):
        return [], []
    try:
        from memory.np_memory import load_jsonl, extract_pairs
        items = load_jsonl(path)
        pairs = extract_pairs(items, MEMORY_KEY_FIELD, MEMORY_VALUE_FIELD)
        return items, pairs
    except Exception as e:
        print(f"[WARN] Memento non-parametric load_memory failed: {e}", flush=True)
        return [], []


def build_prompt_from_cases_2d(
    retrieved_cases: List[dict],
    original_items: List[dict],
    max_pos: int = MEMORY_MAX_POS_EXAMPLES,
    max_neg: int = MEMORY_MAX_NEG_EXAMPLES,
) -> str:
    """
    Format retrieved cases into prompt text (positive/negative by reward).
    Omits repeating the full task (already in the main prompt); each case is code + feedback only.
    """
    positive_cases = []
    negative_cases = []
    for case in retrieved_cases:
        li = case.get("line_index", -1)
        if 0 <= li < len(original_items):
            reward = original_items[li].get("reward", 0)
            # Support both binary (0/1) and score-based reward (0..1); threshold for "positive"
            r = float(reward) if reward is not None else 0.0
            if r >= REWARD_POSITIVE_THRESHOLD:
                positive_cases.append(case)
            else:
                negative_cases.append(case)

    parts = []
    if positive_cases:
        parts.append(
            f"Positive Examples (reward>={REWARD_POSITIVE_THRESHOLD}) - Showing {min(len(positive_cases), max_pos)} of {len(positive_cases)}:"
        )
        for i, case in enumerate(positive_cases[:max_pos], 1):
            li = case.get("line_index", -1)
            feedback = (original_items[li].get("feedback", "") if 0 <= li < len(original_items) else "") or ""
            code = case.get("plan", "") or ""
            if not isinstance(code, str):
                code = str(code)
            parts.append(
                f"Example {i}:\n```python\n{code}\n```\n\n**Feedback / outcome:**\n{(feedback or '').strip()}\n"
            )
    if negative_cases:
        parts.append(
            f"Negative Examples (reward<{REWARD_POSITIVE_THRESHOLD}) - Showing {min(len(negative_cases), max_neg)} of {len(negative_cases)}:"
        )
        for i, case in enumerate(negative_cases[:max_neg], 1):
            li = case.get("line_index", -1)
            feedback = (original_items[li].get("feedback", "") if 0 <= li < len(original_items) else "") or ""
            code = case.get("plan", "") or ""
            if not isinstance(code, str):
                code = str(code)
            parts.append(
                f"Example {i}:\n```python\n{code}\n```\n\n**Feedback / outcome:**\n{(feedback or '').strip()}\n"
            )
    parts.append(
        "Based on the above examples, provide an improved solution. "
        "Focus on positive examples and avoid patterns from negative examples.\n"
    )
    return "\n".join(parts)


def retrieve_for_prompt(
    task_prompt: Any,
    last_feedback: Optional[str],
    items: List[dict],
    pairs: List[Tuple[str, Any, int]],
    top_k: int = MEMORY_TOP_K,
    device_str: str = "auto",
) -> str:
    """
    Retrieve similar cases and return formatted prompt string.
    Uses Memento's np_memory.retrieve (Sup-SimCSE). Query = task_description + last_feedback.
    """
    if not pairs:
        return "(No relevant memories yet.)"
    if task_prompt is None:
        task_desc = ""
    elif isinstance(task_prompt, dict):
        task_desc = task_prompt.get("task_description") or ""
    else:
        task_desc = str(task_prompt)
    query = task_desc.strip()
    if last_feedback and last_feedback.strip():
        query = (query + "\n" + last_feedback.strip()).strip()
    if not query:
        query = "task and feedback"

    try:
        from memory.np_memory import retrieve as mem_retrieve
        tokenizer, model = _get_embedding_model(device_str)
        results = mem_retrieve(
            task=query,
            pairs=pairs,
            tokenizer=tokenizer,
            model=model,
            device_str=device_str,
            top_k=top_k,
            max_length=MEMORY_MAX_LENGTH,
        )
        return build_prompt_from_cases_2d(results, items)
    except Exception as e:
        print(f"[WARN] Memento non-parametric retrieve failed: {e}", flush=True)
        return "(Retrieval failed.)"


def store_after_iteration(
    task_name: str,
    iteration: int,
    score: float,
    feedback: str,
    code: Optional[str],
    memory_path: str,
    task_description: str,
    success: Optional[bool] = None,
    base_task_name: Optional[str] = None,
) -> dict:
    """
    Append one entry to memory JSONL. Returns the entry dict for iteration_history['memory_stored_entry'].
    success: if None, inferred from score > 0.
    reward: 1.0 if success else score/100 (so model can learn from high-score failures).
    base_task_name: when set (e.g. mutated run), store this as task_name so memory stays task-family aligned (e.g. S_01).
    """
    if success is None:
        success = float(score) > 0
    # Score-based reward: success=1.0, else reward in [0,1] so high-score attempts count as "better"
    reward = 1.0 if success else min(1.0, max(0.0, float(score) / 100.0))
    display_task_name = (base_task_name or task_name).strip()
    entry = {
        MEMORY_KEY_FIELD: task_description,
        MEMORY_VALUE_FIELD: (code or "").strip(),
        "feedback": (feedback or "").strip(),
        "reward": reward,
        "task_name": display_task_name,
        "iteration": iteration,
        "score": score,
    }
    os.makedirs(os.path.dirname(memory_path), exist_ok=True)
    with open(memory_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def restore_memory_from_base_log(base_log: Any, memory_path: str) -> None:
    """
    Replay base task's memory entries into memory_path (for mutated tasks).
    Reads iteration_history[].memory_stored_entry (dict) and appends each to memory_path.
    """
    if not base_log or not memory_path:
        return
    history = base_log.get("iteration_history") or []
    for item in history:
        entry = item.get("memory_stored_entry")
        if not entry or not isinstance(entry, dict):
            continue
        try:
            with open(memory_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[WARN] Memento non-parametric restore append failed: {e}", flush=True)
