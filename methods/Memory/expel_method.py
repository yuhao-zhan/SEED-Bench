"""
ExpeL method for 2D_exploration: **insight extraction** (official compare/all-success prompts +
parse_rules/update_rules) then **rule retrieval** at test time — not raw episode replay only.

- **Pair-based (cross-mutation)**: after copying baseline scratch to
  ``expel/.../{task}__{source_env}.json``, runs LLM extraction and writes
  ``{task}__{source_env}.insights.json`` with distilled ``rules``.
- **Category-wide**: rollouts are backfilled from ``evaluation_results/.../baseline`` only; then
  ``ensure_expel_data`` builds ``insights.json`` (ExpeL insight extraction) when missing.

Uses ``get_aux_llm_credentials`` (same as ``SolverInterface``): key from arg / ``OPENAI_API_KEY`` / ``SolverInterface.API_KEY``,
base ``SolverInterface.BASE_URL``. Insight model: ``EXPEL_INSIGHT_MODEL`` or default ``deepseek-v3.2``.
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


def get_expel_pair_path(
    model_identifier: str, category_spec: str, task_name: str, source_env: str
) -> str:
    """Path to pair-based memory JSON: expel/{model}/{category}/{task_name}__{source_env}.json"""
    root = get_expel_root()
    safe_env = source_env.replace("/", "_").strip() or "Initial"
    return os.path.join(root, model_identifier, category_spec, f"{task_name}__{safe_env}.json")


def get_expel_pair_insights_path(
    model_identifier: str, category_spec: str, task_name: str, source_env: str
) -> str:
    """LLM-extracted rules for this (task, source_env) rollout — ExpeL insight extraction output."""
    root = get_expel_root()
    safe_env = source_env.replace("/", "_").strip() or "Initial"
    return os.path.join(
        root, model_identifier, category_spec, f"{task_name}__{safe_env}.insights.json"
    )


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
    Ensure category rollout JSONs under expel/ + insights.json exist (same spirit as Rememberer).

    - Rollout: **only** from existing ``evaluation_results/.../{model}/baseline`` (non-pair JSONs
      with ``iteration_history``). Missing files are copied into ``expel/{model}/{category}/``.
      **Never** runs a live baseline eval here — if nothing to backfill, raises RuntimeError.
    - Insights: if ``insights.json`` is missing, runs official ExpeL-style insight extraction
      (or writes a stub if deps/API fail).
    """
    from evaluation.prompt import get_all_tasks_in_category, parse_task_name
    from evaluation.utils import get_evaluation_results_dir

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
        from methods.Memory.expel.run_rollout import try_backfill_one_task

        for task_name in all_tasks:
            if _rollout_path_exists(model_identifier, task_name):
                continue
            if try_backfill_one_task(task_name, model_identifier, context):
                continue
            try:
                task_path, _ = parse_task_name(task_name)
                parts = task_path.split("/")
                baseline_hint = (
                    os.path.join(
                        get_evaluation_results_dir(),
                        parts[0],
                        parts[1],
                        model_identifier,
                        "baseline",
                    )
                    if len(parts) >= 2
                    else "(parse task path failed)"
                )
            except Exception:
                baseline_hint = f"{get_evaluation_results_dir()}/<category>/<task>/{model_identifier}/baseline"
            expel_dst = get_rollout_path(model_identifier, cat_spec, task_name)
            raise RuntimeError(
                f"[ExpeL] No rollout JSON for {task_name!r} under expel, and could not backfill "
                f"from evaluation_results.\n"
                f"  Look under: {baseline_hint} and sibling dirs (expel, rememberer, …) for any "
                f".json with non-empty iteration_history.\n"
                f"  Or write rollout manually: {expel_dst}"
            )
        # Insights: run once per category after all rollout for that category (missing only)
        insights_path = os.path.join(get_expel_root(), model_identifier, cat_spec, "insights.json")
        if not os.path.isfile(insights_path):
            try:
                from methods.Memory.expel.insight_extraction import (
                    run_insight_extraction_for_category,
                    DEFAULT_MAX_ROUNDS,
                    DEFAULT_MAX_NUM_RULES,
                )
                from evaluation.solver_interface import get_aux_llm_credentials

                _ek, _eu = get_aux_llm_credentials(api_key)
                run_insight_extraction_for_category(
                    cat_spec,
                    model_identifier,
                    model_type,
                    model_name,
                    model_path=model_path,
                    api_key=_ek,
                    device=device,
                    max_rounds=expel_max_rounds
                    if expel_max_rounds is not None
                    else DEFAULT_MAX_ROUNDS,
                    max_num_rules=expel_max_num_rules
                    if expel_max_num_rules is not None
                    else DEFAULT_MAX_NUM_RULES,
                    base_url=_eu,
                    insight_model=os.environ.get("EXPEL_INSIGHT_MODEL"),
                )
            except Exception as e:
                print(
                    f"[ExpeL] Category insight extraction skipped (non-fatal): {e}",
                    flush=True,
                )
                os.makedirs(os.path.dirname(insights_path), exist_ok=True)
                stub = {
                    "rules": [],
                    "insights_by_task": {},
                    "note": "insight_extraction_skipped",
                    "error": str(e)[:800],
                    "hint": "Install: pip install -r DaVinciBench/baseline/Memory/ExpeL/requirements.txt "
                    "then delete this insights.json to regenerate.",
                }
                with open(insights_path, "w", encoding="utf-8") as f:
                    json.dump(stub, f, ensure_ascii=False, indent=2)


