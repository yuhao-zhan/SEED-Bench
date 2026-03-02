"""
ExpeL method for 2D_exploration: experience replay + LLM-extracted rules from same-category other tasks.
Uses DaVinciBench/baseline/Memory/ExpeL's EMBEDDERS, parse_rules, update_rules, and RULE_TEMPLATE.
Test-time memory is READ-ONLY (per original ExpeL eval config).
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
_EXPEL_BASELINE = os.path.join(_DAVINCI_ROOT, "baseline", "Memory", "ExpeL")
if os.path.isdir(_EXPEL_BASELINE) and _EXPEL_BASELINE not in sys.path:
    sys.path.insert(0, _EXPEL_BASELINE)

# Only import EMBEDDERS at top level so 2D load+retrieve work without full ExpeL deps (agent.expel/prompts pull in langchain.prompts).
_EXPEL_IMPORT_ERROR = None
_RULE_TEMPLATE_2D = None
parse_rules = None
update_rules = None
try:
    from memory import EMBEDDERS
except Exception as e:
    _EXPEL_IMPORT_ERROR = e

def _ensure_expel_full_import():
    """Lazy import for ensure_expel_data / insight extraction (needs parse_rules, update_rules, RULE_TEMPLATE)."""
    global parse_rules, update_rules, _RULE_TEMPLATE_2D
    if parse_rules is not None:
        return
    try:
        from agent.expel import parse_rules as _pr, update_rules as _ur
        from prompts.templates.human import RULE_TEMPLATE
        parse_rules = _pr
        update_rules = _ur
        _RULE_TEMPLATE_2D = RULE_TEMPLATE.get("2d_exploration") if isinstance(RULE_TEMPLATE, dict) else None
    except Exception as e:
        raise RuntimeError(
            "ExpeL insight extraction requires full ExpeL package (agent.expel, prompts). "
            "Install: pip install -r DaVinciBench/baseline/Memory/ExpeL/requirements.txt"
        ) from e

# Rollout data root under methods/Memory/expel/
def get_expel_root() -> str:
    return os.path.join(_SCRIPT_DIR, "expel")


def _category_spec_from_task(task_name: str) -> Optional[str]:
    """e.g. category_1_01 -> category_1; category_1_01_Stage_1 -> category_1 (mutated)."""
    m = re.match(r"^category_(\d+)(?:_\d+)?(?:_.*)?$", task_name.lower())
    if m:
        return f"category_{int(m.group(1))}"
    return None


def get_rollout_path(model_identifier: str, category_spec: str, task_name: str) -> str:
    """Path to one task's rollout JSON: expel/{model}/{category}/{task_name}.json"""
    root = get_expel_root()
    return os.path.join(root, model_identifier, category_spec, f"{task_name}.json")


def _rollout_path_exists(model_identifier: str, task_name: str) -> bool:
    cat_spec = _category_spec_from_task(task_name)
    if not cat_spec:
        return False
    return os.path.isfile(get_rollout_path(model_identifier, cat_spec, task_name))


def ensure_expel_data(
    task_list: List[str],
    model_identifier: str,
    model_type: str,
    model_name: str,
    max_iterations: int = 20,
    context: str = "all",
    model_path: Optional[str] = None,
    api_key: Optional[str] = None,
    device: str = "cuda:0",
    max_steps: int = 10000,
    expel_max_rounds: Optional[int] = None,
    expel_max_num_rules: Optional[int] = None,
) -> None:
    """
    Ensure rollout + insights exist for all categories covered by task_list.
    Missing rollout JSONs → run baseline and save; missing insights.json → run insight extraction.
    Called automatically when running evaluate with --method expel so one command does everything.
    """
    _ensure_expel_full_import()
    from evaluation.prompt import get_all_tasks_in_category

    categories = set()
    for t in task_list:
        spec = _category_spec_from_task(t)
        if spec:
            categories.add(spec)
    if not categories:
        return
    for cat_spec in sorted(categories):
        m = re.match(r"^category_(\d+)$", cat_spec.lower())
        cat_num = int(m.group(1)) if m else 0
        if cat_num < 1:
            continue
        all_tasks = get_all_tasks_in_category(cat_num)
        # Rollout: prefer backfill from evaluation_results/.../baseline (best of 1st/2nd/3rd by best_score); else run baseline
        from methods.Memory.expel.run_rollout import run_rollout_one_task, try_backfill_one_task

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
        for task_name in all_tasks:
            if _rollout_path_exists(model_identifier, task_name):
                continue
            if try_backfill_one_task(task_name, model_identifier, context):
                continue
            run_rollout_one_task(task_name, args)
        # Insights: run once per category after all rollout for that category (missing only)
        insights_path = os.path.join(get_expel_root(), model_identifier, cat_spec, "insights.json")
        if not os.path.isfile(insights_path):
            from methods.Memory.expel.run_insight_extraction import (
                run_insight_extraction_for_category,
                DEFAULT_MAX_ROUNDS,
                DEFAULT_MAX_NUM_RULES,
            )

            run_insight_extraction_for_category(
                cat_spec, model_identifier, model_type, model_name,
                model_path=model_path, api_key=api_key, device=device,
                max_rounds=expel_max_rounds if expel_max_rounds is not None else DEFAULT_MAX_ROUNDS,
                max_num_rules=expel_max_num_rules if expel_max_num_rules is not None else DEFAULT_MAX_NUM_RULES,
            )


