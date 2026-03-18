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


def get_rememberer_pair_path(
    model_identifier: str, category_spec: str, task_name: str, source_env: str
) -> str:
    """Path to pair-based memory JSON: rememberer/{model}/{category}/{task_name}__{source_env}.json"""
    root = get_rememberer_root()
    safe_env = source_env.replace("/", "_").strip() or "Initial"
    return os.path.join(root, model_identifier, category_spec, f"{task_name}__{safe_env}.json")


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


def _build_rollout_from_report(report: dict) -> dict:
    """Convert evaluation report (e.g. from evaluation_results_scratch) to rollout-style JSON for memory."""
    hist = report.get("iteration_history") or report.get("history") or []
    task_prompt = report.get("task_prompt") or {}
    task_desc = (task_prompt.get("task_description") or "").strip()
    out_hist = []
    for it in hist:
        td = (it.get("task_description") or task_desc).strip()
        out_hist.append({
            "task_description": td,
            "code": (it.get("code") or "").strip(),
            "feedback": (it.get("feedback") or "").strip(),
            "score": float(it.get("score", 0)),
            "success": bool(it.get("success", False)),
        })
    return {
        "task_prompt": task_prompt,
        "iteration_history": out_hist,
    }


def ensure_rememberer_data_from_scratch(
    task_name: str,
    source_env: str,
    model_identifier: str,
    results_scratch_base: Optional[str] = None,
) -> bool:
    """
    Pair-based protocol: ensure memory data for (task, source_env) from evaluation_results_scratch.
    Copies .../baseline/all_{source_env}.json into rememberer/{model}/{category}/{task_name}__{source_env}.json.
    No fallback: raises FileNotFoundError if scratch file is missing.
    Returns True if data was copied or already present.
    """
    from evaluation.utils import get_scratch_pair_path
    cat_spec = _category_spec_from_task(task_name)
    if not cat_spec:
        raise ValueError(
            f"Rememberer pair-based: task_name {task_name!r} does not map to a category (e.g. category_1_01)."
        )
    scratch_path = get_scratch_pair_path(task_name, source_env, model_identifier, results_scratch_base)
    pair_path = get_rememberer_pair_path(model_identifier, cat_spec, task_name, source_env)
    if os.path.isfile(pair_path):
        return True
    if not os.path.isfile(scratch_path):
        raise FileNotFoundError(
            f"Rememberer pair-based: required scratch file not found: {scratch_path!s}. "
            "Run baseline for this (task, source_env, model) and save under evaluation_results_scratch; no fallback."
        )
    try:
        with open(scratch_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        if not report.get("task_prompt"):
            from evaluation.prompt import load_task_prompt
            report["task_prompt"] = load_task_prompt(task_name)
        report["iteration_history"] = report.get("iteration_history") or report.get("history") or []
        data = _build_rollout_from_report(report)
        os.makedirs(os.path.dirname(pair_path), exist_ok=True)
        with open(pair_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        raise RuntimeError(
            f"Rememberer: failed to copy scratch to {pair_path!s}: {e}"
        ) from e


def load_rememberer_memory_for_task(
    task_name: str,
    model_identifier: str,
    rememberer_root: Optional[str] = None,
    source_env: Optional[str] = None,
) -> Tuple[List[dict], List[Tuple[Tuple[Any, str, Any], dict, int]]]:
    """
    Load rollout data for retrieval.
    - If source_env is set (pair-based): load only from rememberer/.../task_name__source_env.json (same task, original env).
    - Else: load from same-category other tasks (exclude task_name), as before.
    Returns (items, candidates) where candidates are (key, record, line_index) for retrieval.
    """
    from evaluation.prompt import get_all_tasks_in_category

    root = rememberer_root or get_rememberer_root()
    cat_spec = _category_spec_from_task(task_name)
    if not cat_spec:
        return [], []

    # Pair-based: single file for (task, source_env)
    if source_env:
        pair_path = get_rememberer_pair_path(model_identifier, cat_spec, task_name, source_env)
        if not os.path.isfile(pair_path):
            return [], []
        try:
            with open(pair_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return [], []
        hist = data.get("iteration_history") or []
        task_desc = (data.get("task_prompt") or {}).get("task_description") or ""
        if not task_desc and hist:
            task_desc = (hist[0].get("task_description") or "").strip()
        items = []
        candidates = []
        for line_index, it in enumerate(hist):
            task_description = (it.get("task_description") or task_desc).strip()
            code = (it.get("code") or "").strip()
            feedback = (it.get("feedback") or "").strip()
            score = float(it.get("score", 0))
            success = bool(it.get("success", False))
            reward = 1.0 if success else min(1.0, max(0.0, score / 100.0))
            key = ("", task_description, "")
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
            items.append({
                "task_description": task_description,
                "task_name": task_name,
                "code": code,
                "feedback": feedback,
                "score": score,
                "reward": reward,
                "line_index": line_index,
            })
            candidates.append((key, record, line_index))
        return items, candidates

    # Original: same-category other tasks
    m = re.match(r"^category_(\d+)(?:_\d+)?(?:_.*)?$", task_name.lower())
    cat_num = int(m.group(1)) if m else 0
    if cat_num < 1:
        return [], []

    same_category_tasks = get_all_tasks_in_category(cat_num)
    base_task = None
    base_match = re.match(r"^(category_\d+_\d+)", task_name.lower())
    if base_match:
        base_task = base_match.group(1)
    other_tasks = [t for t in same_category_tasks if t != task_name and t != base_task]
    category_dir = os.path.join(root, model_identifier, cat_spec)
    items = []
    candidates = []
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
            key = ("", task_description, "")
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
                "task_name": other,
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


# Cross-mutation: memory is from source-env rollouts; task text shown once, then code+feedback only.
_REMEMBERER_CROSS_MUT_INTRO = """## Relevant experience from memory

These entries are **solution attempts and evaluation feedback from the original (source) environment** — the task **before** it was mutated into the **current new/target** environment described in `# Task Description` above. They are **not** runs under the present mutated physics.

The **shared task background** below applies to **all** following examples (same original setting); each example adds only **code** and **outcome feedback** from that setting.
"""


def _format_rememberer_cross_mutation_block(
    shared_task_description: str,
    rows_pos: List[dict],
    rows_neg: List[dict],
) -> str:
    parts = [_REMEMBERER_CROSS_MUT_INTRO.strip(), ""]
    td = (shared_task_description or "").strip()
    if td:
        parts.append("### Shared task background (original / source environment)")
        parts.append("")
        parts.append(td)
        parts.append("")
    if rows_pos:
        parts.append("**Encouraged** (higher-score attempts in the original environment):")
        parts.append("")
        for i, r in enumerate(rows_pos, 1):
            code = (r.get("code") or "").strip()
            fb = (r.get("feedback") or "").strip()
            sc = float(r.get("score", 0))
            parts.append(f"Example {i}:")
            parts.append("")
            parts.append("```python")
            parts.append(code)
            parts.append("```")
            parts.append("")
            parts.append(f"**Outcome / feedback:** {fb}")
            parts.append(f"(Score in original env: {sc:.1f}/100)")
            parts.append("")
    if rows_neg:
        parts.append("**Discouraged** (lower-score attempts to learn from):")
        parts.append("")
        for i, r in enumerate(rows_neg, 1):
            code = (r.get("code") or "").strip()
            fb = (r.get("feedback") or "").strip()
            sc = float(r.get("score", 0))
            parts.append(f"Example {i}:")
            parts.append("")
            parts.append("```python")
            parts.append(code)
            parts.append("```")
            parts.append("")
            parts.append(f"**Outcome / feedback:** {fb}")
            parts.append(f"(Score in original env: {sc:.1f}/100)")
            parts.append("")
    return "\n".join(parts).strip()


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
    for_cross_mutation_target: bool = False,
) -> str:
    """
    Retrieve similar experiences using Rememberer's DenseInsMatcher (instruction = task_description).
    Format as Encouraged / Discouraged exemplars (same idea as baseline Rememberer advice_template).
    Test-time only: no memory update.

    for_cross_mutation_target: when True, format for mutated-target prompts — state that memory is
    from the original env, show task background once, then code + feedback per example (no repeated task).
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

    rows_pos: List[dict] = []
    rows_neg: List[dict] = []
    for sim, line_index, record, key in top:
        if line_index < 0 or line_index >= len(items):
            continue
        item = items[line_index]
        reward = item.get("reward", 0)
        code = (item.get("code") or "").strip()
        feedback = (item.get("feedback") or "").strip()
        task_description = (item.get("task_description") or "").strip()
        score = item.get("score", 0)
        row = {
            "code": code,
            "feedback": feedback,
            "task_description": task_description,
            "task_name": item.get("task_name"),
            "score": score,
            "reward": reward,
        }
        if reward >= positive_threshold:
            if len(rows_pos) < max_pos:
                rows_pos.append(row)
        else:
            if len(rows_neg) < max_neg:
                rows_neg.append(row)

    if not rows_pos and not rows_neg:
        return "(No relevant experience from other tasks in this category yet.)"

    if for_cross_mutation_target:
        shared_td = ""
        for r in rows_pos + rows_neg:
            if r.get("task_description"):
                shared_td = r["task_description"]
                break
        return _format_rememberer_cross_mutation_block(shared_td, rows_pos, rows_neg)

    # Default: code + feedback only — do not repeat full task_description per example (it often
    # describes Initial/source limits and contradicts mutated Task Description at prompt top).
    _mem_notice = (
        "**Constraint notice:** The examples below are from **other** category tasks or stages. "
        "Their embedded limits may differ from **this** task. Obey **only** the Task Description "
        "and Success Criteria in the main prompt for numeric constraints.\n\n"
    )
    out = [_mem_notice]
    if rows_pos:
        out.append("Encouraged (higher-score solutions from similar tasks in this category):")
        for i, r in enumerate(rows_pos, 1):
            tref = (r.get("task_name") or "").strip() or "related task"
            b = (
                f"[Ref: {tref} — full task spec omitted to avoid conflicting limits]\n\n"
                f"Code:\n```python\n{r['code']}\n```\n\n"
                f"Feedback: {r['feedback']}\n(Score: {float(r['score']):.1f})"
            )
            out.append(f"Example {i}:\n{b}")
    if rows_neg:
        out.append("Discouraged (lower-score solutions to avoid):")
        for i, r in enumerate(rows_neg, 1):
            tref = (r.get("task_name") or "").strip() or "related task"
            b = (
                f"[Ref: {tref} — full task spec omitted to avoid conflicting limits]\n\n"
                f"Code:\n```python\n{r['code']}\n```\n\n"
                f"Feedback: {r['feedback']}\n(Score: {float(r['score']):.1f})"
            )
            out.append(f"Example {i}:\n{b}")
    out.append("Based on the above, provide an improved solution.")
    return "\n\n".join(out)