def ensure_expel_data_from_scratch(
    task_name: str,
    source_env: str,
    model_identifier: str,
    results_scratch_base: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    insight_model: Optional[str] = None,
) -> bool:
    """
    Pair-based protocol: ensure memory data for (task, source_env) from evaluation_results_scratch.
    Copies .../baseline/all_{source_env}.json into expel/{model}/{category}/{task_name}__{source_env}.json.
    No fallback: raises FileNotFoundError if scratch file is missing.
    Returns True if data was copied or already present.
    """
    from evaluation.utils import get_scratch_pair_path
    from methods.Memory.expel.run_rollout import build_rollout_json_from_report

    cat_spec = _category_spec_from_task(task_name)
    if not cat_spec:
        raise ValueError(
            f"ExpeL pair-based: task_name {task_name!r} does not map to a category (e.g. category_1_01)."
        )
    scratch_path = get_scratch_pair_path(task_name, source_env, model_identifier, results_scratch_base)
    pair_path = get_expel_pair_path(model_identifier, cat_spec, task_name, source_env)
    insights_path = get_expel_pair_insights_path(
        model_identifier, cat_spec, task_name, source_env
    )

    def _ensure_pair_insights() -> None:
        if os.path.isfile(insights_path):
            return
        if not os.path.isfile(pair_path):
            return
        print(
            f"[ExpeL] Running pair insight extraction → {os.path.basename(insights_path)}",
            flush=True,
        )
        try:
            from methods.Memory.expel.insight_extraction import run_pair_insight_extraction

            from evaluation.solver_interface import get_aux_llm_credentials
            _pk, _pu = get_aux_llm_credentials(api_key)
            run_pair_insight_extraction(
                pair_path,
                insights_path,
                api_key=_pk,
                base_url=base_url or _pu,
                model=insight_model or os.environ.get("EXPEL_INSIGHT_MODEL"),
            )
        except Exception as e:
            print(f"[ExpeL] Pair insight extraction failed (non-fatal): {e}", flush=True)

    if os.path.isfile(pair_path):
        if os.path.isfile(insights_path):
            print(
                f"[ExpeL] Pair insights already exist, skip extraction: {insights_path}",
                flush=True,
            )
        _ensure_pair_insights()
        return True
    if not os.path.isfile(scratch_path):
        raise FileNotFoundError(
            f"ExpeL pair-based: required scratch file not found: {scratch_path!s}. "
            "Run baseline for this (task, source_env, model) and save under evaluation_results_scratch; no fallback."
        )
    try:
        with open(scratch_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        if not report.get("task_prompt"):
            from evaluation.prompt import load_task_prompt
            report["task_prompt"] = load_task_prompt(task_name)
        report["iteration_history"] = report.get("iteration_history") or report.get("history") or []
        rollout_data = build_rollout_json_from_report(
            report, task_name, model_identifier, "baseline", "all"
        )
        os.makedirs(os.path.dirname(pair_path), exist_ok=True)
        with open(pair_path, "w", encoding="utf-8") as f:
            json.dump(rollout_data, f, ensure_ascii=False, indent=2)
        _ensure_pair_insights()
        return True
    except Exception as e:
        raise RuntimeError(
            f"ExpeL: failed to copy scratch to {pair_path!s}: {e}"
        ) from e


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
    source_env: Optional[str] = None,
) -> Tuple[List[dict], List[str], Any]:
    """
    Load rollout data and insights for retrieval.
    - If source_env is set (pair-based): load only from expel/.../task_name__source_env.json (same task, original env).
    - Else: load from same-category other tasks (exclude task_name), as before.
    Returns (items, rule_strings, embedder).
    """
    from evaluation.prompt import get_all_tasks_in_category

    root = expel_root or get_expel_root()
    cat_spec = _category_spec_from_task(task_name)
    if not cat_spec:
        return [], [], None

    # Pair-based: single file for (task, source_env)
    if source_env:
        pair_path = get_expel_pair_path(model_identifier, cat_spec, task_name, source_env)
        if not os.path.isfile(pair_path):
            return [], [], None
        try:
            with open(pair_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return [], [], None
        hist = data.get("iteration_history") or []
        task_desc = (data.get("task_prompt") or {}).get("task_description") or ""
        if not task_desc and hist:
            task_desc = (hist[0].get("task_description") or "").strip()
        items = []
        for it in hist:
            items.append({
                "task_name": task_name,
                "task_description": (it.get("task_description") or task_desc).strip(),
                "code": (it.get("code") or "").strip(),
                "feedback": (it.get("feedback") or "").strip(),
                "score": float(it.get("score", 0)),
                "success": bool(it.get("success", False)),
            })
        rule_strings = []
        insights_path = get_expel_pair_insights_path(
            model_identifier, cat_spec, task_name, source_env
        )
        if os.path.isfile(insights_path):
            try:
                with open(insights_path, "r", encoding="utf-8") as f:
                    insights_data = json.load(f)
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

    # Original: same-category other tasks
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
        # Do NOT paste stored task_description into snippets: it often matches Initial env while
        # the live prompt is Stage-* (mutated limits). That contradicts "(originally …)" specs.
        traj_header = (
            "**Constraint notice:** Trajectories below omit full task specs (they often match Initial/source "
            "environments and would contradict mutated limits). "
            "**Use only the Task Description and Success Criteria at the top of this message** for joint/anchor "
            "strength, gap geometry, mass budget, and all other numbers.\n\n"
            "Relevant experience (code + feedback from related rollouts):"
        )
        for it in selected_items:
            tn = (it.get("task_name") or "").strip() or "related rollout"
            code = (it.get("code") or "").strip()
            fb = (it.get("feedback") or "").strip()
            snip = (
                f"[Source: {tn} — same-category or prior-env attempt; specs above override.]\n"
                f"Code:\n{code}\nFeedback: {fb}"
            )
            exp_parts.append(snip)
        if exp_parts:
            parts.append(traj_header + "\n\n" + "\n\n".join(exp_parts))

    if not parts:
        return ""
    return "\n\n".join(parts)
