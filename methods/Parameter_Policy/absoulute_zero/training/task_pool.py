"""
2D task pool for AZR-style training: load existing tasks and build prompts (propose = fixed 2D tasks).
"""
import os
import sys
import random
from typing import List, Tuple, Dict, Any

# This file is at methods/Parameter_Policy/absoulute_zero/training/task_pool.py
# Need scripts/ on path for evaluation.prompt imports
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, _SCRIPTS_DIR)

from evaluation.prompt import (
    get_all_tasks,
    get_all_tasks_in_category,
    load_task_prompt,
    format_initial_prompt,
)


def build_task_pool(
    task_spec: str,
    shuffle: bool = True,
    seed: int = 42,
) -> List[Tuple[str, Dict[str, Any], str]]:
    """
    Build list of (task_name, task_prompt_dict, prompt_str) for training.
    task_spec: 'all' | 'category_1' | 'category_1,2' | 'category_1_01,category_1_02'
    """
    if task_spec.strip().lower() == "all":
        task_names = get_all_tasks()
    elif task_spec.strip().lower().startswith("category_"):
        part = task_spec.strip().split("_", 1)[1]  # e.g. "1" or "1,2" or "1_01,category_1_02"
        if "," in part and not part.replace(",", "").replace("_", "").isdigit():
            # e.g. category_1_01,category_1_02
            task_names = [t.strip() for t in task_spec.split(",")]
        else:
            # e.g. category_1 or category_1,2
            cats = [int(x.strip()) for x in part.replace(" ", "").split(",")]
            task_names = []
            for c in cats:
                task_names.extend(get_all_tasks_in_category(c))
    else:
        task_names = [t.strip() for t in task_spec.split(",") if t.strip()]

    pool = []
    for task_name in task_names:
        try:
            task_prompt = load_task_prompt(task_name)
            prompt_str = format_initial_prompt(task_prompt)
            pool.append((task_name, task_prompt, prompt_str))
        except Exception as e:
            print(f"⚠️  Skip task {task_name}: {e}")
            continue

    if shuffle:
        random.seed(seed)
        random.shuffle(pool)
    return pool
