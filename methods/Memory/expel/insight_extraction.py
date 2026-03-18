"""
ExpeL-style insight extraction for 2D_exploration rollouts (pair JSON or full category).
Uses official ExpeL critique prompts + parse_rules / update_rules (same workflow as baseline ExpeL).
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
_DAVINCI_ROOT = os.path.normpath(os.path.join(_SCRIPTS_DIR, "..", ".."))
_EXPEL_BASE = os.path.join(_DAVINCI_ROOT, "baseline", "Memory", "ExpeL")
if os.path.isdir(_EXPEL_BASE) and _EXPEL_BASE not in sys.path:
    sys.path.insert(0, _EXPEL_BASE)

DEFAULT_MAX_ROUNDS = 3
DEFAULT_MAX_NUM_RULES = 12
DEFAULT_EXPEL_INSIGHT_MODEL = "deepseek-v3.2"


def _fmt_trial(it: dict, max_code: int = 12000, max_fb: int = 8000) -> str:
    code = (it.get("code") or "")[:max_code]
    fb = (it.get("feedback") or "")[:max_fb]
    sc = it.get("score", 0)
    ok = it.get("success", False)
    return f"```python\n{code}\n```\n\n**Evaluator feedback:**\n{fb}\n\n**Score:** {sc}  **Success:** {ok}"


def _expel_chat(
    system: str,
    user: str,
    api_key: Optional[str],
    base_url: Optional[str],
    model: str,
) -> str:
    import openai
    from evaluation.solver_interface import get_aux_llm_credentials

    k, u = get_aux_llm_credentials(api_key)
    if base_url:
        u = base_url
    client = openai.OpenAI(api_key=k, base_url=u)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=4096,
    )
    return (resp.choices[0].message.content or "").strip()


def _rules_to_existing_str(rules: List[Tuple[str, int]]) -> str:
    if not rules:
        return "1. (No rules yet — use only ADD operations to propose new general rules.)"
    return "\n".join(f"{i + 1}. {t}" for i, (t, _) in enumerate(rules))


def _compare_round(
    task_desc: str,
    success_block: str,
    fail_block: str,
    rules: List[Tuple[str, int]],
    max_num_rules: int,
    api_key: Optional[str],
    base_url: Optional[str],
    model: str,
) -> List[Tuple[str, int]]:
    from agent.expel import parse_rules, update_rules
    from prompts import HUMAN_CRITIQUES, SYSTEM_CRITIQUE_INSTRUCTION
    from prompts.templates.human import CRITIQUE_SUMMARY_SUFFIX

    bench = "2d_exploration"
    sys_crit = SYSTEM_CRITIQUE_INSTRUCTION[bench]["compare_existing_rules"]
    system = (
        "You are an advanced reasoning agent that can add, edit or remove rules from your "
        "existing rule set, based on forming new critiques of past task trajectories.\n\n"
        + sys_crit
    )
    existing = _rules_to_existing_str(rules)
    msg = HUMAN_CRITIQUES["compare_existing_rules"].format_messages(
        instruction="",
        task=(task_desc or "Physics / code design task")[:2000],
        success_history=success_block,
        fail_history=fail_block,
        existing_rules=existing,
    )[0]
    suffix = (
        CRITIQUE_SUMMARY_SUFFIX["full"]
        if len(rules) >= max_num_rules
        else CRITIQUE_SUMMARY_SUFFIX["not_full"]
    )
    user = (msg.content or "") + suffix
    raw = _expel_chat(system, user, api_key, base_url, model)
    ops = parse_rules(raw)
    return update_rules(list(rules), ops, list_full=len(rules) >= max_num_rules)


def _all_success_round(
    task_desc: str,
    success_blocks: str,
    rules: List[Tuple[str, int]],
    max_num_rules: int,
    api_key: Optional[str],
    base_url: Optional[str],
    model: str,
) -> List[Tuple[str, int]]:
    from agent.expel import parse_rules, update_rules
    from prompts import HUMAN_CRITIQUES, SYSTEM_CRITIQUE_INSTRUCTION
    from prompts.templates.human import CRITIQUE_SUMMARY_SUFFIX

    bench = "2d_exploration"
    sys_crit = SYSTEM_CRITIQUE_INSTRUCTION[bench]["all_success_existing_rules"]
    system = (
        "You are an advanced reasoning agent that can add, edit or remove rules from your "
        "existing rule set, based on successful past task trajectories.\n\n"
        + sys_crit
    )
    existing = _rules_to_existing_str(rules)
    msg = HUMAN_CRITIQUES["all_success_existing_rules"].format_messages(
        instruction="",
        success_history=success_blocks,
        existing_rules=existing,
    )[0]
    suffix = (
        CRITIQUE_SUMMARY_SUFFIX["full"]
        if len(rules) >= max_num_rules
        else CRITIQUE_SUMMARY_SUFFIX["not_full"]
    )
    user = (msg.content or "") + suffix
    raw = _expel_chat(system, user, api_key, base_url, model)
    ops = parse_rules(raw)
    return update_rules(list(rules), ops, list_full=len(rules) >= max_num_rules)


def _fail_only_round(
    task_desc: str,
    fail_blocks: str,
    rules: List[Tuple[str, int]],
    max_num_rules: int,
    api_key: Optional[str],
    base_url: Optional[str],
    model: str,
) -> List[Tuple[str, int]]:
    """No success trial — distill pitfalls from failures (ExpeL-style ADD rules)."""
    from agent.expel import parse_rules, update_rules

    system = (
        "You analyze failed 2D physics/code design attempts. Propose concise, general rules "
        "(tips) that help avoid similar failures on future tasks. Rules must end with a period. "
        "Use only ADD operations in the specified format."
    )
    existing = _rules_to_existing_str(rules)
    user = f"""Task context (summary):
{(task_desc or '')[:2000]}

