#!/usr/bin/env python3
"""
Cross-Mutation evaluation module.
Task pairs (T0, T1) are fixed: T0 is always the **Initial** environment; T1 is each
mutated stage (Stage-1, Stage-2, …). So per task there are K pairs where K = number
of curriculum stages (typically 4), not all-pairs N*(N-1).
Agent starts with the Initial reference solution and adapts to the target env.
All experiments are run ONLY ONCE.

When invoked via run_evaluate_parallel.py (--method X), run_single_pair() uses the
same method implementations as evaluate.py / evaluate_mutated.py: memory retrieval
(rememberer, expel, reasoning_bank, memento, a_mem_sys, ace), reflexion prepend and
reflection generation, and dedicated branches for textgrad, tree_of_thought,
self_refine, etc. The evaluator is a full TaskEvaluator so all method state is
loaded in __init__; we wire it into the revision loop here.
"""
import os
import sys
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.prompt import (
    load_task_prompt,
    format_mutated_prompt,
    format_mutated_revision_prompt,
    format_mutated_revision_prompt_best_plus_previous,
)
from evaluation.feedback import format_feedback
from evaluation.evaluate import TaskEvaluator
from evaluation.utils import get_model_identifier, load_task_stages_module
from methods.Context.reflexion_method import format_reflections_str, inject_reflexion_before_your_task


def _rememberer_memory_block_cross_mut(evaluator: Any, last_feedback: str) -> Optional[str]:
    """Rememberer block for cross-mutation: original-env memory, single task background, code+feedback examples."""
    if getattr(evaluator, "base_method", None) != "rememberer":
        return None
    items = getattr(evaluator, "_rememberer_items", None) or []
    cands = getattr(evaluator, "_rememberer_candidates", None) or []
    if not items and not cands:
        return None
    from methods.Memory.rememberer_method import retrieve_for_prompt as rememberer_retrieve

    rb = rememberer_retrieve(
        evaluator.task_prompt,
        (last_feedback or "").strip(),
        list(items),
        list(cands),
        for_cross_mutation_target=True,
    )
    if rb and not rb.strip().startswith("(No relevant"):
        return rb
    return None


def get_all_stages(base_task_name: str) -> List[Dict[str, Any]]:
    """Get initial task + all curriculum stages."""
    from evaluation.prompt import parse_task_name

    try:
        task_path, _ = parse_task_name(base_task_name)
    except Exception as e:
        print(f"⚠️  Failed to parse task name {base_task_name}: {e}")
        return []

    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    task_dir = os.path.join(script_dir, 'tasks', task_path)
    stages_file = os.path.join(task_dir, 'stages.py')
    
    all_envs = []
    task_id = base_task_name.split("/")[-1] if "/" in base_task_name else base_task_name
    initial_physics = {}
    if task_id == "K_04":
        initial_physics = {"do_sleep": False}  # Pusher needs continuous motion; align with mutated stages
    all_envs.append({
        "stage_id": "Initial",
        "title": "Initial Task",
        "terrain_config": {},
        "physics_config": initial_physics
    })
    
    if os.path.exists(stages_file):
        try:
            stages_mod = load_task_stages_module(stages_file)

            curriculum_func = None
            for name in dir(stages_mod):
                if 'curriculum_stages' in name.lower() and callable(getattr(stages_mod, name)):
                    curriculum_func = getattr(stages_mod, name)
                    break

            if curriculum_func:
                stages = curriculum_func()
                for s in stages:
                    # Shallow copy so we don't mutate the module's stage dicts
                    s_copy = dict(s)
                    tc = s_copy.get("terrain_config", {})
                    tc = dict(tc) if tc else {}
                    tc.setdefault("target_rng_seed", 123)
                    s_copy["terrain_config"] = tc
                    pc = s_copy.get("physics_config", {})
                    if pc is not None:
                        pc = dict(pc)
                        # Do not inject random_seed for C_02: we need Initial ref to fail on mutated stages (e.g. Stage-1)
                        s_copy["physics_config"] = pc
                    all_envs.append(s_copy)
        except Exception as e:
            print(f"⚠️  Failed to load stages from {stages_file}: {e}")

    # Apply same deterministic seed to Initial stage (align with test_reference_solutions and run_evaluate_parallel)
    if all_envs:
        tc = dict(all_envs[0].get("terrain_config", {}) or {})
        tc.setdefault("target_rng_seed", 123)
        all_envs[0]["terrain_config"] = tc

    return all_envs

def next_line_is_def(lines, current_idx):
    for i in range(current_idx + 1, len(lines)):
        if lines[i].strip() == "": continue
        return lines[i].startswith("def ")
    return False