def _get_expel_embedder(embedder_type: str = "huggingface", embedder_path: Optional[str] = None):
    """Return embedder for rule/trajectory retrieval. No fallback: raises if unavailable."""
    if _EXPEL_IMPORT_ERROR is not None:
        raise RuntimeError(
            "ExpeL method requires the ExpeL package to be importable (for EMBEDDERS and embedder). "
            "Install dependencies: pip install -r DaVinciBench/baseline/Memory/ExpeL/requirements.txt"
        ) from _EXPEL_IMPORT_ERROR
    path = embedder_path or os.environ.get("EXPEL_EMBEDDER", "").strip()
    local_candidates = [
        "/home/test/testdata/models/all-MiniLM-L12-v2",
        "/home/test/testdata/models/all-MiniLM-L6-v2",
        "/home/test/testdata/models/all-mpnet-base-v2",
    ]
    if not path:
        for p in local_candidates:
            if os.path.isdir(p):
                path = p
                break
    if not path:
        path = "all-mpnet-base-v2"
    if os.path.isdir(path):
        # HuggingFaceEmbeddings(model_name=path, ...) with local_files_only
        try:
            from langchain.embeddings import HuggingFaceEmbeddings
        except ImportError:
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
            except ImportError:
                raise RuntimeError(
                    "ExpeL embedder requires langchain or langchain_community. "
                    "Install: pip install -r DaVinciBench/baseline/Memory/ExpeL/requirements.txt"
                ) from None
        return HuggingFaceEmbeddings(
            model_name=path,
            model_kwargs={"local_files_only": True},
            encode_kwargs={"normalize_embeddings": False},
        )
    return EMBEDDERS(embedder_type)(model_name=path)


def load_expel_memory_for_task(
    task_name: str,
    model_identifier: str,
    expel_root: Optional[str] = None,
) -> Tuple[List[dict], List[str], Any]:
    """
    Load rollout data and insights from same-category other tasks (exclude task_name).
    Returns (items, rule_strings, embedder) where items are trajectory records for retrieval,
    rule_strings from insights.json, embedder from ExpeL EMBEDDERS (for retrieve_for_prompt).
    """
    from evaluation.prompt import get_all_tasks_in_category

    root = expel_root or get_expel_root()
    cat_spec = _category_spec_from_task(task_name)
    if not cat_spec:
        return [], [], None
    m = re.match(r"^category_(\d+)(?:_\d+)?(?:_.*)?$", task_name.lower())
    cat_num = int(m.group(1)) if m else 0
    if cat_num < 1:
        return [], [], None
    same_category_tasks = get_all_tasks_in_category(cat_num)
    base_task = None
    base_match = re.match(r"^(category_\d+_\d+)", task_name.lower())
    if base_match:
        base_task = base_match.group(1)
    other_tasks = [t for t in same_category_tasks if t != task_name and t != base_task]
    category_dir = os.path.join(root, model_identifier, cat_spec)
    items = []
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
            items.append({
                "task_name": other,
                "task_description": (it.get("task_description") or task_desc).strip(),
                "code": (it.get("code") or "").strip(),
                "feedback": (it.get("feedback") or "").strip(),
                "score": float(it.get("score", 0)),
                "success": bool(it.get("success", False)),
            })
    # Rules: from one insights.json (insights_by_task); take rules from all tasks in category except current task
    rule_strings = []
    insights_path = os.path.join(category_dir, "insights.json")
    if os.path.isfile(insights_path):
        try:
            with open(insights_path, "r", encoding="utf-8") as f:
                insights_data = json.load(f)
            by_task = insights_data.get("insights_by_task") or {}
            for task_key, entry in by_task.items():
                if base_task and task_key == base_task:
                    continue
                rules = entry.get("rules") or entry.get("rule_strings") or []
                rule_strings.extend(rules)
            if not rule_strings and by_task:
                rule_strings = insights_data.get("rules") or insights_data.get("rule_strings") or []
            if isinstance(rule_strings, list) and rule_strings and not isinstance(rule_strings[0], str):
                rule_strings = [r.get("text", r) if isinstance(r, dict) else str(r) for r in rule_strings]
        except Exception:
            pass
    embedder = _get_expel_embedder()
    if embedder is None:
        raise RuntimeError(
            "ExpeL embedder is None after _get_expel_embedder(). "
            "Set EXPEL_EMBEDDER to a valid local path or HuggingFace model name and ensure langchain is installed."
        )
    return items, rule_strings, embedder


