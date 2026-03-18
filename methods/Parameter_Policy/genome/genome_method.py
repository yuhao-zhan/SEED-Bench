"""
GENOME method for 2D_exploration: Phase 1 (GA to select best LoRA) + Phase 2 (refinement with best LoRA).
Phase 1 uses GENOME raw repo GA with 2D fitness; Phase 2 uses GenomeSolver with best LoRA.
"""
import os
import sys
import json

_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_GENOME_ROOT = os.path.normpath(os.path.join(_SCRIPTS_DIR, "..", "..", "baseline", "Parameter_Policy", "GENOME"))

if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
if _GENOME_ROOT not in sys.path:
    sys.path.insert(0, _GENOME_ROOT)


def _run_genome_phase1_2d(
    task_name: str,
    model_path: str,
    lora_dir: str,
    device: str = "auto",
    max_steps: int = 10000,
    population_size: int = 10,
    max_iter: int = 50,
    seed: int = 42,
    cross_rate: float = 0.8,
    individual_mutation_rate: float = 0.15,
    gene_mutation_rate: float = 0.01,
    sigma: float = 0.01,
    elite_percent: float = 0.02,
    combine_method: str = "ties",
    cross_method: str = "ties",
    workspace_prefix: str = None,
) -> str:
    """
    Run GENOME GA with 2D fitness for a single task. Returns best LoRA path (directory).
    Uses GENOME raw repo for init, crossover, mutation, selection; replaces evaluate with genome_fitness_2d.

    Alignment with official GENOME (baseline/Parameter_Policy/GENOME):
    - Genome, GenomeConfig, Individual, get_lora_pools are imported from official repo; no reimplementation.
    - max_valid_samples=1 is intentional: 2D fitness is one rollout per individual (official uses max_valid_samples for per-task sample count).
    - We match official behavior: selection in each _step uses "tournament" (official Genome._step hardcodes it). config.method is used only for crossover parent selection. No change to the official repo; this reimplementation inherits that behavior.
    """
    from src.utils import get_lora_pools
    from src.genome import Genome, GenomeConfig, Individual
    from methods.Parameter_Policy.genome.genome_fitness import genome_fitness_2d

    # Dummy llm_base_url (not used when we override evaluate)
    dummy_ports = [18177, 36048]
    llm_base_url = [f"http://localhost:{p}/v1" for p in dummy_ports]
    pools = get_lora_pools(lora_dir)
    if len(pools) < 2:
        raise ValueError(
            f"lora_dir must have at least 2 expert subdirs (got {len(pools)}). "
            "See methods/Parameter_Policy/genome/README.md and run bootstrap_lora_dir.py in that directory."
        )

    config = GenomeConfig(
        tasks=[task_name],
        test_tasks=[task_name],
        task_weights=[1.0],
        model_name_or_path=model_path,
        N=population_size,
        max_iter=max_iter,
        llm_base_url=llm_base_url,
        pools=pools,
        combine_method=combine_method,
        cross_method=cross_method,
        plot_enabled=False,
        early_stop=False,
        early_stop_iter=5,
        seed=seed,
        method="roulette",
        workspace_prefix=workspace_prefix,
        max_valid_samples=1,  # 2D: one rollout per individual; official default 200 is for multi-sample benchmarks
        cross_rate=cross_rate,
        individual_mutation_rate=individual_mutation_rate,
        gene_mutation_rate=gene_mutation_rate,
        sigma=sigma,
        elite_percent=elite_percent,
    )

    class Genome2D(Genome):
        def evaluate(self, individuals, split="valid", max_valid_samples=None):
            from loguru import logger
            task_scores = {}
            for ind in individuals:
                score = genome_fitness_2d(
                    task_name=self.tasks[0],
                    model_path=self.model_name_or_path,
                    lora_path=ind.weight_path,
                    device=device,
                    max_steps=max_steps,
                )
                task_scores[ind.id] = {"score": score, "path": ind.weight_path}
                ind.task_scores = {self.tasks[0]: score}
                ind.fitness_score = score
                ind.evaluated = {self.tasks[0]: True}
                logger.info(f"Individual {ind.id} fitness (2D): {score:.4f}")
            weighted_scores = {
                iid: {"weighted_score": data["score"], "task_scores": {task_name: data["score"]}, "path": data["path"]}
                for iid, data in task_scores.items()
            }
            for ind in individuals:
                ind.update_fitness(tasks=self.tasks, task_weights=self.task_weights)
            return weighted_scores

        def ensemble_test(self, individuals, split="test"):
            # Skip vLLM test; we only need best LoRA path from validation
            pass

    genome = Genome2D(config=config)
    genome.search()
    best_path = genome.global_max_fitness_path
    return best_path


def _write_genome_phase1_training_log(
    training_log_dir: str,
    task_name: str,
    model_path: str,
    best_lora_path: str,
    population_size: int,
    genome_iters: int,
    seed: int,
    max_steps: int,
) -> None:
    """Write training_config.json and training_summary.txt for GENOME Phase 1 run."""
    os.makedirs(training_log_dir, exist_ok=True)
    config = {
        "method": "genome",
        "phase": "phase1",
        "task_name": task_name,
        "model_path": model_path,
        "best_lora_path": best_lora_path,
        "population_size": population_size,
        "genome_iters": genome_iters,
        "seed": seed,
        "max_steps": max_steps,
    }
    config_path = os.path.join(training_log_dir, "training_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    lines = [
        "Method: genome (Phase 1 GA)",
        f"Task: {task_name}",
        f"Best LoRA path: {best_lora_path}",
        f"Population size: {population_size}",
        f"Max iter: {genome_iters}",
    ]
    summary_path = os.path.join(training_log_dir, "training_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run_genome_phase1(
    task_name: str,
    model_path: str,
    lora_dir: str,
    cache_path: str = None,
    device: str = "auto",
    max_steps: int = 10000,
    population_size: int = 10,
    genome_iters: int = 50,
    seed: int = 42,
    training_log_dir: str = None,  # optional: scripts/training_log/.../genome/
    **kwargs,
) -> str:
    """
    Run Phase 1 (GENOME GA) for this task; cache best LoRA path to cache_path if provided.
    Returns best LoRA path (directory).
    """
    if cache_path and os.path.isfile(cache_path):
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
            return data.get("best_lora_path", "")
        except Exception:
            pass
    workspace_prefix = os.path.abspath(os.path.dirname(cache_path)) if cache_path else None
    best_lora_path = _run_genome_phase1_2d(
        task_name=task_name,
        model_path=model_path,
        lora_dir=lora_dir,
        device=device,
        max_steps=max_steps,
        population_size=population_size,
        max_iter=genome_iters,
        seed=seed,
        workspace_prefix=workspace_prefix,
        **kwargs,
    )
    if training_log_dir:
        _write_genome_phase1_training_log(
            training_log_dir, task_name, model_path, best_lora_path or "",
            population_size, genome_iters, seed, max_steps,
        )
    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump({"best_lora_path": best_lora_path}, f, indent=2)
    return best_lora_path


def get_genome_solver(model_name: str, model_path: str = None, best_lora_path: str = None, device: str = None):
    """Return VLLMGenomeSolver for Phase 2 (used by evaluate.py)."""
    from methods.Parameter_Policy.genome.genome_solver import get_vllm_genome_solver
    return get_vllm_genome_solver(model_name=model_name, model_path=model_path, best_lora_path=best_lora_path, device=device)
