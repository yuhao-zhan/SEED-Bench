import os
import sys
import time
import random
import multiprocessing
import faulthandler
import fcntl  # Unix-based file locking

# Enable fault handler to see C-level stack trace on Segfault
faulthandler.enable()

def _safe_init_sdl():
    """Use a TRUE global file lock to ensure sequential initialization across subprocesses"""
    lock_file = "/tmp/seed_bench_sdl_init.lock"
    with open(lock_file, 'w') as f:
        try:
            # Acquire exclusive lock (blocks until available)
            fcntl.flock(f, fcntl.LOCK_EX)
            
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"
            os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
            os.environ["VLLM_ENABLE_V1_MULTIPROCESSING"] = "0"
            if "DISPLAY" in os.environ:
                del os.environ["DISPLAY"]
            
            # Short delay to let the OS/Driver settle
            time.sleep(1.0)
            
        finally:
            # Release lock
            fcntl.flock(f, fcntl.LOCK_UN)

# GLOBAL INITIALIZATION: This runs at the very start of every subprocess
_safe_init_sdl()

try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass

import argparse
import json
import glob
import traceback
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable=None, **kwargs):
        return iterable if iterable is not None else range(kwargs.get("total", 1))

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from evaluation.prompt import (
    load_task_prompt, format_initial_prompt, format_revision_prompt,
    format_revision_prompt_chat, format_revision_prompt_chat_simplified,
    format_revision_prompt_last_n,
    format_revision_prompt_best_score, format_revision_prompt_best_plus_previous,
    format_revision_prompt_memory_only,
    format_system_prompt_with_task,
    parse_task_name, get_all_tasks_in_category, get_all_tasks,
)
from methods.Context.reflexion_method import (
    REFLEXION_SYSTEM_PROMPT, format_reflection_prompt, format_reflections_str,
    format_revision_prompt_reflexion, format_revision_prompt_reflexion_simple,
)
from evaluation.feedback import format_feedback
from evaluation.solver_interface import SolverInterface
from evaluation.verifier import CodeVerifier
from evaluation.utils import (
    get_model_identifier, get_gif_path,
    get_gif_base_dir, get_evaluation_results_dir,
    run_is_complete, is_cuda_oom, clean_special_tags,
)


