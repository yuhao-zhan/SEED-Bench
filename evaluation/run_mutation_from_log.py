#!/usr/bin/env python3
"""
Run mutation sequence from an existing log file's best_code.
Useful when base task was already completed but mutation sequence wasn't run.
"""
import os
import sys

# Disable vLLM V1 multiprocessing before any vLLM/torch.distributed import.
# Otherwise TCPStore may try to connect to a non-existent worker and timeout (600000ms).
os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")

import json
import argparse
from pathlib import Path

# Add path (point to scripts directory, same as evaluate.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Set CUDA_VISIBLE_DEVICES before any torch/cuda import (same as evaluate.py).
# Otherwise --device cuda:1,2 is ignored and process uses default cuda:0 (physical GPU 0).
if not os.environ.get("CUDA_VISIBLE_DEVICES"):
    for i, arg in enumerate(sys.argv):
        if arg == "--device" and i + 1 < len(sys.argv):
            dev = sys.argv[i + 1]
            if dev.startswith("cuda:") and "," in dev:
                gpu_ids = [x.strip() for x in dev[5:].split(",") if x.strip()]
                if gpu_ids:
                    os.environ["CUDA_VISIBLE_DEVICES"] = ",".join(gpu_ids)
                    print(f"Early CUDA_VISIBLE_DEVICES={os.environ['CUDA_VISIBLE_DEVICES']} (GPUs {gpu_ids})")
            break

from evaluation.evaluate_mutated import run_mutation_sequence
from evaluation.utils import load_best_code_from_log, extract_run_number_from_filename




def extract_task_info_from_log(log_data: dict) -> dict:
    """
    Extract task information from log data.
    
    Returns:
        dict with task_name, model_type, model_name, method, context, max_iterations, max_steps
    """
    return {
        'task_name': log_data.get('task_name'),
        'model_type': log_data.get('model_type'),
        'model_name': log_data.get('model_name'),
        'method': log_data.get('method', 'baseline'),
        'context': log_data.get('context', 'previous'),
        'max_iterations': log_data.get('max_iterations', 20),
        'max_steps': log_data.get('max_steps', 10000),
    }


