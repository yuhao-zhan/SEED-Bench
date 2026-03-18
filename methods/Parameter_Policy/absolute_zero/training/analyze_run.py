#!/usr/bin/env python3
"""
Analyse an AZR training run directory.

Usage:
    python analyze_run.py <run_dir>
    python analyze_run.py runs/Qwen3-8B_all_20260213_153417

Reads:
  - rewards_summary.jsonl  (per-step aggregates)
  - verify_results.jsonl   (per-sample details)
  - proposed_tasks.jsonl   (task diversity)

Prints:
  - Reward curve summary (mean, min, max per window)
  - Success rate over time
  - Error type distribution
  - Task name diversity
  - Code quality (% with build_agent, avg length)
"""
import os
import sys
import json
import argparse
from collections import Counter, defaultdict
from typing import List, Dict, Any


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def analyse_rewards(rows: List[Dict]) -> None:
    if not rows:
        print("  (no data)")
        return
    steps = sorted(set(r["step"] for r in rows))
    rewards = [r["mean_reward"] for r in rows]
    successes = [r["success_rate"] for r in rows]

    print(f"  Steps: {min(steps)} -> {max(steps)} ({len(steps)} steps)")
    print(f"  Mean reward: {sum(rewards)/len(rewards):.4f}  "
          f"(min={min(rewards):.4f}, max={max(rewards):.4f})")
    print(f"  Mean success rate: {sum(successes)/len(successes):.2%}")

    # Windowed progression
    window = max(1, len(steps) // 5)
    print(f"\n  Progression (window={window}):")
    for i in range(0, len(steps), window):
        chunk = rows[i:i+window]
        avg_r = sum(r["mean_reward"] for r in chunk) / len(chunk)
        avg_s = sum(r["success_rate"] for r in chunk) / len(chunk)
        losses = [r.get("loss", 0) for r in chunk if "loss" in r]
        avg_l = sum(losses) / len(losses) if losses else float("nan")
        print(f"    Steps {chunk[0]['step']:>4}-{chunk[-1]['step']:>4}: "
              f"reward={avg_r:+.4f}  success={avg_s:.2%}  loss={avg_l:.4f}")


def analyse_verify(rows: List[Dict]) -> None:
    if not rows:
        print("  (no data)")
        return
    total = len(rows)
    successes = sum(1 for r in rows if r.get("success"))
    print(f"  Total samples: {total}")
    print(f"  Successes: {successes} ({successes/total:.2%})")

    # Error distribution
    error_types = Counter()
    for r in rows:
        err = r.get("error") or ""
        if not err:
            if r.get("success"):
                error_types["success"] += 1
            else:
                error_types["unknown_failure"] += 1
        else:
            # Categorise
            el = err.lower()
            if "format_error" in el or "missing build_agent" in el:
                error_types["format_error"] += 1
            elif "syntax" in el:
                error_types["syntax_error"] += 1
            elif "runtime" in el or "exception" in el or "traceback" in el:
                error_types["runtime_error"] += 1
            elif "timeout" in el:
                error_types["timeout"] += 1
            else:
                error_types[f"other: {err[:60]}"] += 1

    print("\n  Error distribution:")
    for etype, count in error_types.most_common(15):
        print(f"    {etype:40s}  {count:>5d}  ({count/total:.1%})")

    # Reward distribution
    reward_vals = [r.get("reward", 0) for r in rows]
    bins = Counter()
    for rv in reward_vals:
        if rv <= -0.9:
            bins["[-1.0]"] += 1
        elif rv <= -0.7:
            bins["[-0.8]"] += 1
        elif rv <= -0.4:
            bins["[-0.5]"] += 1
        elif rv <= -0.2:
            bins["[-0.3]"] += 1
        elif rv <= 0.0:
            bins["[0.0]"] += 1
        elif rv < 0.5:
            bins["(0,0.5)"] += 1
        elif rv < 1.0:
            bins["[0.5,1)"] += 1
        else:
            bins["[1.0]"] += 1

    print("\n  Reward distribution:")
    for bucket in ["[-1.0]", "[-0.8]", "[-0.5]", "[-0.3]", "[0.0]", "(0,0.5)", "[0.5,1)", "[1.0]"]:
        c = bins.get(bucket, 0)
        bar = "#" * int(40 * c / total) if total > 0 else ""
        print(f"    {bucket:>10s}  {c:>5d}  ({c/total:.1%})  {bar}")

    # Code quality
    codes = [r.get("code", "") for r in rows]
    has_build = sum(1 for c in codes if "def build_agent" in c)
    has_action = sum(1 for c in codes if "def agent_action" in c)
    avg_len = sum(len(c) for c in codes) / len(codes) if codes else 0
    print(f"\n  Code quality:")
    print(f"    Has build_agent: {has_build}/{total} ({has_build/total:.1%})")
    print(f"    Has agent_action: {has_action}/{total} ({has_action/total:.1%})")
    print(f"    Avg code length: {avg_len:.0f} chars")


def analyse_tasks(rows: List[Dict]) -> None:
    if not rows:
        print("  (no data)")
        return
    names = Counter(r.get("task_name", "unknown") for r in rows)
    sources = Counter(r.get("source", "unknown") for r in rows)
    print(f"  Total task instances: {len(rows)}")
    print(f"  Unique task names: {len(names)}")
    print(f"  Sources: {dict(sources)}")
    print(f"\n  Top 10 task names:")
    for name, count in names.most_common(10):
        print(f"    {name:50s}  {count:>4d}")


def main():
    parser = argparse.ArgumentParser(description="Analyse AZR training run")
    parser.add_argument("run_dir", help="Path to run directory")
    args = parser.parse_args()

    run_dir = args.run_dir
    if not os.path.isdir(run_dir):
        print(f"ERROR: {run_dir} is not a directory")
        return 1

    print(f"=== Analysing: {run_dir} ===\n")

    # 1. Rewards summary
    print("--- Rewards Summary ---")
    rewards = load_jsonl(os.path.join(run_dir, "rewards_summary.jsonl"))
    analyse_rewards(rewards)
    print()

    # 2. Verify results
    print("--- Verification Results ---")
    verify = load_jsonl(os.path.join(run_dir, "verify_results.jsonl"))
    analyse_verify(verify)
    print()

    # 3. Task diversity
    print("--- Task Diversity ---")
    tasks = load_jsonl(os.path.join(run_dir, "proposed_tasks.jsonl"))
    analyse_tasks(tasks)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
