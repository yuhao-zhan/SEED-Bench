#!/usr/bin/env python3
"""
Mutated environment evaluation module
Handles task sequences with environment mutations.
Automatically reads from previous task's log file and continues sequence.
"""
import os
import sys
import json
import glob
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from evaluation.prompt import (
    load_task_prompt,
    format_initial_prompt,
    format_mutated_prompt,
    format_mutated_revision_prompt,
    format_mutated_revision_prompt_best_plus_previous,
    format_revision_prompt,
    format_revision_prompt_chat,
)
from methods.Context.reflexion_method import format_reflections_str
from evaluation.feedback import format_feedback
from evaluation.solver_interface import SolverInterface
from evaluation.verifier import CodeVerifier
from evaluation.evaluate import TaskEvaluator
from evaluation.utils import get_model_identifier, load_log_file, is_cuda_oom


def find_latest_log_file(task_name: str, model_type: str, model_name: str, method: str,
                         output_dir: str = "evaluation_results") -> Optional[str]:
    model_identifier = get_model_identifier(model_type, model_name)
    log_dir = os.path.join(output_dir, task_name, model_identifier, method)
    
    if not os.path.exists(log_dir):
        return None
    
    # Find all JSON files in the directory
    pattern = os.path.join(log_dir, "*.json")
    log_files = glob.glob(pattern)
    
    if not log_files:
        return None
    
    # Sort by modification time (newest first)
    log_files.sort(key=os.path.getmtime, reverse=True)
    return log_files[0]




def get_mutation_sequence(base_task_name: str) -> List[str]:
    from evaluation.prompt import parse_task_name
    import importlib.util
    
    # Parse task name to get file system path
    task_path, module_path = parse_task_name(base_task_name)
    
    # Build full path to task directory
    script_dir = os.path.dirname(os.path.dirname(__file__))
    task_dir = os.path.join(script_dir, 'tasks', task_path)
    
    # Check if task directory has stages.py (internal curriculum)
    stages_file = os.path.join(task_dir, 'stages.py')
    if os.path.exists(stages_file):
        try:
            # Load stages module
            spec = importlib.util.spec_from_file_location("task_stages", stages_file)
            stages_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(stages_mod)
            
            # Find curriculum stages function (look for functions containing 'curriculum_stages' in name)
            curriculum_func = None
            for name in dir(stages_mod):
                if 'curriculum_stages' in name.lower() and callable(getattr(stages_mod, name)):
                    curriculum_func = getattr(stages_mod, name)
                    break
            
            if curriculum_func:
                stages = curriculum_func()
                # Return stage IDs as sequence tokens
                return [s["stage_id"] for s in stages]
        except Exception as e:
            print(f"⚠️  Failed to load stages from {stages_file}: {e}")
            # Fall back to directory-based discovery
            pass

    # Fallback: directory-based mutated tasks under tasks/
    tasks_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tasks")
    if not os.path.exists(tasks_dir):
        return []

    mutated_tasks: List[str] = []
    for item in os.listdir(tasks_dir):
        item_path = os.path.join(tasks_dir, item)
        if os.path.isdir(item_path) and item.startswith(base_task_name + "_"):
            required_files = ["environment.py", "evaluator.py", "prompt.py"]
            if all(os.path.exists(os.path.join(item_path, f)) for f in required_files):
                mutated_tasks.append(item)

    mutated_tasks.sort()
    return mutated_tasks


# Lock for thread-safe JSON file writes during parallel mutation execution
_json_write_lock = threading.Lock()


def _append_mutation_to_base_log(base_log_path: Optional[str], mutation_entry: Dict[str, Any],
                                  mutation_index: int, mutation_sequence: List[str]):
    """Append a single mutation result to the base log file (thread-safe, idempotent)."""
    if not base_log_path or not os.path.exists(base_log_path):
        return
    with _json_write_lock:
        try:
            with open(base_log_path, 'r', encoding='utf-8') as f:
                base_log_data = json.load(f)
            
            # Initialize mutation_sequence section if not exists
            if 'mutation_sequence' not in base_log_data:
                base_log_data['mutation_sequence'] = {
                    'total_mutations': len(mutation_sequence),
                    'completed_mutations': 0,
                    'success_rate': 0.0,
                    'sequence_results': [],
                    'timestamp': datetime.now().isoformat()
                }
            
            # Avoid duplicates by mutation_index
            existing_indices = {
                r.get('mutation_index')
                for r in base_log_data['mutation_sequence'].get('sequence_results', [])
            }
            if mutation_index not in existing_indices:
                base_log_data['mutation_sequence']['sequence_results'].append(mutation_entry)
            
            # Sort sequence_results by mutation_index for consistent ordering
            base_log_data['mutation_sequence']['sequence_results'].sort(
                key=lambda r: r.get('mutation_index', 0)
            )
            
            # Update completed count and success rate
            completed = len([
                r for r in base_log_data['mutation_sequence']['sequence_results']
                if r.get('result', {}).get('success', False)
            ])
            total = len(mutation_sequence) if mutation_sequence else 1
            base_log_data['mutation_sequence']['completed_mutations'] = completed
            base_log_data['mutation_sequence']['success_rate'] = completed / total
            base_log_data['mutation_sequence']['timestamp'] = datetime.now().isoformat()
            
            with open(base_log_path, 'w', encoding='utf-8') as f:
                json.dump(base_log_data, f, indent=2, ensure_ascii=False)
            
            mutated_name = mutation_entry.get('mutated_task_name', f'index-{mutation_index}')
            print(f"📝 Mutation {mutated_name} result appended to base log file")
        except Exception as e:
            print(f"⚠️  Failed to append mutation result to base log file: {e}")
            import traceback
            traceback.print_exc()


