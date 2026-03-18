#!/usr/bin/env python3
"""
From-Scratch evaluation module.

Evaluates a **single task** in a **fixed environment** (per env: Initial or Stage-1..4):
no reference solution, no cross-env mutation. The agent receives the task description,
demonstrations, and requirements (with current env's physical quantities substituted
into the prompt) and solves the tool-creation task from scratch. Results are saved
as task name + env (e.g. context_Initial.json, context_Stage-1.json).
"""
import os
import sys
import re
import argparse
import importlib.util
import traceback
from typing import Dict, Any, Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.evaluate import TaskEvaluator, resolve_task_list
from evaluation.prompt import load_task_prompt, parse_task_name
from evaluation.utils import (
    get_max_steps_for_task,
    run_is_complete,
)


def _args_to_evaluator_kwargs(args) -> Dict[str, Any]:
    """Build optional TaskEvaluator kwargs from parsed args (method-specific, device, etc.)."""
    out: Dict[str, Any] = {}
    if getattr(args, "model_path", None) is not None:
        out["model_path"] = args.model_path
    if getattr(args, "device", None) is not None:
        out["device"] = args.device
    for key in (
        "reflect_model_name", "textgrad_engine_name", "a_mem_sys_llm_model",
        "ace_reflector_model", "ace_curator_model",
        "n_select_sample", "n_generate_sample", "reasoning_bank_k",
        "ragen_n_rollouts", "ragen_ppo_epochs",
        "soar_generations", "soar_k_candidates",
        "discover_num_epochs", "discover_group_size", "discover_groups_per_batch",
        "discover_learning_rate", "discover_adv_estimator", "discover_adv_estimator_beta",
        "discover_loss_fn", "discover_lora_rank", "discover_max_tokens",
        "discover_temperature", "discover_num_substeps", "discover_max_expansion_rounds",
        "genome_best_lora_path",
        "theta_evolve_num_rollout", "theta_evolve_rollout_batch_size",
        "genome_iters", "genome_population_size",
        "expel_max_rounds", "expel_max_num_rules",
    ):
        if hasattr(args, key) and getattr(args, key, None) is not None:
            out[key] = getattr(args, key)
    return out


def strip_originally_suffix(text: str) -> str:
    """
    Remove all '(originally ... in the source environment)' fragments from
    the string, so only the current env's values remain (replace-only format).
    """
    if not text:
        return text
    # Match " (originally ... in the source environment)." or " (originally ... in the source environment))"
    # Use negative lookahead so "..." can contain ")" e.g. "centered at (10.0, 1.0)"
    pattern = re.compile(
        r"\s*\(originally\s+(?:(?!\s+in the source environment\)).)*\s+in the source environment\)\.?\)?",
        re.IGNORECASE | re.DOTALL,
    )
    out = pattern.sub("", text)
    # Clean up leftover " ." or " )." -> "."
    out = re.sub(r"\s+\.(\s|$)", r".\1", out)
    out = re.sub(r"\s+\)\.(\s|$)", r").\1", out)
    return out.strip()