class TaskEvaluator:
    """Task evaluator"""
    
    def __init__(self, task_name: str, model_type: str = 'mock', model_name: str = 'gpt-4', 
                 api_key: Optional[str] = None, max_iterations: int = 5, max_steps: int = 10000,
                 headless: bool = True, model_path: Optional[str] = None, device: Optional[str] = None,
                 method: str = 'baseline', context: str = 'previous', env_overrides: Optional[Dict[str, Any]] = None,
                 task_prompt_override: Optional[Dict[str, Any]] = None, 
                 is_mutated_task: bool = False, reflect_model_name: Optional[str] = None,
                 textgrad_engine_name: Optional[str] = None, a_mem_sys_llm_model: Optional[str] = None,
                 initial_memory_system: Optional[Any] = None, base_task_name_for_memory: Optional[str] = None,
                 initial_playbook: Optional[str] = None, ace_reflector_model: Optional[str] = None,
                 ace_curator_model: Optional[str] = None,
                 n_select_sample: Optional[int] = None, n_generate_sample: Optional[int] = None,
                 reasoning_bank_k: Optional[int] = None, genome_best_lora_path: Optional[str] = None,
                 solver_override: Optional[Any] = None,
                 ragen_n_rollouts: int = 8, ragen_ppo_epochs: int = 2,
                 soar_generations: int = 2, soar_k_candidates: int = 4,
                 discover_num_epochs: int = 50, discover_group_size: int = 8,
                 discover_groups_per_batch: int = 64, discover_learning_rate: float = 4e-5,
                 discover_adv_estimator: str = 'entropic', discover_adv_estimator_beta: float = 2.0,
                 discover_loss_fn: str = 'importance_sampling', discover_lora_rank: int = 32,
                 discover_max_tokens: int = 65536, discover_temperature: float = 1.0,
                 discover_num_substeps: int = 1, discover_max_expansion_rounds: int = 2,
                 save_gif: bool = True):
        self.task_name = task_name
        self.save_gif = save_gif
        self.base_task_name_for_memory = base_task_name_for_memory
        
        if method == 'tree_of_thought':
            self.max_iterations = max_iterations
            self.n_select_sample = n_select_sample if n_select_sample is not None else 3
            self.n_generate_sample = n_generate_sample if n_generate_sample is not None else 2
        else:
            self.max_iterations = max_iterations
            self.n_select_sample = None
            self.n_generate_sample = None
            
        if method == 'self_refine':
            self.max_iterations = min(self.max_iterations, 20)
        if method == 'self_refine_inner_only':
            self.max_iterations = 1
            
        self.max_steps = max_steps
        self.headless = headless
        self.method = method
        self.context = context
        self.env_overrides = env_overrides
        self.is_mutated_task = is_mutated_task
        self.mutated_task_name = None  # Set by evaluate_mutated
        
        # Initialize solver
        if solver_override:
            self.solver = solver_override
        else:
            self.solver = SolverInterface(
                model_type=model_type,
                model_name=model_name,
                api_key=api_key,
                model_path=model_path,
                device=device
            )
        
        # Initialize verifier
        self.verifier = CodeVerifier(
            task_name=task_name,
            max_steps=max_steps,
            env_overrides=env_overrides
        )
        
        # Load task prompt
        if task_prompt_override:
            self.task_prompt = task_prompt_override
        else:
            self.task_prompt = load_task_prompt(task_name)
            
        # Evaluation state
        self.iteration_history = []
        self.best_score = -1.0
        self.best_code = None
        self.best_metrics = {}
        
        self._setup_gif_directory()

    def _setup_gif_directory(self):
        """Setup directory for saving GIF animations"""
        # Parse task name to get category and task subdirectories
        try:
            task_path, _ = parse_task_name(self.task_name)
            # task_path is like 'Category1_Statics_Equilibrium/S_01'
            cat_dir, task_subdir = task_path.split('/')
        except Exception:
            # Fallback for non-category tasks
            cat_dir = "other"
            task_subdir = self.task_name

        model_id = get_model_identifier(self.solver.model_type, self.solver.model_name)
        
        # Consistent with user request: gif/{category}/{task}/...
        # We still keep model and method to avoid overwriting between different models/methods
        self.gif_dir = os.path.join(
            get_gif_base_dir(),
            cat_dir,
            task_subdir,
            model_id,
            self.method
        )
        
        if self.save_gif:
            os.makedirs(self.gif_dir, exist_ok=True)

    def _get_gif_path(self, iteration: int) -> str:
        """Get GIF file path for current iteration"""
        task_label = self.mutated_task_name if self.is_mutated_task and self.mutated_task_name else "raw"
        # task_label is often "source_to_target" for cross-mutation
        filename = f"{self.context}_{task_label}_iter_{iteration}.gif"
        return os.path.join(self.gif_dir, filename)

    def evaluate(self):
        """Run iterative evaluation process"""
        print(f"🚀 Starting evaluation for task: {self.task_name}")
        print(f"Method: {self.method}, Context: {self.context}, Max Iterations: {self.max_iterations}")
        
        current_code = None
        
        # Reset solver conversation for new task
        self.solver.reset_conversation()
        
        # Special case for context='all': include task info in system prompt if needed
        if self.context == 'all':
            sys_prompt = format_system_prompt_with_task(self.solver.SYSTEM_PROMPT, self.task_prompt)
            self.solver.set_custom_system_prompt(sys_prompt)
            print("📝 Set system prompt with task information (context='all' mode)")

        pbar = tqdm(range(1, self.max_iterations + 1), desc=f"Evaluating {self.task_name}")
        
        for iteration in pbar:
            if not isinstance(pbar, range):
                pbar.set_postfix_str(f"iter {iteration}/{self.max_iterations}")
            
            print(f"\n{'='*60}")
            print(f"Iteration {iteration}/{self.max_iterations}")
            print(f"{'='*60}\n")
            
            # 1. Generate code
            if iteration == 1:
                prompt = format_initial_prompt(self.task_prompt)
            else:
                last_feedback = self.iteration_history[-1]['feedback']
                if self.context == 'previous':
                    prompt = format_revision_prompt(self.task_prompt, current_code, last_feedback)
                elif self.context == 'all':
                    prompt = format_revision_prompt_chat(self.task_prompt, last_feedback)
                else:
                    # Default fallback
                    prompt = format_revision_prompt(self.task_prompt, current_code, last_feedback)
            
            try:
                new_code, raw_output, token_usage = self.solver.generate_code(
                    prompt, 
                    use_conversation=(self.context == 'all')
                )
                if new_code:
                    current_code = new_code
            except Exception as e:
                print(f"❌ Error generating code: {e}")
                break
                
            # 2. Verify code
            gif_path = get_gif_path(self.gif_dir, self.context, iteration)
            success, score, metrics, error = self.verifier.verify_code(
                current_code, 
                headless=self.headless,
                save_gif_path=gif_path if self.save_gif else None
            )
            
            # 3. Handle GIF cleanup
            if self.save_gif and gif_path and os.path.exists(gif_path):
                # Keep if success, first iteration, or new best score
                is_best = score > self.best_score
                if not success and not is_best and iteration > 1:
                    try:
                        os.remove(gif_path)
                    except:
                        pass

            # 4. Format feedback
            failed = metrics.get('failed', False)
            failure_reason = metrics.get('failure_reason', 'Unknown failure')
            feedback = format_feedback(
                metrics, score, success, failed, failure_reason,
                iteration, error=error, task_name=self.task_name
            )
            
            # 4. Record iteration
            self.iteration_history.append({
                'iteration': iteration,
                'prompt': prompt,
                'code': current_code,
                'success': success,
                'score': score,
                'metrics': metrics,
                'error': error,
                'feedback': feedback,
                'raw_llm_output': raw_output,
                'token_usage': token_usage
            })
            
            # 5. Update best
            if score > self.best_score:
                self.best_score = score
                self.best_code = current_code
                self.best_metrics = metrics
                print(f"🎯 New best score: {score:.1f}/100")
            
            if success:
                print(f"✅ Task solved in {iteration} iterations!")
                break
                
        return self._generate_report()

    def _generate_report(self):
        """Generate final evaluation report"""
        report = {
            'task_name': self.task_name,
            'method': self.method,
            'context': self.context,
            'success': self.best_score >= 100.0,
            'best_score': self.best_score,
            'best_code': self.best_code,
            'best_metrics': self.best_metrics,
            'iterations': len(self.iteration_history),
            'history': self.iteration_history
        }
        return report

    def print_report(self, report):
        """Print summary of evaluation results"""
        print(f"\n{'='*80}")
        print(f"📊 Final Report for {self.task_name}")
        print(f"{'='*80}")
        print(f"Success: {'✅ Yes' if report['success'] else '❌ No'}")
        print(f"Best Score: {report['best_score']:.1f}/100")
        print(f"Total Iterations: {report['iterations']}")
        if report['best_metrics']:
            print(f"Failure Reason: {report['best_metrics'].get('failure_reason', 'None')}")
        print(f"{'='*80}\n")

    def save_report(self, report, output_dir='evaluation_results'):
        """Save evaluation report to JSON file"""
        # Parse task name to get category and task subdirectories
        try:
            task_path, _ = parse_task_name(self.task_name)
            # task_path is like 'Category1_Statics_Equilibrium/S_01'
            cat_dir, task_subdir = task_path.split('/')
        except Exception:
            # Fallback for non-category tasks
            cat_dir = "other"
            task_subdir = self.task_name

        model_id = get_model_identifier(self.solver.model_type, self.solver.model_name)
        
        # Consistent with user request: evaluation_results/{category}/{task}/...
        # We still keep model and method to avoid overwriting between different models/methods
        task_dir = os.path.join(output_dir, cat_dir, task_subdir, model_id, self.method)
        os.makedirs(task_dir, exist_ok=True)
        
        task_label = self.mutated_task_name if self.is_mutated_task and self.mutated_task_name else "raw"
        filename = f"{self.context}_{task_label}.json"
        
        save_path = os.path.join(task_dir, filename)
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            print(f"📄 Evaluation report saved: {save_path}")
        except OSError as e:
            if e.errno == 122: # Disk quota exceeded
                print(f"⚠️  Disk quota exceeded while saving report: {save_path}")
                # Try to disable GIF saving globally for future runs
                try:
                    from common.simulator import Simulator
                    Simulator._global_skip_gif = True
                except:
                    pass
            # Re-raise the error as requested: "没地方保存json就直接报错"
            raise e
        return save_path