def get_reference_solution(base_task_name: str, stage_id: str) -> str:
    """Extract reference solution for a specific stage from agent.py."""
    from evaluation.prompt import parse_task_name
    task_path, _ = parse_task_name(base_task_name)
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agent_path = os.path.join(script_dir, 'tasks', task_path, 'agent.py')
    
    if not os.path.exists(agent_path):
        raise FileNotFoundError(f"Reference agent file not found: {agent_path}")

    with open(agent_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if stage_id == "Initial":
        build_func = "build_agent"
        action_func = "agent_action"
    else:
        try:
            num = stage_id.split("-")[1]
            build_func = f"build_agent_stage_{num}"
            action_func = f"agent_action_stage_{num}"
        except (IndexError, ValueError):
            build_func = f"build_agent_{stage_id}"
            action_func = f"agent_action_{stage_id}"
    
    lines = content.splitlines()

    # Only exclude other stage *entry* functions (build_agent, agent_action, build_agent_stage_N, agent_action_stage_N).
    # Do NOT exclude helpers like agent_action_pd — they are called by entry functions and must be in the
    # reference solution so the prompt gets a complete, runnable snippet (all called functions included).
    def is_stage_entry(name: str) -> bool:
        if name == "build_agent" or name == "agent_action":
            return True
        if name.startswith("build_agent_stage_") and name[len("build_agent_stage_"):].isdigit():
            return True
        if name.startswith("agent_action_stage_") and name[len("agent_action_stage_"):].isdigit():
            return True
        return False

    stage_funcs = set()
    for line in lines:
        if line.startswith("def "):
            name = line.split("(")[0][4:].strip()
            if is_stage_entry(name):
                stage_funcs.add(name)

    targets = {build_func, action_func}
    # Find callees: stage-entry functions that are called by build_func or action_func (e.g. D_06 Stage-2 calls build_agent_stage_1)
    required_callees = set()
    for line in lines:
        stripped = line.strip()
        for name in stage_funcs:
            # Match "name(" as a call (not "def name(")
            if stripped.startswith("def "):
                continue
            if name + "(" in line or line.strip().startswith("return " + name + "("):
                required_callees.add(name)
    to_exclude = stage_funcs - targets - required_callees

    # Split content into top-level blocks
    # A block starts at a non-indented line and continues until the next non-indented line
    blocks = []
    if not lines:
        return ""

    current_block = [lines[0]]
    for line in lines[1:]:
        # A new block starts if the line is not indented and not empty
        if line.strip() != "" and not line.startswith(" ") and not line.startswith("\t"):
            blocks.append("\n".join(current_block))
            current_block = [line]
        else:
            current_block.append(line)
    blocks.append("\n".join(current_block))

    final_imports = []
    final_helpers = []
    final_build = ""
    final_action = ""

    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue

        first_line = block.splitlines()[0]

        if first_line.startswith("import ") or first_line.startswith("from "):
            final_imports.append(block)
        elif first_line.startswith("def "):
            func_name = first_line.split("(")[0][4:].strip()
            if func_name == build_func:
                # Rename to standard build_agent
                new_block = block.replace(f"def {func_name}(", "def build_agent(", 1)
                final_build = new_block
            elif func_name == action_func:
                # Rename to standard agent_action
                new_block = block.replace(f"def {func_name}(", "def agent_action(", 1)
                final_action = new_block
            elif func_name in to_exclude:
                # Skip other stage functions
                continue
            else:
                # It's a helper function
                final_helpers.append(block)
        elif first_line.startswith("class "):
            # Include helper classes
            final_helpers.append(block)
        else:
            # Include top-level variables, docstrings, etc.
            # But skip the if __name__ == "__main__": block if present
            if "__main__" in first_line:
                continue
            final_helpers.append(block)

    final_parts = []
    if final_imports:
        final_parts.append("\n".join(final_imports))

    if final_helpers:
        final_parts.append("\n\n".join(final_helpers))

    if final_build:
        final_parts.append(final_build)
    else:
        # If we couldn't find the target build_func, it's a critical error for a reference solution
        raise ValueError(f"Target build function {build_func} not found in {agent_path}")

    if final_action:
        final_parts.append(final_action)
    # Note: we don't necessarily raise if final_action is missing, 
    # as some simple tasks might only have build_agent.

    return "\n\n".join(final_parts)
def run_cross_mutation_evaluation(base_task_name: str, model_type: str, model_name: str,
                                 method: str, result_method: Optional[str] = None,
                                 granularity: str = "outcome-based",
                                 context: str = 'previous', max_iterations: int = 10,
                                 max_steps: int = 10000, headless: bool = True, api_key: Optional[str] = None,
                                 output_dir: str = "evaluation_results", save_gif: bool = True,
                                 reflect_model_name: Optional[str] = None):
    """
    Run Initial → mutated evaluation only.
    Total pairs = (num_envs - 1): one per non-Initial stage.
    """
    all_envs = get_all_stages(base_task_name)
    num_envs = len(all_envs)
    num_pairs = max(0, num_envs - 1)
    
    print(f"\n🚀 Starting Cross-Mutation Evaluation for {base_task_name}")
    print(f"Total Environments: {num_envs}")
    print(f"Total Pairs (Initial → each mutated env): {num_pairs}")
    
    # Load stages module for visible changes
    from evaluation.prompt import parse_task_name
    task_path, _ = parse_task_name(base_task_name)
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    task_dir = os.path.join(script_dir, 'tasks', task_path)
    stages_file = os.path.join(task_dir, 'stages.py')
    
    stages_mod = None
    update_desc_func = None
    update_criteria_func = None
    if os.path.exists(stages_file):
        try:
            stages_mod = load_task_stages_module(stages_file)
            for name in dir(stages_mod):
                if 'update_task_description_for_visible_changes' in name.lower() and callable(getattr(stages_mod, name)):
                    update_desc_func = getattr(stages_mod, name)
                if 'update_success_criteria_for_visible_changes' in name.lower() and callable(getattr(stages_mod, name)):
                    update_criteria_func = getattr(stages_mod, name)
        except Exception as e:
            print(f"⚠️  Failed to load stages module for updates: {e}")

    results = []
    if not all_envs:
        return results
    env_i = all_envs[0]
    if env_i.get("stage_id") != "Initial":
        print(f"⚠️  Expected first stage to be Initial, got {env_i.get('stage_id')}")
    try:
        ref_code_initial = get_reference_solution(base_task_name, "Initial")
    except Exception as e:
        print(f"⚠️  Failed to get Initial reference solution: {e}")
        return results

    for j in range(1, len(all_envs)):
        env_j = all_envs[j]
        env_i = all_envs[0]
        ref_code = ref_code_initial
        pair_name = f"{env_i['stage_id']}_to_{env_j['stage_id']}"
        print(f"\n--- Evaluating Pair: {pair_name} ---")

        env_overrides = {
            "terrain_config": env_j.get("terrain_config", {}),
            "physics_config": env_j.get("physics_config", {}),
        }

        # Prepare task prompt override with visible changes
        task_prompt_override = None
        try:
            base_prompt = load_task_prompt(base_task_name)
            task_prompt_override = dict(base_prompt)

            desc = base_prompt.get("task_description", "")
            criteria = base_prompt.get("success_criteria", "")

            target_terrain = env_j.get("terrain_config", {})
            target_physics = env_j.get("physics_config", {})
            # Visible prompt text must describe target env vs **initial** source environment,
            # not vs the cross-pair source stage (avoids mismatched numbers in the sentence).
            base_terrain_visible, base_physics_visible = {}, {}

            if update_desc_func:
                try:
                    import inspect
                    sig = inspect.signature(update_desc_func)
                    if len(sig.parameters) >= 5:
                        desc = update_desc_func(
                            desc,
                            target_terrain,
                            base_terrain_visible,
                            target_physics,
                            base_physics_visible,
                        )
                    else:
                        desc = update_desc_func(desc, target_terrain, base_terrain_visible)
                except Exception:
                    desc = update_desc_func(desc, target_terrain, base_terrain_visible)
            if update_criteria_func:
                try:
                    import inspect
                    sig = inspect.signature(update_criteria_func)
                    if len(sig.parameters) >= 5:
                        criteria = update_criteria_func(
                            criteria,
                            target_terrain,
                            base_terrain_visible,
                            target_physics,
                            base_physics_visible,
                        )
                    else:
                        criteria = update_criteria_func(criteria, target_terrain, base_terrain_visible)
                except Exception:
                    criteria = update_criteria_func(criteria, target_terrain, base_terrain_visible)

            # Add suffix from target environment if it exists
            if method.endswith('_CE'):
                import json
                suffix = f'## Environmental Anomalies Detected\n + "terrain_config": {json.dumps(target_terrain)}, \n"physics_config": {json.dumps(env_j.get("physics_config", {}))}'
            else:
                suffix = env_j.get("task_description_suffix", "")

            task_prompt_override["task_description"] = desc
            task_prompt_override["success_criteria"] = criteria
            if suffix:
                task_prompt_override["prompt_trailer"] = suffix
            else:
                task_prompt_override.pop("prompt_trailer", None)
        except Exception as e:
            print(f"⚠️  Failed to prepare prompt override: {e}")

        try:
            evaluator = TaskEvaluator(
                task_name=base_task_name,
                model_type=model_type,
                model_name=model_name,
                api_key=api_key,
                max_iterations=max_iterations,
                max_steps=max_steps,
                headless=headless,
                method=method,
                context=context,
                env_overrides=env_overrides,
                is_mutated_task=True,
                task_prompt_override=task_prompt_override,
                save_gif=save_gif,
                reflect_model_name=reflect_model_name,
                result_method=result_method or method,
                granularity=granularity,
            )
            evaluator.mutated_task_name = pair_name
            evaluator._setup_gif_directory()

            report = run_single_pair(evaluator, ref_code, base_task_name, pair_name)
            if not report.get("skipped"):
                evaluator.save_report(report, output_dir=output_dir)

            results.append({
                "pair": pair_name,
                "source_env": env_i["stage_id"],
                "target_env": env_j["stage_id"],
                "result": report
            })
        except Exception as e:
            print(f"❌ Error evaluating pair {pair_name}: {e}")
            traceback.print_exc()

    return results

def run_single_pair(evaluator, initial_ref_code, base_task_name, pair_name):
    """
    Run evaluation for a single (env_i, env_j) pair.
    - Iteration 0: Run the source env's reference solution in the target env (no model call).
    - Iteration 1..max: First revision and beyond; each iteration builds prompt, generates code, runs it, records prompt+result.
    """
    evaluator.best_score = -1.0
    evaluator.best_code = None
    evaluator.best_metrics = {}
    evaluator.iteration_history = []
    source_stage_id = pair_name.split('_to_')[0]

    # --- Iteration 0: run reference solution in target env (before any revision) ---
    print("Iteration 0 (reference in target env)")
    gif_path_0 = evaluator._get_gif_path(0) if evaluator.save_gif else None
    try:
        success_0, score_0, metrics_0, error_0 = evaluator.verifier.verify_code(
            initial_ref_code, headless=evaluator.headless, save_gif_path=gif_path_0,
            granularity=getattr(evaluator, "granularity", "outcome-based"),
        )
    except Exception as e:
        print(f"❌ Verification error at iteration 0: {e}")
        success_0, score_0, metrics_0, error_0 = False, 0.0, {}, str(e)
    failed_0 = metrics_0.get('failed', False) if metrics_0 else True
    failure_reason_0 = metrics_0.get('failure_reason') if metrics_0 else "Unknown error"
    feedback_0 = evaluator._compose_feedback(
        metrics_0 or {}, score_0, success_0, failed_0, failure_reason_0, 0, error_0
    )
    evaluator.iteration_history.append({
        'iteration': 0,
        'code': initial_ref_code,
        'prompt': None,
        'success': success_0,
        'score': score_0,
        'metrics': metrics_0 or {},
        'error': error_0,
        'feedback': feedback_0,
    })
    if score_0 > evaluator.best_score:
        evaluator.best_score = score_0
        evaluator.best_code = initial_ref_code
        evaluator.best_metrics = metrics_0 or {}
    if success_0:
        print("✅ Reference already passes in target env. Skipping this pair (no revisions).")
        evaluator.verifier.cleanup()
        report = evaluator._generate_report()
        report['skipped'] = True
        report['skip_reason'] = 'reference_passes_in_target'
        return report

    # ref_feedback: used for building revision prompts (iteration 0 result)
    ref_feedback = feedback_0
    current_code = initial_ref_code

    # SCIENCE-CODEEVOLVE: inference-time search via CodeEvolve, starting from T0 reference code.
    # NOTE: This must be an early return; CodeEvolve does its own inner sampling/search/verification.
    if getattr(evaluator, "base_method", None) == "science_codeevolve":
        try:
            from methods.Inference_time_search.science_codeevolve_method import run_single_task
            scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            model_type = getattr(evaluator.solver, "model_type", None)
            model_name = getattr(evaluator.solver, "model_name", None)
            # Use the same (aux) credentials TaskEvaluator received, since CodeEvolve calls the same API backend.
            api_key = getattr(evaluator, "_llm_aux_api_key", None) or getattr(evaluator.solver, "API_KEY", None)
            api_base = getattr(evaluator, "_llm_aux_base_url", None) or os.environ.get("API_BASE")

            exit_code, ce_report = run_single_task(
                task_name=base_task_name,
                run_number=1,
                model_type=model_type,
                model_name=model_name,
                context=getattr(evaluator, "context", "all"),
                max_steps=getattr(evaluator, "max_steps", 10000),
                max_iterations=getattr(evaluator, "max_iterations", 20),
                scripts_dir=scripts_dir,
                initial_code=initial_ref_code,
                api_base=api_base,
                api_key=api_key,
                env_overrides=getattr(evaluator, "env_overrides", None) or {},
                save_report=False,  # let TaskEvaluator.save_report handle the pair filename
            )

            # Merge T0 reference history (iteration 0) + CodeEvolve outer rounds (iterations 1..max_iterations).
            ce_history = ce_report.get("iteration_history", []) or []
            evaluator.iteration_history = list(evaluator.iteration_history) + ce_history
            evaluator.best_score = ce_report.get("best_score", 0.0)
            evaluator.best_code = ce_report.get("best_code")
            evaluator.best_metrics = ce_report.get("best_metrics", {}) or {}

            report = evaluator._generate_report()
            # Expose key CodeEvolve evidence for debugging/analysis.
            report["codeevolve_wall_time_s"] = ce_report.get("codeevolve_wall_time_s")
            report["codeevolve_num_epochs"] = ce_report.get("codeevolve_num_epochs")
            report["codeevolve_num_islands"] = ce_report.get("codeevolve_num_islands")
            report["codeevolve_init_pop"] = ce_report.get("codeevolve_init_pop")
            report["codeevolve_ckpt_interval"] = ce_report.get("codeevolve_ckpt_interval")
            report["codeevolve_population_by_epoch"] = ce_report.get("codeevolve_population_by_epoch", [])
            report["codeevolve_outer_round_stats"] = ce_report.get("codeevolve_outer_round_stats", [])
            report["codeevolve_exit_code"] = ce_report.get("codeevolve_exit_code", exit_code)

            evaluator.verifier.cleanup()
            return report
        except Exception as e:
            print(f"[science_codeevolve] CodeEvolve failed in cross-mutation pair: {e}", flush=True)
            traceback.print_exc()
            evaluator.best_score = 0.0
            evaluator.best_code = None
            evaluator.best_metrics = {"failure_reason": str(e), "failed": True}
            # Return a regular (failed) report so the pipeline can continue.
            report = evaluator._generate_report()
            evaluator.verifier.cleanup()
            return report

    # ThetaEvolve: run per-pair with target env; save report under pair path (all_xx_to_yy.json)
    if getattr(evaluator, "base_method", None) == "theta_evolve":
        import tempfile as _tf
        from evaluation.utils import get_evaluation_results_dir, get_gif_base_dir
        scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmp_out = _tf.mkdtemp(prefix="theta_evolve_pair_")
        try:
            _cleanup = getattr(evaluator.solver, "cleanup", None)
            if callable(_cleanup):
                print("[theta_evolve] Releasing evaluation vLLM before ThetaEvolve (Megatron+SGLang need VRAM)...")
                _cleanup()
            from methods.Parameter_Policy.theta_evolve import run_single_task as theta_evolve_run_single_task
            _exit_code, report = theta_evolve_run_single_task(
                task_name=base_task_name,
                run_number=1,
                model_type=evaluator.solver.model_type,
                model_name=evaluator.solver.model_name,
                context=getattr(evaluator, "context", "all"),
                max_steps=getattr(evaluator, "max_steps", 10000),
                scripts_dir=scripts_dir,
                output_dir=tmp_out,
                gif_base_dir=get_gif_base_dir(),
                initial_code=None,
                model_path=getattr(evaluator.solver, "model_path", None),
                device=getattr(evaluator, "requested_device", None),
                env_overrides=evaluator.env_overrides or {},
                theta_evolve_num_rollout=getattr(evaluator, "theta_evolve_num_rollout", 10000),
                theta_evolve_rollout_batch_size=getattr(evaluator, "theta_evolve_rollout_batch_size", 32),
                training_log_dir=evaluator._get_training_log_dir(),
            )
            if _exit_code != 0:
                raise RuntimeError(
                    f"ThetaEvolve training failed with exit code {_exit_code}. "
                    "Check training log and Ray actor traceback above."
                )
            report["iterations"] = len(report.get("iteration_history", []))
            evaluator.verifier.cleanup()
            evaluator.save_report(report, output_dir="evaluation_results")
            return report
        finally:
            try:
                import shutil
                shutil.rmtree(tmp_out, ignore_errors=True)
            except Exception:
                pass

    # SOAR: run full multi-generation loop with mutation prompts (same as evaluate.py path but with format_mutated_*)
    if getattr(evaluator, "base_method", None) == "soar":
        task_prompt = evaluator.task_prompt
        ref_fb = ref_feedback
        ref_code = initial_ref_code
        ctx = getattr(evaluator, "context", "previous")

        def get_initial_prompt():
            rb = _rememberer_memory_block_cross_mut(evaluator, ref_fb)
            return format_mutated_prompt(task_prompt, ref_code, ref_fb, rememberer_memory_block=rb)

        def get_revision_prompt(selected: Dict, history: List, step: int) -> str:
            lf = selected.get("feedback") or ""
            rb = _rememberer_memory_block_cross_mut(evaluator, lf)
            if not history:
                return format_mutated_revision_prompt(
                    task_prompt, ref_code, ref_fb,
                    selected["code"], selected["feedback"], selected["feedback"],
                    rememberer_memory_block=rb,
                )
            best_item = max(history, key=lambda x: x.get("score", -1))
            previous_item = history[-1]
            if ctx in ("all", "best_score_plus_previous") and best_item and previous_item:
                return format_mutated_revision_prompt_best_plus_previous(
                    task_prompt, ref_code, ref_fb,
                    best_item["code"], best_item["feedback"],
                    previous_item["code"], previous_item["feedback"],
                    selected["feedback"],
                    best_item.get("iteration"), previous_item.get("iteration"), step,
                    rememberer_memory_block=rb,
                )
            return format_mutated_revision_prompt(
                task_prompt, ref_code, ref_fb,
                selected["code"], selected["feedback"], selected["feedback"],
                rememberer_memory_block=rb,
            )

        try:
            result = evaluator.solver.run_pretrain(
                task_prompt=task_prompt,
                verifier=evaluator.verifier,
                max_iterations=evaluator.max_iterations,
                task_name=base_task_name,
                get_initial_prompt=get_initial_prompt,
                get_revision_prompt=get_revision_prompt,
            )
        except Exception as e:
            print(f"[SOAR] run_pretrain failed: {e}")
            traceback.print_exc()
            result = {"iteration_history": [], "best_score": -1.0, "best_code": None, "best_metrics": {}}
        # Merge iteration 0 (reference) with SOAR revision history
        iter0 = list(evaluator.iteration_history)
        evaluator.iteration_history = iter0 + (result.get("iteration_history") or [])
        r_score = result.get("best_score", -1.0)
        if r_score > evaluator.best_score:
            evaluator.best_score = r_score
            evaluator.best_code = result.get("best_code")
            evaluator.best_metrics = result.get("best_metrics", {})
        evaluator._soar_pretrain_stats = {
            "soar_generations": result.get("soar_generations", 0),
            "soar_sft_runs": result.get("soar_sft_runs", 0),
        }
        if "error" in result:
            evaluator._soar_pretrain_stats["error"] = result["error"]
        evaluator.verifier.cleanup()
        return evaluator._generate_report()

    # RAGEN: run per-pair pretrain (rollout + GRPO + PPO), then fall through to revision loop
    if getattr(evaluator, "base_method", None) == "ragen":
        try:
            print("[RAGEN] Running per-pair pretrain (rollout + GRPO + PPO-clip)...")
            training_log_dir = evaluator._get_training_log_dir()
            ragen_stats = evaluator.solver.run_pretrain(
                task_prompt=evaluator.task_prompt,
                verifier=evaluator.verifier,
                training_log_dir=training_log_dir,
                max_iterations=evaluator.max_iterations,
                max_steps_verifier=getattr(evaluator, "max_steps", 10000),
            )
            evaluator._ragen_pretrain_stats = ragen_stats
            print(f"[RAGEN] Pretrain complete: {evaluator._ragen_pretrain_stats}")
        except Exception as e:
            print(f"[RAGEN] Pretrain failed: {e}")
            traceback.print_exc()
            evaluator._ragen_pretrain_stats = {"error": str(e)}

    # Discover: run per-pair pretrain (TTT) with mutated task_prompt, then fall through to revision loop
    if getattr(evaluator, "base_method", None) == "discover":
        try:
            print("[Discover] Running per-pair pretrain (rollout + advantage + LoRA update)...")
            training_log_dir = evaluator._get_training_log_dir()
            discover_stats = evaluator.solver.run_pretrain(
                task_prompt=evaluator.task_prompt,
                verifier=evaluator.verifier,
                training_log_dir=training_log_dir,
                max_iterations=evaluator.max_iterations,
                max_steps_verifier=getattr(evaluator, "max_steps", 10000),
            )
            evaluator._discover_pretrain_stats = discover_stats
            print(f"[Discover] Pretrain complete: {evaluator._discover_pretrain_stats}")
        except Exception as e:
            print(f"[Discover] Pretrain failed: {e}")
            traceback.print_exc()
            evaluator._discover_pretrain_stats = {"error": str(e)}

    tot_states: List[Dict[str, Any]] = []  # ToT: b states (code, feedback, score, ...)
    for iteration in range(1, evaluator.max_iterations + 1):
        print(f"Iteration {iteration}/{evaluator.max_iterations} (revision)")
        gif_path = evaluator._get_gif_path(iteration) if evaluator.save_gif else None

        # ----- Self-Refine: iteration > 1 uses self-verify inner loop then one verifier run -----
        # self_refine_inner_only: same inner loop but only on iteration 1 (max_iterations=1)
        _run_self_refine = (
            (getattr(evaluator, "base_method", None) == "self_refine" and iteration > 1)
            or (getattr(evaluator, "base_method", None) == "self_refine_inner_only" and iteration == 1)
        )
        if _run_self_refine:
            from evaluation.utils import is_cuda_oom
            from methods.Context.self_refine_method import (
                format_self_feedback_prompt,
                format_revision_prompt_self_refine_inner,
                self_verify_says_correct,
            )
            MAX_SELF_VERIFY_STEPS = 5
            self_refine_inner_steps = []
            last_system_feedback = (
                evaluator.iteration_history[-1].get("feedback", "") if evaluator.iteration_history else ref_feedback
            )
            last_code = (
                evaluator.iteration_history[-1].get("code", "") or current_code if evaluator.iteration_history else current_code
            )
            _rb = _rememberer_memory_block_cross_mut(evaluator, last_system_feedback)
            if iteration == 1 and len(evaluator.iteration_history) == 1:
                # First revision round (only iter 0 reference in history): use mutated prompt
                prompt = format_mutated_prompt(
                    evaluator.task_prompt, initial_ref_code, ref_feedback, rememberer_memory_block=_rb,
                )
            elif evaluator.context == "all" or evaluator.context == "best_score_plus_previous":
                best_item = max(evaluator.iteration_history, key=lambda x: x["score"])
                previous_item = evaluator.iteration_history[-1]
                prompt = format_mutated_revision_prompt_best_plus_previous(
                    evaluator.task_prompt, initial_ref_code, evaluator.iteration_history[0]["feedback"],
                    best_item["code"], best_item["feedback"],
                    previous_item["code"], previous_item["feedback"],
                    last_system_feedback,
                    best_item["iteration"], previous_item["iteration"], iteration,
                    rememberer_memory_block=_rb,
                )
            else:
                prompt = format_mutated_revision_prompt(
                    evaluator.task_prompt, initial_ref_code, evaluator.iteration_history[0]["feedback"],
                    last_code, last_system_feedback, last_system_feedback,
                    rememberer_memory_block=_rb,
                )
            print(f"🔄 Self-Refine round {iteration}: generating code then inner self-verify loop...")
            try:
                current_code, raw_output, token_usage = evaluator.solver.generate_code(prompt)
            except Exception as exc:
                if is_cuda_oom(exc):
                    raise
                evaluator.iteration_history.append({
                    "iteration": iteration,
                    "phase": "self_refine_init_failed",
                    "error": str(exc),
                    "self_refine_inner_steps": [],
                })
                continue
            if current_code and len(current_code.strip()) >= 50 and "def build_agent" in current_code:
                inner_step = 0
                while inner_step < MAX_SELF_VERIFY_STEPS:
                    inner_step += 1
                    verify_prompt = format_self_feedback_prompt(current_code, evaluator.task_prompt)
                    try:
                        _out = evaluator.solver.generate_code(verify_prompt)
                        if isinstance(_out, (list, tuple)) and len(_out) >= 2:
                            self_verify_output = (_out[1] or "").strip()
                        else:
                            self_verify_output = (str(_out) if _out else "").strip()
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        self_verify_output = f"(Self-verify failed: {exc})"
                    self_refine_inner_steps.append({"step": inner_step, "self_verify_output": self_verify_output, "code_before": current_code})
                    if self_verify_says_correct(self_verify_output):
                        break
                    refine_prompt = format_revision_prompt_self_refine_inner(evaluator.task_prompt, current_code, self_verify_output)
                    try:
                        _out = evaluator.solver.generate_code(refine_prompt)
                        new_code = _out[0] if isinstance(_out, (list, tuple)) and len(_out) else _out
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        self_refine_inner_steps[-1]["refine_error"] = str(exc)
                        self_refine_inner_steps[-1]["code_after"] = None
                        break
                    self_refine_inner_steps[-1]["code_after"] = new_code
                    if new_code and len(new_code.strip()) >= 50 and "def build_agent" in new_code:
                        current_code = new_code
                    else:
                        break
            save_this_gif = evaluator.save_gif
            gif_path = evaluator._get_gif_path(iteration) if save_this_gif else None
            try:
                success, score, metrics, error = evaluator.verifier.verify_code(
                    current_code if (current_code and "def build_agent" in current_code) else (current_code or ""),
                    headless=evaluator.headless, save_gif_path=gif_path,
                    granularity=getattr(evaluator, "granularity", "outcome-based"),
                )
            except Exception as e:
                success, score, metrics, error = False, 0.0, {}, str(e)
            failed = (metrics or {}).get("failed", False)
            failure_reason = (metrics or {}).get("failure_reason")
            feedback = evaluator._compose_feedback(
                metrics or {}, score, success, failed, failure_reason, iteration, error, include_suggestions=False
            )
            evaluator.iteration_history.append({
                "iteration": iteration,
                "phase": "self_refine_revision",
                "prompt": prompt,
                "code": current_code,
                "raw_llm_output": raw_output,
                "token_usage": token_usage,
                "success": success,
                "score": score,
                "metrics": metrics or {},
                "error": error,
                "feedback": feedback,
                "self_refine_inner_steps": self_refine_inner_steps,
            })
            if score > evaluator.best_score:
                evaluator.best_score = score
                evaluator.best_code = current_code
                evaluator.best_metrics = metrics or {}
            print(f"📊 Self-Refine round {iteration}: Score={score:.1f}/100, Success={'✅' if success else '❌'}")
            if success:
                print(f"✅ Success at iteration {iteration}!")
                break
            continue

        # ----- TextGrad: optimisation step for iterations 2+ -----
        if getattr(evaluator, "base_method", None) == "textgrad" and iteration > 1 and getattr(evaluator, "tg_code_var", None) is not None:
            from evaluation.utils import is_cuda_oom
            last_feedback = evaluator.iteration_history[-1].get("feedback", "")
            print(f"🧮 TextGrad optimisation step (cross-mutation, iteration {iteration})...")
            try:
                from methods.Context.textgrad_method import textgrad_optimize_step, extract_code_from_textgrad_output
                tg_new_code, tg_raw_output, tg_gradient_text = textgrad_optimize_step(
                    evaluator.tg_code_var, evaluator.tg_optimizer, evaluator.tg_engine,
                    last_feedback, evaluator.task_prompt,
                )
                tg_current_code = extract_code_from_textgrad_output(tg_new_code) if tg_new_code else None
                if not tg_current_code and tg_new_code:
                    tg_current_code = tg_new_code
            except Exception as exc:
                if is_cuda_oom(exc):
                    raise
                print(f"❌ TextGrad optimisation failed (cross-mutation): {exc}")
                tg_current_code = None
                tg_raw_output = str(exc)
                tg_gradient_text = None
            if tg_current_code and len(tg_current_code.strip()) >= 50 and "def build_agent" in tg_current_code:
                evaluator.tg_code_var.set_value(tg_current_code)
                current_code = tg_current_code
                gif_path = evaluator._get_gif_path(iteration) if evaluator.save_gif else None
                success, score, metrics, error = evaluator.verifier.verify_code(
                    current_code, headless=evaluator.headless, save_gif_path=gif_path,
                    granularity=getattr(evaluator, "granularity", "outcome-based"),
                )
                failed = (metrics or {}).get("failed", False)
                failure_reason = (metrics or {}).get("failure_reason")
                feedback = evaluator._compose_feedback(
                    metrics or {}, score, success, failed, failure_reason, iteration, error, include_suggestions=False
                )
                evaluator.iteration_history.append({
                    "iteration": iteration, "phase": "textgrad_revision", "prompt": f"[TextGrad step {iteration}]",
                    "code": current_code, "raw_llm_output": tg_raw_output, "token_usage": {},
                    "success": success, "score": score, "metrics": metrics or {}, "error": error, "feedback": feedback,
                })
                if score > evaluator.best_score:
                    evaluator.best_score = score
                    evaluator.best_code = current_code
                    evaluator.best_metrics = metrics or {}
                if success:
                    print(f"✅ Success at iteration {iteration}!")
                    break
                continue

        # ----- Tree-of-Thought: beam search for iterations 2+ (b beams, n samples per beam) -----
        if getattr(evaluator, "base_method", None) == "tree_of_thought" and iteration > 1 and tot_states:
            from evaluation.utils import is_cuda_oom
            b = getattr(evaluator, "n_select_sample", 3)
            n = getattr(evaluator, "n_generate_sample", 2)
            revision_prompts_mut = []
            for state in tot_states:
                _rb = _rememberer_memory_block_cross_mut(evaluator, state.get("feedback") or "")
                p = format_mutated_prompt(
                    evaluator.task_prompt, initial_ref_code, state["feedback"],
                    rememberer_memory_block=_rb,
                )
                for _ in range(n):
                    revision_prompts_mut.append(p)
            all_candidates = []
            use_parallel = getattr(evaluator.solver, "model_type", None) == "openai"
            if use_parallel:
                def _gen_one(prompt: str):
                    try:
                        out = evaluator.solver.generate_code(prompt)
                        code = out[0] if isinstance(out, (list, tuple)) and len(out) else out
                        raw_llm = out[1] if isinstance(out, (list, tuple)) and len(out) > 1 else None
                        tok = out[2] if isinstance(out, (list, tuple)) and len(out) > 2 else {}
                        return (code, raw_llm, tok or {}, prompt)
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        return (None, None, {}, prompt)
                max_workers = min(len(revision_prompts_mut), 16)
                with ThreadPoolExecutor(max_workers=max_workers) as ex:
                    for fut in as_completed([ex.submit(_gen_one, p) for p in revision_prompts_mut]):
                        code, raw_llm, token_usage, rev_prompt = fut.result()
                        if code and len(code.strip()) >= 50 and "def build_agent" in code:
                            all_candidates.append({"code": code, "raw_llm_output": raw_llm, "token_usage": token_usage or {}, "prompt": rev_prompt})
            else:
                for p in revision_prompts_mut:
                    try:
                        out = evaluator.solver.generate_code(p)
                        code = out[0] if isinstance(out, (list, tuple)) and len(out) else out
                        raw_llm = out[1] if isinstance(out, (list, tuple)) and len(out) > 1 else None
                        tok = out[2] if isinstance(out, (list, tuple)) and len(out) > 2 else {}
                        if code and len(code.strip()) >= 50 and "def build_agent" in code:
                            all_candidates.append({"code": code, "raw_llm_output": raw_llm, "token_usage": tok or {}, "prompt": p})
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        print(f"⚠️  ToT (cross-mutation) sample failed: {exc}")
            if not all_candidates:
                evaluator.iteration_history.append({
                    "iteration": iteration, "phase": "tot_revision_failed", "code": None,
                    "error": "No valid revision code", "tot_candidates": 0,
                })
                break
            if all_candidates:
                for c in all_candidates:
                    succ, sc, met, err = evaluator.verifier.verify_code(
                        c["code"], headless=evaluator.headless, save_gif_path=None,
                        granularity=getattr(evaluator, "granularity", "outcome-based"),
                    )
                    c["success"] = succ
                    c["score"] = sc
                    c["metrics"] = met
                    c["error"] = err
                    c["feedback"] = evaluator._compose_feedback(
                        met or {}, sc, succ, met.get("failed", False), met.get("failure_reason"), iteration, err, include_suggestions=False
                    )
                    if sc > evaluator.best_score:
                        evaluator.best_score = sc
                        evaluator.best_code = c["code"]
                        evaluator.best_metrics = met
                all_candidates.sort(key=lambda x: x["score"], reverse=True)
                tot_states = all_candidates[:b]
                round_best = tot_states[0]
                evaluator.iteration_history.append({
                    "iteration": iteration, "phase": "tot_revision", "prompt": round_best.get("prompt"),
                    "code": round_best["code"], "raw_llm_output": round_best.get("raw_llm_output"),
                    "token_usage": round_best.get("token_usage", {}), "success": round_best["success"],
                    "score": round_best["score"], "metrics": round_best.get("metrics"), "error": round_best.get("error"),
                    "feedback": round_best["feedback"], "tot_candidates": len(all_candidates),
                    "tot_top_b": [{"score": s["score"], "success": s["success"]} for s in tot_states],
                })
                if any(s["success"] for s in tot_states):
                    print(f"✅ Success at iteration {iteration}!")
                    break
            continue

        # Build prompt for this revision (prompt that will produce the code we run in this iteration)
        last_feedback = ref_feedback if iteration == 1 else (
            evaluator.iteration_history[-1].get("feedback", "") if evaluator.iteration_history else ""
        )
        rememberer_block = _rememberer_memory_block_cross_mut(evaluator, last_feedback)

        if iteration == 1:
            prompt = format_mutated_prompt(
                evaluator.task_prompt, initial_ref_code, ref_feedback, rememberer_memory_block=rememberer_block,
            )
        else:
            best_item = max(evaluator.iteration_history, key=lambda x: x['score'])
            previous_item = evaluator.iteration_history[-1]
            if evaluator.context == 'all' or evaluator.context == 'best_score_plus_previous':
                prompt = format_mutated_revision_prompt_best_plus_previous(
                    evaluator.task_prompt, initial_ref_code, evaluator.iteration_history[0]['feedback'],
                    best_item['code'], best_item['feedback'],
                    previous_item['code'], previous_item['feedback'],
                    previous_item['feedback'],
                    best_item['iteration'], previous_item['iteration'], iteration,
                    rememberer_memory_block=rememberer_block,
                )
            else:
                prompt = format_mutated_revision_prompt(
                    evaluator.task_prompt, initial_ref_code, evaluator.iteration_history[0]['feedback'],
                    previous_item['code'], previous_item['feedback'],
                    previous_item['feedback'],
                    rememberer_memory_block=rememberer_block,
                )

        # Memory retrieval (expel, reasoning_bank, memento, …) — rememberer is inlined above
        memory_block = None
        base_method = getattr(evaluator, "base_method", None)
        if base_method == "expel" and (
            getattr(evaluator, "_expel_rules", None)
            or getattr(evaluator, "_expel_items", None)
            or getattr(evaluator, "source_env", None)
        ):
            from methods.Memory.expel_method import retrieve_for_prompt as expel_retrieve

            _pair = bool(getattr(evaluator, "source_env", None))
            memory_block = expel_retrieve(
                evaluator.task_prompt,
                last_feedback,
                getattr(evaluator, "_expel_items", []),
                getattr(evaluator, "_expel_rules", []),
                getattr(evaluator, "_expel_embedder", None),
                top_k_rules=8,
                top_k_trajectories=0 if _pair else 3,
                rules_only=_pair,
            )
        elif base_method == "reasoning_bank":
            from methods.Memory.reasoning_bank_method import retrieve_for_prompt as reasoning_bank_retrieve
            bank_items = getattr(evaluator, "_reasoning_bank_items", []) or []
            memory_block = reasoning_bank_retrieve(evaluator.task_prompt, last_feedback, bank_items)
        elif base_method == "memento_nonparametric" and (getattr(evaluator, "_memento_items", None) or getattr(evaluator, "_memento_pairs", None)):
            from methods.Memory.memento_nonparametric_method import retrieve_for_prompt as memento_retrieve
            memory_block = memento_retrieve(
                evaluator.task_prompt, last_feedback,
                getattr(evaluator, "_memento_items", []),
                getattr(evaluator, "_memento_pairs", []),
            )
        elif base_method == "a_mem_sys" and getattr(evaluator, "_a_mem_sys_memory", None):
            from methods.Memory.a_mem_sys_method import retrieve_for_prompt as a_mem_sys_retrieve
            memory_block = a_mem_sys_retrieve(
                evaluator.task_prompt, last_feedback, evaluator._a_mem_sys_memory,
            )
        elif base_method == "ace" and getattr(evaluator, "_ace_playbook", None):
            memory_block = "\n\n## Current Playbook\n\n" + (evaluator._ace_playbook or "")
        if memory_block:
            _mem_title = (
                "## ExpeL insights (distilled rules)\n\n"
                if base_method == "expel" and getattr(evaluator, "source_env", None)
                else "## Relevant experience from memory\n\n"
            )
            prompt = (
                prompt
                + "\n\n---\n"
                + _mem_title
                + memory_block
                + "\n\nProvide an improved solution."
            )

        # Reflexion: after best/previous attempt blocks, before final "Your Task" (not at top)
        if base_method == "reflexion" and getattr(evaluator, "reflections_str", None):
            prompt = inject_reflexion_before_your_task(prompt, evaluator.reflections_str)

        # ACE: ask model to output bullet_ids + code so Reflector gets bullets_used (same as evaluate.py)
        if base_method == "ace" and getattr(evaluator, "_ace_playbook", None):
            from methods.Memory.ace_method import get_playbook_bullet_ids
            ids = get_playbook_bullet_ids(evaluator._ace_playbook)
            prompt = prompt + "\n\n**Output format (ACE):** When you use playbook strategies, cite their bullet IDs. Prefer a JSON block: {\"bullet_ids\": [\"id1\", ...], \"code\": \"...\"}. Available bullet IDs: " + (", ".join(ids) if ids else "(none yet)") + "\n"

        # ----- ReasoningBank MaTTS: K parallel trajectories, contrast_and_distill, pick best -----
        reasoning_bank_matts_done = False
        if base_method == "reasoning_bank" and getattr(evaluator, "reasoning_bank_k", 1) > 1 and getattr(evaluator, "_reasoning_bank_path", None):
            from methods.Memory.reasoning_bank_method import contrast_and_distill, store_after_iteration
            k = getattr(evaluator, "reasoning_bank_k", 2)
            codes_and_outputs = []
            for _ in range(k):
                try:
                    out = evaluator.solver.generate_code(prompt)
                    nc = out[0] if isinstance(out, (list, tuple)) and len(out) else out
                    raw = out[1] if isinstance(out, (list, tuple)) and len(out) > 1 else None
                    tok = out[2] if isinstance(out, (list, tuple)) and len(out) > 2 else {}
                    if nc:
                        codes_and_outputs.append((nc, raw or "", tok or {}))
                except Exception:
                    pass
            if codes_and_outputs:
                trajectories = []
                for (code, raw, tok) in codes_and_outputs:
                    succ, sc, met, err = evaluator.verifier.verify_code(
                        code, headless=evaluator.headless, save_gif_path=None,
                        granularity=getattr(evaluator, "granularity", "outcome-based"),
                    )
                    fb = evaluator._compose_feedback(
                        met or {}, sc, succ, (met or {}).get("failed", False), (met or {}).get("failure_reason"), iteration, err
                    )
                    trajectories.append({
                        "code": code, "feedback": fb, "score": sc, "success": succ,
                        "metrics": met, "error": err, "raw_output": raw, "token_usage": tok,
                    })
                task_desc = (evaluator.task_prompt.get("task_description") or "") if isinstance(evaluator.task_prompt, dict) else str(evaluator.task_prompt)
                _aux_k = getattr(evaluator, "_llm_aux_api_key", None)
                _aux_u = getattr(evaluator, "_llm_aux_base_url", None)
                if _aux_k is None:
                    from evaluation.solver_interface import get_aux_llm_credentials
                    _aux_k, _aux_u = get_aux_llm_credentials(None)
                import os as _os_rb2
                new_items = contrast_and_distill(
                    trajectories, task_desc,
                    api_key=_aux_k,
                    base_url=_aux_u,
                    judge_model=_os_rb2.environ.get("REASONING_BANK_INDUCE_MODEL", "deepseek-v3.2"),
                    use_llm_judge=False,
                )
                if new_items:
                    evaluator._reasoning_bank_items = store_after_iteration(
                        evaluator._reasoning_bank_path, evaluator._reasoning_bank_items, new_items,
                    )
                    revision_entry_matts = {"reasoning_bank_stored_items": new_items}
                else:
                    revision_entry_matts = {}
                best_t = max(trajectories, key=lambda t: (t["success"], t["score"]))
                current_code = best_t["code"]
                raw_output = best_t.get("raw_output", "")
                token_usage = best_t.get("token_usage", {})
                success = best_t["success"]
                score = best_t["score"]
                metrics = best_t.get("metrics") or {}
                error = best_t.get("error")
                feedback = best_t["feedback"]
                revision_entry_matts.update({
                    "iteration": iteration, "phase": "revision", "prompt": prompt, "code": current_code,
                    "raw_llm_output": raw_output, "token_usage": token_usage,
                    "success": success, "score": score, "metrics": metrics, "error": error, "feedback": feedback, "reflection": None,
                })
                evaluator.iteration_history.append(revision_entry_matts)
                if score > evaluator.best_score:
                    evaluator.best_score = score
                    evaluator.best_code = current_code
                    evaluator.best_metrics = metrics
                if getattr(evaluator, "method", None) == "seal":
                    evaluator._seal_ttt_step()
                if success:
                    print(f"✅ Success at iteration {iteration}!")
                    break
                reasoning_bank_matts_done = True
                continue

        if not reasoning_bank_matts_done:
            try:
                new_code, raw_output, token_usage = evaluator.solver.generate_code(prompt)
                if new_code:
                    current_code = new_code
                else:
                    print(f"⚠️  Solver returned no code at iteration {iteration}")
                    break
            except Exception as e:
                print(f"❌ Solver error at iteration {iteration}: {e}")
                break

            # Mock in cross-mutation: do not "improve" (return ref so score stays baseline-consistent with test_mutated_tasks)
            if getattr(evaluator.solver, 'model_type', None) == 'mock':
                current_code = initial_ref_code

            try:
                save_this_gif = evaluator.save_gif
                gif_path = evaluator._get_gif_path(iteration) if save_this_gif else None
                success, score, metrics, error = evaluator.verifier.verify_code(
                    current_code, headless=evaluator.headless, save_gif_path=gif_path,
                    granularity=getattr(evaluator, "granularity", "outcome-based"),
                )
                if gif_path and os.path.exists(gif_path):
                    is_best = score > evaluator.best_score
                    if not is_best and not success:
                        try:
                            os.remove(gif_path)
                        except Exception:
                            pass
            except Exception as e:
                print(f"❌ Verification error at iteration {iteration}: {e}")
                success, score, metrics, error = False, 0.0, {}, str(e)

            failed = (metrics or {}).get("failed", False)
            failure_reason = (metrics or {}).get("failure_reason")
            feedback = evaluator._compose_feedback(
                metrics or {}, score, success, failed, failure_reason,
                iteration, error, include_suggestions=getattr(evaluator, "enable_feedback", False)
            )

            revision_entry = {
                "iteration": iteration,
                "phase": "revision",
                "code": current_code,
                "prompt": prompt,
                "success": success,
                "score": score,
                "metrics": metrics or {},
                "error": error,
                "feedback": feedback,
                "raw_llm_output": raw_output,
                "token_usage": token_usage,
                "reflection": None,
            }
            evaluator.iteration_history.append(revision_entry)

            # Reflexion: generate reflection after failed revision
            if not success and getattr(evaluator, "base_method", None) == "reflexion" and getattr(evaluator, "reflect_solver", None) is not None:
                try:
                    reflection = evaluator._generate_reflection(current_code, feedback, iteration)
                    evaluator.reflections.append(reflection)
                    evaluator.reflections_str = format_reflections_str(evaluator.reflections)
                    revision_entry["reflection"] = reflection
                except Exception as e:
                    print(f"⚠️  Reflexion (cross-mutation): failed to generate reflection: {e}")

            # ReasoningBank (single trajectory): store after iteration
            if base_method == "reasoning_bank" and getattr(evaluator, "_reasoning_bank_path", None):
                try:
                    import os as _os_rb
                    from methods.Memory.reasoning_bank_method import (
                        extract_memory_items_llm, store_after_iteration as rb_store,
                        judge_success_llm,
                    )
                    task_desc = (evaluator.task_prompt.get("task_description") or "") if isinstance(evaluator.task_prompt, dict) else str(evaluator.task_prompt)
                    _aux_k = getattr(evaluator, "_llm_aux_api_key", None)
                    _aux_u = getattr(evaluator, "_llm_aux_base_url", None)
                    if _aux_k is None:
                        from evaluation.solver_interface import get_aux_llm_credentials
                        _aux_k, _aux_u = get_aux_llm_credentials(None)
                    if _os_rb.environ.get("REASONING_BANK_LLM_JUDGE", "").lower() in ("1", "true", "yes"):
                        success_for_memory = judge_success_llm(
                            task_desc, current_code, feedback, score,
                            api_key=_aux_k,
                            base_url=_aux_u,
                        )
                    else:
                        success_for_memory = bool(success)
                    new_items = extract_memory_items_llm(
                        task_desc, current_code, feedback, score, success_for_memory,
                        api_key=_aux_k,
                        base_url=_aux_u,
                        raw_reasoning=(revision_entry.get("raw_llm_output") or None),
                    )
                    if new_items:
                        evaluator._reasoning_bank_items = rb_store(
                            evaluator._reasoning_bank_path, evaluator._reasoning_bank_items, new_items,
                        )
                        revision_entry["reasoning_bank_stored_items"] = new_items
                except Exception as e:
                    print(f"⚠️  ReasoningBank store after iter failed (non-fatal): {e}")

            # Memento non-parametric: store and reload memory
            if base_method == "memento_nonparametric" and getattr(evaluator, "_memento_memory_path", None):
                try:
                    from methods.Memory.memento_nonparametric_method import store_after_iteration as memento_store, load_memory
                    task_desc = (evaluator.task_prompt.get("task_description") or "") if isinstance(evaluator.task_prompt, dict) else str(evaluator.task_prompt)
                    entry = memento_store(
                        base_task_name, iteration, score, feedback, current_code,
                        evaluator._memento_memory_path, task_desc, success=success,
                        base_task_name=base_task_name,
                    )
                    revision_entry["memory_stored_entry"] = entry
                    evaluator._memento_items, evaluator._memento_pairs = load_memory(evaluator._memento_memory_path)
                except Exception as e:
                    print(f"⚠️  Memento store after iter failed (non-fatal): {e}")

            # A-mem-sys: store this iteration in memory for future retrieval
            if base_method == "a_mem_sys" and getattr(evaluator, "_a_mem_sys_memory", None):
                try:
                    from methods.Memory.a_mem_sys_method import store_after_iteration as a_mem_sys_store
                    stored = a_mem_sys_store(
                        base_task_name, iteration, score, feedback, current_code,
                        evaluator._a_mem_sys_memory,
                    )
                    revision_entry["a_mem_sys_stored"] = stored[:200] + "..." if len(stored) > 200 else stored
                except Exception as e:
                    print(f"⚠️  A-mem-sys store after iter failed (non-fatal): {e}")

            # ACE: reflect then curator update playbook for next iteration
            if base_method == "ace" and getattr(evaluator, "_ace_reflector", None) and getattr(evaluator, "_ace_curator", None):
                try:
                    from methods.Memory.ace_method import (
                        reflect_on_iteration, update_playbook_after_iteration,
                        parse_bullet_ids_from_output, extract_playbook_bullets,
                    )
                    task_desc = (evaluator.task_prompt.get("task_description") or "") if isinstance(evaluator.task_prompt, dict) else str(evaluator.task_prompt)
                    raw_out = revision_entry.get("raw_llm_output") or ""
                    bullet_ids = parse_bullet_ids_from_output(raw_out)
                    bullets_used = extract_playbook_bullets(evaluator._ace_playbook or "", bullet_ids) if bullet_ids else "(No bullets used by generator)"
                    reflection_content, bullet_tags, _ = reflect_on_iteration(
                        evaluator._ace_reflector,
                        question=task_desc,
                        reasoning_trace=current_code or "",
                        predicted_answer=current_code or "",
                        environment_feedback=feedback,
                        bullets_used=bullets_used,
                    )
                    evaluator._ace_playbook, evaluator._ace_next_global_id = update_playbook_after_iteration(
                        evaluator._ace_playbook or "",
                        reflection_content,
                        question_context=task_desc,
                        iteration=iteration,
                        max_iterations=evaluator.max_iterations,
                        token_budget=8000,
                        curator=evaluator._ace_curator,
                        bullet_tags=bullet_tags,
                        next_global_id=getattr(evaluator, "_ace_next_global_id", None),
                    )
                    revision_entry["ace_reflection_len"] = len(reflection_content)
                except Exception as e:
                    print(f"⚠️  ACE reflect/curate after iter failed (non-fatal): {e}")

            # Bootstrap for next iteration: ToT needs states; TextGrad needs current code in tg_code_var
            if getattr(evaluator, "base_method", None) == "tree_of_thought":
                tot_states = [evaluator.iteration_history[-1]]
            if getattr(evaluator, "base_method", None) == "textgrad":
                if getattr(evaluator, "tg_code_var", None) is None and current_code and getattr(evaluator, "tg_engine", None) is not None:
                    try:
                        from methods.Context.textgrad_method import init_textgrad_components
                        evaluator.tg_code_var, evaluator.tg_optimizer = init_textgrad_components(current_code, evaluator.tg_engine)
                        print("🧮 TextGrad: initialized Variable and Optimizer after first revision")
                    except Exception as e:
                        print(f"⚠️  TextGrad init after iter 1 failed (non-fatal): {e}")
                elif getattr(evaluator, "tg_code_var", None) is not None:
                    try:
                        evaluator.tg_code_var.set_value(current_code)
                    except Exception:
                        pass

            if score > evaluator.best_score:
                evaluator.best_score = score
                evaluator.best_code = current_code
                evaluator.best_metrics = metrics or {}

            if evaluator.method == "seal":
                evaluator._seal_ttt_step()

            if success:
                print(f"✅ Success at iteration {iteration}!")
                break

    evaluator.verifier.cleanup()
    return evaluator._generate_report()
