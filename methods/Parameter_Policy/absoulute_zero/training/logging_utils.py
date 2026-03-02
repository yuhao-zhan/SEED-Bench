"""
Training logs: proposed tasks, verify results, rewards (JSONL + summary).
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional


def ensure_log_dir(log_dir: str) -> str:
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def log_proposed_tasks(
    log_dir: str,
    step: int,
    tasks: List[Dict[str, Any]],
    file_prefix: str = "proposed_tasks",
) -> str:
    """Append proposed/used tasks to JSONL. Full prompt recorded (no truncation)."""
    ensure_log_dir(log_dir)
    path = os.path.join(log_dir, f"{file_prefix}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        for t in tasks:
            row = {
                "step": step,
                "task_name": t.get("task_name"),
                "prompt": t.get("prompt_str", ""),          # full prompt, no truncation
                "variation": t.get("variation"),             # proposer variation params
                "source": t.get("source", "fixed"),
                "ts": datetime.now().isoformat(),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def log_verify_results(
    log_dir: str,
    step: int,
    results: List[Dict[str, Any]],
    file_prefix: str = "verify_results",
) -> str:
    """Append verify results to JSONL. Full code recorded (no truncation)."""
    ensure_log_dir(log_dir)
    path = os.path.join(log_dir, f"{file_prefix}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        for r in results:
            row = {
                "step": step,
                "task_name": r.get("task_name"),
                "success": r.get("success"),
                "score": r.get("score"),
                "reward": r.get("reward"),
                "error": r.get("error"),
                "code": r.get("code", ""),                  # full code, no truncation
                "raw_response": r.get("raw_response", ""),  # full model response
                "ts": datetime.now().isoformat(),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def log_rewards_summary(
    log_dir: str,
    step: int,
    mean_reward: float,
    success_rate: float,
    n: int,
    extra: Optional[Dict[str, Any]] = None,
    file_prefix: str = "rewards_summary",
) -> str:
    """Append one line per step to rewards summary JSONL."""
    ensure_log_dir(log_dir)
    path = os.path.join(log_dir, f"{file_prefix}.jsonl")
    row = {
        "step": step,
        "mean_reward": mean_reward,
        "success_rate": success_rate,
        "n": n,
        "ts": datetime.now().isoformat(),
    }
    if extra:
        row.update(extra)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path