def resolve_task_list(task_spec: str) -> List[str]:
    """Resolve task specification to a list of task names"""
    if task_spec == 'all':
        return get_all_tasks()
    
    if task_spec.startswith('category_'):
        parts = task_spec.split('_')
        if len(parts) == 2:  # category_X
            return get_all_tasks_in_category(int(parts[1]))
        else:  # category_X_YY
            return [task_spec]
            
    return [task_spec]


def evaluate_single_task(task_name, args):
    """
    Unified entry point for a single task evaluation.
    Each task is run ONLY ONCE.
    """
    # Force dummy video driver for headless stability in parallel mode
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    import time, random
    time.sleep(random.uniform(0.1, 0.5)) # Tiny random jitter to avoid SDL initialization peaks
    
    print(f"\n{'='*80}")
    print(f"Evaluating task: {task_name}")
    print(f"{'='*80}\n")
    
    # Cross-mutation pair?
    current_mutated_name = None
    if getattr(args, 'source_env', None) and getattr(args, 'target_env', None):
        current_mutated_name = f"{args.source_env}_to_{args.target_env}"

    # Check if complete
    if run_is_complete(
        task_name=task_name,
        model_type=args.model_type,
        model_name=args.model_name,
        method=args.method,
        context=args.context,
        mutated_task_name=current_mutated_name
    ):
        pair_label = f" [{current_mutated_name}]" if current_mutated_name else ""
        print(f"✅ Task {task_name}{pair_label}: Already complete. Skipping.")
        return 0

    max_steps = 150000 if task_name == 'category_2_06' else args.max_steps

    # Execute evaluation
    try:
        is_category_task = task_name.startswith('category_')
        is_mutation_capable = is_category_task and not args.method in ['alpha_evolve', 'theta_evolve', 'genome', 'seal', 'ragen', 'soar', 'discover']
        
        if is_mutation_capable:
            from evaluation.evaluate_cross_mutated import run_cross_mutation_evaluation, run_single_pair, get_all_stages, get_reference_solution
            
            if getattr(args, 'source_env', None) and getattr(args, 'target_env', None):
                source_env = args.source_env
                target_env = args.target_env
                pair_name = f"{source_env}_to_{target_env}"
                
                print(f"🚀 Running Cross-Mutation Pair: {pair_name}")
                
                all_envs = get_all_stages(task_name)
                env_i = next((e for e in all_envs if e["stage_id"] == source_env), None)
                env_j = next((e for e in all_envs if e["stage_id"] == target_env), None)
                if not env_j: raise ValueError(f"Target env {target_env} not found")
                if not env_i: env_i = {"terrain_config": {}}
                
                try:
                    ref_code = get_reference_solution(task_name, source_env)
                except Exception as e:
                    print(f"⏭️  Skipping pair {pair_name}: reference solution for {source_env} not found: {e}")
                    return 0
                
                # Compute task_prompt_override
                from evaluation.prompt import parse_task_name, load_task_prompt
                import importlib.util
                task_path, _ = parse_task_name(task_name)
                script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                task_dir = os.path.join(script_dir, 'tasks', task_path)
                stages_file = os.path.join(task_dir, 'stages.py')
                
                update_desc_func = None
                update_criteria_func = None
                if os.path.exists(stages_file):
                    spec = importlib.util.spec_from_file_location("task_stages", stages_file)
                    stages_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(stages_mod)
                    for name in dir(stages_mod):
                        if 'update_task_description_for_visible_changes' in name.lower() and callable(getattr(stages_mod, name)):
                            update_desc_func = getattr(stages_mod, name)
                        if 'update_success_criteria_for_visible_changes' in name.lower() and callable(getattr(stages_mod, name)):
                            update_criteria_func = getattr(stages_mod, name)

                base_prompt = load_task_prompt(task_name)
                task_prompt_override = dict(base_prompt)
                desc = base_prompt.get("task_description", "")
                criteria = base_prompt.get("success_criteria", "")
                
                target_terrain = env_j.get("terrain_config", {})
                base_terrain = env_i.get("terrain_config", {})
                
                if update_desc_func:
                    desc = update_desc_func(desc, target_terrain, base_terrain)
                if update_criteria_func:
                    criteria = update_criteria_func(criteria, target_terrain, base_terrain)
                    
                suffix = env_j.get("task_description_suffix", "")
                if suffix:
                    desc += "\n" + suffix
                    
                task_prompt_override["task_description"] = desc
                task_prompt_override["success_criteria"] = criteria
                
                evaluator = TaskEvaluator(
                    task_name=task_name,
                    model_type=args.model_type,
                    model_name=args.model_name,
                    api_key=args.api_key,
                    max_iterations=args.max_iterations,
                    max_steps=max_steps,
                    headless=True,
                    method=args.method,
                    context=args.context,
                    env_overrides={"terrain_config": env_j.get("terrain_config", {}), "physics_config": env_j.get("physics_config", {})},
                    is_mutated_task=True,
                    task_prompt_override=task_prompt_override,
                    save_gif=args.save_gif
                )
                evaluator.mutated_task_name = pair_name
                
                report = run_single_pair(evaluator, ref_code, task_name, pair_name)
                if not report.get('skipped'):
                    evaluator.save_report(report, output_dir='evaluation_results')
            else:
                # Run full suite
                run_cross_mutation_evaluation(
                    base_task_name=task_name,
                    model_type=args.model_type,
                    model_name=args.model_name,
                    method=args.method,
                    context=args.context,
                    max_iterations=args.max_iterations,
                    max_steps=max_steps,
                    headless=True,
                    api_key=args.api_key,
                    output_dir='evaluation_results',
                    save_gif=args.save_gif
                )
        else:
            evaluator = TaskEvaluator(
                task_name=task_name,
                model_type=args.model_type,
                model_name=args.model_name,
                api_key=args.api_key,
                max_iterations=args.max_iterations,
                max_steps=max_steps,
                headless=True,
                method=args.method,
                context=args.context,
                save_gif=args.save_gif
            )
            report = evaluator.evaluate()
            evaluator.print_report(report)
            evaluator.save_report(report, output_dir='evaluation_results')
            evaluator.verifier.cleanup()
            
        return 0
    except KeyboardInterrupt:
        print("\n🛑 Evaluation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        err_msg = str(e).lower()
        # Detect fatal API errors that should stop the entire process
        fatal_keywords = ["insufficient quota", "rate limit", "authentication failed", "429", "insufficient_quota", "too many requests"]
        if any(k in err_msg for k in fatal_keywords):
            print(f"\n🛑 FATAL API ERROR in {task_name}: {e}")
            sys.exit(99) # Exit with specific code for run_evaluate_parallel to pick up
        
        print(f"❌ Evaluation failed for {task_name}: {e}")
        traceback.print_exc()
        return 1


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Task evaluator')
    parser.add_argument('--task', type=str, nargs='+', default=['basic'],
                       help='Task(s) to evaluate.')
    parser.add_argument('--model-type', type=str, default='mock', choices=['openai', 'local', 'mock'])
    parser.add_argument('--model-name', type=str, default='deepseek-v3.2')
    parser.add_argument('--api-key', type=str, default=None)
    parser.add_argument('--model-path', type=str, default=None)
    parser.add_argument('--device', type=str, default='auto')
    parser.add_argument('--max-iterations', type=int, default=20)
    parser.add_argument('--max-steps', type=int, default=10000)
    parser.add_argument('--method', type=str, default='baseline', 
                       choices=['baseline', 'sys_feedback', 'reflexion', 'textgrad', 'self_refine', 'self_refine_inner_only', 'a_mem_sys', 'memento_nonparametric', 'rememberer', 'expel', 'ace', 'tree_of_thought', 'reasoning_bank', 'absolute_zero', 'absolute_zero_iter', 'science_codeevolve', 'alpha_evolve', 'theta_evolve', 'genome', 'seal', 'ragen', 'soar', 'discover'])
    parser.add_argument('--context', type=str, default='all',
                       choices=['previous', 'all', 'last_3', 'best_score', 'best_score_plus_previous'])
    parser.add_argument('--source-env', type=str, default=None)
    parser.add_argument('--target-env', type=str, default=None)
    parser.add_argument('--save-gif', action='store_true', default=True, help='Save GIF animations of simulations')
    parser.add_argument('--no-save-gif', action='store_false', dest='save_gif', help='Disable saving GIF animations')
    
    args = parser.parse_args()

    if len(args.task) == 1:
        task_list = resolve_task_list(args.task[0])
    else:
        task_list = list(args.task)
    
    if not task_list:
        print(f"❌ No tasks found for specification: {args.task}")
        return 1
    
    results = []
    for task_name in task_list:
        exit_code = evaluate_single_task(task_name, args)
        results.append((task_name, exit_code))
    
    return 0 if all(code == 0 for _, code in results) else 1


if __name__ == "__main__":
    sys.exit(main())