def run_mutation_sequence(base_task_name: str, model_type: str, model_name: str,
                          method: str, context: str = 'previous', max_iterations: int = 20, max_steps: int = 10000,
                          headless: bool = True, api_key: Optional[str] = None,
                          model_path: Optional[str] = None, device: Optional[str] = None,
                          output_dir: str = "evaluation_results", initial_code: Optional[str] = None,
                          base_log_path: Optional[str] = None,
                          reflect_model_name: Optional[str] = None,
                          textgrad_engine_name: Optional[str] = None,
                          a_mem_sys_llm_model: Optional[str] = None,
                          ace_reflector_model: Optional[str] = None,
                          ace_curator_model: Optional[str] = None,
                          n_select_sample: Optional[int] = None,
                          n_generate_sample: Optional[int] = None,
                          reasoning_bank_k: Optional[int] = None,
                          solver_override: Optional[Any] = None,
                          save_gif: bool = True) -> Dict[str, Any]:
    """
    Run mutation sequence evaluation.
    
    Each mutated task (Stage) is INDEPENDENT:
      - Every Stage always starts from the raw (base task) best_code.
      - If a Stage fails, we still continue to the next Stage.
      - For API models (openai, anthropic, etc.): mutations run in PARALLEL via ThreadPoolExecutor.
      - For local/huggingface models: mutations run sequentially (single model instance).
    """
    print(f"\n{'='*60}")
    print(f"Starting mutation sequence evaluation")
    print(f"Base task: {base_task_name}")
    print(f"Model: {model_type}/{model_name}")
    print(f"Method: {method}")
    print(f"NOTE: Each mutated task is independent (always uses raw best_code)")
    print(f"{'='*60}\n")
    
    # Get mutation sequence
    mutation_sequence = get_mutation_sequence(base_task_name)
    if not mutation_sequence:
        print(f"⚠️  No mutated tasks found for {base_task_name}")
        return {
            'base_task_name': base_task_name,
            'model_type': model_type,
            'model_name': model_name,
            'method': method,
            'total_mutations': 0,
            'completed_mutations': 0,
            'sequence_results': [],
            'error': 'No mutated tasks found'
        }
    
    print(f"Found {len(mutation_sequence)} mutated tasks: {mutation_sequence}\n")
    if solver_override and model_type == 'local':
        print(f"🔄 Reusing base task's vLLM model for mutations (avoids OOM from reloading)\n")
    
    # ReasoningBank: resolve k from base log if not provided
    if method == 'reasoning_bank' and reasoning_bank_k is None and base_log_path and os.path.exists(base_log_path):
        try:
            _bl = load_log_file(base_log_path)
            reasoning_bank_k = _bl.get('reasoning_bank_k', 2)
        except Exception:
            reasoning_bank_k = 2
    if method == 'reasoning_bank' and reasoning_bank_k is None:
        reasoning_bank_k = 2
    
    sequence_results = []
    raw_best_code = None          # The raw (base task) best code — never changes across mutations
    completed_indices = set()     # Track which mutation indices are already processed
    genome_best_lora_path = None  # GENOME: from base log when method == 'genome'

    # ── Determine raw_best_code and which mutations are already done ──
    if initial_code:
        print(f"📝 Using provided initial code (length: {len(initial_code)} characters)")
        raw_best_code = initial_code

        # Check base_log for already-completed mutation results and (for genome) genome_best_lora_path
        if base_log_path and os.path.exists(base_log_path):
            try:
                with open(base_log_path, 'r', encoding='utf-8') as f:
                    base_log_data = json.load(f)
                if method == 'genome':
                    genome_best_lora_path = base_log_data.get('genome_best_lora_path')
                if 'mutation_sequence' in base_log_data:
                    existing_results = base_log_data['mutation_sequence'].get('sequence_results', [])
                    for result in existing_results:
                        idx = result.get('mutation_index')
                        if idx is not None:
                            completed_indices.add(idx)
                    if completed_indices:
                        print(f"🔄 Found {len(completed_indices)} already-processed mutations, will skip them")
            except Exception as e:
                print(f"⚠️  Failed to read mutation_sequence from base_log_path: {e}")
    else:
        # Get raw_best_code from base task log
        if base_log_path and os.path.exists(base_log_path):
            print(f"📄 Using provided base log path: {base_log_path}")
            base_log = load_log_file(base_log_path)
        else:
            base_log_path = find_latest_log_file(base_task_name, model_type, model_name, method, output_dir)
            if base_log_path:
                print(f"📄 Found base task log: {base_log_path}")
                base_log = load_log_file(base_log_path)
            else:
                base_log = None
        
        if not base_log_path or not base_log:
            print(f"⚠️  No base task log found, cannot start mutation sequence")
            return {
                'base_task_name': base_task_name,
                'model_type': model_type,
                'model_name': model_name,
                'method': method,
                'total_mutations': len(mutation_sequence),
                'completed_mutations': 0,
                'sequence_results': [],
                'error': 'Base task log not found'
            }
        
        # Extract raw_best_code from base task (this is the ONLY code we use for all mutations)
        raw_best_code = base_log.get('best_code')
        if not raw_best_code:
            print(f"❌ No best_code in base task log, cannot start mutation sequence")
            return {
                'base_task_name': base_task_name,
                'model_type': model_type,
                'model_name': model_name,
                'method': method,
                'total_mutations': len(mutation_sequence),
                'completed_mutations': 0,
                'sequence_results': [],
                'error': 'No best_code in base task log'
            }
        genome_best_lora_path = base_log.get('genome_best_lora_path') if method == 'genome' else None
        
        if base_log.get('success'):
            print(f"✅ Base task succeeded, using best_code as raw code for ALL mutations")
        else:
            print(f"⚠️  Base task did not succeed, but using best_code anyway")
        
        # Check for already-completed mutations (skip regardless of success/failure)
        if 'mutation_sequence' in base_log:
            existing_results = base_log['mutation_sequence'].get('sequence_results', [])
            for result in existing_results:
                idx = result.get('mutation_index')
                if idx is not None:
                    completed_indices.add(idx)
            if completed_indices:
                print(f"🔄 Found {len(completed_indices)} already-processed mutations, will skip them")
    
    # ── Phase 1: Pre-filter — determine which mutations need evaluation ──
    mutations_to_run = []  # List of dicts: {idx, mutated_task_name, log_task_name, already_succeeded}
    
    if not raw_best_code:
        print(f"❌ No raw best code available, cannot evaluate mutations")
        return {
            'base_task_name': base_task_name, 'model_type': model_type,
            'model_name': model_name, 'method': method,
            'total_mutations': len(mutation_sequence), 'completed_mutations': 0,
            'sequence_results': [], 'error': 'No raw best code available'
        }
    
    for idx, mutated_task_name in enumerate(mutation_sequence):
        # Skip mutations that were already processed
        if idx in completed_indices:
            print(f"⏭️  Skipping mutation {idx + 1}/{len(mutation_sequence)}: {mutated_task_name} (already processed)")
            continue
        
        # For internal curriculum stages (Stage-*), we store logs under a synthetic name.
        log_task_name = mutated_task_name
        if mutated_task_name.startswith("Stage-"):
            log_task_name = f"{base_task_name}_curriculum_{mutated_task_name}"

        # Check if this mutation already has results in base_log_path's mutation_sequence
        already_in_base_log = False
        if base_log_path and os.path.exists(base_log_path):
            try:
                with open(base_log_path, 'r', encoding='utf-8') as f:
                    base_log_data = json.load(f)
                
                if 'mutation_sequence' in base_log_data:
                    existing_results = base_log_data['mutation_sequence'].get('sequence_results', [])
                    for existing_result in existing_results:
                        if existing_result.get('mutation_index') == idx:
                            already_in_base_log = True
                            result_data = existing_result.get('result', {})
                            if result_data.get('success', False):
                                print(f"✅ Mutation {mutated_task_name} already succeeded in base log, skipping")
                            else:
                                print(f"⚠️  Mutation {mutated_task_name} already failed in base log, skipping")
                            sequence_results.append(existing_result)
                            break
            except Exception as e:
                print(f"⚠️  Failed to check mutation_sequence in base_log_path: {e}")
        
        if already_in_base_log:
            continue

        # Check if this mutation already has a log (independent log file)
        already_succeeded = False
        mutation_log_path = find_latest_log_file(log_task_name, model_type, model_name, method, output_dir)
        if mutation_log_path:
            mutation_log = load_log_file(mutation_log_path)
            if mutation_log and mutation_log.get('success'):
                print(f"✅ Mutation {mutated_task_name} already succeeded (independent log)")
                print(f"🔄 Will re-run to generate GIF...")
                already_succeeded = True  # Still need to run for GIF
            elif mutation_log and not mutation_log.get('success'):
                print(f"⚠️  Mutation {mutated_task_name} already failed (independent log), skipping")
                mutation_entry = {
                    'mutated_task_name': mutated_task_name,
                    'mutation_index': idx,
                    'status': 'already_failed',
                    'result': mutation_log
                }
                sequence_results.append(mutation_entry)
                _append_mutation_to_base_log(base_log_path, mutation_entry, idx, mutation_sequence)
                continue
        
        # This mutation needs evaluation
        mutations_to_run.append({
            'idx': idx,
            'mutated_task_name': mutated_task_name,
            'log_task_name': log_task_name,
            'already_succeeded': already_succeeded,
        })
    
    if not mutations_to_run:
        print(f"\n✅ All mutations already processed, nothing to run.")
    else:
        # ── Phase 2: Execute mutations (parallel for API models, sequential for local) ──
        # API-based models (openai, anthropic, etc.) run in parallel; local/huggingface run sequentially
        # For local model without solver_override (standalone run_mutation_from_log): create shared solver
        # so all mutations reuse ONE vLLM instance instead of reloading per mutation (avoids OOM)
        can_parallel = model_type not in ('local', 'huggingface') and len(mutations_to_run) > 1
        METHODS_WITH_CUSTOM_SOLVER = {'absolute_zero', 'absolute_zero_iter', 'seal', 'ragen', 'soar', 'discover', 'genome'}
        uses_vllm = model_type == 'local' and method not in METHODS_WITH_CUSTOM_SOLVER
        shared_solver = None
        try:
            if uses_vllm and solver_override is None and mutations_to_run:
                print(f"🔄 Loading vLLM model once; all mutations will reuse it sequentially (avoids OOM)\n")
                shared_solver = SolverInterface(
                    model_type=model_type,
                    model_name=model_name,
                    api_key=api_key,
                    model_path=model_path,
                    device=device,
                )
                solver_override = shared_solver

            def _evaluate_mutation_worker(task_item):
                """Worker function for evaluating a single mutation. Thread-safe."""
                idx = task_item['idx']
                m_task_name = task_item['mutated_task_name']
                m_log_task_name = task_item['log_task_name']
                m_already_succeeded = task_item['already_succeeded']
                
                print(f"\n{'='*60}")
                print(f"{'[Parallel] ' if can_parallel else ''}Mutation {idx + 1}/{len(mutation_sequence)}: {m_task_name}")
                print(f"{'='*60}\n")
                
                try:
                    result = evaluate_single_mutation(
                        base_task_name=base_task_name,
                        mutated_task_name=m_task_name,
                        previous_successful_code=raw_best_code,   # Always use raw best code
                        model_type=model_type,
                        model_name=model_name,
                        method=method,
                        context=context,
                        max_iterations=max_iterations,
                        max_steps=max_steps,
                        headless=headless,
                        api_key=api_key,
                        model_path=model_path,
                        device=device,
                        output_dir=output_dir,
                        log_task_name=m_log_task_name,
                        generate_gif_only=m_already_succeeded,
                        reflect_model_name=reflect_model_name,
                        textgrad_engine_name=textgrad_engine_name,
                        a_mem_sys_llm_model=a_mem_sys_llm_model,
                        ace_reflector_model=ace_reflector_model,
                        ace_curator_model=ace_curator_model,
                        base_log_path=base_log_path,  # A-mem-sys: restore T0 memory for mutated task
                        n_select_sample=n_select_sample,  # ToT: b
                        n_generate_sample=n_generate_sample,  # ToT: n
                        reasoning_bank_k=reasoning_bank_k,  # ReasoningBank: parallel K
                        genome_best_lora_path=genome_best_lora_path,  # GENOME: best LoRA from base task
                        solver_override=solver_override,  # Reuse base task's vLLM model (avoids OOM)
                        save_gif=save_gif
                    )
                except Exception as exc:
                    if is_cuda_oom(exc):
                        print(f"❌ CUDA out of memory - stopping immediately: {exc}")
                        raise
                    print(f"❌ Mutation {m_task_name} raised exception: {exc}")
                    import traceback
                    traceback.print_exc()
                    result = {
                        'success': False,
                        'error': str(exc),
                        'best_score': 0.0,
                        'best_code': None,
                    }
                
                mutation_entry = {
                    'mutated_task_name': m_task_name,
                    'mutation_index': idx,
                    'status': 'evaluated',
                    'result': result,
                }
                
                # Thread-safe append to base log file
                _append_mutation_to_base_log(base_log_path, mutation_entry, idx, mutation_sequence)
                
                if result.get('success'):
                    print(f"✅ Mutation {m_task_name} completed successfully!")
                else:
                    print(f"❌ Mutation {m_task_name} failed.")
                
                return mutation_entry

            if can_parallel:
                num_workers = len(mutations_to_run)
                print(f"\n🚀 Running {num_workers} mutations in PARALLEL (API model: {model_type})")
                print(f"{'='*60}\n")
                
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    future_to_item = {
                        executor.submit(_evaluate_mutation_worker, item): item
                        for item in mutations_to_run
                    }
                    for future in as_completed(future_to_item):
                        item = future_to_item[future]
                        try:
                            entry = future.result()
                            sequence_results.append(entry)
                        except Exception as e:
                            if is_cuda_oom(e):
                                print(f"❌ CUDA out of memory - stopping immediately: {e}")
                                raise
                            print(f"❌ Mutation {item['mutated_task_name']} thread failed: {e}")
                            import traceback
                            traceback.print_exc()
                            # Still record a failure entry
                            fail_entry = {
                                'mutated_task_name': item['mutated_task_name'],
                                'mutation_index': item['idx'],
                                'status': 'thread_error',
                                'result': {'success': False, 'error': str(e), 'best_score': 0.0}
                            }
                            sequence_results.append(fail_entry)
                            _append_mutation_to_base_log(
                                base_log_path, fail_entry, item['idx'], mutation_sequence
                            )
            else:
                if len(mutations_to_run) > 1:
                    print(f"\n🔄 Running {len(mutations_to_run)} mutations SEQUENTIALLY (model: {model_type})")
                for item in mutations_to_run:
                    entry = _evaluate_mutation_worker(item)
                    sequence_results.append(entry)

        finally:
            # Always release vLLM so next run_mutation_for_log has full GPU (avoids "12.9 GiB free" on 2nd+ log)
            if shared_solver is not None:
                try:
                    shared_solver.cleanup()
                    print(f"✅ Released vLLM model after mutation sequence\n")
                except Exception as e:
                    print(f"⚠️  Shared solver cleanup warning: {e}\n")
    
    # Sort sequence_results by mutation_index for consistent ordering
    sequence_results.sort(key=lambda r: r.get('mutation_index', 0))
    
    # Generate final report
    completed = len([r for r in sequence_results if r.get('result', {}).get('success')])
    report = {
        'base_task_name': base_task_name,
        'model_type': model_type,
        'model_name': model_name,
        'method': method,
        'max_iterations_per_task': max_iterations,
        'total_mutations': len(mutation_sequence),
        'completed_mutations': completed,
        'success_rate': completed / len(mutation_sequence) if mutation_sequence else 0.0,
        'sequence_results': sequence_results,
        'timestamp': datetime.now().isoformat()
    }
    
    # Always write full sequence_results back to base log so file is complete (success + failure).
    # This covers: parallel workers that didn't get to append, or partial run; ensures all 4 slots exist.
    if base_log_path and os.path.exists(base_log_path):
        with _json_write_lock:
            try:
                with open(base_log_path, 'r', encoding='utf-8') as f:
                    base_log_data = json.load(f)
                if 'mutation_sequence' not in base_log_data:
                    base_log_data['mutation_sequence'] = {}
                base_log_data['mutation_sequence']['total_mutations'] = len(mutation_sequence)
                base_log_data['mutation_sequence']['completed_mutations'] = completed
                base_log_data['mutation_sequence']['success_rate'] = (
                    completed / len(mutation_sequence) if mutation_sequence else 0.0
                )
                base_log_data['mutation_sequence']['sequence_results'] = sequence_results
                base_log_data['mutation_sequence']['timestamp'] = report['timestamp']
                with open(base_log_path, 'w', encoding='utf-8') as f:
                    json.dump(base_log_data, f, indent=2, ensure_ascii=False)
                print(f"📝 Wrote full mutation_sequence ({len(sequence_results)} results) to base log")
            except Exception as e:
                print(f"⚠️  Failed to write full mutation_sequence to base log: {e}")
                import traceback
                traceback.print_exc()
    
    return report