FAILED TRIALS:
{fail_blocks}

EXISTING RULES:
{existing}

By examining failures, output operations to improve the rule set. Each new rule must be general (not task-specific IDs). Format:

ADD 1: First rule ending with period.
ADD 2: Second rule ending with period.

You may also use REMOVE, EDIT, AGREE on existing rule numbers when appropriate.
"""
    raw = _expel_chat(system, user, api_key, base_url, model)
    ops = parse_rules(raw)
    return update_rules(list(rules), ops, list_full=len(rules) >= max_num_rules)


def run_pair_insight_extraction(
    pair_json_path: str,
    insights_json_path: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    max_num_rules: int = DEFAULT_MAX_NUM_RULES,
) -> Dict[str, Any]:
    """
    Read one pair rollout JSON (iteration_history), run ExpeL-style critique rounds, write insights JSON.
    """
    model = model or os.environ.get("EXPEL_INSIGHT_MODEL") or DEFAULT_EXPEL_INSIGHT_MODEL
    from evaluation.solver_interface import get_aux_llm_credentials

    if not (get_aux_llm_credentials(api_key)[0] or "").strip():
        payload = {
            "rules": [],
            "error": "no_api_key",
            "hint": "Set OPENAI_API_KEY or SolverInterface.API_KEY to run ExpeL insight extraction.",
            "source": os.path.basename(pair_json_path),
        }
        os.makedirs(os.path.dirname(insights_json_path), exist_ok=True)
        with open(insights_json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return payload

    with open(pair_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    hist: List[dict] = data.get("iteration_history") or []
    task_desc = (data.get("task_prompt") or {}).get("task_description") or ""
    if not hist:
        out = {"rules": [], "note": "empty_iteration_history", "source": os.path.basename(pair_json_path)}
        with open(insights_json_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        return out

    def _score(h: dict) -> float:
        try:
            return float(h.get("score", 0))
        except (TypeError, ValueError):
            return 0.0

    successes = [h for h in hist if h.get("success") or _score(h) >= 70.0]
    failures = [h for h in hist if not (h.get("success") or _score(h) >= 70.0)]

    rules: List[Tuple[str, int]] = []
    rounds_done = 0
    for rnd in range(max_rounds):
        if len(rules) >= max_num_rules and rnd > 0:
            break
        rounds_done += 1
        if successes and failures:
            best = max(successes, key=_score)
            worst = min(failures, key=_score)
            rules = _compare_round(
                task_desc,
                _fmt_trial(best),
                _fmt_trial(worst),
                rules,
                max_num_rules,
                api_key,
                base_url,
                model,
            )
        elif successes:
            blocks = "\n\n---\n\n".join(_fmt_trial(h) for h in successes[:5])
            rules = _all_success_round(
                task_desc, blocks, rules, max_num_rules, api_key, base_url, model
            )
        else:
            blocks = "\n\n---\n\n".join(_fmt_trial(h) for h in failures[:6])
            rules = _fail_only_round(
                task_desc, blocks, rules, max_num_rules, api_key, base_url, model
            )

    rule_strings = [r[0] for r in rules][:max_num_rules]
    out = {
        "rules": rule_strings,
        "source_pair": os.path.basename(pair_json_path),
        "extraction_rounds": rounds_done,
        "max_num_rules": max_num_rules,
    }
    os.makedirs(os.path.dirname(insights_json_path), exist_ok=True)
    with open(insights_json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(
        f"[ExpeL] Wrote {len(rule_strings)} rules to {insights_json_path}",
        flush=True,
    )
    return out


def run_insight_extraction_for_category(
    cat_spec: str,
    model_identifier: str,
    model_type: str,
    model_name: str,
    model_path: Optional[str] = None,
    api_key: Optional[str] = None,
    device: str = "cuda:0",
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    max_num_rules: int = DEFAULT_MAX_NUM_RULES,
    base_url: Optional[str] = None,
    insight_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Aggregate all per-task rollout JSONs under expel/{model}/{cat}/ (exclude *__*.json pair files),
    run multi-round extraction, write insights.json for category-wide retrieval.
    """
    root = os.path.join(_SCRIPT_DIR, model_identifier, cat_spec)
    if not os.path.isdir(root):
        return {"rules": [], "error": "no_category_dir", "path": root}

    rollouts: List[Tuple[str, List[dict], str]] = []
    for name in os.listdir(root):
        if not name.endswith(".json") or ".insights" in name:
            continue
        if re.match(r"^category_\d+_\d+__", name):
            continue
        path = os.path.join(root, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        hist = data.get("iteration_history") or []
        if not hist:
            continue
        td = (data.get("task_prompt") or {}).get("task_description") or ""
        rollouts.append((name.replace(".json", ""), hist, td))

    insights_path = os.path.join(root, "insights.json")
    if not rollouts:
        out = {"rules": [], "note": "no_rollout_jsons", "insights_by_task": {}}
        with open(insights_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        return out

    all_items: List[dict] = []
    for _tn, hist, td in rollouts:
        for it in hist:
            it = dict(it)
            it["_task_name"] = _tn
            it["_task_desc"] = td
            all_items.append(it)

    def _sc(h: dict) -> float:
        try:
            return float(h.get("score", 0))
        except (TypeError, ValueError):
            return 0.0

    successes = [h for h in all_items if h.get("success") or _sc(h) >= 70.0]
    failures = [h for h in all_items if not (h.get("success") or _sc(h) >= 70.0)]

    task_desc = (
        "Aggregated 2D_exploration tasks in category "
        f"{cat_spec}: physics/code design with sandbox API."
    )
    rules: List[Tuple[str, int]] = []
    insight_model = insight_model or os.environ.get("EXPEL_INSIGHT_MODEL") or DEFAULT_EXPEL_INSIGHT_MODEL

    from evaluation.solver_interface import get_aux_llm_credentials

    if not (get_aux_llm_credentials(api_key)[0] or "").strip():
        out = {
            "rules": [],
            "error": "no_api_key",
            "insights_by_task": {},
        }
        with open(insights_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        return out

    for rnd in range(max_rounds):
        if len(rules) >= max_num_rules and rnd > 0:
            break
        if successes and failures:
            import random

            s = random.choice(successes)
            f = random.choice(failures)
            td = (s.get("_task_desc") or f.get("_task_desc") or task_desc)[:2000]
            rules = _compare_round(
                td,
                _fmt_trial(s),
                _fmt_trial(f),
                rules,
                max_num_rules,
                api_key,
                base_url,
                insight_model,
            )
        elif successes:
            import random

            sample = random.sample(successes, min(4, len(successes)))
            blocks = "\n\n---\n\n".join(_fmt_trial(h) for h in sample)
            rules = _all_success_round(
                task_desc, blocks, rules, max_num_rules, api_key, base_url, insight_model
            )
        else:
            sample = failures[:6]
            blocks = "\n\n---\n\n".join(_fmt_trial(h) for h in sample)
            rules = _fail_only_round(
                task_desc, blocks, rules, max_num_rules, api_key, base_url, insight_model
            )

    rule_strings = [r[0] for r in rules][:max_num_rules]
    out = {
        "rules": rule_strings,
        "insights_by_task": {},
        "category": cat_spec,
        "model_identifier": model_identifier,
    }
    with open(insights_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[ExpeL] Category {cat_spec}: wrote {len(rule_strings)} rules to {insights_path}", flush=True)
    return out
