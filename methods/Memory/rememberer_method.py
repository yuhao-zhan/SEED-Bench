"""
Rememberer method for 2D_exploration: experience replay from same-category other tasks.
Uses DaVinciBench/baseline/Memory/Rememberer's DenseInsMatcher for similarity (instruction = task_description).
Test-time memory is READ-ONLY: no updates during evaluation; memory is pre-filled from rollout data.
"""
import os
import sys
import json
import re
from typing import Optional, Tuple, List, Any

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# methods/Memory -> methods -> scripts
_SCRIPTS_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
_DAVINCI_ROOT = os.path.normpath(os.path.join(_SCRIPTS_DIR, "..", ".."))
_REMEMBERER_BASELINE = os.path.join(_DAVINCI_ROOT, "baseline", "Memory", "Rememberer")
if os.path.isdir(_REMEMBERER_BASELINE) and _REMEMBERER_BASELINE not in sys.path:
    sys.path.insert(0, _REMEMBERER_BASELINE)

# 2D key type for DenseInsMatcher: (observation_placeholder, task_description, available_actions_placeholder)
# index=1 is instruction (task_description) in original Rememberer
REMEMBERER_KEY_INDEX = 1

# Rollout data root under methods/Memory/rememberer/
def get_rememberer_root() -> str:
    return os.path.join(_SCRIPT_DIR, "rememberer")


def _category_spec_from_task(task_name: str) -> Optional[str]:
    """e.g. category_1_01 -> category_1; category_1_01_Stage_1 -> category_1 (mutated)."""
    m = re.match(r"^category_(\d+)(?:_\d+)?(?:_.*)?$", task_name.lower())
    if m:
        return f"category_{int(m.group(1))}"
    return None


def get_rollout_path(model_identifier: str, category_spec: str, task_name: str) -> str:
    """Path to one task's rollout JSON: rememberer/{model}/{category}/{task_name}.json"""
    root = get_rememberer_root()
    return os.path.join(root, model_identifier, category_spec, f"{task_name}.json")


def _rollout_path_exists(model_identifier: str, task_name: str) -> bool:
    cat_spec = _category_spec_from_task(task_name)
    if not cat_spec:
        return False
    return os.path.isfile(get_rollout_path(model_identifier, cat_spec, task_name))


def ensure_rememberer_data(
    task_list: list,
    model_identifier: str,
    model_type: str,
    model_name: str,
    max_iterations: int = 20,
    context: str = "all",
    model_path: Optional[str] = None,
    api_key: Optional[str] = None,
    device: str = "cuda:0",
    max_steps: int = 10000,
) -> None:
    """
    Ensure rollout exists for all categories covered by task_list.
    Missing rollout JSONs → run baseline and save. Called automatically when running
    evaluate with --method rememberer so one command does everything.
    """
    from evaluation.prompt import get_all_tasks_in_category

    categories = set()
    for t in task_list:
        spec = _category_spec_from_task(t)
        if spec:
            categories.add(spec)
    if not categories:
        return
    from methods.Memory.rememberer.run_rollout import run_rollout_one_task

    class _Args:
        pass

    args = _Args()
    args.model_type = model_type
    args.model_name = model_name
    args.model_path = model_path
    args.api_key = api_key
    args.max_iterations = 20  # Rollout always 20 iterations (or until success); ignore caller max_iterations
    args.context = context
    args.device = device
    args.max_steps = max_steps
    for cat_spec in sorted(categories):
        m = re.match(r"^category_(\d+)$", cat_spec.lower())
        cat_num = int(m.group(1)) if m else 0
        if cat_num < 1:
            continue
        all_tasks = get_all_tasks_in_category(cat_num)
        for task_name in all_tasks:
            if not _rollout_path_exists(model_identifier, task_name):
                run_rollout_one_task(task_name, args)


