#!/usr/bin/env python3
"""
Resolve a task spec to filesystem paths under tasks/ (same rules as
evaluation.evaluate.resolve_task_list used by run_evaluate_parallel.py).

Examples:
  all
  category_1
  category_1_01
  Category1_Statics_Equilibrium/S_01
  tasks/Category1_Statics_Equilibrium/S_01

Prints one line per task: tasks/<Category...>/<TaskDir> (relative to repo root).
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: resolve_task_dirs.py <task_spec>", file=sys.stderr)
        sys.exit(2)
    spec = sys.argv[1].strip()
    if spec.startswith("tasks/"):
        spec = spec[6:]

    sys.path.insert(0, REPO_ROOT)
    os.chdir(REPO_ROOT)

    from evaluation.utils import get_task_resolver
    resolve_task_list, parse_task_name = get_task_resolver()

    try:
        names = resolve_task_list(spec)
    except Exception as e:
        print(f"resolve_task_list({spec!r}) failed: {e}", file=sys.stderr)
        sys.exit(1)

    for name in names:
        task_path, _ = parse_task_name(name)
        print(os.path.join("tasks", task_path))


if __name__ == "__main__":
    main()
