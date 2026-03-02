"""
2D fitness for GENOME Phase 1: given (task_name, model_path, lora_path), run one-shot 2D evaluation
and return the numerical task score (0-100) for selection/crossover.
"""
import os
import sys

_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


def genome_fitness_2d(
    task_name: str,
    model_path: str,
    lora_path: str,
    device: str = "auto",
    max_steps: int = 10000,
) -> float:
    """
    Run one-shot 2D evaluation: load base + LoRA, generate code for task, verify, return numerical score.
    Returns score in [0, 100] (or 0 on error). Used as fitness in Phase 1.
    """
    from evaluation.prompt import load_task_prompt, format_initial_prompt
    from evaluation.verifier import CodeVerifier
    from methods.Parameter_Policy.genome.genome_solver import get_genome_solver

    try:
        task_prompt = load_task_prompt(task_name)
        prompt = format_initial_prompt(task_prompt)
    except Exception as e:
        return 0.0

    try:
        solver = get_genome_solver(
            model_name=model_path,
            model_path=model_path,
            best_lora_path=lora_path,
            device=device,
        )
        code, _, _ = solver.generate_code(prompt, use_conversation=False, reset_conversation=False)
    except Exception as e:
        return 0.0

    if not code or len(code.strip()) < 50:
        return 0.0

    verifier = None
    try:
        verifier = CodeVerifier(task_name=task_name, max_steps=max_steps)
        success, score, metrics, error_msg = verifier.verify_code(code, headless=True)
        return float(score) if score is not None else (100.0 if success else 0.0)
    except Exception as e:
        return 0.0
    finally:
        if verifier is not None:
            verifier.cleanup()