def run_mutation_for_log(
    log_path: str,
    model_type: str | None = None,
    model_name: str | None = None,
    method: str | None = None,
    context: str | None = None,
    max_iterations: int | None = None,
    max_steps: int | None = None,
    api_key: str | None = None,
    model_path: str | None = None,
    device: str = 'auto',
    output_dir: str = 'evaluation_results',
    headless: bool = True,
    verbose: bool = True,
    reflect_model_name: str | None = None,
    textgrad_engine_name: str | None = None,
    a_mem_sys_llm_model: str | None = None,
    ace_reflector_model: str | None = None,
    ace_curator_model: str | None = None,
    n_select_sample: int | None = None,
    n_generate_sample: int | None = None,
    reasoning_bank_k: int | None = None,
) -> tuple[int, dict | None]:
    """
    Run mutation sequence from an existing log file. Can be called programmatically.
    
    Override args (model_type, model_name, etc.) take precedence over values in the log.
    
    Returns:
        (exit_code, sequence_report). sequence_report is None if load/run failed.
    """
    log_path = os.path.abspath(log_path)
    try:
        best_code, log_data = load_best_code_from_log(log_path)
    except Exception as e:
        print(f"❌ Failed to load log file {log_path}: {e}")
        return 1, None

    if verbose:
        print(f"📄 Loading log file: {log_path}")
        print(f"✅ Loaded best_code ({len(best_code)} characters)")
        if 'mutation_sequence' in log_data:
            existing_count = len(log_data['mutation_sequence'].get('sequence_results', []))
            print(f"ℹ️  Log file already contains 'mutation_sequence' with {existing_count} result(s). Will skip completed and append remaining.")

    task_info = extract_task_info_from_log(log_data)
    model_type = model_type or task_info['model_type']
    if model_type == 'huggingface':
        model_type = 'local'  # backward compat: old logs may have huggingface
    model_name = model_name or task_info['model_name']
    method = method or task_info['method']
    context = context or task_info['context']
    max_iterations = max_iterations or task_info['max_iterations']
    max_steps = max_steps or task_info['max_steps']
    base_task_name = task_info['task_name']
    # ACE: restore from log if not overridden
    if ace_reflector_model is None and log_data.get('ace_reflector_model'):
        ace_reflector_model = log_data['ace_reflector_model']
    if ace_curator_model is None and log_data.get('ace_curator_model'):
        ace_curator_model = log_data['ace_curator_model']
    # ToT: restore from log if not overridden
    if method == 'tree_of_thought':
        if n_select_sample is None and log_data.get('tree_of_thought_n_select') is not None:
            n_select_sample = log_data['tree_of_thought_n_select']
        if n_generate_sample is None and log_data.get('tree_of_thought_n_generate') is not None:
            n_generate_sample = log_data['tree_of_thought_n_generate']
        if n_select_sample is None:
            n_select_sample = 3
        if n_generate_sample is None:
            n_generate_sample = 2
    # ReasoningBank: restore k from log if not overridden
    if method == 'reasoning_bank' and reasoning_bank_k is None and log_data.get('reasoning_bank_k') is not None:
        reasoning_bank_k = log_data['reasoning_bank_k']

    if not base_task_name:
        print("❌ Could not determine base_task_name from log file")
        return 1, None

    log_filename = os.path.basename(log_path)
    run_number = extract_run_number_from_filename(log_filename)

    if verbose:
        print(f"\n{'='*80}")
        print("🚀 Mutation Sequence Configuration")
        print(f"{'='*80}")
        print(f"Base task: {base_task_name}")
        print(f"Model: {model_type}/{model_name}")
        print(f"Method: {method}")
        print(f"Context: {context}")
        print(f"Max iterations per mutation: {max_iterations}")
        print(f"Max steps per simulation: {max_steps}")
        print(f"Output directory: {output_dir}")
        if run_number:
            print(f"Run number: {run_number}")
        print(f"{'='*80}\n")

    try:
        sequence_report = run_mutation_sequence(
            base_task_name=base_task_name,
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
            initial_code=best_code,
            base_log_path=log_path,
            run_number=run_number,
            reflect_model_name=reflect_model_name,
            textgrad_engine_name=textgrad_engine_name,
            a_mem_sys_llm_model=a_mem_sys_llm_model,
            ace_reflector_model=ace_reflector_model,
            ace_curator_model=ace_curator_model,
            n_select_sample=n_select_sample,
            n_generate_sample=n_generate_sample,
            reasoning_bank_k=reasoning_bank_k,
        )
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"❌ Mutation sequence error: {e}")
        import traceback
        traceback.print_exc()
        return 1, None

    if sequence_report.get('error'):
        return 1, sequence_report
    if sequence_report.get('total_mutations', 0) == 0:
        return 1, sequence_report
    completed = sequence_report.get('completed_mutations', 0)
    total = sequence_report.get('total_mutations', 0)
    return (0 if completed == total else 1), sequence_report