def evaluate_single_mutation(base_task_name: str, mutated_task_name: str, previous_successful_code: str,
                             model_type: str, model_name: str, method: str, context: str = 'previous',
                             max_iterations: int = 20, max_steps: int = 10000, headless: bool = True,
                             api_key: Optional[str] = None, model_path: Optional[str] = None,
                             device: Optional[str] = None, output_dir: str = "evaluation_results", log_task_name: str = None,
                             generate_gif_only: bool = False,
                             reflect_model_name: Optional[str] = None,
                             textgrad_engine_name: Optional[str] = None,
                             a_mem_sys_llm_model: Optional[str] = None,
                             ace_reflector_model: Optional[str] = None,
                             ace_curator_model: Optional[str] = None,
                             base_log_path: Optional[str] = None,
                             n_select_sample: Optional[int] = None,
                             n_generate_sample: Optional[int] = None,
                             reasoning_bank_k: Optional[int] = None,
                             genome_best_lora_path: Optional[str] = None,
                             solver_override: Optional[Any] = None,
                             save_gif: bool = True) -> Dict[str, Any]:
    # Science-CodeEvolve: run CodeEvolve for mutated task with base best_code as initial (same idea as baseline: env mutation only)
    if method == 'science_codeevolve':
        from methods.Inference_time_search.science_codeevolve_method import run_single_task
        script_dir = os.path.dirname(os.path.dirname(__file__))
        # For Stage-* use base_task_name so load_task_prompt/CodeVerifier find the task dir; pass env_overrides so verification runs in mutated environment
        ce_task_name = base_task_name if mutated_task_name.startswith("Stage-") else mutated_task_name
        ce_env_overrides: Dict[str, Any] = {}
        if mutated_task_name.startswith("Stage-"):
            from evaluation.prompt import parse_task_name
            import importlib.util
            task_path, _ = parse_task_name(base_task_name)
            task_dir = os.path.join(script_dir, 'tasks', task_path)
            stages_file = os.path.join(task_dir, 'stages.py')
            if os.path.exists(stages_file):
                try:
                    spec = importlib.util.spec_from_file_location("task_stages", stages_file)
                    stages_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(stages_mod)
                    curriculum_func = next(
                        (getattr(stages_mod, n) for n in dir(stages_mod)
                         if 'curriculum_stages' in n.lower() and callable(getattr(stages_mod, n))),
                        None,
                    )
                    if curriculum_func:
                        stages = curriculum_func()
                        stage = next((s for s in stages if s.get("stage_id") == mutated_task_name), None)
                        if stage:
                            ce_env_overrides = {
                                "terrain_config": stage.get("terrain_config", {}) or {},
                                "physics_config": stage.get("physics_config", {}) or {},
                            }
                except Exception:
                    pass
        exit_code, report = run_single_task(
            task_name=ce_task_name,
            run_number=run_number or 1,
            model_type=model_type,
            model_name=model_name,
            context=context,
            max_steps=max_steps,
            scripts_dir=script_dir,
            initial_code=previous_successful_code,
            api_base=os.environ.get('API_BASE'),
            api_key=api_key or os.environ.get('API_KEY'),
            codeevolve_python=os.environ.get('CODEEVOLVE_PYTHON'),
            env_overrides=ce_env_overrides if ce_env_overrides else None,
        )
        return {
            'success': report.get('success', False),
            'best_score': report.get('best_score', 0.0),
            'best_code': report.get('best_code'),
            'error': None if report.get('success') else report.get('iteration_history', [{}])[0].get('error'),
        }

    # Alpha Evolve (OpenEvolve): run OpenEvolve for mutated task with base best_code as initial (same as baseline: env mutation only)
    if method == 'alpha_evolve':
        from methods.Inference_time_search.alpha_evolve_method import run_single_task as alpha_evolve_run_single_task
        script_dir = os.path.dirname(os.path.dirname(__file__))
        ae_task_name = base_task_name if mutated_task_name.startswith("Stage-") else mutated_task_name
        ae_env_overrides: Dict[str, Any] = {}
        if mutated_task_name.startswith("Stage-"):
            from evaluation.prompt import parse_task_name
            import importlib.util
            task_path, _ = parse_task_name(base_task_name)
            task_dir = os.path.join(script_dir, 'tasks', task_path)
            stages_file = os.path.join(task_dir, 'stages.py')
            if os.path.exists(stages_file):
                try:
                    spec = importlib.util.spec_from_file_location("task_stages", stages_file)
                    stages_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(stages_mod)
                    curriculum_func = next(
                        (getattr(stages_mod, n) for n in dir(stages_mod)
                         if 'curriculum_stages' in n.lower() and callable(getattr(stages_mod, n))),
                        None,
                    )
                    if curriculum_func:
                        stages = curriculum_func()
                        stage = next((s for s in stages if s.get("stage_id") == mutated_task_name), None)
                        if stage:
                            ae_env_overrides = {
                                "terrain_config": stage.get("terrain_config", {}) or {},
                                "physics_config": stage.get("physics_config", {}) or {},
                            }
                except Exception:
                    pass
        exit_code, report = alpha_evolve_run_single_task(
            task_name=ae_task_name,
            run_number=run_number or 1,
            model_type=model_type,
            model_name=model_name,
            context=context,
            max_steps=max_steps,
            scripts_dir=script_dir,
            initial_code=previous_successful_code,
            api_base=os.environ.get('API_BASE'),
            api_key=api_key or os.environ.get('API_KEY'),
            env_overrides=ae_env_overrides if ae_env_overrides else None,
        )
        return {
            'success': report.get('success', False),
            'best_score': report.get('best_score', 0.0),
            'best_code': report.get('best_code'),
            'error': None if report.get('success') else report.get('iteration_history', [{}])[0].get('error'),
        }

    # ThetaEvolve: run ThetaEvolve for mutated task with base best_code as initial (env mutation only)
    if method == 'theta_evolve':
        from methods.Parameter_Policy.theta_evolve import run_single_task as theta_evolve_run_single_task
        from evaluation.utils import get_evaluation_results_dir, get_gif_base_dir
        script_dir = os.path.dirname(os.path.dirname(__file__))
        te_task_name = base_task_name if mutated_task_name.startswith("Stage-") else mutated_task_name
        te_env_overrides: Dict[str, Any] = {}
        if mutated_task_name.startswith("Stage-"):
            from evaluation.prompt import parse_task_name
            import importlib.util
            task_path, _ = parse_task_name(base_task_name)
            task_dir = os.path.join(script_dir, 'tasks', task_path)
            stages_file = os.path.join(task_dir, 'stages.py')
            if os.path.exists(stages_file):
                try:
                    spec = importlib.util.spec_from_file_location("task_stages", stages_file)
                    stages_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(stages_mod)
                    curriculum_func = next(
                        (getattr(stages_mod, n) for n in dir(stages_mod)
                         if 'curriculum_stages' in n.lower() and callable(getattr(stages_mod, n))),
                        None,
                    )
                    if curriculum_func:
                        stages = curriculum_func()
                        stage = next((s for s in stages if s.get("stage_id") == mutated_task_name), None)
                        if stage:
                            te_env_overrides = {
                                "terrain_config": stage.get("terrain_config", {}) or {},
                                "physics_config": stage.get("physics_config", {}) or {},
                            }
                except Exception:
                    pass
        exit_code, report = theta_evolve_run_single_task(
            task_name=te_task_name,
            run_number=run_number or 1,
            model_type=model_type,
            model_name=model_name,
            context=context,
            max_steps=max_steps,
            scripts_dir=script_dir,
            output_dir=get_evaluation_results_dir(),
            gif_base_dir=get_gif_base_dir(),
            initial_code=previous_successful_code,
            model_path=model_path,
            device=device,
            env_overrides=te_env_overrides if te_env_overrides else None,
            theta_evolve_num_rollout=3000,
            theta_evolve_rollout_batch_size=32,
        )
        return {
            'success': report.get('success', False),
            'best_score': report.get('best_score', 0.0),
            'best_code': report.get('best_code'),
            'error': None if report.get('success') else report.get('iteration_history', [{}])[0].get('error'),
        }

    # Determine if this is an internal curriculum stage (no new task directory)
    env_overrides: Dict[str, Any] = {}
    task_prompt_override = None
    evaluator_task_name = mutated_task_name

    # Check if this is a Stage-* mutation (internal curriculum)
    if mutated_task_name.startswith("Stage-"):
        evaluator_task_name = base_task_name  # Use base task name for evaluator
        
        # Parse task name to get file system path
        from evaluation.prompt import parse_task_name
        import importlib.util
        
        task_path, _ = parse_task_name(base_task_name)
        script_dir = os.path.dirname(os.path.dirname(__file__))
        task_dir = os.path.join(script_dir, 'tasks', task_path)
        stages_file = os.path.join(task_dir, 'stages.py')
        
        if os.path.exists(stages_file):
            try:
                # Load stages module
                spec = importlib.util.spec_from_file_location("task_stages", stages_file)
                stages_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(stages_mod)
                
                # Find curriculum stages function
                curriculum_func = None
                for name in dir(stages_mod):
                    if 'curriculum_stages' in name.lower() and callable(getattr(stages_mod, name)):
                        curriculum_func = getattr(stages_mod, name)
                        break
                
                if curriculum_func:
                    stages = curriculum_func()
                    stage = next(s for s in stages if s["stage_id"] == mutated_task_name)
                    env_overrides = {
                        "terrain_config": stage.get("terrain_config", {}) or {},
                        "physics_config": stage.get("physics_config", {}) or {},
                    }

                    base_prompt = load_task_prompt(base_task_name)
                    task_prompt_override = dict(base_prompt)
                    
                    # Update task description for visible physical changes (e.g., gap width, cliff positions)
                    # For invisible physical parameters (gravity, damping, etc.), changes are NOT reflected
                    base_description = base_prompt.get("task_description", "")
                    base_success_criteria = base_prompt.get("success_criteria", "")
                    
                    # Check if stages module has update functions for visible changes
                    update_desc_func = None
                    update_criteria_func = None
                    for name in dir(stages_mod):
                        if 'update_task_description_for_visible_changes' in name.lower() and callable(getattr(stages_mod, name)):
                            update_desc_func = getattr(stages_mod, name)
                        if 'update_success_criteria_for_visible_changes' in name.lower() and callable(getattr(stages_mod, name)):
                            update_criteria_func = getattr(stages_mod, name)
                    
                    terrain_config = env_overrides.get("terrain_config", {})
                    # For evaluate_mutated, the base is always the initial task (empty config)
                    base_terrain_config = {}
                    
                    if update_desc_func:
                        # Update description with visible changes explicitly marked
                        updated_description = update_desc_func(base_description, terrain_config, base_terrain_config)
                    else:
                        updated_description = base_description
                    
                    if update_criteria_func:
                        # Update success criteria with visible changes explicitly marked
                        updated_criteria = update_criteria_func(base_success_criteria, terrain_config, base_terrain_config)
                    else:
                        updated_criteria = base_success_criteria
                    
                    # Append environmental warning suffix
                    task_prompt_override["task_description"] = (
                        updated_description
                        + "\n"
                        + (stage.get("task_description_suffix", "") or "")
                    )
                    task_prompt_override["success_criteria"] = updated_criteria
            except Exception as e:
                print(f"⚠️  Failed to load stage config for {mutated_task_name}: {e}")
                import traceback
                traceback.print_exc()

    # A-mem-sys: restore memory from base task (T0) so mutated task (T1, T2, ...) starts with
    # full memory from initial task. Each mutation gets a fresh copy of T0's memory (T1 and T2
    # do not share each other's updates; only T0's memory is carried over).
    initial_memory_system = None
    if method == 'a_mem_sys' and base_log_path and os.path.exists(base_log_path):
        try:
            from methods.Memory.a_mem_sys_method import get_memory_system, restore_memory_from_base_log
            base_log_for_memory = load_log_file(base_log_path)
            if base_log_for_memory and base_log_for_memory.get('iteration_history'):
                initial_memory_system = get_memory_system(
                    llm_model=a_mem_sys_llm_model or 'deepseek-v3.2',
                    api_key=api_key,
                )
                restore_memory_from_base_log(initial_memory_system, base_log_for_memory)
                n_notes = len(base_log_for_memory.get('iteration_history', []))
                print(f"🧠 A-mem-sys: restored {n_notes} memory note(s) from base task for mutated task")
        except Exception as e:
            print(f"⚠️  A-mem-sys: failed to restore memory from base log: {e}")
            initial_memory_system = None
    # Memento non-parametric: create memory path for this mutated run and replay T0's memory entries
    if method == 'memento_nonparametric' and base_log_path and os.path.exists(base_log_path):
        try:
            from methods.Memory.memento_nonparametric_method import get_memory_path, restore_memory_from_base_log
            base_log_for_memory = load_log_file(base_log_path)
            if base_log_for_memory and base_log_for_memory.get('iteration_history'):
                model_identifier = get_model_identifier(model_type, model_name)
                # Use log_task_name (mutated task name for dir) for this mutation run
                memento_memory_path = get_memory_path(
                    output_dir, log_task_name or evaluator_task_name, model_identifier
                )
                restore_memory_from_base_log(base_log_for_memory, memento_memory_path)
                initial_memory_system = memento_memory_path  # pass path (str) so evaluator uses pre-filled JSONL
                n_entries = len([h for h in base_log_for_memory.get('iteration_history', []) if h.get('memory_stored_entry')])
                print(f"🧠 Memento non-parametric: restored {n_entries} memory entries from base task for mutated task")
        except Exception as e:
            print(f"⚠️  Memento non-parametric: failed to restore memory from base log: {e}")
            initial_memory_system = None
    # ACE: restore playbook from base task (T0) so mutated task starts with T0's playbook
    initial_playbook = None
    if method == 'ace' and base_log_path and os.path.exists(base_log_path):
        try:
            from methods.Memory.ace_method import restore_playbook_from_base_log
            base_log_for_ace = load_log_file(base_log_path)
            initial_playbook = restore_playbook_from_base_log(base_log_for_ace)
            if initial_playbook and initial_playbook.strip():
                print(f"📚 ACE: restored playbook from base task for mutated task ({len(initial_playbook)} chars)")
        except Exception as e:
            print(f"⚠️  ACE: failed to restore playbook from base log: {e}")
            initial_playbook = None
    # ReasoningBank: restore bank from base task (T0) so mutated task starts with T0's memory
    if method == 'reasoning_bank' and base_log_path and os.path.exists(base_log_path):
        try:
            from methods.Memory.reasoning_bank_method import get_memory_path, restore_memory_from_base_log
            base_log_for_rb = load_log_file(base_log_path)
            if base_log_for_rb and base_log_for_rb.get('iteration_history'):
                model_identifier = get_model_identifier(model_type, model_name)
                reasoning_bank_path = get_memory_path(
                    output_dir, log_task_name or evaluator_task_name, model_identifier
                )
                restore_memory_from_base_log(base_log_for_rb, reasoning_bank_path)
                initial_memory_system = reasoning_bank_path
                n_items = len([h for h in base_log_for_rb.get('iteration_history', []) if h.get('reasoning_bank_stored_items')])
                print(f"🧠 ReasoningBank: restored memory from base task for mutated task ({n_items} stored blocks)")
        except Exception as e:
            print(f"⚠️  ReasoningBank: failed to restore memory from base log: {e}")
            initial_memory_system = None

    # Create evaluator for (possibly overridden) task
    # solver_override: reuse base task's vLLM model (avoids OOM from reloading)
    evaluator = TaskEvaluator(
        task_name=evaluator_task_name,
        model_type=model_type,
        model_name=model_name,
        api_key=api_key,
        max_iterations=max_iterations,
        max_steps=max_steps,
        headless=headless,
        model_path=model_path,
        device=device,
        method=method,
        context=context,
        env_overrides=env_overrides,
        task_prompt_override=task_prompt_override,
        is_mutated_task=True,  # Mark this as a mutated task evaluation
        reflect_model_name=reflect_model_name,  # Reflexion method
        textgrad_engine_name=textgrad_engine_name,  # TextGrad method
        a_mem_sys_llm_model=a_mem_sys_llm_model,  # A-mem-sys: memory LLM
        initial_memory_system=initial_memory_system,  # A-mem-sys / Memento: T0 memory for mutated task
        base_task_name_for_memory=f"{base_task_name}_{mutated_task_name.replace('-', '_')}" if method == 'memento_nonparametric' else None,  # Memento: store with suffix, underscores only (e.g. category_1_01_Stage_1)
        initial_playbook=initial_playbook if method == 'ace' else None,  # ACE: T0 playbook for mutated task
        ace_reflector_model=ace_reflector_model,  # ACE: Reflector model
        ace_curator_model=ace_curator_model,  # ACE: Curator model
        n_select_sample=n_select_sample,  # ToT: b
        n_generate_sample=n_generate_sample,  # ToT: n
        reasoning_bank_k=reasoning_bank_k,  # ReasoningBank: parallel K
        genome_best_lora_path=genome_best_lora_path,  # GENOME: best LoRA from base task
        solver_override=solver_override,  # Reuse base task's vLLM (avoids OOM)
        save_gif=save_gif
    )

    # Mutated task: same context and method as top-level; one whole prompt per round (no system/user split)
    use_conversation = False

    # Set mutated task name for GIF directory
    if mutated_task_name.startswith("Stage-"):
        evaluator.mutated_task_name = mutated_task_name
    else:
        if mutated_task_name.startswith(evaluator.task_name + "_"):
            mutation_name = mutated_task_name[len(evaluator.task_name) + 1 :]
        else:
            mutation_name = mutated_task_name
        evaluator.mutated_task_name = mutation_name
    
    # Re-setup GIF directory with mutated task name
    evaluator._setup_gif_directory()
    
    # Override the evaluate method to use mutated initial prompt
    original_evaluate = evaluator.evaluate
    
    def mutated_evaluate():
        """Modified evaluate that uses previous code in first iteration"""
        current_code = previous_successful_code
        previous_code = None
        tot_states: List[Dict[str, Any]] = []  # ToT: b states (code, feedback, score, ...)
        
        # If generate_gif_only is True, only run one iteration to generate GIF
        max_iter = 1 if generate_gif_only else evaluator.max_iterations
        
        for iteration in range(1, max_iter + 1):
            print(f"\n{'='*60}")
            print(f"Iteration {iteration}/{max_iter}")
            if generate_gif_only:
                print("(GIF generation only)")
            print(f"{'='*60}\n")
            
            try:
                if iteration == 1:
                    # First iteration: run previous code in new environment
                    print("🔄 Running previous successful code in mutated environment...")
                    # For first iteration in mutated task, use special GIF naming: {raw}_{in}_{Stage-X}
                    if mutated_task_name.startswith("Stage-"):
                        gif_filename = f"raw_in_{mutated_task_name}.gif"
                    else:
                        gif_filename = f"raw_in_{mutated_task_name}.gif"
                    gif_path = os.path.join(evaluator.gif_dir, gif_filename) if evaluator.save_gif else None
                    success, score, metrics, error = evaluator.verifier.verify_code(
                        current_code, headless=evaluator.headless, save_gif_path=gif_path
                    )
                    
                    # Generate feedback
                    failed = metrics.get('failed', False)
                    failure_reason = metrics.get('failure_reason', None)
                    # For feedback module lookup, always use base_task_name (not log_task_name which may be synthetic)
                    # log_task_name is only for file naming, not for task module lookup
                    feedback_task_name = base_task_name
                    feedback = format_feedback(
                        metrics, score, success, failed, failure_reason, iteration,
                        error=error, task_name=feedback_task_name,
                        include_suggestions=evaluator.enable_feedback
                    )
                    
                    # Mutated task: every round is revision/adaptation (previous code + feedback in new env)
                    prompt = format_mutated_prompt(
                        evaluator.task_prompt,
                        current_code,
                        feedback
                    )

                    # Record test result
                    evaluator.iteration_history.append({
                        'iteration': iteration,
                        'phase': 'initial_test',
                        'prompt': prompt,  # The prompt generated FROM this initial test for the NEXT iteration
                        'code': current_code,
                        'success': success,
                        'score': score,
                        'metrics': metrics,
                        'error': error,
                        'feedback': feedback,
                        'reflection': None,
                    })
                # ===== TextGrad: self-contained optimisation for mutated iterations 2+ =====
                elif evaluator.method == 'textgrad' and iteration > 1 and evaluator.tg_code_var is not None:
                    last_feedback = evaluator.iteration_history[-1].get('feedback', '')
                    print(f"🧮 TextGrad optimisation step (mutated, iteration {iteration})...")
                    
                    tg_current_code = None
                    tg_raw_output = None
                    tg_gradient_text = None
                    
                    try:
                        from methods.Context.textgrad_method import textgrad_optimize_step, extract_code_from_textgrad_output
                        tg_new_code, tg_raw_output, tg_gradient_text = textgrad_optimize_step(
                            evaluator.tg_code_var, evaluator.tg_optimizer, evaluator.tg_engine,
                            last_feedback, evaluator.task_prompt
                        )
                        if tg_new_code is not None:
                            tg_current_code = extract_code_from_textgrad_output(tg_new_code) or tg_new_code
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        print(f"❌ TextGrad optimisation failed (mutated): {exc}")
                        tg_raw_output = str(exc)
                    
                    if tg_current_code and len(tg_current_code.strip()) >= 50 and 'def build_agent' in tg_current_code:
                        evaluator.tg_code_var.set_value(tg_current_code)
                        current_code = tg_current_code
                        
                        gif_path = evaluator._get_gif_path(iteration) if evaluator.save_gif else None
                        success, score, metrics, error = evaluator.verifier.verify_code(
                            current_code, headless=evaluator.headless, save_gif_path=gif_path
                        )
                        
                        feedback_task_name = base_task_name
                        failed = metrics.get('failed', False)
                        failure_reason = metrics.get('failure_reason', None)
                        feedback = format_feedback(
                            metrics, score, success, failed, failure_reason, iteration,
                            error=error, task_name=feedback_task_name,
                            include_suggestions=False
                        )
                        
                        evaluator.iteration_history.append({
                            'iteration': iteration,
                            'phase': 'textgrad_revision',
                            'prompt': f"[TextGrad step {iteration}]",
                            'code': current_code,
                            'raw_llm_output': tg_raw_output,
                            'token_usage': {},
                            'success': success,
                            'score': score,
                            'metrics': metrics,
                            'error': error,
                            'feedback': feedback,
                            'gradient': tg_gradient_text,
                            'reflection': None,
                        })
                        
                        if score > evaluator.best_score:
                            evaluator.best_score = score
                            evaluator.best_code = current_code
                            evaluator.best_metrics = metrics
                            print(f"🎯 New best score: {score:.1f}/100")
                        
                        print(f"📊 TextGrad (mutated): Score={score:.1f}/100, Success={'✅' if success else '❌'}")
                        if success:
                            print(f"🎉 Task completed! Iterations: {iteration}")
                            break
                    else:
                        error_msg = f"TextGrad (mutated) generated invalid code: {tg_raw_output}"
                        evaluator.iteration_history.append({
                            'iteration': iteration,
                            'phase': 'textgrad_revision_failed',
                            'code': tg_current_code,
                            'raw_llm_output': tg_raw_output,
                            'success': False,
                            'score': 0.0,
                            'error': error_msg,
                            'feedback': error_msg,
                            'gradient': tg_gradient_text,
                            'reflection': None,
                        })
                    continue  # TextGrad handled this iteration
                
                # ===== Self-Refine: original-repo pipeline (inner self-verify until "It is correct", then one verifier) =====
                elif evaluator.method == 'self_refine' and iteration > 1:
                    from methods.Context.self_refine_method import (
                        format_self_feedback_prompt,
                        format_revision_prompt_self_refine_inner,
                        self_verify_says_correct,
                    )
                    MAX_SELF_VERIFY_STEPS = 5   # cap per round: at most 5 self-verify+refine cycles
                    self_refine_inner_steps = []
                    last_system_feedback = evaluator.iteration_history[-1].get('feedback', '')
                    last_code = evaluator.iteration_history[-1].get('code', '') or current_code
                    # Revision prompt for this round (mutated: use last system feedback)
                    prompt = format_revision_prompt(evaluator.task_prompt, last_code, last_system_feedback) if last_code else format_initial_prompt(evaluator.task_prompt)
                    print(f"🔄 Self-Refine round {iteration} (mutated): generating code then inner self-verify loop...")
                    try:
                        current_code, raw_llm_output, token_usage = evaluator.solver.generate_code(
                            prompt, use_conversation=use_conversation, reset_conversation=False
                        )
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        evaluator.iteration_history.append({
                            'iteration': iteration, 'phase': 'self_refine_init_failed', 'error': str(exc),
                            'self_refine_inner_steps': [], 'reflection': None,
                        })
                        continue
                    if not current_code or len(current_code.strip()) < 50 or 'def build_agent' not in current_code:
                        pass  # will verify anyway and record
                    else:
                        inner_step = 0
                        while inner_step < MAX_SELF_VERIFY_STEPS:
                            inner_step += 1
                            verify_prompt = format_self_feedback_prompt(current_code, evaluator.task_prompt)
                            try:
                                _, raw_verify, _ = evaluator.solver.generate_code(verify_prompt, use_conversation=False, reset_conversation=False)
                                self_verify_output = (raw_verify or "").strip()
                            except Exception as exc:
                                if is_cuda_oom(exc):
                                    raise
                                self_verify_output = f"(Self-verify failed: {exc})"
                            self_refine_inner_steps.append({'step': inner_step, 'self_verify_output': self_verify_output, 'code_before': current_code})
                            if self_verify_says_correct(self_verify_output):
                                break
                            refine_prompt = format_revision_prompt_self_refine_inner(evaluator.task_prompt, current_code, self_verify_output)
                            try:
                                new_code, _, _ = evaluator.solver.generate_code(refine_prompt, use_conversation=use_conversation, reset_conversation=False)
                            except Exception as exc:
                                if is_cuda_oom(exc):
                                    raise
                                self_refine_inner_steps[-1]['refine_error'] = str(exc)
                                self_refine_inner_steps[-1]['code_after'] = None
                                break
                            self_refine_inner_steps[-1]['code_after'] = new_code
                            if new_code and len(new_code.strip()) >= 50 and 'def build_agent' in new_code:
                                current_code = new_code
                            else:
                                break
                    gif_path = evaluator._get_gif_path(iteration) if evaluator.save_gif else None
                    success, score, metrics, error = evaluator.verifier.verify_code(
                        current_code if (current_code and 'def build_agent' in current_code) else (current_code or ""),
                        headless=evaluator.headless, save_gif_path=gif_path
                    )
                    feedback_task_name = base_task_name
                    failed = metrics.get('failed', False)
                    failure_reason = metrics.get('failure_reason', None)
                    feedback = format_feedback(
                        metrics, score, success, failed, failure_reason, iteration,
                        error=error, task_name=feedback_task_name, include_suggestions=False,
                    )
                    evaluator.iteration_history.append({
                        'iteration': iteration, 'phase': 'self_refine_revision',
                        'prompt': prompt, 'code': current_code, 'raw_llm_output': raw_llm_output,
                        'token_usage': token_usage, 'success': success, 'score': score,
                        'metrics': metrics, 'error': error, 'feedback': feedback,
                        'self_refine_inner_steps': self_refine_inner_steps, 'reflection': None,
                    })
                    if score > evaluator.best_score:
                        evaluator.best_score = score
                        evaluator.best_code = current_code
                        evaluator.best_metrics = metrics
                        print(f"🎯 New best score: {score:.1f}/100")
                    print(f"📊 Self-Refine (mutated) round {iteration}: Score={score:.1f}/100, Success={'✅' if success else '❌'}")
                    if success:
                        print(f"🎉 Task completed! Iterations: {iteration}")
                        break
                    continue  # Self-Refine handled this iteration
                
                # ===== Tree-of-Thought: mutated rounds 2+ (b beams, n samples per beam; API: parallel) =====
                elif evaluator.method == 'tree_of_thought' and iteration > 1 and tot_states:
                    from evaluation.feedback import format_feedback as _format_feedback
                    b = getattr(evaluator, 'n_select_sample', 3)
                    n = getattr(evaluator, 'n_generate_sample', 2)
                    revision_prompts_mut = []
                    for state in tot_states:
                        prompt = format_mutated_prompt(
                            evaluator.task_prompt, previous_successful_code, state['feedback']
                        )
                        for _ in range(n):
                            revision_prompts_mut.append(prompt)
                    all_candidates = []
                    use_parallel_mut = getattr(evaluator.solver, 'model_type', None) == 'openai'
                    if use_parallel_mut:
                        def _gen_one_mut(prompt: str):
                            try:
                                code, raw_llm, token_usage = evaluator.solver.generate_code(
                                    prompt, use_conversation=False, reset_conversation=False
                                )
                                return (code, raw_llm, token_usage or {}, prompt)
                            except Exception as exc:
                                if is_cuda_oom(exc):
                                    raise
                                return (None, None, {}, prompt)
                        num_gen_mut = len(revision_prompts_mut)
                        max_workers_mut = min(num_gen_mut, 16)
                        print(f"🔄 ToT (mutated) round {iteration}: generating {num_gen_mut} revisions in parallel (max_workers={max_workers_mut})...")
                        with ThreadPoolExecutor(max_workers=max_workers_mut) as ex:
                            futures = [ex.submit(_gen_one_mut, p) for p in revision_prompts_mut]
                            for fut in as_completed(futures):
                                code, raw_llm, token_usage, rev_prompt = fut.result()
                                if code and len(code.strip()) >= 50 and 'def build_agent' in code:
                                    all_candidates.append({'code': code, 'raw_llm_output': raw_llm, 'token_usage': token_usage, 'prompt': rev_prompt})
                    else:
                        for prompt in revision_prompts_mut:
                            try:
                                code, raw_llm, token_usage = evaluator.solver.generate_code(
                                    prompt, use_conversation=False, reset_conversation=False
                                )
                                if code and len(code.strip()) >= 50 and 'def build_agent' in code:
                                    all_candidates.append({'code': code, 'raw_llm_output': raw_llm, 'token_usage': token_usage or {}, 'prompt': prompt})
                            except Exception as exc:
                                if is_cuda_oom(exc):
                                    raise
                                print(f"⚠️  ToT (mutated) sample failed: {exc}")
                    if not all_candidates:
                        evaluator.iteration_history.append({
                            'iteration': iteration, 'phase': 'tot_revision_failed', 'code': None,
                            'error': 'No valid revision code', 'tot_candidates': 0,
                        })
                        break
                    for c in all_candidates:
                        succ, sc, met, err = evaluator.verifier.verify_code(
                            c['code'], headless=evaluator.headless, save_gif_path=None
                        )
                        c['success'] = succ
                        c['score'] = sc
                        c['metrics'] = met
                        c['error'] = err
                        c['feedback'] = _format_feedback(met, sc, succ, met.get('failed', False), met.get('failure_reason'), iteration, error=err, task_name=base_task_name, include_suggestions=False)
                        if sc > evaluator.best_score:
                            evaluator.best_score = sc
                            evaluator.best_code = c['code']
                            evaluator.best_metrics = met
                            gif_path = evaluator._get_gif_path(iteration) if evaluator.save_gif else None
                            evaluator.verifier.verify_code(c['code'], headless=evaluator.headless, save_gif_path=gif_path)
                    all_candidates.sort(key=lambda x: x['score'], reverse=True)
                    tot_states = all_candidates[:b]
                    round_best = tot_states[0]
                    evaluator.iteration_history.append({
                        'iteration': iteration, 'phase': 'tot_revision', 'prompt': round_best.get('prompt'),
                        'code': round_best['code'], 'raw_llm_output': round_best.get('raw_llm_output'),
                        'token_usage': round_best.get('token_usage', {}), 'success': round_best['success'],
                        'score': round_best['score'], 'metrics': round_best.get('metrics'), 'error': round_best.get('error'),
                        'feedback': round_best['feedback'], 'tot_candidates': len(all_candidates),
                        'tot_top_b': [{'score': s['score'], 'success': s['success']} for s in tot_states],
                    })
                    if any(s['success'] for s in tot_states):
                        print(f"🎉 ToT (mutated) success at iteration {iteration}")
                        break
                    continue  # ToT handled this iteration
                
                else:
                    # Subsequent iterations: same context and method as top-level (e.g. best+previous when context='all')
                    last_feedback = evaluator.iteration_history[-1].get('feedback', '')
                    feedback_from_round1 = (evaluator.iteration_history[0].get('feedback', '') if evaluator.iteration_history else '')
                    effective_context = 'best_score_plus_previous' if context == 'all' else context
                    if effective_context == 'best_score_plus_previous':
                        best_item = None
                        best_score = -1.0
                        best_iteration = None
                        for item in evaluator.iteration_history:
                            s = item.get('score', 0.0)
                            if s > best_score:
                                best_score = s
                                best_item = item
                                best_iteration = item.get('iteration')
                        previous_item = evaluator.iteration_history[-1] if evaluator.iteration_history else None
                        previous_iteration = previous_item.get('iteration') if previous_item else None
                        previous_code = previous_item.get('code', '') if previous_item else ''
                        previous_feedback = previous_item.get('feedback', '') if previous_item else ''
                        if best_item and best_item.get('code') and previous_code:
                            best_code = best_item.get('code', '')
                            best_fb = best_item.get('feedback', '')
                            if best_iteration == previous_iteration:
                                prompt = format_mutated_revision_prompt_best_plus_previous(
                                    evaluator.task_prompt, previous_successful_code, feedback_from_round1,
                                    best_code, best_fb, '', '', last_feedback,
                                    best_iteration, previous_iteration, iteration
                                )
                                print(f"📝 Mutated revision prompt (best only, iter={best_iteration}, best_score={best_score:.1f})...")
                            else:
                                prompt = format_mutated_revision_prompt_best_plus_previous(
                                    evaluator.task_prompt, previous_successful_code, feedback_from_round1,
                                    best_code, best_fb, previous_code, previous_feedback, last_feedback,
                                    best_iteration, previous_iteration, iteration
                                )
                                print(f"📝 Mutated revision prompt (best+previous, best_iter={best_iteration}, prev_iter={previous_iteration}, best_score={best_score:.1f})...")
                        elif previous_code:
                            prompt = format_mutated_revision_prompt(
                                evaluator.task_prompt, previous_successful_code, feedback_from_round1,
                                previous_code, previous_feedback, last_feedback
                            )
                            print("📝 Mutated revision prompt (previous only)...")
                        else:
                            prompt = format_mutated_prompt(evaluator.task_prompt, previous_successful_code, last_feedback)
                            print("📝 Mutated revision prompt (fallback to env+feedback only)...")
                    elif effective_context == 'previous':
                        previous_code = evaluator.iteration_history[-1].get('code', '') if evaluator.iteration_history else ''
                        previous_feedback = evaluator.iteration_history[-1].get('feedback', '') if evaluator.iteration_history else ''
                        if previous_code:
                            prompt = format_mutated_revision_prompt(
                                evaluator.task_prompt, previous_successful_code, feedback_from_round1,
                                previous_code, previous_feedback, last_feedback
                            )
                            print("📝 Mutated revision prompt (previous)...")
                        else:
                            prompt = format_mutated_prompt(evaluator.task_prompt, previous_successful_code, last_feedback)
                            print("📝 Mutated revision prompt (fallback)...")
                    else:
                        # Fallback: previous only
                        previous_code = evaluator.iteration_history[-1].get('code', '') if evaluator.iteration_history else ''
                        previous_feedback = evaluator.iteration_history[-1].get('feedback', '') if evaluator.iteration_history else ''
                        if previous_code:
                            prompt = format_mutated_revision_prompt(
                                evaluator.task_prompt, previous_successful_code, feedback_from_round1,
                                previous_code, previous_feedback, last_feedback
                            )
                        else:
                            prompt = format_mutated_prompt(evaluator.task_prompt, previous_successful_code, last_feedback)
                        print(f"📝 Mutated revision prompt (context={effective_context}, fallback)...")
                
                # Reflexion: prepend reflections to prompt when using reflexion method
                if evaluator.method == 'reflexion' and evaluator.reflections_str:
                    prompt = "# Reflections from Previous Attempts\n\n" + evaluator.reflections_str + "\n\n" + prompt
                
                # Call solver
                print("🤖 Calling solver agent...")
                try:
                    new_code, raw_llm_output, token_usage = evaluator.solver.generate_code(
                        prompt,
                        use_conversation=use_conversation,
                        reset_conversation=False
                    )
                except Exception as exc:
                    if is_cuda_oom(exc):
                        print(f"❌ CUDA out of memory - stopping immediately: {exc}")
                        raise
                    print(f"❌ Code generation failed: {exc}")
                    evaluator.iteration_history.append({
                        'iteration': iteration,
                        'phase': 'generation_failed',
                        'error': str(exc)
                    })
                    continue
                
                if not new_code or len(new_code.strip()) < 50:
                    print("⚠️ Generated code too short")
                    continue
                
                current_code = new_code
                previous_code = current_code
                
                # Verify new code
                print("🔍 Verifying new code...")
                gif_path = evaluator._get_gif_path(iteration) if evaluator.save_gif else None
                success, score, metrics, error = evaluator.verifier.verify_code(
                    current_code, headless=evaluator.headless, save_gif_path=gif_path
                )
                
                # Generate feedback
                failed = metrics.get('failed', False)
                failure_reason = metrics.get('failure_reason', None)
                # For feedback module lookup, always use base_task_name (not log_task_name which may be synthetic)
                # log_task_name is only for file naming, not for task module lookup
                feedback_task_name = base_task_name
                feedback = format_feedback(
                    metrics, score, success, failed, failure_reason, iteration,
                    error=error, task_name=feedback_task_name,
                    include_suggestions=evaluator.enable_feedback
                )
                
                # Record result
                iteration_result = {
                    'iteration': iteration,
                    'phase': 'revision',
                    'prompt': prompt,
                    'code': current_code,
                    'raw_llm_output': raw_llm_output,
                    'token_usage': token_usage,
                    'success': success,
                    'score': score,
                    'metrics': metrics,
                    'error': error,
                    'feedback': feedback,
                    'reflection': None,
                }
                evaluator.iteration_history.append(iteration_result)
                
                # Reflexion: generate reflection after failed revision iteration
                if not success and evaluator.method == 'reflexion' and evaluator.reflect_solver is not None:
                    try:
                        reflection = evaluator._generate_reflection(current_code, feedback, iteration)
                        evaluator.reflections.append(reflection)
                        evaluator.reflections_str = format_reflections_str(evaluator.reflections)
                        evaluator.iteration_history[-1]['reflection'] = reflection
                    except Exception as e:
                        print(f"⚠️  Reflexion (mutated): failed to generate reflection: {e}")
                
                # Update best
                if score > evaluator.best_score:
                    evaluator.best_score = score
                    evaluator.best_code = current_code
                    evaluator.best_metrics = metrics
                    print(f"🎯 New best score: {score:.1f}/100")
                
                print(f"📊 Score: {score:.1f}/100, Success: {success}")
                
                if success:
                    print(f"🎉 Task completed! Iterations: {iteration}")
                    break
                
                # SEAL TTT: train LoRA on accumulated solutions (mutated task, same as base)
                if evaluator.method == 'seal':
                    evaluator._seal_ttt_step()
                    
            except Exception as exc:
                if is_cuda_oom(exc):
                    print(f"❌ CUDA out of memory - stopping immediately: {exc}")
                    raise
                print(f"❌ Iteration error: {exc}")
                import traceback
                traceback.print_exc()
                continue
        
        # Cleanup and return report
        evaluator.verifier.cleanup()
        return evaluator._generate_report()
    
    # Replace evaluate method
    evaluator.evaluate = mutated_evaluate
    
    # Run evaluation
    report = evaluator.evaluate()
    
    # Don't save separate JSON file for each mutation
    # The mutation results will be appended to the base task's JSON file by run_mutation_sequence
    # Only save if explicitly needed for debugging (commented out for now)
    # original_task_name = evaluator.task_name
    # evaluator.task_name = log_task_name
    # try:
    #     evaluator.save_report(report, output_dir=output_dir)
    # finally:
    #     evaluator.task_name = original_task_name
    
    return report
