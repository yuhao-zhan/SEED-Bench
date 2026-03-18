"""
ExpeL rollout: backfill from evaluation_results baseline JSONs into expel/{model}/category_*/.
Live baseline eval (run_rollout_one_task) is optional/manual only; category prep uses try_backfill only.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

_EXPel_ROOT = os.path.dirname(os.path.abspath(__file__))


def _rollout_dest_path(model_identifier: str, task_name: str) -> Optional[str]:
    m = re.match(r"^category_(\d+)(?:_\d+)?(?:_.*)?$", task_name.lower())
    if not m:
        return None
    cat = f"category_{int(m.group(1))}"
    return os.path.join(_EXPel_ROOT, model_identifier, cat, f"{task_name}.json")


def build_rollout_json_from_report(
    report: dict,
    task_name: str,
    model_identifier: str,
    method: str,
    context: str,
) -> dict[str, Any]:
    """
    Convert evaluation report to rollout-style JSON for ExpeL retrieval / insight extraction.
    """
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


def _load_rollout_candidates_from_dir(
    dir_path: str, *, exclude_pair: bool
) -> list[tuple[float, dict, str]]:
    """JSON reports with iteration_history; optionally skip cross-mutation pair files."""
    out: list[tuple[float, dict, str]] = []
    if not os.path.isdir(dir_path):
        return out
    for fn in os.listdir(dir_path):
        if not fn.endswith(".json"):
            continue
        if exclude_pair and "_to_" in fn and fn.startswith("all_"):
            continue
        path = os.path.join(dir_path, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                rep = json.load(f)
        except Exception:
            continue
        hist = rep.get("iteration_history") or rep.get("history") or []
        if not hist:
            continue
        sc = float(rep.get("best_score", 0) or 0)
        out.append((sc, rep, fn))
    return out


def try_backfill_one_task(
    task_name: str, model_identifier: str, context: str
) -> bool:
    """
    Copy best-scoring report with iteration_history from evaluation_results into expel rollout JSON.

    Search order:
    1. ``.../{model}/baseline/`` — prefer non-pair JSONs; if none, use pair (e.g. all_Initial_to_Stage-1.json).
    2. Any other method subdir under ``.../{model}/`` (expel, rememberer, ace, …) if baseline has nothing usable.
    """
    from evaluation.prompt import load_task_prompt, parse_task_name
    from evaluation.utils import get_evaluation_results_dir

    try:
        task_path, _ = parse_task_name(task_name)
        parts = task_path.split("/")
        if len(parts) >= 2:
            cat_dir, sub = parts[0], parts[1]
        else:
            return False
    except Exception:
        return False

    model_root = os.path.join(
        get_evaluation_results_dir(), cat_dir, sub, model_identifier
    )
    baseline_dir = os.path.join(model_root, "baseline")

    candidates: list[tuple[float, dict, str]] = _load_rollout_candidates_from_dir(
        baseline_dir, exclude_pair=True
    )
    if not candidates:
        candidates = _load_rollout_candidates_from_dir(baseline_dir, exclude_pair=False)
    if not candidates and os.path.isdir(model_root):
        # e.g. only ran expel/rememberer cross-mutation; no plain baseline logs
        for method_name in sorted(os.listdir(model_root)):
            if method_name == "baseline":
                continue
            subdir = os.path.join(model_root, method_name)
            if not os.path.isdir(subdir):
                continue
            more = _load_rollout_candidates_from_dir(subdir, exclude_pair=False)
            candidates.extend(more)
    if not candidates:
        return False
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, best_rep, _ = candidates[0]
    if not best_rep.get("task_prompt"):
        try:
            best_rep["task_prompt"] = load_task_prompt(task_name)
        except Exception:
            best_rep["task_prompt"] = {}
    best_rep["iteration_history"] = (
        best_rep.get("iteration_history") or best_rep.get("history") or []
    )
    data = build_rollout_json_from_report(
        best_rep, task_name, model_identifier, "baseline", context
    )
    out = _rollout_dest_path(model_identifier, task_name)
    if not out:
        return False
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(
        f"[ExpeL] Backfilled rollout for {task_name} from evaluation_results",
        flush=True,
    )
    return True


def run_rollout_one_task(task_name: str, args: Any) -> None:
    """Run baseline TaskEvaluator on task_name; write expel rollout JSON."""
    from evaluation.evaluate import TaskEvaluator
    from evaluation.utils import get_model_identifier, get_max_steps_for_task

    model_id = get_model_identifier(args.model_type, args.model_name)
    max_steps = int(getattr(args, "max_steps", 0) or get_max_steps_for_task(task_name))
    print(
        f"[ExpeL] Running baseline rollout for {task_name} (up to "
        f"{getattr(args, 'max_iterations', 20)} iters)...",
        flush=True,
    )
    ev = TaskEvaluator(
        task_name=task_name,
        model_type=args.model_type,
        model_name=args.model_name,
        api_key=getattr(args, "api_key", None),
        max_iterations=getattr(args, "max_iterations", 20),
        max_steps=max_steps,
        headless=True,
        method="baseline",
        context=getattr(args, "context", "all"),
        model_path=getattr(args, "model_path", None),
        device=getattr(args, "device", None),
        save_gif=False,
    )
    report = ev.evaluate()
    try:
        ev.verifier.cleanup()
    except Exception:
        pass
    report["iteration_history"] = report.get("iteration_history") or report.get(
        "history"
    ) or []
    if not report.get("task_prompt"):
        from evaluation.prompt import load_task_prompt

        report["task_prompt"] = load_task_prompt(task_name)
    data = build_rollout_json_from_report(
        report, task_name, model_id, "baseline", getattr(args, "context", "all")
    )
    out = _rollout_dest_path(model_id, task_name)
    if not out:
        print(f"[ExpeL] Skip rollout save: task {task_name!r} not a category task", flush=True)
        return
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[ExpeL] Saved rollout: {out}", flush=True)
