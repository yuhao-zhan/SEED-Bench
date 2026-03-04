#!/usr/bin/env python3
"""
Cross-Mutation evaluation module.
Pairs all environments (Initial + Stages) to evaluate adaptive capability.
Total 20 pairs: (env_i, env_j) for i != j.
Agent starts with reference solution of env_i and tries to solve env_j.
All experiments are run ONLY ONCE.
"""
import os
import sys
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

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
from evaluation.utils import get_model_identifier

def get_all_stages(base_task_name: str) -> List[Dict[str, Any]]:
    """Get initial task + all curriculum stages."""
    from evaluation.prompt import parse_task_name
    import importlib.util
    
    try:
        task_path, _ = parse_task_name(base_task_name)
    except Exception as e:
        print(f"⚠️  Failed to parse task name {base_task_name}: {e}")
        return []

    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    task_dir = os.path.join(script_dir, 'tasks', task_path)
    stages_file = os.path.join(task_dir, 'stages.py')
    
    all_envs = []
    all_envs.append({
        "stage_id": "Initial",
        "title": "Initial Task",
        "terrain_config": {},
        "physics_config": {}
    })
    
    if os.path.exists(stages_file):
        try:
            spec = importlib.util.spec_from_file_location("task_stages", stages_file)
            stages_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(stages_mod)
            
            curriculum_func = None
            for name in dir(stages_mod):
                if 'curriculum_stages' in name.lower() and callable(getattr(stages_mod, name)):
                    curriculum_func = getattr(stages_mod, name)
                    break
            
            if curriculum_func:
                stages = curriculum_func()
                all_envs.extend(stages)
        except Exception as e:
            print(f"⚠️  Failed to load stages from {stages_file}: {e}")
            
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

    # Identify all stage entry point functions to exclude those that aren't our target
    stage_funcs = set()
    for line in lines:
        if line.startswith("def "):
            # Extract function name before '('
            name = line.split("(")[0][4:].strip()
            if name.startswith("build_agent") or name.startswith("agent_action"):
                stage_funcs.add(name)

    targets = {build_func, action_func}
    to_exclude = stage_funcs - targets

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
                                 method: str, context: str = 'previous', max_iterations: int = 10,
                                 max_steps: int = 10000, headless: bool = True, api_key: Optional[str] = None,
                                 output_dir: str = "evaluation_results", save_gif: bool = True):
    """
    Run the new paradigm: all-pairs evaluation.
    Total pairs = N * (N-1). For N=5, pairs=20.
    """
    all_envs = get_all_stages(base_task_name)
    num_envs = len(all_envs)
    
    print(f"\n🚀 Starting Cross-Mutation Evaluation for {base_task_name}")
    print(f"Total Environments: {num_envs}")
    print(f"Total Pairs: {num_envs * (num_envs - 1)}")
    
    # Load stages module for visible changes
    from evaluation.prompt import parse_task_name
    import importlib.util
    task_path, _ = parse_task_name(base_task_name)
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    task_dir = os.path.join(script_dir, 'tasks', task_path)
    stages_file = os.path.join(task_dir, 'stages.py')
    
    stages_mod = None
    update_desc_func = None
    update_criteria_func = None
    if os.path.exists(stages_file):
        try:
            spec = importlib.util.spec_from_file_location("task_stages", stages_file)
            stages_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(stages_mod)
            for name in dir(stages_mod):
                if 'update_task_description_for_visible_changes' in name.lower() and callable(getattr(stages_mod, name)):
                    update_desc_func = getattr(stages_mod, name)
                if 'update_success_criteria_for_visible_changes' in name.lower() and callable(getattr(stages_mod, name)):
                    update_criteria_func = getattr(stages_mod, name)
        except Exception as e:
            print(f"⚠️  Failed to load stages module for updates: {e}")

    results = []
    
    for i, env_i in enumerate(all_envs):
        try:
            ref_code = get_reference_solution(base_task_name, env_i["stage_id"])
        except Exception as e:
            print(f"⚠️  Failed to get reference solution for {env_i['stage_id']}: {e}")
            continue
            
        for j, env_j in enumerate(all_envs):
            if i == j: continue
            
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
                base_terrain = env_i.get("terrain_config", {})
                
                if update_desc_func:
                    desc = update_desc_func(desc, target_terrain, base_terrain)
                if update_criteria_func:
                    criteria = update_criteria_func(criteria, target_terrain, base_terrain)
                
                # Add suffix from target environment if it exists
                suffix = env_j.get("task_description_suffix", "")
                if suffix:
                    desc += "\n" + suffix
                
                task_prompt_override["task_description"] = desc
                task_prompt_override["success_criteria"] = criteria
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
                    save_gif=save_gif
                )
                evaluator.mutated_task_name = pair_name
                evaluator._setup_gif_directory()

                report = run_single_pair(evaluator, ref_code, base_task_name, pair_name)
                if not report.get('skipped'):
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
            initial_ref_code, headless=evaluator.headless, save_gif_path=gif_path_0
        )
    except Exception as e:
        print(f"❌ Verification error at iteration 0: {e}")
        success_0, score_0, metrics_0, error_0 = False, 0.0, {}, str(e)
    failed_0 = metrics_0.get('failed', False) if metrics_0 else True
    failure_reason_0 = metrics_0.get('failure_reason') if metrics_0 else "Unknown error"
    feedback_0 = format_feedback(
        metrics_0 or {}, score_0, success_0, failed_0, failure_reason_0,
        0, error=error_0, task_name=base_task_name
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

    for iteration in range(1, evaluator.max_iterations + 1):
        print(f"Iteration {iteration}/{evaluator.max_iterations} (revision)")
        gif_path = evaluator._get_gif_path(iteration) if evaluator.save_gif else None

        # Build prompt for this revision (prompt that will produce the code we run in this iteration)
        if iteration == 1:
            prompt = format_mutated_prompt(evaluator.task_prompt, initial_ref_code, ref_feedback)
        else:
            best_item = max(evaluator.iteration_history, key=lambda x: x['score'])
            previous_item = evaluator.iteration_history[-1]
            if evaluator.context == 'all' or evaluator.context == 'best_score_plus_previous':
                prompt = format_mutated_revision_prompt_best_plus_previous(
                    evaluator.task_prompt, initial_ref_code, evaluator.iteration_history[0]['feedback'],
                    best_item['code'], best_item['feedback'],
                    previous_item['code'], previous_item['feedback'],
                    previous_item['feedback'],
                    best_item['iteration'], previous_item['iteration'], iteration
                )
            else:
                prompt = format_mutated_revision_prompt(
                    evaluator.task_prompt, initial_ref_code, evaluator.iteration_history[0]['feedback'],
                    previous_item['code'], previous_item['feedback'],
                    previous_item['feedback']
                )

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
            # Only save GIF if it's potentially the best or last iteration
            save_this_gif = evaluator.save_gif
            gif_path = evaluator._get_gif_path(iteration) if save_this_gif else None
            
            success, score, metrics, error = evaluator.verifier.verify_code(
                current_code, headless=evaluator.headless, save_gif_path=gif_path
            )
            
            # If not best and not success, delete the GIF to save space
            if gif_path and os.path.exists(gif_path):
                is_best = score > evaluator.best_score
                if not is_best and not success:
                    try:
                        os.remove(gif_path)
                    except:
                        pass
                elif is_best:
                    # Optional: remove previous best GIFs if they weren't successful
                    # For now, keeping it simple: just keep the new best
                    pass
                    
        except Exception as e:
            print(f"❌ Verification error at iteration {iteration}: {e}")
            success, score, metrics, error = False, 0.0, {}, str(e)

        failed = metrics.get('failed', False) if metrics else True
        failure_reason = metrics.get('failure_reason') if metrics else "Unknown error"
        feedback = format_feedback(
            metrics or {}, score, success, failed, failure_reason,
            iteration, error=error, task_name=base_task_name
        )

        evaluator.iteration_history.append({
            'iteration': iteration,
            'code': current_code,
            'prompt': prompt,
            'success': success,
            'score': score,
            'metrics': metrics or {},
            'error': error,
            'feedback': feedback,
        })

        if score > evaluator.best_score:
            evaluator.best_score = score
            evaluator.best_code = current_code
            evaluator.best_metrics = metrics or {}

        if success:
            print(f"✅ Success at iteration {iteration}!")
            break

    evaluator.verifier.cleanup()
    return evaluator._generate_report()