def main():
    parser = argparse.ArgumentParser(
        description='Run mutation sequence from an existing log file\'s best_code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use all settings from log file
  python run_mutation_from_log.py --log evaluation_results/category_1_01/openai_deepseek-v3.2/baseline/previous_20260206_114931.json
  
  # Override specific parameters
  python run_mutation_from_log.py --log previous_20260206_114931.json --max-iterations 30 --max-steps 15000
  
  # Use different model
  python run_mutation_from_log.py --log previous_20260206_114931.json --model-name gpt-4
        """
    )
    
    parser.add_argument('--log', type=str, required=True,
                       help='Path to log JSON file containing best_code (will append mutation_sequence results to this file)')
    parser.add_argument('--model-type', type=str, default=None,
                       choices=['openai', 'local', 'mock'],
                       help='Override model type from log file')
    parser.add_argument('--model-name', type=str, default=None,
                       help='Override model name from log file')
    parser.add_argument('--api-key', type=str, default=None,
                       help='API key (if not provided, will use environment variable)')
    parser.add_argument('--model-path', type=str, default=None,
                       help='Local model path (if model-type is local)')
    parser.add_argument('--device', type=str, default='auto',
                       help='Device type: auto (automatic), cuda (use default GPU), cpu, cuda:1 (single GPU), or cuda:1,2,3 (multiple GPUs)')
    parser.add_argument('--max-iterations', type=int, default=20,
                       help='Override max iterations from log file')
    parser.add_argument('--max-steps', type=int, default=10000,
                       help='Override max simulation steps from log file')
    parser.add_argument('--method', type=str, default='baseline',
                       choices=['baseline', 'sys_feedback', 'reflexion', 'textgrad', 'self_refine', 'self_refine_inner_only', 'a_mem_sys', 'memento_nonparametric', 'rememberer', 'expel', 'ace', 'tree_of_thought', 'reasoning_bank', 'absolute_zero', 'absolute_zero_iter', 'science_codeevolve', 'alpha_evolve', 'theta_evolve', 'genome', 'seal', 'ragen', 'soar', 'discover'],
                       help='Override evaluation method from log file')
    parser.add_argument('--n-select-sample', type=int, default=None, dest='n_select_sample',
                       help='ToT: beams to keep per round (b). Default: from log or 3')
    parser.add_argument('--n-generate-sample', type=int, default=None, dest='n_generate_sample',
                       help='ToT: samples per beam per round (n). Default: from log or 2')
    parser.add_argument('--reasoning-bank-k', type=int, default=None, dest='reasoning_bank_k',
                       help='ReasoningBank: parallel k. Default: from log or 2')
    parser.add_argument('--ace-reflector-model', type=str, default=None, dest='ace_reflector_model',
                       help='Model for ACE Reflector (only when method=ace). Default: from log or deepseek-v3.2')
    parser.add_argument('--ace-curator-model', type=str, default=None, dest='ace_curator_model',
                       help='Model for ACE Curator (only when method=ace). Default: from log or deepseek-v3.2')
    parser.add_argument('--reflect-model-name', type=str, default='gpt-4o',
                       help='Model name for reflection LLM (only used when method=reflexion). Default: gpt-4o')
    parser.add_argument('--textgrad-engine-name', type=str, default='deepseek-v3.2',
                       help='Engine for TextGrad backward/optimizer (only used when method=textgrad). Default: deepseek-v3.2')
    parser.add_argument('--a-mem-llm-model', type=str, default='deepseek-v3.2',
                       help='LLM for memory module (only when method=a_mem_sys). Default: deepseek-v3.2')
    parser.add_argument('--context', type=str, default='all',
                       choices=['previous', 'all', 'last_3', 'best_score', 'best_score_plus_previous'],
                       help='Override context strategy from log file')
    parser.add_argument('--output-dir', type=str, default='evaluation_results',
                       help='Output directory for mutation sequence logs')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run in headless mode (default: True)')
    
    args = parser.parse_args()
    log_path = os.path.abspath(args.log)
    try:
        exit_code, sequence_report = run_mutation_for_log(
            log_path,
            model_type=args.model_type,
            model_name=args.model_name,
            method=args.method,
            context=args.context,
            max_iterations=args.max_iterations,
            max_steps=args.max_steps,
            api_key=args.api_key,
            model_path=args.model_path,
            device=args.device,
            output_dir=args.output_dir,
            headless=args.headless,
            verbose=True,
            reflect_model_name=getattr(args, 'reflect_model_name', None),
            textgrad_engine_name=getattr(args, 'textgrad_engine_name', None),
            a_mem_sys_llm_model=getattr(args, 'a_mem_llm_model', None),
            ace_reflector_model=getattr(args, 'ace_reflector_model', None),
            ace_curator_model=getattr(args, 'ace_curator_model', None),
            n_select_sample=getattr(args, 'n_select_sample', None),
            n_generate_sample=getattr(args, 'n_generate_sample', None),
            reasoning_bank_k=getattr(args, 'reasoning_bank_k', None),
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Mutation sequence interrupted by user")
        return 130

    if sequence_report is None:
        return exit_code

    # Print summary
    print(f"\n{'='*80}")
    print("📊 Mutation Sequence Summary")
    print(f"{'='*80}")
    print(f"Total mutations: {sequence_report.get('total_mutations', 0)}")
    print(f"Completed mutations: {sequence_report.get('completed_mutations', 0)}")
    if sequence_report.get('total_mutations', 0) > 0:
        print(f"Success rate: {sequence_report.get('success_rate', 0.0)*100:.1f}%")
    if sequence_report.get('error'):
        print(f"⚠️  Error: {sequence_report['error']}")
    print(f"\nDetailed results:")
    for result in sequence_report.get('sequence_results', []):
        mutated_task = result.get('mutated_task_name', 'unknown')
        status = result.get('status', 'unknown')
        result_data = result.get('result', {})
        success = result_data.get('success', False) if isinstance(result_data, dict) else False
        if status == 'already_completed':
            print(f"  ✅ {mutated_task}: Already completed (skipped)")
        elif status == 'already_failed':
            print(f"  ❌ {mutated_task}: Already failed (skipped)")
        elif success:
            print(f"  ✅ {mutated_task}: Success")
        else:
            print(f"  ❌ {mutated_task}: Failed")
    print(f"{'='*80}\n")
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            final_log_data = json.load(f)
        if 'mutation_sequence' in final_log_data:
            print(f"✅ Mutation sequence results saved incrementally to: {log_path}")
        else:
            print(f"⚠️  Warning: mutation_sequence not found in log file")
    except Exception as e:
        print(f"⚠️  Failed to verify mutation sequence in log file: {e}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