def retrieve_for_prompt(
    task_prompt: Any,
    last_feedback: Optional[str],
    items: List[dict],
    rule_strings: List[str],
    embedder: Any,
    top_k_rules: int = 5,
    top_k_trajectories: int = 3,
) -> str:
    """
    Retrieve top-k rules and optionally trajectory snippets by task similarity.
    Returns a single string to append to the revision prompt (rules + optional experience).
    """
    task_description = ""
    if hasattr(task_prompt, "get"):
        task_description = (task_prompt.get("task_description") or "").strip()
    elif isinstance(task_prompt, dict):
        task_description = (task_prompt.get("task_description") or "").strip()
    if not task_description and getattr(task_prompt, "task_description", None):
        task_description = (task_prompt.task_description or "").strip()
    query = (task_description or "") + " " + (last_feedback or "")

    parts = []
    if rule_strings:
        if embedder is None:
            raise RuntimeError(
                "ExpeL rule retrieval requires an embedder. "
                "Embedder is None (ExpeL package or langchain/embedding model failed to load). "
                "Fix: install ExpeL deps and set EXPEL_EMBEDDER to a local model path or HuggingFace model name."
            )
        query_emb = embedder.embed_query(query)
        rule_embs = embedder.embed_documents(rule_strings)
        from numpy import dot
        from numpy.linalg import norm
        scores = [dot(query_emb, re) / (norm(query_emb) * norm(re) + 1e-9) for re in rule_embs]
        idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k_rules]
        selected = [rule_strings[i] for i in idx]
        if selected:
            rules_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(selected)])
            if _RULE_TEMPLATE_2D is not None:
                msg = _RULE_TEMPLATE_2D.format_messages(rules=rules_text)
                if msg and len(msg) > 0:
                    parts.append(msg[0].content if hasattr(msg[0], "content") else str(msg[0]))
            else:
                parts.append("The following are experiences from similar tasks. Use them as references:\n" + rules_text)

    if items and top_k_trajectories > 0:
        if embedder is None:
            raise RuntimeError(
                "ExpeL trajectory retrieval requires an embedder. "
                "Embedder is None. Set EXPEL_EMBEDDER and ensure ExpeL/langchain are available."
            )
        task_descs = [it.get("task_description") or "" for it in items]
        if not task_descs:
            task_descs = [query]
        query_emb = embedder.embed_query(query)
        doc_embs = embedder.embed_documents(task_descs[: min(len(task_descs), 100)])
        from numpy import dot
        from numpy.linalg import norm
        scores = [dot(query_emb, de) / (norm(query_emb) * norm(de) + 1e-9) for de in doc_embs]
        idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k_trajectories]
        selected_items = [items[i] for i in idx]
        exp_parts = []
        for it in selected_items:
            snip = f"[Task: {it.get('task_description', '')}]\nCode:\n{it.get('code', '')}\nFeedback: {it.get('feedback', '')}"
            exp_parts.append(snip)
        if exp_parts:
            parts.append("Relevant experience from same-category tasks:\n" + "\n\n".join(exp_parts))

    if not parts:
        return ""
    return "\n\n".join(parts)