def get_task_prompt_override_for_stage(
    task_name: str,
    stage_dict: Dict[str, Any],
    all_envs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build task_prompt (description + success_criteria) for a single stage env.
    Uses the task's update_task_description_for_visible_changes and
    update_success_criteria_for_visible_changes, then strips 'originally...'
    so the prompt contains only the current env's physical values.
    No task_description_suffix (no mutation-awareness text).
    """
    base_prompt = load_task_prompt(task_name)
    task_prompt_override = dict(base_prompt)
    desc = base_prompt.get("task_description", "")
    criteria = base_prompt.get("success_criteria", "")

    initial = all_envs[0] if all_envs else {}
    base_terrain = initial.get("terrain_config", {})
    base_physics = initial.get("physics_config", {})
    target_terrain = stage_dict.get("terrain_config", {})
    target_physics = stage_dict.get("physics_config", {})

    task_path, _ = parse_task_name(task_name)
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    task_dir = os.path.join(script_dir, "tasks", task_path)
    stages_file = os.path.join(task_dir, "stages.py")

    if os.path.exists(stages_file):
        try:
            spec = importlib.util.spec_from_file_location("task_stages", stages_file)
            stages_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(stages_mod)

            update_desc_func = None
            update_criteria_func = None
            for name in dir(stages_mod):
                if "update_task_description_for_visible_changes" in name and callable(getattr(stages_mod, name)):
                    update_desc_func = getattr(stages_mod, name)
                if "update_success_criteria_for_visible_changes" in name and callable(getattr(stages_mod, name)):
                    update_criteria_func = getattr(stages_mod, name)

            if update_desc_func:
                try:
                    import inspect
                    sig = inspect.signature(update_desc_func)
                    if len(sig.parameters) >= 5:
                        desc = update_desc_func(desc, target_terrain, base_terrain, target_physics, base_physics)
                    else:
                        desc = update_desc_func(desc, target_terrain, base_terrain)
                except Exception:
                    desc = update_desc_func(desc, target_terrain, base_terrain)
                desc = strip_originally_suffix(desc)

            if update_criteria_func:
                try:
                    import inspect
                    sig = inspect.signature(update_criteria_func)
                    if len(sig.parameters) >= 5:
                        criteria = update_criteria_func(criteria, target_terrain, base_terrain, target_physics, base_physics)
                    else:
                        criteria = update_criteria_func(criteria, target_terrain, base_terrain)
                except Exception:
                    criteria = update_criteria_func(criteria, target_terrain, base_terrain)
                criteria = strip_originally_suffix(criteria)
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"Failed to build prompt override for {task_name} stage {stage_dict.get('stage_id')}: {e}")

    task_prompt_override["task_description"] = desc
    task_prompt_override["success_criteria"] = criteria
    return task_prompt_override


def run_from_scratch_evaluation(
    task_name: str,
    model_type: str = "mock",
    model_name: str = "gpt-4",
    api_key: Optional[str] = None,
    max_iterations: int = 10,
    max_steps: Optional[int] = None,
    headless: bool = True,
    method: str = "baseline",
    context: str = "previous",
    save_gif: bool = False,
    output_dir: str = "evaluation_results_scratch",
    stage_id: Optional[str] = None,
    env_overrides: Optional[Dict[str, Any]] = None,
    task_prompt_override: Optional[Dict[str, Any]] = None,
    **extra_evaluator_kwargs: Any,
) -> Dict[str, Any]:
    """
    Run from-scratch evaluation for a single task (optionally for one stage env).

    - When stage_id/env_overrides/task_prompt_override are provided: run in that
      fixed env with prompt containing only that env's physical values; save as
      context_{stage_id}.json (e.g. previous_Initial.json, all_Stage-1.json).
    - When not provided: run in default task env, save as context_raw.json.
    - No reference solution: format_initial_prompt then format_revision_prompt
      with feedback (same as backup evaluate.py; context 'all' = previous + all).
    - extra_evaluator_kwargs: passed to TaskEvaluator (e.g. model_path, device,
      reflect_model_name, n_select_sample, ...).
    """
    if max_steps is None:
        max_steps = get_max_steps_for_task(task_name)

    is_stage_run = stage_id is not None and (env_overrides is not None or task_prompt_override is not None)

    evaluator = TaskEvaluator(
        task_name=task_name,
        model_type=model_type,
        model_name=model_name,
        api_key=api_key,
        max_iterations=max_iterations,
        max_steps=max_steps,
        headless=headless,
        method=method,
        context=context,
        env_overrides=env_overrides or {},
        task_prompt_override=task_prompt_override,
        is_mutated_task=is_stage_run,
        save_gif=save_gif,
        output_dir=output_dir,
        **extra_evaluator_kwargs,
    )
    if is_stage_run and stage_id:
        evaluator.mutated_task_name = stage_id

    report = evaluator.evaluate()
    evaluator.verifier.cleanup()
    evaluator.print_report(report)
    evaluator.save_report(report, output_dir=output_dir)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="From-scratch evaluation: single task per env, fixed environment, no reference solution."
    )
    parser.add_argument(
        "--task",
        type=str,
        nargs="+",
        default=["basic"],
        help="Task(s) to evaluate. Single spec: category_X_YY, category_X, or 'all'. Multiple: explicit task names. "
             "Without --stage-id: each task runs all 5 envs (Initial + Stage-1..4) and saves one JSON per env.",
    )
    parser.add_argument(
        "--stage-id",
        type=str,
        default=None,
        help="When set, run only this env for the given task (e.g. Initial, Stage-1). When NOT set, run all 5 envs per task.",
    )
    parser.add_argument("--model-type", type=str, default="mock", choices=["openai", "local", "mock"])
    parser.add_argument("--model-name", type=str, default="deepseek-v3.2")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--max-steps", type=int, default=None, help="Override per-task default (default: use task-specific)")
    parser.add_argument("--method", type=str, default="baseline")
    parser.add_argument(
        "--context",
        type=str,
        default="all",
        choices=["previous", "all", "last_3", "best_score", "best_score_plus_previous"],
    )
    parser.add_argument("--output-dir", type=str, default="evaluation_results_scratch")
    # Method-specific (same as run_evaluate_parallel; forward to TaskEvaluator)
    parser.add_argument("--reflect-model-name", type=str, default=None)
    parser.add_argument("--textgrad-engine-name", type=str, default=None)
    parser.add_argument("--a-mem-llm-model", type=str, default=None, dest="a_mem_sys_llm_model")
    parser.add_argument("--ace-reflector-model", type=str, default=None, dest="ace_reflector_model")
    parser.add_argument("--ace-curator-model", type=str, default=None, dest="ace_curator_model")
    parser.add_argument("--n-select-sample", type=int, default=None, dest="n_select_sample")
    parser.add_argument("--n-generate-sample", type=int, default=None, dest="n_generate_sample")
    parser.add_argument("--reasoning-bank-k", type=int, default=None, dest="reasoning_bank_k")
    parser.add_argument("--ragen-n-rollouts", type=int, default=None, dest="ragen_n_rollouts")
    parser.add_argument("--ragen-ppo-epochs", type=int, default=None, dest="ragen_ppo_epochs")
    parser.add_argument("--soar-generations", type=int, default=None, dest="soar_generations")
    parser.add_argument("--soar-k-candidates", type=int, default=None, dest="soar_k_candidates")
    parser.add_argument("--discover-num-epochs", type=int, default=None, dest="discover_num_epochs")
    parser.add_argument("--discover-group-size", type=int, default=None, dest="discover_group_size")
    parser.add_argument("--discover-groups-per-batch", type=int, default=None, dest="discover_groups_per_batch")
    parser.add_argument("--discover-learning-rate", type=float, default=None, dest="discover_learning_rate")
    parser.add_argument("--discover-adv-estimator", type=str, default=None, dest="discover_adv_estimator")
    parser.add_argument("--discover-adv-estimator-beta", type=float, default=None, dest="discover_adv_estimator_beta")
    parser.add_argument("--discover-loss-fn", type=str, default=None, dest="discover_loss_fn")
    parser.add_argument("--discover-lora-rank", type=int, default=None, dest="discover_lora_rank")
    parser.add_argument("--discover-max-tokens", type=int, default=None, dest="discover_max_tokens")
    parser.add_argument("--discover-temperature", type=float, default=None, dest="discover_temperature")
    parser.add_argument("--discover-num-substeps", type=int, default=None, dest="discover_num_substeps")
    parser.add_argument("--discover-max-expansion-rounds", type=int, default=None, dest="discover_max_expansion_rounds")
    parser.add_argument("--genome-iters", type=int, default=None, dest="genome_iters")
    parser.add_argument("--genome-population-size", type=int, default=None, dest="genome_population_size")
    parser.add_argument("--genome-best-lora-path", type=str, default=None, dest="genome_best_lora_path")
    parser.add_argument("--theta-evolve-num-rollout", type=int, default=10000, dest="theta_evolve_num_rollout",
                        help="ThetaEvolve: number of rollout steps (official default 10000).")
    parser.add_argument("--theta-evolve-rollout-batch-size", type=int, default=32, dest="theta_evolve_rollout_batch_size")
    parser.add_argument("--expel-max-rounds", type=int, default=None, dest="expel_max_rounds")
    parser.add_argument("--expel-max-num-rules", type=int, default=None, dest="expel_max_num_rules")
    parser.add_argument("--save-gif", action="store_true", default=False, help="From-scratch defaults to no GIF; use this to enable.")
    parser.add_argument("--no-save-gif", action="store_false", dest="save_gif")
    parser.add_argument("--skip-complete", action="store_true", default=True, help="Skip (task, stage) that already have a result JSON")
    parser.add_argument("--no-skip-complete", action="store_false", dest="skip_complete")

    args = parser.parse_args()

    # Single (task, stage_id) run: used by parallel runner
    if args.stage_id is not None:
        if len(args.task) != 1:
            print("When --stage-id is set, exactly one --task must be given.")
            return 1
        task_name = args.task[0]
        stage_id = args.stage_id
        from evaluation.evaluate_cross_mutated import get_all_stages

        all_envs = get_all_stages(task_name)
        stage_dict = next((e for e in all_envs if e.get("stage_id") == stage_id), None)
        if not stage_dict:
            print(f"Unknown stage_id: {stage_id} for task {task_name}")
            return 1
        if args.skip_complete and run_is_complete(
            task_name=task_name,
            model_type=args.model_type,
            model_name=args.model_name,
            method=args.method,
            context=args.context,
            mutated_task_name=stage_id,
            results_base_dir=args.output_dir,
        ):
            print(f"Already complete: {task_name} {stage_id}. Skipping.")
            return 0
        env_overrides = {
            "terrain_config": stage_dict.get("terrain_config", {}),
            "physics_config": stage_dict.get("physics_config", {}),
        }
        task_prompt_override = get_task_prompt_override_for_stage(task_name, stage_dict, all_envs)
        extra = _args_to_evaluator_kwargs(args)
        # GENOME: ensure Phase 1 cache exists (run GA if missing), then pass best LoRA path
        if args.method == "genome" and not getattr(args, "genome_best_lora_path", None):
            from evaluation.utils import get_model_identifier, get_training_log_dir
            from methods.Parameter_Policy.genome import get_genome_experts_dir, get_genome_cache_path
            from methods.Parameter_Policy.genome.genome_method import run_genome_phase1
            model_identifier = get_model_identifier(args.model_type, args.model_name)
            lora_dir = get_genome_experts_dir()
            cache_path = get_genome_cache_path(task_name, model_identifier)
            training_log_dir = get_training_log_dir(task_name, model_identifier, "genome")
            best_lora = run_genome_phase1(
                task_name=task_name,
                model_path=args.model_path or args.model_name,
                lora_dir=lora_dir,
                cache_path=cache_path,
                device=args.device,
                max_steps=get_max_steps_for_task(task_name),
                population_size=getattr(args, "genome_population_size", 10),
                genome_iters=getattr(args, "genome_iters", 50),
                training_log_dir=training_log_dir,
            )
            if best_lora:
                extra["genome_best_lora_path"] = best_lora
        run_from_scratch_evaluation(
            task_name=task_name,
            model_type=args.model_type,
            model_name=args.model_name,
            api_key=args.api_key,
            max_iterations=args.max_iterations,
            max_steps=args.max_steps,
            headless=True,
            method=args.method,
            context=args.context,
            save_gif=args.save_gif,
            output_dir=args.output_dir,
            stage_id=stage_id,
            env_overrides=env_overrides,
            task_prompt_override=task_prompt_override,
            **extra,
        )
        return 0

    # Multi-task / multi-env: resolve task list and run each (task, stage) once
    if len(args.task) == 1:
        task_list = resolve_task_list(args.task[0])
    else:
        task_list = list(args.task)

    if not task_list:
        print(f"No tasks found for specification: {args.task}")
        return 1

    from evaluation.evaluate_cross_mutated import get_all_stages

    work_items: List[tuple] = []
    for task_name in task_list:
        all_envs = get_all_stages(task_name)
        for env in all_envs:
            work_items.append((task_name, env.get("stage_id", "Initial")))

    print(f"\nFrom-Scratch Evaluation: {len(work_items)} (task, env) runs, fixed env per run, no reference solution.\n")
    results: List[tuple] = []

    for task_name, stage_id in work_items:
        print(f"\n{'='*80}")
        print(f"Task: {task_name}  Env: {stage_id}")
        print(f"{'='*80}\n")

        if args.skip_complete and run_is_complete(
            task_name=task_name,
            model_type=args.model_type,
            model_name=args.model_name,
            method=args.method,
            context=args.context,
            mutated_task_name=stage_id,
            results_base_dir=args.output_dir,
        ):
            print(f"Already complete. Skipping (use --no-skip-complete to re-run).\n")
            results.append((f"{task_name}/{stage_id}", 0))
            continue

        all_envs = get_all_stages(task_name)
        stage_dict = next((e for e in all_envs if e.get("stage_id") == stage_id), None)
        if not stage_dict:
            results.append((f"{task_name}/{stage_id}", 1))
            continue
        env_overrides = {
            "terrain_config": stage_dict.get("terrain_config", {}),
            "physics_config": stage_dict.get("physics_config", {}),
        }
        task_prompt_override = get_task_prompt_override_for_stage(task_name, stage_dict, all_envs)
        extra = _args_to_evaluator_kwargs(args)
        # GENOME: ensure Phase 1 cache exists (run GA if missing), then pass best LoRA path
        if args.method == "genome" and not getattr(args, "genome_best_lora_path", None):
            from evaluation.utils import get_model_identifier, get_training_log_dir
            from methods.Parameter_Policy.genome import get_genome_experts_dir, get_genome_cache_path
            from methods.Parameter_Policy.genome.genome_method import run_genome_phase1
            model_identifier = get_model_identifier(args.model_type, args.model_name)
            lora_dir = get_genome_experts_dir()
            cache_path = get_genome_cache_path(task_name, model_identifier)
            training_log_dir = get_training_log_dir(task_name, model_identifier, "genome")
            best_lora = run_genome_phase1(
                task_name=task_name,
                model_path=args.model_path or args.model_name,
                lora_dir=lora_dir,
                cache_path=cache_path,
                device=args.device,
                max_steps=get_max_steps_for_task(task_name),
                population_size=getattr(args, "genome_population_size", 10),
                genome_iters=getattr(args, "genome_iters", 50),
                training_log_dir=training_log_dir,
            )
            if best_lora:
                extra["genome_best_lora_path"] = best_lora
        try:
            run_from_scratch_evaluation(
                task_name=task_name,
                model_type=args.model_type,
                model_name=args.model_name,
                api_key=args.api_key,
                max_iterations=args.max_iterations,
                max_steps=args.max_steps,
                headless=True,
                method=args.method,
                context=args.context,
                save_gif=args.save_gif,
                output_dir=args.output_dir,
                stage_id=stage_id,
                env_overrides=env_overrides,
                task_prompt_override=task_prompt_override,
                **extra,
            )
            results.append((f"{task_name}/{stage_id}", 0))
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            sys.exit(1)
        except Exception as e:
            err_msg = str(e).lower()
            fatal = any(
                k in err_msg
                for k in [
                    "insufficient quota",
                    "rate limit",
                    "authentication failed",
                    "429",
                    "insufficient_quota",
                    "too many requests",
                ]
            )
            if fatal:
                print(f"\nFATAL API ERROR: {e}")
                sys.exit(99)
            print(f"Evaluation failed for {task_name} {stage_id}: {e}")
            traceback.print_exc()
            results.append((f"{task_name}/{stage_id}", 1))

    completed = sum(1 for _, code in results if code == 0)
    total = len(results)
    print(f"\n{'='*80}")
    print("From-Scratch Evaluation Summary")
    print(f"{'='*80}")
    print(f"Completed (exit 0): {completed}/{total}")
    for label, code in results:
        status = "Completed" if code == 0 else "Failed/Crashed"
        print(f"  {label}: {status}")
    print(f"{'='*80}\n")
    return 0 if completed == total else 1


if __name__ == "__main__":
    sys.exit(main())
