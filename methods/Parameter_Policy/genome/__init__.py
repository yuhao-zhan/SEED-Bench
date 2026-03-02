# GENOME method for 2D_exploration: Phase 1 (GA to select best LoRA) + Phase 2 (refinement with best LoRA).
# Paths are stored under genome/ with layout: experts/, {task}/{model}/best_lora_path.json, {task}/{model}/Genome_workspace/...
import os

_GENOME_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_genome_experts_dir() -> str:
    """Default LoRA pool: genome/experts/ (code_alpaca, gpt4_alpaca, ...). Run bootstrap_lora_dir.py to create."""
    return os.path.join(_GENOME_PACKAGE_DIR, "experts")


def get_genome_task_model_dir(task_name: str, model_identifier: str) -> str:
    """Per-task-per-model dir: genome/{task}/{model}/ for cache and workspace."""
    return os.path.join(_GENOME_PACKAGE_DIR, task_name, model_identifier)


def get_genome_cache_path(task_name: str, model_identifier: str) -> str:
    """Phase 1 cache: genome/{task}/{model}/best_lora_path.json"""
    return os.path.join(get_genome_task_model_dir(task_name, model_identifier), "best_lora_path.json")