def load_rememberer_memory_for_task(
    task_name: str,
    model_identifier: str,
    rememberer_root: Optional[str] = None,
) -> Tuple[List[dict], List[Tuple[Tuple[Any, str, Any], dict, int]]]:
    """
    Load rollout data from same-category other tasks (exclude task_name).
    Returns (items, candidates) where candidates are (key, record, line_index) for retrieval.
    key = (obs_placeholder, task_description, actions_placeholder) for DenseInsMatcher(index=1).
    record = { "other_info": {...}, "action_dict": { action_key: { "reward", "qvalue", "number" } }, "id" }.
    """
    from evaluation.prompt import get_all_tasks_in_category

    root = rememberer_root or get_rememberer_root()
    cat_spec = _category_spec_from_task(task_name)
    if not cat_spec:
        return [], []

    m = re.match(r"^category_(\d+)(?:_\d+)?(?:_.*)?$", task_name.lower())
    cat_num = int(m.group(1)) if m else 0
    if cat_num < 1:
        return [], []

    same_category_tasks = get_all_tasks_in_category(cat_num)
    # Exclude current task and its base (e.g. category_1_01_Stage_1 still excludes category_1_01)
    base_task = None
    base_match = re.match(r"^(category_\d+_\d+)", task_name.lower())
    if base_match:
        base_task = base_match.group(1)
    other_tasks = [t for t in same_category_tasks if t != task_name and t != base_task]
    category_dir = os.path.join(root, model_identifier, cat_spec)
    items = []
    candidates = []  # (key, record, line_index)
    line_index = 0
    for other in other_tasks:
        path = os.path.join(category_dir, f"{other}.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        hist = data.get("iteration_history") or []
        task_desc = (data.get("task_prompt") or {}).get("task_description") or ""
        if not task_desc and hist:
            task_desc = (hist[0].get("task_description") or "").strip()
        for it in hist:
            task_description = (it.get("task_description") or task_desc).strip()
            code = (it.get("code") or "").strip()
            feedback = (it.get("feedback") or "").strip()
            score = float(it.get("score", 0))
            success = bool(it.get("success", False))
            reward = 1.0 if success else min(1.0, max(0.0, score / 100.0))
            # Key for DenseInsMatcher: (obs, instruction, available_actions); index=1 = instruction
            key = ("", task_description, "")
            # Action: use (code_snippet, feedback_snippet) as hashable; for display we have full code/feedback in item
            action_key = (code[:500], feedback[:300])
            record = {
                "other_info": {
                    "action_history": [(code, feedback)],
                    "last_reward": reward,
                    "total_reward": reward,
                    "number": 1,
                },
                "action_dict": {
                    action_key: {"reward": reward, "qvalue": reward, "number": 1},
                },
                "id": line_index,
            }
            item = {
                "task_description": task_description,
                "code": code,
                "feedback": feedback,
                "score": score,
                "reward": reward,
                "line_index": line_index,
            }
            items.append(item)
            candidates.append((key, record, line_index))
            line_index += 1
    return items, candidates


# Lazy singleton for SentenceTransformer (same as Rememberer uses)
_rememberer_transformer = None

# Default local paths (loaded with local_files_only=True, no network)
_REMEMBERER_LOCAL_MODEL_CANDIDATES = [
    "/home/test/testdata/models/all-MiniLM-L12-v2",
    "/home/test/testdata/models/all-MiniLM-L6-v2",
]


def _get_rememberer_transformer(device_str: str = "auto"):
    """Lazy load SentenceTransformer for DenseInsMatcher. Prefer local path to avoid network."""
    global _rememberer_transformer
    if _rememberer_transformer is not None:
        return _rememberer_transformer
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        model_name = os.environ.get("REMEMBERER_SENTENCE_TRANSFORMER", "").strip()
        if not model_name:
            for path in _REMEMBERER_LOCAL_MODEL_CANDIDATES:
                if os.path.isdir(path):
                    model_name = path
                    break
        if not model_name:
            model_name = "all-MiniLM-L12-v2"
        if os.path.isdir(model_name):
            _rememberer_transformer = SentenceTransformer(model_name, local_files_only=True)
        else:
            _rememberer_transformer = SentenceTransformer(model_name)
        if device_str != "cpu" and torch.cuda.is_available():
            _rememberer_transformer = _rememberer_transformer.to("cuda")
        return _rememberer_transformer
    except Exception as e:
        raise RuntimeError(
            f"Rememberer: failed to load SentenceTransformer: {e}. "
            "Put model under /home/test/testdata/models/all-MiniLM-L12-v2 or all-MiniLM-L6-v2, or set REMEMBERER_SENTENCE_TRANSFORMER."
        ) from e


def retrieve_for_prompt(
    task_prompt: Any,
    last_feedback: Optional[str],
    items: List[dict],
    candidates: List[Tuple[Tuple[Any, str, Any], dict, int]],
    top_k: int = 5,
    device_str: str = "auto",
    positive_threshold: float = 0.5,
    max_pos: int = 5,
    max_neg: int = 5,
) -> str:
    """
    Retrieve similar experiences using Rememberer's DenseInsMatcher (instruction = task_description).
    Format as Encouraged / Discouraged exemplars (same idea as baseline Rememberer advice_template).
    Test-time only: no memory update.
    """
    if not candidates or not items:
        return "(No relevant experience from other tasks in this category yet.)"

    try:
        import history as rememberer_history
    except ImportError:
        raise RuntimeError(
            "Rememberer: cannot import history from baseline. "
            f"Ensure DaVinciBench/baseline/Memory/Rememberer is on PYTHONPATH (e.g. {_REMEMBERER_BASELINE})."
        ) from None

    if task_prompt is None:
        task_desc = ""
    elif isinstance(task_prompt, dict):
        task_desc = (task_prompt.get("task_description") or "").strip()
    else:
        task_desc = str(task_prompt).strip()
    if last_feedback and last_feedback.strip():
        query_instruction = (task_desc + "\n" + last_feedback.strip()).strip()
    else:
        query_instruction = task_desc or "task"
    query_key = ("", query_instruction, "")

    transformer = _get_rememberer_transformer(device_str)
    matcher = rememberer_history.DenseInsMatcher(query_key, transformer=transformer, index=REMEMBERER_KEY_INDEX)
    scored = []
    for (key, record, line_index) in candidates:
        sim = matcher(key)
        scored.append((sim, line_index, record, key))
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    top = scored[: top_k * 2]

    positive_parts = []
    negative_parts = []
    for sim, line_index, record, key in top:
        if line_index < 0 or line_index >= len(items):
            continue
        item = items[line_index]
        reward = item.get("reward", 0)
        code = (item.get("code") or "").strip()
        feedback = (item.get("feedback") or "").strip()
        task_description = (item.get("task_description") or "").strip()
        score = item.get("score", 0)
        block = f"Task: {task_description}\n\nCode:\n```python\n{code}\n```\n\nFeedback: {feedback}\n(Score: {score:.1f})"
        if reward >= positive_threshold:
            if len(positive_parts) < max_pos:
                positive_parts.append(block)
        else:
            if len(negative_parts) < max_neg:
                negative_parts.append(block)

    # Same structure as Rememberer prompts/advice_template.txt: Encouraged / Discouraged
    out = []
    if positive_parts:
        out.append("Encouraged (higher-score solutions from similar tasks in this category):")
        for i, b in enumerate(positive_parts, 1):
            out.append(f"Example {i}:\n{b}")
    if negative_parts:
        out.append("Discouraged (lower-score solutions to avoid):")
        for i, b in enumerate(negative_parts, 1):
            out.append(f"Example {i}:\n{b}")
    if not out:
        return "(No relevant experience from other tasks in this category yet.)"
    out.append("Based on the above, provide an improved solution.")
    return "\n\n".join(out)
