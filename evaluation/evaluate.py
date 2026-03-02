import os
import sys

# CRITICAL: Disable vLLM's V1 multiprocessing BEFORE any vllm import.
# vLLM V1 spawns EngineCore as a separate process by default, which causes
# IPC failures when evaluate.py itself is already a subprocess (e.g. from
# run_evaluate_parallel.py).  Running EngineCore in-process avoids this.
os.environ["VLLM_ENABLE_V1_MULTIPROCESSING"] = "0"

# Use 'spawn' for multiprocessing so CUDA can be used (fork + CUDA = "Cannot re-initialize
# CUDA in forked subprocess"). Required for alpha_evolve/OpenEvolve process_parallel.
import multiprocessing
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass  # already set

import argparse
import json
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
    get_model_identifier, get_run_suffix, get_gif_path,
    get_gif_base_dir, get_evaluation_results_dir, detect_next_run_number,
    all_three_runs_complete, run_is_complete, is_cuda_oom, clean_special_tags,
)


class TaskEvaluator:
    """Task evaluator"""
    
    def __init__(self, task_name: str, model_type: str = 'mock', model_name: str = 'gpt-4', 
                 api_key: Optional[str] = None, max_iterations: int = 5, max_steps: int = 10000,
                 headless: bool = True, model_path: Optional[str] = None, device: Optional[str] = None,
                 method: str = 'baseline', context: str = 'previous', env_overrides: Optional[Dict[str, Any]] = None,
                 task_prompt_override: Optional[Dict[str, Any]] = None, run_number: Optional[int] = None,
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
        self.base_task_name_for_memory = base_task_name_for_memory  # For memento_nonparametric: store entries under base task (e.g. S_01) when running mutated task
        # Tree-of-Thought: use passed max_iterations (default 10 is set in main() when method=ToT); b=3, n=2
        if method == 'tree_of_thought':
            self.max_iterations = max_iterations
            self.n_select_sample = n_select_sample if n_select_sample is not None else 3
            self.n_generate_sample = n_generate_sample if n_generate_sample is not None else 2
        else:
            self.max_iterations = max_iterations
            self.n_select_sample = None
            self.n_generate_sample = None
        # Self-Refine: at most 10 "big refine" rounds (each round gets baseline-style verifier feedback); inner self-verify still capped at 5 per round
        if method == 'self_refine':
            self.max_iterations = min(self.max_iterations, 20)
        # Self-Refine inner-only: no external feedback; one round = generate + self-verify/refine up to 20 steps + one system eval
        if method == 'self_refine_inner_only':
            self.max_iterations = 1
        self.max_steps = max_steps
        self.headless = headless
        self.model_type = model_type
        self.model_name = model_name
        self.api_key = api_key
        self.method = method
        self.enable_feedback = (method == 'sys_feedback')
        self.context = context
        # When context is 'all', we actually use best_score_plus_previous behavior and save with _pseudo suffix
        self.use_conversation = False if context == 'all' else (context == 'all')
        self.env_overrides = env_overrides or {}
        self.is_mutated_task = is_mutated_task  # Flag to indicate if this is a mutated task
        
        # Load task prompt (can be overridden for stage/curriculum without creating new task dirs)
        if task_prompt_override is not None:
            self.task_prompt = task_prompt_override
        else:
            try:
                self.task_prompt = load_task_prompt(task_name)
            except Exception as e:
                raise ValueError(f"Failed to load prompt for task {task_name}: {e}")
        
        # Absolute-Zero / Absolute-Zero-Iter: use AZR HF inference (local only); absolute_zero = initial only (1 iter)
        if method in ('absolute_zero', 'absolute_zero_iter'):
            if model_type != 'local':
                raise ValueError(
                    "absolute_zero and absolute_zero_iter only support --model-type local. "
                    "Use baseline or sys_feedback for API models."
                )
            from methods.Parameter_Policy.absoulute_zero.absolute_zero_method import get_azr_solver
            self.solver = get_azr_solver(
                model_name=model_name,
                model_path=model_path,
                device=device or 'auto',
            )
            if method == 'absolute_zero':
                self.max_iterations = 1
        elif method == 'seal':
            # SEAL Test-Time Training: per-task LoRA adaptation (local only)
            if model_type != 'local':
                raise ValueError(
                    "seal only supports --model-type local. "
                    "Use baseline or sys_feedback for API models."
                )
            from methods.Parameter_Policy.seal.seal_method import get_seal_solver
            self.solver = get_seal_solver(
                model_name=model_name,
                model_path=model_path,
                device=device or 'cuda:0',
            )
        elif method == 'ragen':
            # RAGEN (StarPO): per-task multi-turn RL with GRPO + PPO-clip (local only)
            if model_type != 'local':
                raise ValueError(
                    "ragen only supports --model-type local. "
                    "Use baseline or sys_feedback for API models."
                )
            from methods.Parameter_Policy.ragen.ragen_method import get_ragen_solver
            self.solver = get_ragen_solver(
                model_name=model_name,
                model_path=model_path,
                device=device or 'cuda:0',
                ragen_n_rollouts=ragen_n_rollouts,
                ragen_ppo_epochs=ragen_ppo_epochs,
            )
            self.ragen_n_rollouts = ragen_n_rollouts
            self.ragen_ppo_epochs = ragen_ppo_epochs
        elif method == 'soar':
            # SOAR (Self-improving Operators for Automated Refinements):
            # per-task evolutionary search + SFT self-improvement (local only)
            if model_type != 'local':
                raise ValueError(
                    "soar only supports --model-type local. "
                    "Use baseline or sys_feedback for API models."
                )
            from methods.Parameter_Policy.soar.soar_method import get_soar_solver
            self.solver = get_soar_solver(
                model_name=model_name,
                model_path=model_path,
                device=device or 'cuda:0',
                soar_generations=soar_generations,
                soar_k_candidates=soar_k_candidates,
            )
            self.soar_generations = soar_generations
            self.soar_k_candidates = soar_k_candidates
        elif method == 'discover':
            # TTT-Discover: per-task test-time RL (local only)
            if model_type != 'local':
                raise ValueError(
                    "discover only supports --model-type local (involves LoRA tuning). "
                    "Use baseline or sys_feedback for API models."
                )
            from methods.Parameter_Policy.discover.discover_method import get_discover_solver
            self.solver = get_discover_solver(
                model_name=model_name,
                model_path=model_path,
                device=device or 'cuda:0',
                discover_num_epochs=discover_num_epochs,
                discover_group_size=discover_group_size,
                discover_groups_per_batch=discover_groups_per_batch,
                discover_learning_rate=discover_learning_rate,
                discover_adv_estimator=discover_adv_estimator,
                discover_adv_estimator_beta=discover_adv_estimator_beta,
                discover_loss_fn=discover_loss_fn,
                discover_lora_rank=discover_lora_rank,
                discover_max_tokens=discover_max_tokens,
                discover_temperature=discover_temperature,
                discover_num_substeps=discover_num_substeps,
                discover_max_expansion_rounds=discover_max_expansion_rounds,
            )
            self.discover_num_epochs = discover_num_epochs
            self.discover_group_size = discover_group_size
            self.discover_max_expansion_rounds = discover_max_expansion_rounds
        elif method == 'genome':
            if model_type != 'local':
                raise ValueError(
                    "genome only supports --model-type local. Run bootstrap_lora_dir.py first (creates genome/experts/)."
                )
            if not genome_best_lora_path:
                raise ValueError("genome requires genome_best_lora_path (Phase 1 best LoRA). Ensure Phase 1 cache exists.")
            from methods.Parameter_Policy.genome.genome_method import get_genome_solver
            self.solver = get_genome_solver(
                model_name=model_name,
                model_path=model_path,
                best_lora_path=genome_best_lora_path,
                device=device or 'auto',
            )
            self.genome_best_lora_path = genome_best_lora_path
            self.max_iterations = 20  # Phase 2: up to 20 refinement iterations
        else:
            # Initialize solver interface (or reuse base task's solver for mutated tasks)
            if solver_override is not None:
                self.solver = solver_override  # Reuse vLLM model to avoid OOM on mutation sequence
            else:
                self.solver = SolverInterface(
                    model_type=model_type,
                    model_name=model_name,
                    api_key=api_key,
                    model_path=model_path,
                    device=device
                )
        
        # Initialize verifier (allow environment overrides for mutated stages)
        self.verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=self.env_overrides)
        
        # Record iteration history
        self.iteration_history = []
        self.best_score = 0.0
        self.best_code = None
        self.best_metrics = None
        
        # Reflexion method: initialize reflection buffer (FIFO queue, max 3) and reflection LLM
        self.reflections = deque(maxlen=3) if method == 'reflexion' else []  # At most 3 reflections, oldest dropped
        self.reflections_str = ''      # Formatted reflections for prompt injection
        self.reflect_solver = None     # Reflection LLM (separate SolverInterface, always API)
        self.reflect_model_name = reflect_model_name or 'gpt-4o'
        if method == 'reflexion':
            print(f"🔄 Reflexion method: initializing reflection LLM ({self.reflect_model_name}), experience buffer max 3...")
            self.reflect_solver = SolverInterface(
                model_type='openai',
                model_name=self.reflect_model_name,
            )
            # Set the reflexion-specific system prompt on the reflection LLM
            self.reflect_solver.set_custom_system_prompt(REFLEXION_SYSTEM_PROMPT)
        
        # TextGrad method: lazy-init engine, Variable, and Optimizer
        self.tg_engine = None
        self.tg_code_var = None
        self.tg_optimizer = None
        self.textgrad_engine_name = textgrad_engine_name or 'deepseek-v3.2'
        if method == 'textgrad':
            print(f"🧮 TextGrad method: engine={self.textgrad_engine_name} (backward + optimizer)")
            from methods.Context.textgrad_method import create_textgrad_engine
            self.tg_engine = create_textgrad_engine(self.textgrad_engine_name)
        
        # A-mem-sys: memory module (LLM for memory = deepseek-v3.2 by default, not solver)
        # When initial_memory_system is set (e.g. from base task for mutated tasks), reuse it so
        # mutated task's first iteration sees full memory from the initial task (no reset).
        self._memory_system = initial_memory_system if initial_memory_system is not None else None
        self.a_mem_sys_llm_model = a_mem_sys_llm_model or 'deepseek-v3.2'
        if method == 'a_mem_sys':
            print(f"🧠 A-mem-sys method: memory LLM={self.a_mem_sys_llm_model} (not solver)")
            if initial_memory_system is not None:
                print(f"🧠 A-mem-sys: using initial memory from base task (mutated task will see T0's memory)")
        # Memento non-parametric: JSONL memory + Sup-SimCSE retrieve; prompt from retrieved cases only (no best+previous)
        self._memento_np_memory_path = None
        self._memento_np_items = []
        self._memento_np_pairs = []
        if method == 'memento_nonparametric':
            from methods.Memory.memento_nonparametric_method import get_memory_path, load_memory
            from evaluation.utils import get_evaluation_results_dir, get_model_identifier
            output_dir = get_evaluation_results_dir()
            model_identifier = get_model_identifier(model_type, model_name)
            # When initial_memory_system is a str, it is the pre-filled memory path (mutated task)
            if isinstance(initial_memory_system, str):
                self._memento_np_memory_path = initial_memory_system
                print(f"🧠 Memento non-parametric: using pre-filled memory from base task (mutated task)")
            else:
                self._memento_np_memory_path = get_memory_path(output_dir, task_name, model_identifier, run_number)
            self._memento_np_items, self._memento_np_pairs = load_memory(self._memento_np_memory_path)
            print(f"🧠 Memento non-parametric method: memory from {self._memento_np_memory_path} ({len(self._memento_np_items)} entries)")
        # ACE: playbook + Reflector/Curator (lazy-init when we have api_key); playbook in context each round
        self._playbook = initial_playbook if (initial_playbook and initial_playbook.strip()) else None
        self._ace_reflector = None
        self._ace_curator = None
        self._ace_next_global_id = 1
        self.ace_reflector_model = ace_reflector_model or 'deepseek-v3.2'
        self.ace_curator_model = ace_curator_model or 'deepseek-v3.2'
        if method == 'ace':
            from methods.Memory.ace_method import get_initial_playbook
            if self._playbook is None:
                self._playbook = get_initial_playbook()
            print(f"📚 ACE method: Reflector={self.ace_reflector_model}, Curator={self.ace_curator_model} (playbook in context each round)")
            if initial_playbook and initial_playbook.strip():
                print(f"📚 ACE: using initial playbook from base task (mutated task)")
        # ReasoningBank (parallel MaTTS): structured memory (title, description, content), K solutions per iteration
        self._reasoning_bank_path = None
        self._reasoning_bank_items = []
        self.reasoning_bank_k = 2 if reasoning_bank_k is None else max(1, int(reasoning_bank_k))
        if method == 'reasoning_bank':
            from methods.Memory.reasoning_bank_method import get_memory_path, load_bank
            from evaluation.utils import get_evaluation_results_dir, get_model_identifier
            output_dir = get_evaluation_results_dir()
            model_identifier = get_model_identifier(model_type, model_name)
            if isinstance(initial_memory_system, str):
                self._reasoning_bank_path = initial_memory_system
                self._reasoning_bank_items = load_bank(initial_memory_system)
                print(f"🧠 ReasoningBank: using pre-filled bank from base task ({len(self._reasoning_bank_items)} items)")
            else:
                self._reasoning_bank_path = get_memory_path(output_dir, task_name, model_identifier, run_number)
                self._reasoning_bank_items = load_bank(self._reasoning_bank_path)
            print(f"🧠 ReasoningBank (parallel MaTTS): k={self.reasoning_bank_k}, memory from {self._reasoning_bank_path} ({len(self._reasoning_bank_items)} items)")
        # Rememberer: read-only memory from same-category other tasks (rollout data); no update at test time
        self._rememberer_items = []
        self._rememberer_candidates = []
        if method == 'rememberer':
            from evaluation.utils import get_model_identifier
            from methods.Memory.rememberer_method import load_rememberer_memory_for_task, get_rememberer_root
            model_identifier = get_model_identifier(model_type, model_name)
            root = get_rememberer_root()
            self._rememberer_items, self._rememberer_candidates = load_rememberer_memory_for_task(
                task_name, model_identifier, root
            )
            print(f"🧠 Rememberer method: read-only memory from same-category other tasks ({len(self._rememberer_items)} entries)")
        # ExpeL: read-only memory from same-category other tasks (rollout + insights); no update at test time
        self._expel_items = []
        self._expel_rules = []
        self._expel_embedder = None
        if method == 'expel':
            from evaluation.utils import get_model_identifier
            from methods.Memory.expel_method import load_expel_memory_for_task
            model_identifier = get_model_identifier(model_type, model_name)
            self._expel_items, self._expel_rules, self._expel_embedder = load_expel_memory_for_task(
                task_name, model_identifier
            )
            print(f"🧠 ExpeL method: read-only memory from same-category other tasks ({len(self._expel_items)} entries, {len(self._expel_rules)} rules)")
        
        self.gif_base_dir = get_gif_base_dir()
        self.mutated_task_name = None
        self.run_number = run_number
        self._setup_gif_directory()

    def _sampling_seed(self, iteration: int = 0, offset: int = 0) -> int:
        """Seed for LLM sampling. Different per (run_number, iteration, offset) so 1st/2nd/3rd pass and iterations get diverse outputs."""
        return (self.run_number or 1) * 1000000 + iteration * 100 + offset

    def _build_revision_prompt(self, iteration: int, last_feedback: str, memory_block: Optional[str] = None) -> str:
        # Reflexion method: use reflexion-specific revision prompts with reflections injected
        if self.method == 'reflexion':
            return self._build_reflexion_revision_prompt(iteration, last_feedback)
        
        # When context is 'all', actually use best_score_plus_previous logic (pseudo mode)
        effective_context = 'best_score_plus_previous' if self.context == 'all' else self.context
        if effective_context == 'best_score_plus_previous':
            # Best-scoring + previous iteration (also used when --context all, pseudo mode)
            best_item = None
            best_score = -1.0
            best_iteration = None
            for item in self.iteration_history:
                score = item.get('score', 0.0)
                if score > best_score:
                    best_score = score
                    best_item = item
                    best_iteration = item.get('iteration')

            previous_item = self.iteration_history[-1] if self.iteration_history else None
            previous_iteration = previous_item.get('iteration') if previous_item else None
            previous_code = previous_item.get('code', '') if previous_item else ''
            previous_feedback = previous_item.get('feedback', '') if previous_item else ''

            current_iteration = iteration

            if best_item and best_item.get('code') and previous_code:
                best_code = best_item.get('code', '')
                best_feedback = best_item.get('feedback', '')

                if best_iteration == previous_iteration:
                    prompt = format_revision_prompt_best_plus_previous(
                        self.task_prompt, best_code, best_feedback,
                        '', '', last_feedback, best_iteration, previous_iteration, current_iteration,
                        memory_block=memory_block,
                    )
                    print(f"📝 Generating revision prompt (best score only, same iteration as previous, iteration={best_iteration}, best_score={best_score:.1f})...")
                else:
                    prompt = format_revision_prompt_best_plus_previous(
                        self.task_prompt, best_code, best_feedback,
                        previous_code, previous_feedback, last_feedback, best_iteration, previous_iteration, current_iteration,
                        memory_block=memory_block,
                    )
                    print(f"📝 Generating revision prompt (best score + previous context, best_iteration={best_iteration}, previous_iteration={previous_iteration}, best_score={best_score:.1f})...")
            elif previous_code:
                prompt = format_revision_prompt(self.task_prompt, previous_code, last_feedback)
                print("📝 Generating revision prompt (fallback to previous only - no best score found)...")
            else:
                prompt = format_initial_prompt(self.task_prompt)
                print("📝 Generating revision prompt (fallback to initial - no history available)...")
        elif effective_context == 'previous':
            # Default: only previous iteration
            previous_code = self.iteration_history[-1].get('code', '')
            if not previous_code:
                prompt = format_initial_prompt(self.task_prompt)
                print("📝 Generating revision prompt (no previous code available)...")
            else:
                prompt = format_revision_prompt(self.task_prompt, previous_code, last_feedback)
                print("📝 Generating revision prompt (previous iteration context)...")
        elif self.context == 'last_3':
            # Last 3 iterations: from the latest one, count backwards 3 iterations
            # e.g., if current is iteration 4, include iterations 1, 2, 3
            history_items = []
            # Get the last 3 iterations (including the most recent one)
            start_idx = max(0, len(self.iteration_history) - 3)
            for i in range(start_idx, len(self.iteration_history)):
                item = self.iteration_history[i]
                code = item.get('code', '')
                feedback = item.get('feedback', '')
                if code:
                    history_items.append((code, feedback))
            if len(history_items) == 0:
                # Fallback to previous
                previous_code = self.iteration_history[-1].get('code', '') if self.iteration_history else ''
                if previous_code:
                    prompt = format_revision_prompt(self.task_prompt, previous_code, last_feedback)
                else:
                    prompt = format_initial_prompt(self.task_prompt)
                print("📝 Generating revision prompt (fallback to previous)...")
            else:
                prompt = format_revision_prompt_last_n(self.task_prompt, history_items, last_feedback)
                print(f"📝 Generating revision prompt (last {len(history_items)} iterations context)...")
        elif self.context == 'best_score':
            # Best-scoring iteration
            best_item = None
            best_score = -1.0
            for item in self.iteration_history:
                score = item.get('score', 0.0)
                if score > best_score:
                    best_score = score
                    best_item = item
            
            if best_item and best_item.get('code'):
                best_code = best_item.get('code', '')
                best_feedback = best_item.get('feedback', '')
                prompt = format_revision_prompt_best_score(self.task_prompt, best_code, best_feedback, last_feedback)
                print(f"📝 Generating revision prompt (best score context, score={best_score:.1f})...")
            else:
                # Fallback to previous
                previous_code = self.iteration_history[-1].get('code', '') if self.iteration_history else ''
                if previous_code:
                    prompt = format_revision_prompt(self.task_prompt, previous_code, last_feedback)
                else:
                    prompt = format_initial_prompt(self.task_prompt)
                print("📝 Generating revision prompt (fallback to previous - no best score found)...")
        else:
            # Unknown context strategy, fallback to previous
            previous_code = self.iteration_history[-1].get('code', '') if self.iteration_history else ''
            if previous_code:
                prompt = format_revision_prompt(self.task_prompt, previous_code, last_feedback)
            else:
                prompt = format_initial_prompt(self.task_prompt)
            print(f"📝 Generating revision prompt (unknown context '{self.context}', fallback to previous)...")
        
        return prompt
    
    def _build_reflexion_revision_prompt(self, iteration: int, last_feedback: str) -> str:
        """Build revision prompt for reflexion method, using best_score_plus_previous logic + reflections."""
        # Find best-scoring item
        best_item = None
        best_score = -1.0
        best_iteration = None
        for item in self.iteration_history:
            score = item.get('score', 0.0)
            if score > best_score:
                best_score = score
                best_item = item
                best_iteration = item.get('iteration')

        previous_item = self.iteration_history[-1] if self.iteration_history else None
        previous_iteration = previous_item.get('iteration') if previous_item else None
        previous_code = previous_item.get('code', '') if previous_item else ''
        previous_feedback = previous_item.get('feedback', '') if previous_item else ''

        if best_item and best_item.get('code') and previous_code:
            best_code = best_item.get('code', '')
            best_fb = best_item.get('feedback', '')

            prompt = format_revision_prompt_reflexion(
                self.task_prompt, self.reflections_str,
                best_code, best_fb,
                previous_code if best_iteration != previous_iteration else '',
                previous_feedback if best_iteration != previous_iteration else '',
                last_feedback,
                best_iteration, previous_iteration, iteration
            )
            print(f"📝 Generating reflexion revision prompt (best_iter={best_iteration}, prev_iter={previous_iteration}, best_score={best_score:.1f}, reflections={len(self.reflections)})...")
        elif previous_code:
            prompt = format_revision_prompt_reflexion_simple(
                self.task_prompt, self.reflections_str, previous_code, last_feedback
            )
            print(f"📝 Generating reflexion revision prompt (previous only, reflections={len(self.reflections)})...")
        else:
            prompt = format_initial_prompt(self.task_prompt)
            print("📝 Generating reflexion revision prompt (fallback to initial - no history available)...")
        return prompt

    def _generate_reflection(self, code: str, feedback: str, iteration: int) -> str:
        """
        Call the reflection LLM to generate a diagnostic reflection after a failed iteration.
        
        Args:
            code: The code that was attempted (may be None if code generation failed)
            feedback: The baseline feedback string (metrics, scores, errors)
            iteration: The iteration number that just failed
        Returns:
            str: The reflection text
        """
        if self.reflect_solver is None:
            return ''
        
        code_str = code if code else '(No code was generated - code generation failed)'
        reflection_prompt = format_reflection_prompt(
            self.task_prompt, code_str, feedback, iteration
        )
        
        try:
            print(f"🔄 Generating reflection (iteration {iteration})...")
            # The reflection LLM generates text, not code. We use generate_code but
            # extract the raw text response instead of the code.
            _, raw_output, token_usage = self.reflect_solver.generate_code(reflection_prompt)
            
            # Extract the reflection text: take the raw output, strip code blocks if any
            # The reflection should be plain text (diagnosis + plan), not code
            reflection = raw_output.strip() if raw_output else ''
            
            # Truncate very long reflections to keep prompt manageable
            max_reflection_len = 1000
            if len(reflection) > max_reflection_len:
                reflection = reflection[:max_reflection_len] + '...'
            
            print(f"💭 Reflection (iteration {iteration}): {reflection[:200]}...")
            return reflection
        except Exception as e:
            print(f"⚠️  Failed to generate reflection: {e}")
            return f"(Reflection generation failed: {str(e)})"

    def _seal_ttt_step(self):
        """
        SEAL Test-Time Training step: collect good solutions from iteration_history
        and train LoRA.  Called after each iteration's verification.
        
        Following SEAL (update_model.py) pattern: reset LoRA → retrain on all
        accumulated positive-score (prompt, response) pairs.
        """
        solutions = []
        for item in self.iteration_history:
            if item.get('code') and item.get('score', 0) > 0:
                solutions.append({
                    'prompt': item.get('prompt', ''),
                    'code': item['code'],
                    'score': item['score'],
                    'raw_output': item.get('raw_llm_output') or item.get('code', ''),
                })
        if solutions:
            try:
                self.solver.train_on_solutions(solutions)
            except Exception as exc:
                print(f"⚠️  SEAL TTT training failed (non-fatal): {exc}")
                import traceback
                traceback.print_exc()
        else:
            print("🔧 SEAL: no positive-score solutions yet, skipping TTT")

    def _ragen_pretrain(self):
        """
        RAGEN pre-training step: collect N rollout episodes, train LoRA via
        GRPO + PPO-clip.  Called ONCE before the main evaluation loop.

        Following RAGEN (StarPO) pattern (agent_trainer.py fit()):
            1. Reset LoRA to blank state.
            2. Collect N complete multi-turn episodes (each up to max_turns turns).
            3. Filter episodes by reward (StarPO-S rollout filtering).
            4. Compute GRPO advantages and PPO-clip update on LoRA.
            5. Freeze parameters for evaluation.
        """
        try:
            stats = self.solver.run_pretrain(
                task_prompt=self.task_prompt,
                verifier=self.verifier,
            )
            self._ragen_pretrain_stats = stats
            if stats.get("skipped"):
                print("[RAGEN] Pre-training was skipped (insufficient data)")
            else:
                print(f"[RAGEN] Pre-training complete: "
                      f"{stats.get('n_episodes', 0)} episodes, "
                      f"mean_reward={stats.get('mean_reward', 0):.3f}")
        except Exception as exc:
            print(f"[RAGEN] Pre-training failed (non-fatal): {exc}")
            import traceback
            traceback.print_exc()
            self._ragen_pretrain_stats = {"skipped": True, "error": str(exc)}

    def _discover_pretrain(self):
        """
        Discover pre-training: num_epochs of (group_size rollouts -> [optional expansion if constant reward]
        -> advantage -> importance_sampling update). Called ONCE before the main evaluation loop.
        """
        try:
            stats = self.solver.run_pretrain(
                task_prompt=self.task_prompt,
                verifier=self.verifier,
            )
            self._discover_pretrain_stats = stats
            print(f"[Discover] Pre-training complete: "
                  f"epochs={stats.get('n_epochs', 0)}, "
                  f"mean_reward={stats.get('mean_reward', 0):.4f}, "
                  f"expansion_rounds_used={stats.get('expansion_rounds_used', 0)}, "
                  f"total_trajectories={stats.get('expansion_total_trajectories', 0)}")
        except Exception as exc:
            print(f"[Discover] Pre-training failed (non-fatal): {exc}")
            import traceback
            traceback.print_exc()
            self._discover_pretrain_stats = {"error": str(exc)}

    def _run_soar_evaluation(self):
        """
        SOAR self-improving evolutionary search evaluation.

        Runs G generations. Each generation = a full 20-iteration episode with
        K candidates per iteration (test-time search) + best-of-K selection.
        After each generation (except the last), SFT train LoRA on the
        accumulated archive. The last generation's results become the
        evaluation output.

        Ref: Algorithm 1 in Pourcel et al. (ICML 2025, arXiv 2507.14172)
        Ref: soar/repair/rex.py (REX Thompson sampling)
        Ref: soar/training/train_unsloth.py (SFT training)
        """
        from evaluation.prompt import (
            format_initial_prompt,
            format_revision_prompt_best_plus_previous,
        )
        from evaluation.feedback import format_feedback
        from evaluation.utils import is_cuda_oom

        G = self.soar_generations
        K = self.soar_k_candidates
        solver = self.solver

        print(f"[SOAR] Starting evaluation: {G} generations, "
              f"K={K} candidates/iter, {self.max_iterations} iters/gen")

        for gen in range(1, G + 1):
            is_final_gen = (gen == G)
            print(f"\n{'='*60}")
            print(f"[SOAR] Generation {gen}/{G}"
                  f"{' (FINAL — results used for evaluation)' if is_final_gen else ''}")
            print(f"{'='*60}")

            # SFT train before non-first generations (on accumulated archive)
            if gen > 1 and len(solver.archive) > 0:
                print(f"[SOAR] SFT training on archive ({len(solver.archive)} entries)...")
                try:
                    sft_stats = solver.sft_train_on_archive()
                    if sft_stats.get("skipped"):
                        print("[SOAR] SFT skipped (no valid data)")
                    else:
                        print(f"[SOAR] SFT done: {sft_stats.get('n_total_texts', 0)} samples")
                except Exception as exc:
                    print(f"[SOAR] SFT failed (non-fatal): {exc}")
                    import traceback
                    traceback.print_exc()

            # Run one generation (20-iteration episode)
            gen_history: List[Dict[str, Any]] = []
            gen_best_score = 0.0
            gen_best_code: Optional[str] = None
            gen_best_metrics: Optional[Dict] = None
            gen_best_feedback = ""
            gen_best_iteration: Optional[int] = None
            previous_code: Optional[str] = None
            total_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

            for iteration in range(1, self.max_iterations + 1):
                print(f"\n  [SOAR gen {gen}] Iteration {iteration}/{self.max_iterations}")

                try:
                    # 1. Build prompt
                    if iteration == 1:
                        prompt = format_initial_prompt(self.task_prompt)
                    else:
                        # REX Thompson sampling: select which past solution to
                        # use as "best" context (exploration/exploitation balance)
                        thompson_best = solver.thompson_select_best()
                        if thompson_best and thompson_best.get("code"):
                            ctx_best_code = thompson_best["code"]
                            ctx_best_feedback = thompson_best.get("feedback", "")
                            ctx_best_iter = thompson_best.get("iteration")
                        else:
                            ctx_best_code = gen_best_code or ""
                            ctx_best_feedback = gen_best_feedback
                            ctx_best_iter = gen_best_iteration

                        prev_feedback = gen_history[-1].get("feedback", "") if gen_history else ""
                        prompt = format_revision_prompt_best_plus_previous(
                            self.task_prompt,
                            best_code=ctx_best_code,
                            best_feedback=ctx_best_feedback,
                            previous_code=previous_code or "",
                            previous_feedback=prev_feedback,
                            current_feedback=prev_feedback,
                            best_iteration=ctx_best_iter,
                            previous_iteration=iteration - 1,
                            current_iteration=iteration,
                        )

                    # 2. Generate K candidates (SOAR test-time search)
                    candidates = solver.generate_k_candidates(prompt, k=K)

                    # 3. Verify each candidate, pick best
                    best_candidate = None
                    best_cand_score = -1.0
                    all_cand_results: List[Dict] = []

                    for ci, (cand_code, cand_raw, cand_tok) in enumerate(candidates):
                        cand_score = 0.0
                        cand_success = False
                        cand_metrics: Dict[str, Any] = {}
                        cand_error = None

                        if cand_code and "def build_agent" in cand_code and len(cand_code.strip()) >= 30:
                            try:
                                gif_path = None
                                if is_final_gen and ci == 0 and self.save_gif:
                                    gif_path = self._get_gif_path(iteration)
                                cand_success, cand_score, cand_metrics, cand_error = (
                                    self.verifier.verify_code(
                                        cand_code, headless=self.headless,
                                        save_gif_path=gif_path,
                                    )
                                )
                            except Exception as exc:
                                if is_cuda_oom(exc):
                                    raise
                                cand_error = str(exc)
                                cand_metrics = {"error_type": "verification_error"}
                        elif cand_code:
                            cand_error = "missing build_agent or too short"
                            cand_metrics = {"error_type": "code_validation"}
                        else:
                            cand_error = "no code extracted"
                            cand_metrics = {"error_type": "code_extraction"}

                        all_cand_results.append({
                            "code": cand_code, "raw_output": cand_raw,
                            "token_usage": cand_tok, "score": cand_score,
                            "success": cand_success, "metrics": cand_metrics,
                            "error": cand_error,
                        })

                        # Add ALL candidates to archive (SOAR keeps everything)
                        parent_uid = None
                        if gen_history:
                            last_uid = gen_history[-1].get("_soar_best_uid")
                            if last_uid is not None:
                                parent_uid = last_uid

                        solver.add_to_archive(
                            code=cand_code, raw_output=cand_raw,
                            score=cand_score, success=cand_success,
                            prompt=prompt, feedback="",
                            iteration=iteration, generation=gen,
                            parent_uid=parent_uid,
                        )

                        if cand_score > best_cand_score:
                            best_cand_score = cand_score
                            best_candidate = all_cand_results[-1]

                    # 4. Use best candidate
                    if best_candidate and best_candidate["code"]:
                        current_code = best_candidate["code"]
                        raw_llm_output = best_candidate["raw_output"]
                        token_usage = best_candidate["token_usage"] or {}
                        score = best_candidate["score"]
                        success = best_candidate["success"]
                        metrics = best_candidate["metrics"]
                        error = best_candidate["error"]
                    else:
                        # All K candidates failed
                        current_code = None
                        raw_llm_output = None
                        token_usage = {}
                        score = 0.0
                        success = False
                        metrics = {"error_type": "all_candidates_failed"}
                        error = "All K candidates failed"

                    # Accumulate token usage
                    for cr in all_cand_results:
                        tu = cr.get("token_usage") or {}
                        total_token_usage["prompt_tokens"] += tu.get("prompt_tokens", 0)
                        total_token_usage["completion_tokens"] += tu.get("completion_tokens", 0)
                        total_token_usage["total_tokens"] += tu.get("total_tokens", 0)

                    # 5. Generate feedback
                    failed = metrics.get("failed", False)
                    failure_reason = metrics.get("failure_reason", None)
                    feedback = format_feedback(
                        metrics, score, success, failed, failure_reason, iteration,
                        error=error, task_name=self.task_name,
                        include_suggestions=self.enable_feedback,
                    )

                    # Update last archive entry's feedback
                    if solver.archive:
                        solver.archive[-1]["feedback"] = feedback

                    # 6. Record iteration result
                    iter_result = {
                        "iteration": iteration,
                        "prompt": prompt,
                        "code": current_code,
                        "raw_llm_output": raw_llm_output,
                        "token_usage": token_usage,
                        "success": success,
                        "score": score,
                        "metrics": metrics,
                        "error": error,
                        "feedback": feedback,
                        "soar_k_candidates": K,
                        "soar_all_candidates_scores": [c["score"] for c in all_cand_results],
                        "soar_generation": gen,
                        "_soar_best_uid": solver.archive[-1]["unique_id"] if solver.archive else None,
                    }
                    gen_history.append(iter_result)

                    # 7. Update generation best
                    if score > gen_best_score:
                        gen_best_score = score
                        gen_best_code = current_code
                        gen_best_metrics = metrics
                        gen_best_feedback = feedback
                        gen_best_iteration = iteration
                        print(f"    New best: {score:.1f}/100")

                    print(f"    Best-of-{K}: score={score:.1f}, "
                          f"all_scores={[c['score'] for c in all_cand_results]}")

                    # 8. Check success
                    if success:
                        print(f"    Task solved at iteration {iteration}!")
                        break

                    previous_code = current_code

                except Exception as exc:
                    if is_cuda_oom(exc):
                        print(f"[SOAR] CUDA OOM - stopping: {exc}")
                        raise
                    print(f"  [SOAR] Iteration {iteration} error: {exc}")
                    import traceback
                    traceback.print_exc()
                    gen_history.append({
                        "iteration": iteration,
                        "prompt": prompt if "prompt" in locals() else None,
                        "code": None,
                        "raw_llm_output": None,
                        "token_usage": {},
                        "success": False,
                        "score": 0.0,
                        "metrics": {"error_type": "iteration_error", "error_message": str(exc)},
                        "error": str(exc),
                        "feedback": "",
                        "soar_generation": gen,
                    })
                    previous_code = None
                    continue

            # After last generation: set evaluation results
            if is_final_gen:
                self.iteration_history = gen_history
                self.best_score = gen_best_score
                self.best_code = gen_best_code
                self.best_metrics = gen_best_metrics

            print(f"[SOAR] Generation {gen} complete: best_score={gen_best_score:.1f}, "
                  f"iters={len(gen_history)}, archive={len(solver.archive)}")

        # Store SOAR stats for report
        self._soar_stats = {
            "generations": G,
            "k_candidates": K,
            "archive_size": len(solver.archive),
            "train_count": solver._train_count,
            "final_best_score": self.best_score,
        }

    def evaluate(self) -> Dict[str, Any]:
        """
        Execute evaluation process
        Returns:
            Evaluation result dictionary
        """
        print(f"\n{'='*60}")
        print(f"Starting evaluation for task: {self.task_name}")
        print(f"Model: {self.solver.model_type}/{self.solver.model_name}")
        print(f"Method: {self.method}")
        if self.method == 'reflexion':
            print(f"Reflection LLM: {self.reflect_model_name}")
        if self.method == 'textgrad':
            print(f"TextGrad engine: {self.textgrad_engine_name}")
        print(f"Context: {self.context}")
        print(f"Max iterations: {self.max_iterations}")
        if self.method == 'tree_of_thought':
            print(f"ToT: b={self.n_select_sample}, n={self.n_generate_sample} (1 run only)")
        print(f"{'='*60}\n")
        
        # Tree-of-Thought: verifier-guided beam search (b beams, n samples per beam per round)
        if self.method == 'tree_of_thought':
            self._run_tree_of_thought()
            self.verifier.cleanup()
            return self._generate_report()
        
        # SOAR: self-improving evolutionary search (G generations, K candidates/iter)
        if self.method == 'soar':
            self._run_soar_evaluation()
            self.verifier.cleanup()
            return self._generate_report()
        
        current_code = None
        previous_code = None

        # RAGEN: run RL pre-training (collect N rollout episodes, GRPO+PPO update)
        # before the main evaluation loop.  After this, LoRA params are frozen.
        if self.method == 'ragen':
            self._ragen_pretrain()
        if self.method == 'discover':
            self._discover_pretrain()

        # In multi-turn chat mode, keep a single shared context window for the whole task.
        if self.use_conversation:
            self.solver.reset_conversation()
            # Set system prompt with task information (only once at the start)
            system_prompt = format_system_prompt_with_task(self.task_prompt, include_demonstrations=True)
            self.solver.set_custom_system_prompt(system_prompt)
            print("📝 Set system prompt with task information (context='all' mode)")
        
        it_range = range(1, self.max_iterations + 1)
        pbar = tqdm(it_range, desc=f"{self.task_name} iter", total=self.max_iterations, unit="iter")
        for iteration in pbar:
            pbar.set_postfix_str(f"iter {iteration}/{self.max_iterations}")
            print(f"\n{'='*60}")
            print(f"Iteration {iteration}/{self.max_iterations}")
            print(f"{'='*60}\n")
            # Checkpoint so segfault/crash does not lose results (saves state from previous iterations)
            if iteration > 1:
                self._save_checkpoint(output_dir='evaluation_results')
            try:
                # ===== TextGrad: self-contained optimisation for iterations 2+ =====
                if self.method == 'textgrad' and iteration > 1 and self.tg_code_var is not None:
                    last_feedback = self.iteration_history[-1].get('feedback', '')
                    print(f"🧮 TextGrad optimisation step (iteration {iteration})...")
                    
                    tg_current_code = None
                    tg_raw_output = None
                    tg_gradient_text = None
                    
                    try:
                        from methods.Context.textgrad_method import textgrad_optimize_step, extract_code_from_textgrad_output
                        tg_new_code, tg_raw_output, tg_gradient_text = textgrad_optimize_step(
                            self.tg_code_var, self.tg_optimizer, self.tg_engine,
                            last_feedback, self.task_prompt
                        )
                        if tg_new_code is not None:
                            tg_current_code = extract_code_from_textgrad_output(tg_new_code) or tg_new_code
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        print(f"❌ TextGrad optimisation failed: {exc}")
                        tg_raw_output = str(exc)
                    
                    # Valid code → verify → record
                    if tg_current_code and len(tg_current_code.strip()) >= 50 and 'def build_agent' in tg_current_code:
                        self.tg_code_var.set_value(tg_current_code)
                        
                        gif_path = self._get_gif_path(iteration) if self.save_gif else None
                        if gif_path:
                            print(f"📹 Will save GIF to: {gif_path}")
                        success, score, metrics, error = self.verifier.verify_code(
                            tg_current_code, headless=self.headless, save_gif_path=gif_path
                        )
                        if gif_path and os.path.exists(gif_path):
                            print(f"✅ GIF saved: {gif_path}")
                        
                        failed = metrics.get('failed', False)
                        failure_reason = metrics.get('failure_reason', None)
                        feedback = format_feedback(
                            metrics, score, success, failed, failure_reason, iteration,
                            error=error, task_name=self.task_name,
                            include_suggestions=False  # TextGrad provides its own feedback via gradients
                        )
                        
                        self.iteration_history.append({
                            'iteration': iteration,
                            'prompt': f"[TextGrad step {iteration}]",
                            'code': tg_current_code,
                            'raw_llm_output': tg_raw_output,
                            'token_usage': {},
                            'success': success,
                            'score': score,
                            'metrics': metrics,
                            'error': error,
                            'feedback': feedback,
                            'gradient': tg_gradient_text,
                        })
                        
                        if score > self.best_score:
                            self.best_score = score
                            self.best_code = tg_current_code
                            self.best_metrics = metrics
                            print(f"🎯 New best score: {score:.1f}/100")
                        
                        print(f"📊 TextGrad result: Score={score:.1f}/100, Success={'✅' if success else '❌'}")
                        
                        if success:
                            print(f"\n🎉 Task completed successfully! Iterations: {iteration}")
                            break
                        
                        previous_code = tg_current_code
                    else:
                        # Invalid / no code produced → record error
                        error_msg = 'TextGrad generated invalid code'
                        if tg_current_code is None:
                            error_msg = f'TextGrad optimisation failed: {tg_raw_output}'
                        elif len(tg_current_code.strip()) < 50:
                            error_msg = 'TextGrad generated code is too short'
                        elif 'def build_agent' not in tg_current_code:
                            error_msg = "TextGrad code missing 'def build_agent'"
                        print(f"⚠️  {error_msg}")
                        
                        error_metrics = {
                            'error_type': 'textgrad_generation_error',
                            'error_stage': 'textgrad_step',
                            'error_message': error_msg,
                        }
                        feedback = format_feedback(
                            error_metrics, 0.0, False, False, None, iteration,
                            error=error_msg, task_name=self.task_name,
                            include_suggestions=False
                        )
                        self.iteration_history.append({
                            'iteration': iteration,
                            'prompt': f"[TextGrad step {iteration}]",
                            'code': tg_current_code,
                            'raw_llm_output': tg_raw_output,
                            'token_usage': {},
                            'success': False,
                            'score': 0.0,
                            'metrics': error_metrics,
                            'error': error_msg,
                            'feedback': feedback,
                            'gradient': tg_gradient_text,
                        })
                        previous_code = tg_current_code or (self.tg_code_var.value if self.tg_code_var else None)
                    
                    continue  # TextGrad handled this iteration; skip the standard solver path
                
                # ===== Self-Refine: at most 10 big-refine rounds (each gets baseline-style feedback), 5 self-verify per round =====
                if self.method == 'self_refine':
                    from methods.Context.self_refine_method import (
                        format_self_feedback_prompt,
                        format_revision_prompt_self_refine_inner,
                        self_verify_says_correct,
                    )
                    # Per round: at most 5 self-verify steps => at most 4 inner refine cycles. Total rounds capped in __init__ (max 10).
                    MAX_SELF_VERIFY_STEPS = 5
                    self_refine_inner_steps = []  # per-round self-verify history for JSON

                    # --- Step A: Get initial code for this round ---
                    if iteration == 1:
                        prompt = format_initial_prompt(self.task_prompt)
                        print("📝 Self-Refine round 1: initial prompt...")
                    else:
                        last_system_feedback = self.iteration_history[-1].get('feedback', '')
                        prompt = self._build_revision_prompt(iteration, last_system_feedback)
                        print(f"📝 Self-Refine round {iteration}: revision prompt (from last system feedback)...")
                    print("🤖 Generating initial code for this round...")
                    try:
                        current_code, raw_llm_output, token_usage = self.solver.generate_code(
                            prompt, use_conversation=self.use_conversation, reset_conversation=False,
                            seed=self._sampling_seed(iteration, 0)
                        )
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        print(f"❌ Self-Refine code generation failed: {exc}")
                        error_msg = f'Self-Refine code generation failed: {str(exc)}'
                        error_metrics = {'error_type': 'self_refine_init_error', 'error_stage': 'init', 'error_message': str(exc)}
                        feedback = format_feedback(error_metrics, 0.0, False, False, None, iteration, error=error_msg, task_name=self.task_name, include_suggestions=False)
                        self.iteration_history.append({
                            'iteration': iteration, 'prompt': prompt, 'code': None, 'raw_llm_output': None, 'token_usage': {},
                            'success': False, 'score': 0.0, 'metrics': error_metrics, 'error': error_msg, 'feedback': feedback,
                            'self_refine_inner_steps': [],
                        })
                        continue

                    if not current_code or len(current_code.strip()) < 50 or 'def build_agent' not in current_code:
                        print("⚠️  Self-Refine initial code invalid for this round; skipping inner loop.")
                        current_code = current_code or "(invalid)"
                    else:
                        # --- Step B: Inner self-verify loop (no system verifier until exit) ---
                        self_refine_inner_steps = []
                        inner_step = 0
                        while inner_step < MAX_SELF_VERIFY_STEPS:
                            inner_step += 1
                            print(f"  🔄 Self-verify step {inner_step}...")
                            verify_prompt = format_self_feedback_prompt(current_code, self.task_prompt)
                            try:
                                _, raw_verify, verify_tokens = self.solver.generate_code(
                                    verify_prompt, use_conversation=False, reset_conversation=False,
                                    seed=self._sampling_seed(iteration, inner_step * 10 + 1)
                                )
                                self_verify_output = (raw_verify or "").strip()
                            except Exception as exc:
                                if is_cuda_oom(exc):
                                    raise
                                self_verify_output = f"(Self-verify failed: {exc})"
                                verify_tokens = {}
                            self_refine_inner_steps.append({
                                'step': inner_step,
                                'self_verify_output': self_verify_output,
                                'code_before': current_code,
                            })
                            if self_verify_says_correct(self_verify_output):
                                print(f"  ✅ Model said 'It is correct.' — exiting self-verify loop after {inner_step} step(s).")
                                break
                            # Refine
                            refine_prompt = format_revision_prompt_self_refine_inner(self.task_prompt, current_code, self_verify_output)
                            try:
                                new_code, new_raw, refine_tokens = self.solver.generate_code(
                                    refine_prompt, use_conversation=self.use_conversation, reset_conversation=False,
                                    seed=self._sampling_seed(iteration, inner_step * 10 + 2)
                                )
                            except Exception as exc:
                                if is_cuda_oom(exc):
                                    raise
                                self_refine_inner_steps[-1]['refine_error'] = str(exc)
                                self_refine_inner_steps[-1]['code_after'] = None
                                print(f"  ⚠️  Refine failed: {exc}; keeping previous code.")
                                break
                            self_refine_inner_steps[-1]['code_after'] = new_code
                            if new_code and len(new_code.strip()) >= 50 and 'def build_agent' in new_code:
                                current_code = new_code
                            else:
                                print("  ⚠️  Refined code invalid; keeping previous code.")
                                break
                        if inner_step >= MAX_SELF_VERIFY_STEPS:
                            print(f"  ⚠️  Reached max self-verify steps ({MAX_SELF_VERIFY_STEPS}); proceeding to verifier.")

                    # --- Step C: Run system verifier once ---
                    code_to_verify = current_code if (current_code and 'def build_agent' in current_code) else (current_code or "")
                    gif_path = self._get_gif_path(iteration) if self.save_gif else None
                    if gif_path:
                        print(f"  📹 Running system verifier once (GIF: {gif_path})...")
                    success, score, metrics, error = self.verifier.verify_code(
                        code_to_verify,
                        headless=self.headless, save_gif_path=gif_path
                    )
                    if gif_path and os.path.exists(gif_path):
                        print(f"  ✅ GIF saved: {gif_path}")
                    failed = metrics.get('failed', False)
                    failure_reason = metrics.get('failure_reason', None)
                    feedback = format_feedback(
                        metrics, score, success, failed, failure_reason, iteration,
                        error=error, task_name=self.task_name, include_suggestions=False,
                    )
                    hist_entry = {
                        'iteration': iteration,
                        'prompt': prompt,
                        'code': current_code,
                        'raw_llm_output': raw_llm_output if 'raw_llm_output' in dir() else None,
                        'token_usage': token_usage if 'token_usage' in dir() else {},
                        'success': success,
                        'score': score,
                        'metrics': metrics,
                        'error': error,
                        'feedback': feedback,
                        'self_refine_inner_steps': self_refine_inner_steps,
                    }
                    self.iteration_history.append(hist_entry)
                    if score > self.best_score:
                        self.best_score = score
                        self.best_code = current_code
                        self.best_metrics = metrics
                        print(f"  🎯 New best score: {score:.1f}/100")
                    print(f"  📊 Self-Refine round {iteration}: Score={score:.1f}/100, Success={'✅' if success else '❌'}")
                    if success:
                        print(f"\n🎉 Task completed successfully! Iterations: {iteration}")
                        break
                    previous_code = current_code
                    continue  # Self-Refine handled this iteration

                # ===== Self-Refine inner-only: no external feedback; one round = generate + self-verify/refine (max 20) + one eval =====
                if self.method == 'self_refine_inner_only':
                    from methods.Context.self_refine_method import (
                        format_self_feedback_prompt,
                        format_revision_prompt_self_refine_inner,
                        self_verify_says_correct,
                    )
                    MAX_SELF_VERIFY_STEPS_INNER_ONLY = 20  # cap to prevent infinite self-verify loop
                    self_refine_inner_steps = []

                    # --- Step A: Get initial code (only round; no system feedback) ---
                    prompt = format_initial_prompt(self.task_prompt)
                    print("📝 Self-Refine inner-only: initial prompt (no external feedback), then self-verify/refine up to 20 steps...")
                    try:
                        current_code, raw_llm_output, token_usage = self.solver.generate_code(
                            prompt, use_conversation=self.use_conversation, reset_conversation=False,
                            seed=self._sampling_seed(iteration, 0)
                        )
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        print(f"❌ Self-Refine inner-only code generation failed: {exc}")
                        error_msg = f'Self-Refine inner-only code generation failed: {str(exc)}'
                        error_metrics = {'error_type': 'self_refine_init_error', 'error_stage': 'init', 'error_message': str(exc)}
                        feedback = format_feedback(error_metrics, 0.0, False, False, None, iteration, error=error_msg, task_name=self.task_name, include_suggestions=False)
                        self.iteration_history.append({
                            'iteration': iteration, 'prompt': prompt, 'code': None, 'raw_llm_output': None, 'token_usage': {},
                            'success': False, 'score': 0.0, 'metrics': error_metrics, 'error': error_msg, 'feedback': feedback,
                            'self_refine_inner_steps': [],
                        })
                        break

                    if not current_code or len(current_code.strip()) < 50 or 'def build_agent' not in current_code:
                        print("⚠️  Self-Refine inner-only: initial code invalid; skipping inner loop.")
                        current_code = current_code or "(invalid)"
                    else:
                        # --- Step B: Inner self-verify loop (max 20 steps; no system verifier until exit) ---
                        inner_step = 0
                        while inner_step < MAX_SELF_VERIFY_STEPS_INNER_ONLY:
                            inner_step += 1
                            print(f"  🔄 Self-verify step {inner_step}/{MAX_SELF_VERIFY_STEPS_INNER_ONLY}...")
                            verify_prompt = format_self_feedback_prompt(current_code, self.task_prompt)
                            try:
                                _, raw_verify, verify_tokens = self.solver.generate_code(
                                    verify_prompt, use_conversation=False, reset_conversation=False,
                                    seed=self._sampling_seed(iteration, inner_step * 10 + 1)
                                )
                                self_verify_output = (raw_verify or "").strip()
                            except Exception as exc:
                                if is_cuda_oom(exc):
                                    raise
                                self_verify_output = f"(Self-verify failed: {exc})"
                                verify_tokens = {}
                            self_refine_inner_steps.append({
                                'step': inner_step,
                                'self_verify_output': self_verify_output,
                                'code_before': current_code,
                            })
                            if self_verify_says_correct(self_verify_output):
                                print(f"  ✅ Model said 'It is correct.' — exiting self-verify loop after {inner_step} step(s).")
                                break
                            # Refine
                            refine_prompt = format_revision_prompt_self_refine_inner(self.task_prompt, current_code, self_verify_output)
                            try:
                                new_code, new_raw, refine_tokens = self.solver.generate_code(
                                    refine_prompt, use_conversation=self.use_conversation, reset_conversation=False,
                                    seed=self._sampling_seed(iteration, inner_step * 10 + 2)
                                )
                            except Exception as exc:
                                if is_cuda_oom(exc):
                                    raise
                                self_refine_inner_steps[-1]['refine_error'] = str(exc)
                                self_refine_inner_steps[-1]['code_after'] = None
                                print(f"  ⚠️  Refine failed: {exc}; keeping previous code.")
                                break
                            self_refine_inner_steps[-1]['code_after'] = new_code
                            if new_code and len(new_code.strip()) >= 50 and 'def build_agent' in new_code:
                                current_code = new_code
                            else:
                                print("  ⚠️  Refined code invalid; keeping previous code.")
                                break
                        if inner_step >= MAX_SELF_VERIFY_STEPS_INNER_ONLY:
                            print(f"  ⚠️  Reached max self-verify steps ({MAX_SELF_VERIFY_STEPS_INNER_ONLY}); using final code for evaluation.")

                    # --- Step C: Run system verifier once (only evaluation) ---
                    code_to_verify = current_code if (current_code and 'def build_agent' in current_code) else (current_code or "")
                    gif_path = self._get_gif_path(iteration) if self.save_gif else None
                    if gif_path:
                        print(f"  📹 Running system verifier once (GIF: {gif_path})...")
                    success, score, metrics, error = self.verifier.verify_code(
                        code_to_verify,
                        headless=self.headless, save_gif_path=gif_path
                    )
                    if gif_path and os.path.exists(gif_path):
                        print(f"  ✅ GIF saved: {gif_path}")
                    failed = metrics.get('failed', False)
                    failure_reason = metrics.get('failure_reason', None)
                    feedback = format_feedback(
                        metrics, score, success, failed, failure_reason, iteration,
                        error=error, task_name=self.task_name, include_suggestions=False,
                    )
                    hist_entry = {
                        'iteration': iteration,
                        'prompt': prompt,
                        'code': current_code,
                        'raw_llm_output': raw_llm_output if 'raw_llm_output' in dir() else None,
                        'token_usage': token_usage if 'token_usage' in dir() else {},
                        'success': success,
                        'score': score,
                        'metrics': metrics,
                        'error': error,
                        'feedback': feedback,
                        'self_refine_inner_steps': self_refine_inner_steps,
                    }
                    self.iteration_history.append(hist_entry)
                    if score > self.best_score:
                        self.best_score = score
                        self.best_code = current_code
                        self.best_metrics = metrics
                        print(f"  🎯 New best score: {score:.1f}/100")
                    print(f"  📊 Self-Refine inner-only: Score={score:.1f}/100, Success={'✅' if success else '❌'}")
                    if success:
                        print(f"\n🎉 Task completed successfully! (inner-only, 1 round)")
                    break  # single round only; no external feedback, no iteration 2

                # Per-iteration memory state for a_mem_sys / reasoning_bank (logged in JSON)
                memory_retrieved_this_iter = ""
                
                # 1. Generate prompt
                if iteration == 1:
                    # First iteration: for context='all', use simplified prompt (task info is in system prompt)
                    if self.use_conversation:
                        # Simplified initial prompt - task info is already in system prompt
                        prompt = "# Your Task\n\nPlease provide your initial solution.\n\nBegin with your physical analysis, then provide the code."
                        print("📝 Generating initial prompt (simplified - task info in system prompt)...")
                    else:
                        # Normal initial prompt with full task info
                        prompt = format_initial_prompt(self.task_prompt)
                        print("📝 Generating initial prompt...")
                else:
                    # Subsequent iterations: revision prompt based on context strategy
                    if self.method == 'a_mem_sys':
                        # a_mem_sys: revision-style prompt (REVISION_DEMONSTRATION) but no inline solution/feedback; history from memory only
                        prompt = format_revision_prompt_memory_only(self.task_prompt)
                        print("📝 Generating revision prompt (a_mem_sys: revision demo + memory-only history)...")
                    elif self.method == 'memento_nonparametric':
                        # memento_nonparametric: same as a_mem_sys — revision from memory only (no best+previous even if context=all)
                        prompt = format_revision_prompt_memory_only(self.task_prompt)
                        print("📝 Generating revision prompt (memento_nonparametric: revision demo + memory-only history)...")
                    elif self.method == 'rememberer':
                        # Rememberer: retrieve memory first, then build prompt with memory after demonstration, before best attempt
                        last_feedback = self.iteration_history[-1].get('feedback', '') if self.iteration_history else ''
                        from methods.Memory.rememberer_method import retrieve_for_prompt as rememberer_retrieve
                        last_fb = last_feedback
                        device_str = 'cuda' if (getattr(self.solver, 'device', None) or '').startswith('cuda') else 'auto'
                        memory_retrieved_this_iter = rememberer_retrieve(
                            self.task_prompt, last_fb,
                            self._rememberer_items, self._rememberer_candidates,
                            device_str=device_str,
                        )
                        memory_block = (memory_retrieved_this_iter or "").strip()
                        prompt = self._build_revision_prompt(iteration, last_feedback, memory_block=memory_block if memory_block else None)
                        print("📝 Generating revision prompt (rememberer: demonstration → memory → best+previous)...")
                    elif self.method == 'expel':
                        last_feedback = self.iteration_history[-1].get('feedback', '') if self.iteration_history else ''
                        prompt = self._build_revision_prompt(iteration, last_feedback)
                        print("📝 Generating revision prompt (expel: best+previous + memory)...")
                    elif self.method == 'reasoning_bank':
                        last_feedback = self.iteration_history[-1].get('feedback', '') if self.iteration_history else ''
                        prompt = self._build_revision_prompt(iteration, last_feedback)
                        print("📝 Generating revision prompt (reasoning_bank: best+previous + memory)...")
                    else:
                        last_feedback = self.iteration_history[-1].get('feedback', '')
                        if not last_feedback:
                            prompt = format_initial_prompt(self.task_prompt)
                            print("📝 Generating revision prompt (without feedback - no feedback available)...")
                        else:
                            prompt = self._build_revision_prompt(iteration, last_feedback)
                
                # A-mem-sys: retrieve relevant memories and append after prompt (memory LLM = deepseek-v3.2)
                if self.method == 'a_mem_sys':
                    if self._memory_system is None:
                        from methods.Memory.a_mem_sys_method import get_memory_system
                        # Use same API key and base_url as solver when not passed via args (e.g. solver_interface)
                        api_key = self.api_key
                        base_url = None
                        if getattr(self.solver, 'model_type', None) == 'openai':
                            if api_key is None:
                                api_key = getattr(self.solver, 'API_KEY', None)
                            base_url = getattr(self.solver, 'BASE_URL', None)
                        self._memory_system = get_memory_system(
                            llm_model=self.a_mem_sys_llm_model,
                            api_key=api_key,
                            base_url=base_url,
                        )
                    from methods.Memory.a_mem_sys_method import retrieve_for_prompt
                    last_fb = self.iteration_history[-1].get('feedback', '') if self.iteration_history else ''
                    memory_retrieved_this_iter = retrieve_for_prompt(
                        self.task_prompt, last_fb, self._memory_system, k=5
                    )
                    # Append memory after task + revision context (so model sees task and previous solution+feedback first)
                    suffix = "\n\n---\n\n## Relevant experience from memory\n"
                    if memory_retrieved_this_iter:
                        suffix += memory_retrieved_this_iter + "\n\n"
                    else:
                        suffix += "(No relevant memories yet.)\n\n"
                    prompt = prompt + suffix
                elif self.method == 'memento_nonparametric':
                    from methods.Memory.memento_nonparametric_method import retrieve_for_prompt as memento_retrieve
                    last_fb = self.iteration_history[-1].get('feedback', '') if self.iteration_history else ''
                    device_str = 'cuda' if (getattr(self.solver, 'device', None) or '').startswith('cuda') else 'auto'
                    memory_retrieved_this_iter = memento_retrieve(
                        self.task_prompt, last_fb,
                        self._memento_np_items, self._memento_np_pairs,
                        device_str=device_str,
                    )
                    suffix = "\n\n---\n\n## Relevant experience from memory\n"
                    if memory_retrieved_this_iter and memory_retrieved_this_iter.strip() != "(No relevant memories yet.)":
                        suffix += memory_retrieved_this_iter + "\n\n"
                    else:
                        suffix += "(No relevant memories yet.)\n\n"
                    prompt = prompt + suffix
                elif self.method == 'rememberer':
                    # Memory already inserted in prompt (after demonstration, before best attempt); nothing to append
                    pass
                elif self.method == 'expel':
                    from methods.Memory.expel_method import retrieve_for_prompt as expel_retrieve
                    last_fb = self.iteration_history[-1].get('feedback', '') if self.iteration_history else ''
                    memory_retrieved_this_iter = expel_retrieve(
                        self.task_prompt, last_fb,
                        getattr(self, '_expel_items', []),
                        getattr(self, '_expel_rules', []),
                        getattr(self, '_expel_embedder', None),
                        top_k_rules=5,
                        top_k_trajectories=3,
                    )
                    suffix = "\n\n---\n\n## Relevant insights and experience from same-category tasks\n\n"
                    suffix += (memory_retrieved_this_iter or "(No relevant insights yet.)") + "\n\n"
                    prompt = prompt + suffix
                # ACE: append full playbook as experience each round
                if self.method == 'ace':
                    playbook_str = (self._playbook or '').strip() or '(empty playbook)'
                    prompt = prompt + "\n\n---\n\n## Playbook (Experience)\n\n" + playbook_str
                # ReasoningBank: retrieve strategies and append
                if self.method == 'reasoning_bank':
                    from methods.Memory.reasoning_bank_method import retrieve_for_prompt as rb_retrieve
                    last_fb = self.iteration_history[-1].get('feedback', '') if self.iteration_history else ''
                    device_str = 'cuda' if (getattr(self.solver, 'device', None) or '').startswith('cuda') else 'auto'
                    memory_retrieved_this_iter = rb_retrieve(
                        self.task_prompt, last_fb,
                        self._reasoning_bank_items,
                        device_str=device_str,
                    )
                    suffix = "\n\n---\n\n## Relevant experience from memory\n\n" + (memory_retrieved_this_iter or "(No relevant memories yet.)") + "\n\n"
                    prompt = prompt + suffix
                
                # 2. Parallel K branch (ReasoningBank with k > 1): generate K solutions, verify K, contrast, pick best
                if self.method == 'reasoning_bank' and getattr(self, 'reasoning_bank_k', 1) > 1:
                    from methods.Memory.reasoning_bank_method import (
                        contrast_and_distill, store_after_iteration,
                    )
                    api_key = self.api_key
                    base_url = None
                    if getattr(self.solver, 'model_type', None) == 'openai':
                        if api_key is None:
                            api_key = getattr(self.solver, 'API_KEY', None)
                        base_url = getattr(self.solver, 'BASE_URL', None)
                    task_desc = (self.task_prompt.get('task_description') or '').strip() or '(task)'
                    parallel_trajectories = []
                    # API mode: parallel K LLM calls; local: sequential
                    use_parallel_llm = getattr(self.solver, 'model_type', None) == 'openai'
                    if use_parallel_llm:
                        # Build one messages list and call API K times in parallel (no conversation mutation)
                        system_prompt = self.solver.get_system_prompt()
                        conv = getattr(self.solver, '_conversation_messages', None) or []
                        if self.use_conversation and not hasattr(self.solver, '_conversation_messages'):
                            conv = []
                        messages = (
                            [{"role": "system", "content": system_prompt}]
                            + (conv if self.use_conversation else [])
                            + [{"role": "user", "content": prompt}]
                        )

                        def _gen_one(_ki: int):
                            try:
                                return self.solver.generate_code_from_messages(messages), None
                            except Exception as e:
                                return (None, None, {}), e

                        with ThreadPoolExecutor(max_workers=self.reasoning_bank_k) as ex:
                            futures = [ex.submit(_gen_one, ki) for ki in range(self.reasoning_bank_k)]
                            gen_results = [f.result() for f in futures]

                        # Append best turn to conversation after we pick best (done below)
                        best_raw_for_conv = None
                        for ki, ((code_i, raw_i, tok_i), exc_i) in enumerate(gen_results):
                            if not code_i or len(code_i.strip()) < 50:
                                parallel_trajectories.append({
                                    'code': code_i, 'feedback': 'Generated code too short or empty', 'score': 0.0, 'success': False,
                                    'metrics': {}, 'error': str(exc_i) if exc_i else None,
                                })
                                continue
                            gif_path_i = self._get_gif_path(iteration) if (self.save_gif and ki == 0) else None
                            succ_i, sc_i, met_i, err_i = self.verifier.verify_code(code_i, headless=self.headless, save_gif_path=gif_path_i)
                            fb_i = format_feedback(met_i, sc_i, succ_i, met_i.get('failed', False), met_i.get('failure_reason'), iteration, error=err_i, task_name=self.task_name, include_suggestions=self.enable_feedback)
                            parallel_trajectories.append({
                                'code': code_i, 'feedback': fb_i, 'score': sc_i, 'success': succ_i,
                                'metrics': met_i, 'error': err_i, 'raw_llm_output': raw_i, 'token_usage': tok_i or {},
                            })
                    else:
                        # Sequential: original loop (local model or fallback)
                        for ki in range(self.reasoning_bank_k):
                            exc_i = None
                            try:
                                code_i, raw_i, tok_i = self.solver.generate_code(
                                    prompt, use_conversation=self.use_conversation, reset_conversation=False,
                                    seed=self._sampling_seed(iteration, ki)
                                )
                            except Exception as exc_i:
                                code_i, raw_i, tok_i = None, None, {}
                            if not code_i or len(code_i.strip()) < 50:
                                parallel_trajectories.append({
                                    'code': code_i, 'feedback': 'Generated code too short or empty', 'score': 0.0, 'success': False,
                                    'metrics': {}, 'error': str(exc_i) if exc_i else None,
                                })
                                continue
                            gif_path_i = self._get_gif_path(iteration) if (self.save_gif and ki == 0) else None
                            succ_i, sc_i, met_i, err_i = self.verifier.verify_code(code_i, headless=self.headless, save_gif_path=gif_path_i)
                            fb_i = format_feedback(met_i, sc_i, succ_i, met_i.get('failed', False), met_i.get('failure_reason'), iteration, error=err_i, task_name=self.task_name, include_suggestions=self.enable_feedback)
                            parallel_trajectories.append({
                                'code': code_i, 'feedback': fb_i, 'score': sc_i, 'success': succ_i,
                                'metrics': met_i, 'error': err_i, 'raw_llm_output': raw_i, 'token_usage': tok_i or {},
                            })
                    new_items = contrast_and_distill(
                        parallel_trajectories, task_desc,
                        api_key=api_key, base_url=base_url,
                    )
                    self._reasoning_bank_items = store_after_iteration(
                        self._reasoning_bank_path, self._reasoning_bank_items, new_items
                    )
                    best_idx = 0
                    for i in range(1, len(parallel_trajectories)):
                        t = parallel_trajectories[i]
                        b = parallel_trajectories[best_idx]
                        if (t.get('success'), t.get('score', 0)) > (b.get('success'), b.get('score', 0)):
                            best_idx = i
                    best = parallel_trajectories[best_idx]
                    # So next iteration has correct history: append best turn when we used parallel API
                    if use_parallel_llm and parallel_trajectories:
                        self.solver._append_conversation_turn(prompt, clean_special_tags(best.get('raw_llm_output') or ''))
                    current_code = best.get('code')
                    success = best.get('success', False)
                    score = best.get('score', 0.0)
                    metrics = best.get('metrics', {})
                    error = best.get('error')
                    feedback = best.get('feedback', '')
                    raw_llm_output = best.get('raw_llm_output')
                    token_usage = best.get('token_usage', {})
                    # Save all K candidates so JSON has full picture (best is first by convention)
                    parallel_candidates = [
                        {
                            'code': t.get('code'),
                            'score': t.get('score', 0.0),
                            'success': t.get('success', False),
                            'feedback': t.get('feedback', ''),
                            'raw_llm_output': t.get('raw_llm_output'),
                            'token_usage': t.get('token_usage', {}),
                            'metrics': t.get('metrics', {}),
                            'error': t.get('error'),
                        }
                        for t in parallel_trajectories
                    ]
                    iteration_result = {
                        'iteration': iteration, 'prompt': prompt, 'code': current_code,
                        'raw_llm_output': raw_llm_output, 'token_usage': token_usage,
                        'success': success, 'score': score, 'metrics': metrics, 'error': error, 'feedback': feedback,
                        'memory_retrieved': memory_retrieved_this_iter,
                        'reasoning_bank_stored_items': new_items,
                        'reasoning_bank_parallel_k': self.reasoning_bank_k,
                        'reasoning_bank_parallel_candidates': parallel_candidates,
                    }
                    self.iteration_history.append(iteration_result)
                    if score > self.best_score:
                        self.best_score = score
                        self.best_code = current_code
                        self.best_metrics = metrics
                        print(f"🎯 New best score: {score:.1f}/100 (from {self.reasoning_bank_k} parallel)")
                    print(f"\n📊 ReasoningBank parallel: {self.reasoning_bank_k} attempts, best score={score:.1f}, success={success}")
                    if success:
                        print(f"\n🎉 Task completed successfully! Iterations: {iteration}")
                        break
                    previous_code = current_code
                    continue
                
                # 2. Call solver agent to generate code (single or reasoning_bank k=1)
                print("🤖 Calling solver agent to generate code...")
                try:
                    current_code, raw_llm_output, token_usage = self.solver.generate_code(
                        prompt,
                        use_conversation=self.use_conversation,
                        reset_conversation=False,
                        seed=self._sampling_seed(iteration, 0)
                    )
                except Exception as exc:
                    if is_cuda_oom(exc):
                        print(f"❌ CUDA out of memory - stopping immediately: {exc}")
                        raise
                    print(f"❌ Code generation failed: {exc}")
                    # Get current prompt (if generated)
                    current_prompt = prompt if 'prompt' in locals() else None
                    error_msg = f'Code generation failed: {str(exc)}'
                    error_metrics = {
                        'error_type': 'code_generation_error',
                        'error_stage': 'llm_generation',
                        'error_message': str(exc)
                    }
                    # Always generate feedback with execution results, but only include suggestions in sys_feedback mode
                    feedback = format_feedback(
                        error_metrics, 0.0, False, False, None, iteration, 
                        error=error_msg, task_name=self.task_name, 
                        include_suggestions=self.enable_feedback
                    )
                    hist_entry = {
                        'iteration': iteration,
                        'prompt': current_prompt,
                        'code': None,
                        'raw_llm_output': None,
                        'token_usage': {},
                        'success': False,
                        'score': 0.0,
                        'metrics': error_metrics,
                        'error': error_msg,
                        'feedback': feedback
                    }
                    if self.method == 'a_mem_sys':
                        hist_entry['memory_retrieved'] = memory_retrieved_this_iter
                    if self.method == 'memento_nonparametric':
                        hist_entry['memory_retrieved'] = memory_retrieved_this_iter
                    if self.method == 'reasoning_bank':
                        hist_entry['memory_retrieved'] = memory_retrieved_this_iter
                    self.iteration_history.append(hist_entry)
                    # Reflexion: generate reflection after failed iteration
                    if self.method == 'reflexion':
                        reflection = self._generate_reflection(None, feedback, iteration)
                        self.reflections.append(reflection)
                        self.reflections_str = format_reflections_str(self.reflections)
                        self.iteration_history[-1]['reflection'] = reflection
                    # A-mem-sys: store this iteration for future retrieval
                    if self.method == 'a_mem_sys' and self._memory_system is not None:
                        from methods.Memory.a_mem_sys_method import store_after_iteration
                        stored = store_after_iteration(
                            self.task_name, iteration, 0.0, feedback or '',
                            None, self._memory_system
                        )
                        self.iteration_history[-1]['memory_stored'] = stored
                    # ReasoningBank: store failure for future retrieval (single path only; parallel path handles its own)
                    if self.method == 'reasoning_bank' and getattr(self, '_reasoning_bank_path', None) and getattr(self, 'reasoning_bank_k', 1) == 1:
                        from methods.Memory.reasoning_bank_method import extract_memory_items_llm, store_after_iteration as rb_store
                        task_desc = (self.task_prompt.get('task_description') or '').strip() or '(task)'
                        api_key = self.api_key or (getattr(self.solver, 'API_KEY', None) if getattr(self.solver, 'model_type', None) == 'openai' else None)
                        base_url = getattr(self.solver, 'BASE_URL', None) if getattr(self.solver, 'model_type', None) == 'openai' else None
                        new_items = extract_memory_items_llm(task_desc, None, feedback or '', 0.0, False, api_key=api_key, base_url=base_url)
                        self._reasoning_bank_items = rb_store(self._reasoning_bank_path, self._reasoning_bank_items, new_items)
                        self.iteration_history[-1]['reasoning_bank_stored_items'] = new_items
                    # Memento non-parametric: store entry and reload items/pairs
                    if self.method == 'memento_nonparametric' and getattr(self, '_memento_np_memory_path', None):
                        from methods.Memory.memento_nonparametric_method import store_after_iteration as memento_store, load_memory
                        task_desc = self.task_prompt.get('task_description', '')
                        entry = memento_store(
                            self.task_name, iteration, 0.0, feedback or '', None,
                            self._memento_np_memory_path, task_desc, success=False,
                            base_task_name=getattr(self, 'base_task_name_for_memory', None),
                        )
                        self.iteration_history[-1]['memory_stored_entry'] = entry
                        self._memento_np_items, self._memento_np_pairs = load_memory(self._memento_np_memory_path)
                    previous_code = current_code if 'current_code' in locals() else None
                    continue
                
                if not current_code or len(current_code.strip()) < 50:
                    print("⚠️  Warning: Generated code is too short, may have issues")
                    print(f"Generated code:\n{current_code[:200] if current_code else 'None'}...")
                    current_prompt = prompt if 'prompt' in locals() else None
                    error_msg = 'Generated code is too short or empty'
                    error_metrics = {
                        'error_type': 'code_too_short',
                        'error_stage': 'code_extraction',
                        'error_message': error_msg,
                        'code_length': len(current_code) if current_code else 0
                    }
                    # Always generate feedback with execution results, but only include suggestions in sys_feedback mode
                    feedback = format_feedback(
                        error_metrics, 0.0, False, False, None, iteration, 
                        error=error_msg, task_name=self.task_name, 
                        include_suggestions=self.enable_feedback
                    )
                    hist_entry = {
                        'iteration': iteration,
                        'prompt': current_prompt,
                        'code': current_code,
                        'raw_llm_output': raw_llm_output if 'raw_llm_output' in locals() else None,
                        'token_usage': token_usage if 'token_usage' in locals() else {},
                        'success': False,
                        'score': 0.0,
                        'metrics': error_metrics,
                        'error': error_msg,
                        'feedback': feedback
                    }
                    if self.method == 'a_mem_sys':
                        hist_entry['memory_retrieved'] = memory_retrieved_this_iter
                    if self.method == 'memento_nonparametric':
                        hist_entry['memory_retrieved'] = memory_retrieved_this_iter
                    if self.method == 'reasoning_bank':
                        hist_entry['memory_retrieved'] = memory_retrieved_this_iter
                    self.iteration_history.append(hist_entry)
                    # Reflexion: generate reflection after failed iteration
                    if self.method == 'reflexion':
                        reflection = self._generate_reflection(current_code, feedback, iteration)
                        self.reflections.append(reflection)
                        self.reflections_str = format_reflections_str(self.reflections)
                        self.iteration_history[-1]['reflection'] = reflection
                    # A-mem-sys: store this iteration
                    if self.method == 'a_mem_sys' and self._memory_system is not None:
                        from methods.Memory.a_mem_sys_method import store_after_iteration
                        stored = store_after_iteration(
                            self.task_name, iteration, 0.0, feedback or '',
                            current_code, self._memory_system
                        )
                        self.iteration_history[-1]['memory_stored'] = stored
                    # ReasoningBank: store failure (short code)
                    if self.method == 'reasoning_bank' and getattr(self, '_reasoning_bank_path', None) and getattr(self, 'reasoning_bank_k', 1) == 1:
                        from methods.Memory.reasoning_bank_method import extract_memory_items_llm, store_after_iteration as rb_store
                        task_desc = (self.task_prompt.get('task_description') or '').strip() or '(task)'
                        api_key = self.api_key or (getattr(self.solver, 'API_KEY', None) if getattr(self.solver, 'model_type', None) == 'openai' else None)
                        base_url = getattr(self.solver, 'BASE_URL', None) if getattr(self.solver, 'model_type', None) == 'openai' else None
                        new_items = extract_memory_items_llm(task_desc, current_code, feedback or '', 0.0, False, api_key=api_key, base_url=base_url)
                        self._reasoning_bank_items = rb_store(self._reasoning_bank_path, self._reasoning_bank_items, new_items)
                        self.iteration_history[-1]['reasoning_bank_stored_items'] = new_items
                    # Memento non-parametric: store entry and reload
                    if self.method == 'memento_nonparametric' and getattr(self, '_memento_np_memory_path', None):
                        from methods.Memory.memento_nonparametric_method import store_after_iteration as memento_store, load_memory
                        task_desc = self.task_prompt.get('task_description', '')
                        entry = memento_store(
                            self.task_name, iteration, 0.0, feedback or '', current_code,
                            self._memento_np_memory_path, task_desc, success=False,
                            base_task_name=getattr(self, 'base_task_name_for_memory', None),
                        )
                        self.iteration_history[-1]['memory_stored_entry'] = entry
                        self._memento_np_items, self._memento_np_pairs = load_memory(self._memento_np_memory_path)
                    previous_code = current_code
                    continue
                
                # Check if code contains necessary functions
                if 'def build_agent' not in current_code:
                    print("⚠️  Warning: No 'def build_agent' function found in generated code")
                    print(f"Generated code first 500 chars:\n{current_code[:500]}")
                    current_prompt = prompt if 'prompt' in locals() else None
                    error_msg = "Code missing 'def build_agent' function definition"
                    error_metrics = {
                        'error_type': 'missing_function',
                        'error_stage': 'code_validation',
                        'error_message': error_msg,
                        'code_preview': current_code[:500] if current_code else ''
                    }
                    # Always generate feedback with execution results, but only include suggestions in sys_feedback mode
                    feedback = format_feedback(
                        error_metrics, 0.0, False, False, None, iteration, 
                        error=error_msg, task_name=self.task_name, 
                        include_suggestions=self.enable_feedback
                    )
                    hist_entry = {
                        'iteration': iteration,
                        'prompt': current_prompt,
                        'code': current_code,
                        'raw_llm_output': raw_llm_output if 'raw_llm_output' in locals() else None,
                        'token_usage': token_usage if 'token_usage' in locals() else {},
                        'success': False,
                        'score': 0.0,
                        'metrics': error_metrics,
                        'error': error_msg,
                        'feedback': feedback
                    }
                    if self.method == 'a_mem_sys':
                        hist_entry['memory_retrieved'] = memory_retrieved_this_iter
                    if self.method == 'memento_nonparametric':
                        hist_entry['memory_retrieved'] = memory_retrieved_this_iter
                    if self.method == 'reasoning_bank':
                        hist_entry['memory_retrieved'] = memory_retrieved_this_iter
                    self.iteration_history.append(hist_entry)
                    # Reflexion: generate reflection after failed iteration
                    if self.method == 'reflexion':
                        reflection = self._generate_reflection(current_code, feedback, iteration)
                        self.reflections.append(reflection)
                        self.reflections_str = format_reflections_str(self.reflections)
                        self.iteration_history[-1]['reflection'] = reflection
                    # A-mem-sys: store this iteration
                    if self.method == 'a_mem_sys' and self._memory_system is not None:
                        from methods.Memory.a_mem_sys_method import store_after_iteration
                        stored = store_after_iteration(
                            self.task_name, iteration, 0.0, feedback or '',
                            current_code, self._memory_system
                        )
                        self.iteration_history[-1]['memory_stored'] = stored
                    # ReasoningBank: store failure (missing build_agent)
                    if self.method == 'reasoning_bank' and getattr(self, '_reasoning_bank_path', None) and getattr(self, 'reasoning_bank_k', 1) == 1:
                        from methods.Memory.reasoning_bank_method import extract_memory_items_llm, store_after_iteration as rb_store
                        task_desc = (self.task_prompt.get('task_description') or '').strip() or '(task)'
                        api_key = self.api_key or (getattr(self.solver, 'API_KEY', None) if getattr(self.solver, 'model_type', None) == 'openai' else None)
                        base_url = getattr(self.solver, 'BASE_URL', None) if getattr(self.solver, 'model_type', None) == 'openai' else None
                        new_items = extract_memory_items_llm(task_desc, current_code, feedback or '', 0.0, False, api_key=api_key, base_url=base_url)
                        self._reasoning_bank_items = rb_store(self._reasoning_bank_path, self._reasoning_bank_items, new_items)
                        self.iteration_history[-1]['reasoning_bank_stored_items'] = new_items
                    # Memento non-parametric: store entry and reload
                    if self.method == 'memento_nonparametric' and getattr(self, '_memento_np_memory_path', None):
                        from methods.Memory.memento_nonparametric_method import store_after_iteration as memento_store, load_memory
                        task_desc = self.task_prompt.get('task_description', '')
                        entry = memento_store(
                            self.task_name, iteration, 0.0, feedback or '', current_code,
                            self._memento_np_memory_path, task_desc, success=False,
                            base_task_name=getattr(self, 'base_task_name_for_memory', None),
                        )
                        self.iteration_history[-1]['memory_stored_entry'] = entry
                        self._memento_np_items, self._memento_np_pairs = load_memory(self._memento_np_memory_path)
                    previous_code = current_code
                    continue
                
                print(f"✅ Code generation completed (length: {len(current_code)} characters)")
                print(f"Code preview (first 200 chars):\n{current_code[:200]}...")
                
                # 3. Verify code
                print("🔍 Verifying code and running simulation...")
                # Generate GIF path (skip when save_gif=False, e.g. during rollout)
                gif_path = self._get_gif_path(iteration) if self.save_gif else None
                if gif_path:
                    print(f"📹 Will save GIF to: {gif_path}")
                success, score, metrics, error = self.verifier.verify_code(
                    current_code, headless=self.headless, save_gif_path=gif_path
                )
                
                # Check if GIF was saved successfully
                if gif_path and os.path.exists(gif_path):
                    print(f"✅ GIF saved: {gif_path}")
                elif gif_path:
                    print(f"⚠️  Warning: GIF not saved to {gif_path}")
                
                # 4. Generate feedback
                # Always generate feedback with execution results and metrics
                # But only include improvement suggestions in sys_feedback mode
                failed = metrics.get('failed', False)
                failure_reason = metrics.get('failure_reason', None)
                feedback = format_feedback(
                    metrics, score, success, failed, failure_reason, iteration, 
                    error=error, task_name=self.task_name, 
                    include_suggestions=self.enable_feedback  # Only include suggestions in sys_feedback mode
                )
                
                # 5. Record results
                iteration_result = {
                    'iteration': iteration,
                    'prompt': prompt,  # Save prompt used in this iteration
                    'code': current_code,  # Save complete generated code
                    'raw_llm_output': raw_llm_output if 'raw_llm_output' in locals() else None,  # Save raw LLM output
                    'token_usage': token_usage if 'token_usage' in locals() else {},  # Save token usage
                    'success': success,
                    'score': score,
                    'metrics': metrics,
                    'error': error,
                    'feedback': feedback  # Save verifier feedback
                }
                if self.method == 'a_mem_sys':
                    iteration_result['memory_retrieved'] = memory_retrieved_this_iter
                if self.method == 'memento_nonparametric':
                    iteration_result['memory_retrieved'] = memory_retrieved_this_iter
                if self.method == 'reasoning_bank':
                    iteration_result['memory_retrieved'] = memory_retrieved_this_iter
                self.iteration_history.append(iteration_result)
                
                # ReasoningBank (single path k=1): extract and store memory items
                if self.method == 'reasoning_bank' and getattr(self, '_reasoning_bank_path', None) and getattr(self, 'reasoning_bank_k', 1) == 1:
                    from methods.Memory.reasoning_bank_method import (
                        extract_memory_items_llm, judge_success, store_after_iteration,
                    )
                    task_desc = (self.task_prompt.get('task_description') or '').strip() or '(task)'
                    api_key = self.api_key
                    base_url = getattr(self.solver, 'BASE_URL', None) if getattr(self.solver, 'model_type', None) == 'openai' else None
                    if api_key is None and getattr(self.solver, 'model_type', None) == 'openai':
                        api_key = getattr(self.solver, 'API_KEY', None)
                    new_items = extract_memory_items_llm(
                        task_desc, current_code, feedback, score, success,
                        api_key=api_key, base_url=base_url,
                    )
                    self._reasoning_bank_items = store_after_iteration(
                        self._reasoning_bank_path, self._reasoning_bank_items, new_items
                    )
                    self.iteration_history[-1]['reasoning_bank_stored_items'] = new_items
                
                # A-mem-sys: store this iteration for future retrieval (JSON: memory_stored)
                if self.method == 'a_mem_sys' and self._memory_system is not None:
                    from methods.Memory.a_mem_sys_method import store_after_iteration
                    stored = store_after_iteration(
                        self.task_name, iteration, score,
                        feedback or '',
                        current_code,
                        self._memory_system
                    )
                    self.iteration_history[-1]['memory_stored'] = stored
                # Memento non-parametric: store entry and reload
                if self.method == 'memento_nonparametric' and getattr(self, '_memento_np_memory_path', None):
                    from methods.Memory.memento_nonparametric_method import store_after_iteration as memento_store, load_memory
                    task_desc = self.task_prompt.get('task_description', '')
                    entry = memento_store(
                        self.task_name, iteration, score, feedback or '', current_code,
                        self._memento_np_memory_path, task_desc, success=success,
                        base_task_name=getattr(self, 'base_task_name_for_memory', None),
                    )
                    self.iteration_history[-1]['memory_stored_entry'] = entry
                    self._memento_np_items, self._memento_np_pairs = load_memory(self._memento_np_memory_path)
                
                # ACE: Reflector + Curator update playbook after each iteration
                if self.method == 'ace':
                    if self._ace_reflector is None:
                        from methods.Memory.ace_method import build_ace_reflector_curator
                        api_key_ace = self.api_key
                        base_url_ace = None
                        if getattr(self.solver, 'model_type', None) == 'openai':
                            if api_key_ace is None:
                                api_key_ace = getattr(self.solver, 'API_KEY', None)
                            base_url_ace = getattr(self.solver, 'BASE_URL', None)
                        # Fallback: env vars, then SolverInterface defaults (same API/URL as solver_interface.py)
                        if api_key_ace is None:
                            api_key_ace = os.environ.get('OPENAI_API_KEY') or os.environ.get('API_KEY') or getattr(SolverInterface, 'API_KEY', None)
                        if base_url_ace is None:
                            base_url_ace = os.environ.get('OPENAI_BASE_URL') or getattr(SolverInterface, 'BASE_URL', None)
                        self._ace_reflector, self._ace_curator, self._ace_next_global_id = build_ace_reflector_curator(
                            reflector_model=self.ace_reflector_model,
                            curator_model=self.ace_curator_model,
                            api_key=api_key_ace,
                            base_url=base_url_ace,
                        )
                    from methods.Memory.ace_method import reflect_on_iteration, update_playbook_after_iteration
                    task_desc = (self.task_prompt.get('task_description') or '').strip() or '(task)'
                    bullets_used = ((self._playbook or '').strip() or '(none)')[:4000]
                    ace_log_dir = os.path.join(
                        get_evaluation_results_dir(),
                        self.task_name,
                        get_model_identifier(self.model_type, self.model_name),
                        "ace",
                        "ace_logs",
                    )
                    os.makedirs(ace_log_dir, exist_ok=True)
                    reflection_content, bullet_tags, _ = reflect_on_iteration(
                        self._ace_reflector,
                        question=task_desc,
                        reasoning_trace=current_code or '',
                        predicted_answer=current_code or '(no code)',
                        environment_feedback=feedback,
                        bullets_used=bullets_used,
                        use_ground_truth=False,
                        call_id=f"iter_{iteration}",
                        log_dir=ace_log_dir,
                    )
                    self._playbook, self._ace_next_global_id = update_playbook_after_iteration(
                        self._playbook,
                        reflection_content,
                        question_context=task_desc,
                        iteration=iteration,
                        max_iterations=self.max_iterations,
                        token_budget=80000,
                        curator=self._ace_curator,
                        bullet_tags=bullet_tags,
                        next_global_id=self._ace_next_global_id,
                        log_dir=ace_log_dir,
                    )
                
                # 6. Update best results
                if score > self.best_score:
                    self.best_score = score
                    self.best_code = current_code
                    self.best_metrics = metrics
                    print(f"🎯 New best score: {score:.1f}/100")
                
                # 7. Print results
                print(f"\n📊 Evaluation results:")
                print(f"  Success: {'✅' if success else '❌'}")
                print(f"  Score: {score:.1f}/100")
                if error:
                    print(f"  Error: {error}")
                if self.enable_feedback:
                    print(f"\n💬 Feedback:")
                    print(feedback)
                
                # 8. Check if successful
                if success:
                    print(f"\n🎉 Task completed successfully! Iterations: {iteration}")
                    break
                
                # 8.5. Reflexion: generate reflection after failed iteration
                if self.method == 'reflexion':
                    reflection = self._generate_reflection(current_code, feedback, iteration)
                    self.reflections.append(reflection)
                    self.reflections_str = format_reflections_str(self.reflections)
                    # Store reflection in the iteration history entry we just appended
                    self.iteration_history[-1]['reflection'] = reflection
                
                # 8.6. TextGrad: initialise Variable + Optimizer after iteration 1
                if self.method == 'textgrad' and iteration == 1 and current_code:
                    from methods.Context.textgrad_method import init_textgrad_components
                    self.tg_code_var, self.tg_optimizer = init_textgrad_components(
                        current_code, self.tg_engine
                    )
                    print(f"🧮 TextGrad: Variable + Optimizer initialised for iterations 2-{self.max_iterations}")
                
                # 8.7. SEAL TTT: train LoRA on accumulated good solutions after each iteration
                if self.method == 'seal':
                    self._seal_ttt_step()
                
                # 9. Prepare for next iteration
                previous_code = current_code
                
            except Exception as exc:
                if is_cuda_oom(exc):
                    print(f"❌ CUDA out of memory - stopping immediately: {exc}")
                    raise
                print(f"❌ Iteration {iteration} error: {exc}")
                import traceback
                error_traceback = traceback.format_exc()
                print(error_traceback)
                # Safely get local variables (avoid Python 3.13 variable scope issues)
                current_prompt_val = locals().get('prompt', None)
                current_code_val = locals().get('current_code', None)
                error_msg = f"{str(exc)}\n{error_traceback}"
                error_metrics = {
                    'error_type': 'iteration_process_error',
                    'error_stage': 'iteration_execution',
                    'error_message': str(exc)
                }
                # Always generate feedback with execution results, but only include suggestions in sys_feedback mode
                feedback = format_feedback(
                    error_metrics, 0.0, False, False, None, iteration, 
                    error=error_msg, task_name=self.task_name, 
                    include_suggestions=self.enable_feedback
                )
                exc_entry = {
                    'iteration': iteration,
                    'prompt': current_prompt_val,
                    'code': current_code_val,
                    'token_usage': {},
                    'success': False,
                    'score': 0.0,
                    'metrics': error_metrics,
                    'error': error_msg,
                    'feedback': feedback
                }
                if self.method == 'a_mem_sys':
                    exc_entry['memory_retrieved'] = locals().get('memory_retrieved_this_iter', '')
                if self.method == 'memento_nonparametric':
                    exc_entry['memory_retrieved'] = locals().get('memory_retrieved_this_iter', '')
                if self.method == 'reasoning_bank':
                    exc_entry['memory_retrieved'] = locals().get('memory_retrieved_this_iter', '')
                self.iteration_history.append(exc_entry)
                # Reflexion: generate reflection after failed iteration
                if self.method == 'reflexion':
                    try:
                        reflection = self._generate_reflection(current_code_val, feedback, iteration)
                        self.reflections.append(reflection)
                        self.reflections_str = format_reflections_str(self.reflections)
                        self.iteration_history[-1]['reflection'] = reflection
                    except Exception:
                        pass  # Don't let reflection failure prevent continued evaluation
                # A-mem-sys: store this iteration
                if self.method == 'a_mem_sys' and getattr(self, '_memory_system', None) is not None:
                    try:
                        from methods.Memory.a_mem_sys_method import store_after_iteration
                        stored = store_after_iteration(
                            self.task_name, iteration, 0.0, feedback or '',
                            current_code_val, self._memory_system
                        )
                        self.iteration_history[-1]['memory_stored'] = stored
                    except Exception:
                        self.iteration_history[-1]['memory_stored'] = None
                # Memento non-parametric: store entry and reload
                if self.method == 'memento_nonparametric' and getattr(self, '_memento_np_memory_path', None):
                    try:
                        from methods.Memory.memento_nonparametric_method import store_after_iteration as memento_store, load_memory
                        task_desc = self.task_prompt.get('task_description', '')
                        entry = memento_store(
                            self.task_name, iteration, 0.0, feedback or '', current_code_val,
                            self._memento_np_memory_path, task_desc, success=False,
                            base_task_name=getattr(self, 'base_task_name_for_memory', None),
                        )
                        self.iteration_history[-1]['memory_stored_entry'] = entry
                        self._memento_np_items, self._memento_np_pairs = load_memory(self._memento_np_memory_path)
                    except Exception:
                        self.iteration_history[-1]['memory_stored_entry'] = None
                previous_code = current_code_val
                continue
        
        # Cleanup resources
        self.verifier.cleanup()
        
        # Generate final report
        return self._generate_report()
    
    def _setup_gif_directory(self):
        """Setup GIF save directory structure"""
        model_identifier = get_model_identifier(self.model_type, self.model_name)
        mutated_name = self.mutated_task_name if self.mutated_task_name else 'raw'
        base_dir = os.path.join(self.gif_base_dir, self.task_name, model_identifier, self.method, mutated_name)
        
        if self.run_number is not None:
            run_suffix = get_run_suffix(self.run_number)
            self.gif_dir = os.path.join(base_dir, f"{run_suffix}_pass")
        else:
            self.gif_dir = base_dir
        
        os.makedirs(self.gif_dir, exist_ok=True)
        print(f"📁 GIF save directory: {self.gif_dir}")
    
    def _get_gif_path(self, iteration: int) -> str:
        """Generate GIF file path"""
        return get_gif_path(self.gif_dir, self.context, iteration)
    
    def _run_tree_of_thought(self) -> None:
        """Tree-of-Thought: b beams, n samples per beam per round; verifier scores, keep top b. Success = any of final b has success; best = global best across all rounds."""
        b = self.n_select_sample
        n = self.n_generate_sample
        # states: list of dict with keys code, feedback, score, success, metrics, error, ...
        states: List[Dict[str, Any]] = []
        global_best_score = 0.0
        global_best_code = None
        global_best_metrics = None
        global_best_feedback = ''
        global_best_iteration: Optional[int] = None
        initial_prompt = format_initial_prompt(self.task_prompt)
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'='*60}")
            print(f"ToT round {iteration}/{self.max_iterations}")
            print(f"{'='*60}\n")
            
            if iteration == 1:
                # No beams yet: generate b*n initial codes (same prompt). API: parallel; local: sequential.
                candidates = []
                num_gen = b * n
                use_parallel = getattr(self.solver, 'model_type', self.model_type) == 'openai'
                if use_parallel:
                    def _gen_one(prompt: str, seed: int):
                        try:
                            return self.solver.generate_code(prompt, use_conversation=False, reset_conversation=False, seed=seed)
                        except Exception as exc:
                            if is_cuda_oom(exc):
                                raise
                            return (None, None, {})
                    max_workers = min(num_gen, 16)
                    print(f"🔄 ToT round {iteration}: generating {num_gen} samples in parallel (max_workers={max_workers})...")
                    with ThreadPoolExecutor(max_workers=max_workers) as ex:
                        futures = [ex.submit(_gen_one, initial_prompt, self._sampling_seed(iteration, idx)) for idx in range(num_gen)]
                        for fut in as_completed(futures):
                            code, raw_llm, token_usage = fut.result()
                            if code and len(code.strip()) >= 50 and 'def build_agent' in code:
                                candidates.append({'code': code, 'raw_llm_output': raw_llm, 'token_usage': token_usage or {}})
                else:
                    for idx in range(num_gen):
                        try:
                            code, raw_llm, token_usage = self.solver.generate_code(
                                initial_prompt, use_conversation=False, reset_conversation=False,
                                seed=self._sampling_seed(iteration, idx)
                            )
                            if code and len(code.strip()) >= 50 and 'def build_agent' in code:
                                candidates.append({'code': code, 'raw_llm_output': raw_llm, 'token_usage': token_usage or {}})
                        except Exception as exc:
                            if is_cuda_oom(exc):
                                raise
                            print(f"⚠️  ToT initial sample failed: {exc}")
                if not candidates:
                    # No valid code: record failure and break
                    self.iteration_history.append({
                        'iteration': iteration, 'prompt': initial_prompt, 'code': None, 'raw_llm_output': None,
                        'token_usage': {}, 'success': False, 'score': 0.0, 'metrics': {}, 'error': 'No valid code generated',
                        'feedback': 'ToT round 1: no valid code from b*n samples', 'tot_candidates': 0, 'tot_top_b': [], 'tot_retained_beams': []
                    })
                    break
                # Run verifier on each candidate
                for c in candidates:
                    success, score, metrics, error = self.verifier.verify_code(
                        c['code'], headless=self.headless, save_gif_path=None
                    )
                    c['success'] = success
                    c['score'] = score
                    c['metrics'] = metrics
                    c['error'] = error
                    c['feedback'] = format_feedback(metrics, score, success, metrics.get('failed', False), metrics.get('failure_reason'), iteration, error=error, task_name=self.task_name, include_suggestions=False)
                    if score > global_best_score:
                        global_best_score = score
                        global_best_code = c['code']
                        global_best_metrics = metrics
                        global_best_feedback = c['feedback']
                        global_best_iteration = iteration
                        gif_path = self._get_gif_path(iteration) if self.save_gif else None
                        self.verifier.verify_code(c['code'], headless=self.headless, save_gif_path=gif_path)
                        if gif_path and os.path.exists(gif_path):
                            print(f"✅ GIF saved (global best): {gif_path}")
                # Keep top b by score
                candidates.sort(key=lambda x: x['score'], reverse=True)
                states = candidates[:b]
                round_best = states[0]
                max_fb_len = 800
                tot_retained = [{'code': s['code'], 'score': s['score'], 'success': s['success'], 'feedback': (s.get('feedback') or '')[:max_fb_len]} for s in states]
                self.iteration_history.append({
                    'iteration': iteration, 'prompt': initial_prompt, 'code': round_best['code'],
                    'raw_llm_output': round_best.get('raw_llm_output'), 'token_usage': round_best.get('token_usage', {}),
                    'success': round_best['success'], 'score': round_best['score'], 'metrics': round_best.get('metrics', {}),
                    'error': round_best.get('error'), 'feedback': round_best['feedback'],
                    'tot_candidates': len(candidates), 'tot_top_b': [{'score': s['score'], 'success': s['success']} for s in states],
                    'tot_retained_beams': tot_retained,
                })
                if any(s['success'] for s in states):
                    print(f"🎉 ToT success at round {iteration}")
                    break
                continue
            
            # Round 2+: from each of b states, build revision prompt and generate n new codes (API: parallel)
            # When best and previous are the same solution, only show once (same as all/best_score_plus_previous mode).
            revision_prompts: List[str] = []
            best_code = global_best_code or (states[0]['code'] if states else '')
            best_feedback = global_best_feedback or (states[0].get('feedback', '') if states else '')
            # best_iteration = round where global best came from (not iteration - 1)
            best_iter = global_best_iteration
            for state in states:
                is_same_as_best = (state['code'] == best_code) if (best_code and state.get('code')) else False
                if is_same_as_best:
                    prev_code, prev_fb = '', ''
                else:
                    prev_code, prev_fb = state['code'], state['feedback']
                rev_prompt = format_revision_prompt_best_plus_previous(
                    self.task_prompt,
                    best_code,
                    best_feedback,
                    prev_code,
                    prev_fb,
                    state['feedback'],
                    best_iteration=best_iter,
                    previous_iteration=iteration - 1,
                    current_iteration=iteration,
                )
                for _ in range(n):
                    revision_prompts.append(rev_prompt)
            all_candidates = []
            use_parallel_rev = getattr(self.solver, 'model_type', self.model_type) == 'openai'
            num_gen_rev = len(revision_prompts)
            if use_parallel_rev:
                def _gen_one_rev(prompt: str, seed: int):
                    try:
                        code, raw_llm, token_usage = self.solver.generate_code(prompt, use_conversation=False, reset_conversation=False, seed=seed)
                        return (code, raw_llm, token_usage or {}, prompt)
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        return (None, None, {}, prompt)
                max_workers_rev = min(num_gen_rev, 16)
                print(f"🔄 ToT round {iteration}: generating {num_gen_rev} revisions in parallel (max_workers={max_workers_rev})...")
                with ThreadPoolExecutor(max_workers=max_workers_rev) as ex:
                    futures = [ex.submit(_gen_one_rev, p, self._sampling_seed(iteration, 100 + i)) for i, p in enumerate(revision_prompts)]
                    for fut in as_completed(futures):
                        code, raw_llm, token_usage, rev_prompt = fut.result()
                        if code and len(code.strip()) >= 50 and 'def build_agent' in code:
                            all_candidates.append({'code': code, 'raw_llm_output': raw_llm, 'token_usage': token_usage, 'prompt': rev_prompt})
            else:
                for i, rev_prompt in enumerate(revision_prompts):
                    try:
                        code, raw_llm, token_usage = self.solver.generate_code(
                            rev_prompt, use_conversation=False, reset_conversation=False,
                            seed=self._sampling_seed(iteration, 100 + i)
                        )
                        if code and len(code.strip()) >= 50 and 'def build_agent' in code:
                            all_candidates.append({'code': code, 'raw_llm_output': raw_llm, 'token_usage': token_usage or {}, 'prompt': rev_prompt})
                    except Exception as exc:
                        if is_cuda_oom(exc):
                            raise
                        print(f"⚠️  ToT revision sample failed (beam {i // n}): {exc}")
            
            if not all_candidates:
                max_fb_len = 800
                tot_retained_fail = [{'code': s['code'], 'score': s['score'], 'success': s['success'], 'feedback': (s.get('feedback') or '')[:max_fb_len]} for s in states]
                self.iteration_history.append({
                    'iteration': iteration, 'prompt': '(revision)', 'code': None, 'raw_llm_output': None,
                    'token_usage': {}, 'success': False, 'score': 0.0, 'metrics': {}, 'error': 'No valid revision code',
                    'feedback': f'ToT round {iteration}: no valid code from b*n revisions', 'tot_candidates': 0, 'tot_top_b': [{'score': s['score'], 'success': s['success']} for s in states], 'tot_retained_beams': tot_retained_fail
                })
                break
            
            for c in all_candidates:
                success, score, metrics, error = self.verifier.verify_code(
                    c['code'], headless=self.headless, save_gif_path=None
                )
                c['success'] = success
                c['score'] = score
                c['metrics'] = metrics
                c['error'] = error
                c['feedback'] = format_feedback(metrics, score, success, metrics.get('failed', False), metrics.get('failure_reason'), iteration, error=error, task_name=self.task_name, include_suggestions=False)
                if score > global_best_score:
                    global_best_score = score
                    global_best_code = c['code']
                    global_best_metrics = metrics
                    global_best_feedback = c['feedback']
                    global_best_iteration = iteration
                    gif_path = self._get_gif_path(iteration) if self.save_gif else None
                    self.verifier.verify_code(c['code'], headless=self.headless, save_gif_path=gif_path)
                    if gif_path and os.path.exists(gif_path):
                        print(f"✅ GIF saved (global best): {gif_path}")
            
            all_candidates.sort(key=lambda x: x['score'], reverse=True)
            states = all_candidates[:b]
            round_best = states[0]
            max_fb_len = 800
            tot_retained = [{'code': s['code'], 'score': s['score'], 'success': s['success'], 'feedback': (s.get('feedback') or '')[:max_fb_len]} for s in states]
            self.iteration_history.append({
                'iteration': iteration, 'prompt': round_best.get('prompt', '(revision)'), 'code': round_best['code'],
                'raw_llm_output': round_best.get('raw_llm_output'), 'token_usage': round_best.get('token_usage', {}),
                'success': round_best['success'], 'score': round_best['score'], 'metrics': round_best.get('metrics', {}),
                'error': round_best.get('error'), 'feedback': round_best['feedback'],
                'tot_candidates': len(all_candidates), 'tot_top_b': [{'score': s['score'], 'success': s['success']} for s in states],
                'tot_retained_beams': tot_retained,
            })
            if any(s['success'] for s in states):
                print(f"🎉 ToT success at round {iteration}")
                break
        
        self.best_score = global_best_score
        self.best_code = global_best_code
        self.best_metrics = global_best_metrics
    
    def _generate_report(self) -> Dict[str, Any]:
        final_iteration = self.iteration_history[-1] if self.iteration_history else None
        
        # Get token statistics if available (for API-based models)
        # Include reflexion LLM token usage when method=reflexion
        token_statistics = {}
        if self.solver.model_type == 'openai':
            token_statistics = self.solver.get_token_statistics().copy()
        if self.method == 'reflexion' and getattr(self, 'reflect_solver', None) and self.reflect_solver.model_type == 'openai':
            reflect_stats = self.reflect_solver.get_token_statistics()
            if reflect_stats.get('call_count', 0) > 0:
                if not token_statistics:
                    token_statistics = {'total_tokens': 0, 'total_prompt_tokens': 0, 'total_completion_tokens': 0, 'average_tokens': 0.0, 'call_count': 0, 'per_call_usage': []}
                token_statistics['total_tokens'] = token_statistics.get('total_tokens', 0) + reflect_stats.get('total_tokens', 0)
                token_statistics['total_prompt_tokens'] = token_statistics.get('total_prompt_tokens', 0) + reflect_stats.get('total_prompt_tokens', 0)
                token_statistics['total_completion_tokens'] = token_statistics.get('total_completion_tokens', 0) + reflect_stats.get('total_completion_tokens', 0)
                token_statistics['call_count'] = token_statistics.get('call_count', 0) + reflect_stats.get('call_count', 0)
                token_statistics['per_call_usage'] = list(token_statistics.get('per_call_usage', [])) + list(reflect_stats.get('per_call_usage', []))
                if token_statistics['call_count'] > 0:
                    token_statistics['average_tokens'] = round(token_statistics['total_tokens'] / token_statistics['call_count'], 2)
        
        report = {
            'task_name': self.task_name,
            'model_type': self.solver.model_type,
            'model_name': self.solver.model_name,
            'method': self.method,
            'context': self.context if hasattr(self, 'context') else 'previous',
            'max_iterations': self.max_iterations,
            'total_iterations': len(self.iteration_history),
            'best_score': self.best_score,
            'final_score': final_iteration['score'] if final_iteration else 0.0,
            'success': final_iteration['success'] if final_iteration else False,
            'best_metrics': self.best_metrics,
            'final_metrics': final_iteration['metrics'] if final_iteration else {},
            'best_code': self.best_code,
            'token_statistics': token_statistics,  # Add token statistics
            'task_prompt': {
                'initial_prompt': (
                    format_initial_prompt(self.task_prompt) if self.iteration_history else None
                ),
                'task_description': self.task_prompt.get('task_description', ''),
                'success_criteria': self.task_prompt.get('success_criteria', ''),
                'primitives_api': self.task_prompt.get('primitives_api', '')
            },
            'iteration_history': [
                {
                    'iteration': h['iteration'],
                    'prompt': h.get('prompt'),  # Save prompt for each iteration
                    'code': h.get('code'),  # Save complete code for each iteration
                    'raw_llm_output': h.get('raw_llm_output'),  # Save raw LLM output for each iteration
                    'token_usage': h.get('token_usage', {}),  # Save token usage for each iteration
                    'score': h['score'],
                    'success': h['success'],
                    'error': h.get('error'),
                    'feedback': h.get('feedback'),  # Save verifier feedback
                    'reflection': h.get('reflection'),  # Save reflexion reflection (if any)
                    'gradient': h.get('gradient'),  # Save TextGrad gradient text (if any)
                    'self_feedback': h.get('self_feedback'),  # Save Self-Refine self-critique (if any)
                    'self_refine_inner_steps': h.get('self_refine_inner_steps', []),  # Self-Refine: each self-verify step output for inspection
                    'metrics': h.get('metrics', {}),  # Save complete metrics
                    'metrics_summary': {
                        k: v for k, v in h.get('metrics', {}).items() 
                        if k not in ['step_count']  # Exclude some unimportant fields
                    },
                    **({'memory_retrieved': h.get('memory_retrieved'), 'memory_stored': h.get('memory_stored')} if self.method == 'a_mem_sys' else {}),
                    **({'memory_retrieved': h.get('memory_retrieved'), 'memory_stored_entry': h.get('memory_stored_entry')} if self.method == 'memento_nonparametric' else {}),
                    **({'memory_retrieved': h.get('memory_retrieved'), 'reasoning_bank_stored_items': h.get('reasoning_bank_stored_items'), 'reasoning_bank_parallel_k': h.get('reasoning_bank_parallel_k'), 'reasoning_bank_parallel_candidates': h.get('reasoning_bank_parallel_candidates')} if self.method == 'reasoning_bank' else {}),
                    **({'tot_candidates': h.get('tot_candidates'), 'tot_top_b': h.get('tot_top_b'), 'tot_retained_beams': h.get('tot_retained_beams')} if self.method == 'tree_of_thought' else {}),
                }
                for h in self.iteration_history
            ],
            'timestamp': datetime.now().isoformat()
        }
        
        # Reflexion method: include accumulated reflections in report (list for JSON serialization)
        if self.method == 'reflexion':
            report['reflections'] = list(self.reflections)
            report['reflect_model_name'] = self.reflect_model_name
        
        # TextGrad method: include engine name
        if self.method == 'textgrad':
            report['textgrad_engine_name'] = self.textgrad_engine_name
        
        # SEAL method: include TTT training stats
        if self.method == 'seal' and hasattr(self, 'solver'):
            stats = getattr(self.solver, 'get_token_statistics', lambda: {})()
            report['seal_ttt_train_count'] = stats.get('seal_train_count', 0)
        
        # RAGEN method: include RL pre-training stats
        if self.method == 'ragen':
            ragen_stats = getattr(self, '_ragen_pretrain_stats', {})
            report['ragen_pretrain_episodes'] = ragen_stats.get('n_episodes', 0)
            report['ragen_pretrain_filtered'] = ragen_stats.get('n_filtered', 0)
            report['ragen_mean_rollout_reward'] = ragen_stats.get('mean_reward', 0.0)
            report['ragen_reward_std'] = ragen_stats.get('reward_std', 0.0)
            report['ragen_ppo_epochs'] = ragen_stats.get('ppo_epochs', 0)
            report['ragen_mean_loss'] = ragen_stats.get('mean_loss', 0.0)
        if self.method == 'discover':
            discover_stats = getattr(self, '_discover_pretrain_stats', {})
            report['discover_pretrain_epochs'] = discover_stats.get('n_epochs', 0)
            report['discover_group_size'] = getattr(self, 'discover_group_size', 0)
            report['discover_mean_reward'] = discover_stats.get('mean_reward', 0.0)
            report['discover_expansion_rounds_used'] = discover_stats.get('expansion_rounds_used', 0)
            report['discover_expansion_total_trajectories'] = discover_stats.get('expansion_total_trajectories', 0)
            report['discover_train_steps_done'] = discover_stats.get('train_steps_done', 0)
        
        # SOAR method: include evolutionary search stats
        if self.method == 'soar':
            soar_stats = getattr(self, '_soar_stats', {})
            report['soar_generations'] = soar_stats.get('generations', 0)
            report['soar_k_candidates'] = soar_stats.get('k_candidates', 0)
            report['soar_archive_size'] = soar_stats.get('archive_size', 0)
            report['soar_sft_train_count'] = soar_stats.get('train_count', 0)
        
        # GENOME method: include best LoRA path for mutation
        if self.method == 'genome' and getattr(self, 'genome_best_lora_path', None):
            report['genome_best_lora_path'] = self.genome_best_lora_path
        
        # A-mem-sys method: include memory LLM name
        if self.method == 'a_mem_sys':
            report['a_mem_sys_llm_model'] = self.a_mem_sys_llm_model
        # Memento non-parametric: include memory path and summary (top_k, score_per_iteration for improvement inspection)
        if self.method == 'memento_nonparametric':
            from methods.Memory.memento_nonparametric_method import MEMORY_TOP_K
            report['memento_nonparametric_memory_path'] = getattr(self, '_memento_np_memory_path', None)
            report['memento_nonparametric_summary'] = {
                'top_k': MEMORY_TOP_K,
                'score_per_iteration': [h['score'] for h in self.iteration_history],
                'best_score': self.best_score,
            }
        # ACE method: include final playbook and Reflector/Curator model names (for mutation restore)
        if self.method == 'ace':
            report['final_playbook'] = getattr(self, '_playbook', None) or ''
            report['ace_reflector_model'] = getattr(self, 'ace_reflector_model', 'deepseek-v3.2')
            report['ace_curator_model'] = getattr(self, 'ace_curator_model', 'deepseek-v3.2')
        # Tree-of-Thought: include b, n for reproducibility
        if self.method == 'tree_of_thought':
            report['tree_of_thought_n_select'] = getattr(self, 'n_select_sample', 3)
            report['tree_of_thought_n_generate'] = getattr(self, 'n_generate_sample', 2)
        # ReasoningBank: include k and memory path (for mutation restore)
        if self.method == 'reasoning_bank':
            report['reasoning_bank_k'] = getattr(self, 'reasoning_bank_k', 2)
            report['reasoning_bank_memory_path'] = getattr(self, '_reasoning_bank_path', None)
        # Rememberer: read-only memory from same-category rollout (no store at test time)
        if self.method == 'rememberer':
            report['rememberer_memory_entries'] = len(getattr(self, '_rememberer_items', []))
        if self.method == 'expel':
            report['expel_memory_entries'] = len(getattr(self, '_expel_items', []))
            report['expel_rules_count'] = len(getattr(self, '_expel_rules', []))
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """Print evaluation report"""
        print(f"\n{'='*60}")
        print("📋 Final Evaluation Report")
        print(f"{'='*60}\n")
        
        print(f"Task: {report['task_name']}")
        print(f"Model: {report['model_type']}/{report['model_name']}")
        print(f"Method: {report.get('method', 'baseline')}")
        print(f"Context: {report.get('context', 'previous')}")
        print(f"Total iterations: {report['total_iterations']}/{report['max_iterations']}")
        print(f"Best score: {report['best_score']:.1f}/100")
        print(f"Final score: {report['final_score']:.1f}/100")
        print(f"Final status: {'✅ Success' if report['success'] else '❌ Not successful'}")
        
        # Print token statistics if available
        if report.get('token_statistics') and report['token_statistics'].get('call_count', 0) > 0:
            token_stats = report['token_statistics']
            print(f"\n📊 Token Usage Statistics:")
            print(f"  Total tokens: {token_stats['total_tokens']:,}")
            print(f"  Total prompt tokens: {token_stats['total_prompt_tokens']:,}")
            print(f"  Total completion tokens: {token_stats['total_completion_tokens']:,}")
            print(f"  Average tokens per call: {token_stats['average_tokens']:.2f}")
            print(f"  Total API calls: {token_stats['call_count']}")
        
        if report['best_metrics']:
            print(f"\nBest result metrics:")
            for key, value in report['best_metrics'].items():
                if key not in ['step_count']:
                    print(f"  {key}: {value}")
        
        print(f"\nIteration history:")
        for hist in report['iteration_history']:
            status = "✅" if hist['success'] else "❌"
            print(f"  Iteration {hist['iteration']}: {status} Score={hist['score']:.1f}")
            if hist.get('error'):
                print(f"    Error: {hist['error']}")
        
        print(f"\n{'='*60}\n")
    
    def _checkpoint_filepath(self, output_dir: str, suffix: str = "_checkpoint") -> str:
        """Build filepath for checkpoint or final report (same dir/name pattern, optional suffix before .json)."""
        model_identifier = get_model_identifier(self.model_type, self.model_name)
        task_model_method_dir = os.path.join(output_dir, self.task_name, model_identifier, self.method)
        os.makedirs(task_model_method_dir, exist_ok=True)
        context_prefix = self.context if hasattr(self, 'context') else 'previous'
        pseudo_suffix = "_pseudo" if (self.run_number is not None and getattr(self, 'context', None) == 'all') else ""
        if self.run_number is not None:
            run_suffix = get_run_suffix(self.run_number)
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"{context_prefix}_{run_suffix}_pass_{date_str}{pseudo_suffix}{suffix}.json"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{context_prefix}_{timestamp}{suffix}.json"
        return os.path.join(task_model_method_dir, filename)

    def _save_checkpoint(self, output_dir: str = "evaluation_results") -> Optional[str]:
        """Save current state to a checkpoint file so crash/segfault does not lose all results."""
        try:
            report = self._generate_report()
            report["_checkpoint"] = True  # Mark as partial result (e.g. process died before final save)
            filepath = self._checkpoint_filepath(output_dir, suffix="_checkpoint")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            return filepath
        except Exception as e:
            print(f"⚠️ Checkpoint save failed (non-fatal): {e}", flush=True)
            return None

    def save_report(self, report: Dict[str, Any], output_dir: str = "evaluation_results"):
        """Save evaluation report to file"""
        model_identifier = get_model_identifier(self.model_type, self.model_name)
        task_model_method_dir = os.path.join(output_dir, self.task_name, model_identifier, self.method)
        os.makedirs(task_model_method_dir, exist_ok=True)
        filepath = self._checkpoint_filepath(output_dir, suffix="")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        # Remove checkpoint file if it exists so we only keep the final report
        checkpoint_path = self._checkpoint_filepath(output_dir, suffix="_checkpoint")
        if os.path.isfile(checkpoint_path):
            try:
                os.remove(checkpoint_path)
            except Exception:
                pass
        print(f"📄 Evaluation report saved: {filepath}")
        return filepath




def evaluate_single_task(task_name: str, args, run_number_override: Optional[int] = None) -> int:
    """
    Evaluate one task. When run_number_override is set (1, 2, or 3), run only that round.
    Otherwise detect missing runs and run from the next needed run up to 3 rounds.
    """
    print(f"\n{'='*80}")
    print(f"Evaluating task: {task_name}")
    print(f"{'='*80}\n")
    
    max_runs = 3

    # Tree-of-Thought: only 1 run (no 3 independent runs)
    if args.method == 'tree_of_thought':
        run_to_use = run_number_override if run_number_override is not None else 1
        if run_to_use != 1:
            print(f"⚠️  ToT only supports run 1. Ignoring run_number_override={run_number_override}.")
            run_to_use = 1
        if run_is_complete(task_name=task_name, model_type=args.model_type, model_name=args.model_name, method=args.method, context=args.context, run_number=run_to_use):
            print(f"✅ Task {task_name}: ToT run 1 already complete. Skipping.")
            return 0
        start_run = 1
        actual_rounds = 1
        print(f"🔄 ToT: running only run 1 (no 2nd/3rd pass)")
    # Science-CodeEvolve: default only 1st pass (run 1), no 2nd/3rd
    elif args.method == 'science_codeevolve':
        run_to_use = run_number_override if run_number_override is not None else 1
        if run_to_use != 1:
            print(f"⚠️  science_codeevolve only runs 1st pass. Ignoring run_number_override={run_number_override}.")
            run_to_use = 1
        if run_is_complete(task_name=task_name, model_type=args.model_type, model_name=args.model_name, method=args.method, context=args.context, run_number=run_to_use):
            print(f"✅ Task {task_name}: science_codeevolve run 1 (1st pass) already complete. Skipping.")
            return 0
        start_run = 1
        actual_rounds = 1
        print(f"🔄 science_codeevolve: running only run 1 (1st pass, no 2nd/3rd)")
    # Alpha Evolve (OpenEvolve): default only 1st pass (run 1), no 2nd/3rd
    elif args.method == 'alpha_evolve':
        run_to_use = run_number_override if run_number_override is not None else 1
        if run_to_use != 1:
            print(f"⚠️  alpha_evolve only runs 1st pass. Ignoring run_number_override={run_number_override}.")
            run_to_use = 1
        if run_is_complete(task_name=task_name, model_type=args.model_type, model_name=args.model_name, method=args.method, context=args.context, run_number=run_to_use):
            print(f"✅ Task {task_name}: alpha_evolve run 1 (1st pass) already complete. Skipping.")
            return 0
        start_run = 1
        actual_rounds = 1
        print(f"🔄 alpha_evolve: running only run 1 (1st pass, no 2nd/3rd)")
    elif run_number_override is not None:
        # Single run requested (e.g. by parallel runner): run only that round
        if run_number_override < 1 or run_number_override > max_runs:
            print(f"⚠️  Invalid run_number_override={run_number_override}; must be 1, 2, or 3. Skipping.")
            return 1
        # If this run is already complete (JSON exists), skip and return success
        if run_is_complete(
            task_name=task_name,
            model_type=args.model_type,
            model_name=args.model_name,
            method=args.method,
            context=args.context,
            run_number=run_number_override,
        ):
            run_suffix = get_run_suffix(run_number_override)
            print(f"✅ Task {task_name}: Run {run_number_override} ({run_suffix} pass) already complete (JSON). Skipping.")
            return 0
        start_run = run_number_override
        actual_rounds = 1
        print(f"🔄 Running only round {start_run} (run_number_override)")
    else:
        # Check if all 3 runs (1st, 2nd, 3rd pass) already exist for this task/model/method
        if all_three_runs_complete(
            task_name=task_name,
            model_type=args.model_type,
            model_name=args.model_name,
            method=args.method,
            context=args.context
        ):
            print(f"✅ Task {task_name}: All 3 runs (1st, 2nd, 3rd pass) already exist. Skipping.")
            return 0

        # Detect starting run number
        start_run = detect_next_run_number(
            task_name=task_name,
            model_type=args.model_type,
            model_name=args.model_name,
            method=args.method,
            context=args.context
        )
        actual_rounds = min(3, max_runs - start_run + 1)
        print(f"🔄 Starting from run {start_run} (will run {actual_rounds} round{'s' if actual_rounds > 1 else ''} total)")

    # ExpeL / Rememberer: ensure rollout (and for ExpeL, insights) for this task's category before loading memory.
    # So whether we are invoked by run_evaluate_parallel or directly, the category is always ready.
    if args.method == "expel":
        from evaluation.utils import get_model_identifier
        from methods.Memory.expel_method import ensure_expel_data
        model_identifier = get_model_identifier(args.model_type, args.model_name)
        ensure_expel_data(
            [task_name],
            model_identifier,
            model_type=args.model_type,
            model_name=args.model_name,
            max_iterations=20,  # Rollout always 20 iterations (or until success); ignore --max-iterations
            context=getattr(args, "context", "all"),
            model_path=getattr(args, "model_path", None),
            api_key=getattr(args, "api_key", None),
            device=getattr(args, "device", None) or ("cpu" if args.model_type == "openai" else "cuda:0"),
            max_steps=getattr(args, "max_steps", 10000),
            expel_max_rounds=getattr(args, "expel_max_rounds", None),
            expel_max_num_rules=getattr(args, "expel_max_num_rules", None),
        )
    if args.method == "rememberer":
        from evaluation.utils import get_model_identifier
        from methods.Memory.rememberer_method import ensure_rememberer_data
        model_identifier = get_model_identifier(args.model_type, args.model_name)
        ensure_rememberer_data(
            [task_name],
            model_identifier,
            model_type=args.model_type,
            model_name=args.model_name,
            max_iterations=20,  # Rollout always 20 iterations (or until success); ignore --max-iterations
            context=getattr(args, "context", "all"),
            model_path=getattr(args, "model_path", None),
            api_key=getattr(args, "api_key", None),
            device=getattr(args, "device", None) or ("cpu" if args.model_type == "openai" else "cuda:0"),
            max_steps=getattr(args, "max_steps", 10000),
        )

    all_reports = []
    all_success = True

    # Run the requested round(s)
    for round_num in range(actual_rounds):
        run_number = start_run + round_num
        if run_number > max_runs:
            print(f"⚠️  Skipping run {run_number} (only {max_runs} runs allowed)")
            break

        # Round display: show which run this is out of total (1-3)
        print(f"\n{'='*80}")
        print(f"🔄 Round {run_number}/{max_runs} - Run {run_number}")
        print(f"{'='*80}\n")

        # K-06 (category_2_06): ref agent needs ~105k steps for 100% removal (45 particles)
        max_steps = 150000 if task_name == 'category_2_06' else args.max_steps

        # Science-CodeEvolve: run CodeEvolve per (task, run), then verifier; no TaskEvaluator
        if args.method == 'science_codeevolve':
            from methods.Inference_time_search.science_codeevolve_method import run_single_task
            from evaluation.utils import get_model_identifier, get_run_suffix, get_evaluation_results_dir
            scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            exit_code, report = run_single_task(
                task_name=task_name,
                run_number=run_number,
                model_type=args.model_type,
                model_name=args.model_name,
                context=args.context,
                max_steps=max_steps,
                scripts_dir=scripts_dir,
                api_base=getattr(args, 'api_base', None) or os.environ.get('API_BASE'),
                api_key=args.api_key or os.environ.get('API_KEY'),
                codeevolve_python=os.environ.get('CODEEVOLVE_PYTHON'),
            )
            if exit_code != 0:
                all_success = False
            model_identifier = get_model_identifier(args.model_type, args.model_name)
            run_suffix = get_run_suffix(run_number)
            date_str = datetime.now().strftime("%Y%m%d")
            pseudo_suffix = "_pseudo" if args.context == 'all' else ""
            report_path = os.path.join(
                get_evaluation_results_dir(), task_name, model_identifier, "science_codeevolve",
                f"{args.context}_{run_suffix}_pass_{date_str}{pseudo_suffix}.json"
            )
            all_reports.append((run_number, report, report_path))
            if report.get('success'):
                print(f"\n{'='*60}")
                print(f"✅ Base task succeeded (Run {run_number}). Checking for mutation sequence...")
                print(f"{'='*60}\n")
                try:
                    from evaluation.evaluate_mutated import run_mutation_sequence
                    sequence_report = run_mutation_sequence(
                        base_task_name=task_name,
                        model_type=args.model_type,
                        model_name=args.model_name,
                        method=args.method,
                        context=args.context,
                        max_iterations=args.max_iterations,
                        max_steps=max_steps,
                        headless=True,
                        api_key=args.api_key,
                        model_path=args.model_path,
                        device=args.device,
                        output_dir='evaluation_results',
                        initial_code=report.get('best_code'),
                        base_log_path=report_path,
                        run_number=run_number,
                    )
                except Exception as e:
                    print(f"⚠️ Mutation sequence failed: {e}")
            continue

        # Alpha Evolve (OpenEvolve): run OpenEvolve per (task, run), then verifier; no TaskEvaluator
        if args.method == 'alpha_evolve':
            from methods.Inference_time_search.alpha_evolve_method import run_single_task as alpha_evolve_run_single_task
            from evaluation.utils import get_model_identifier, get_run_suffix, get_evaluation_results_dir
            scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            exit_code, report = alpha_evolve_run_single_task(
                task_name=task_name,
                run_number=run_number,
                model_type=args.model_type,
                model_name=args.model_name,
                context=args.context,
                max_iterations=args.max_iterations,
                max_steps=max_steps,
                scripts_dir=scripts_dir,
                api_base=getattr(args, 'api_base', None) or os.environ.get('API_BASE'),
                api_key=args.api_key or os.environ.get('API_KEY'),
            )
            if exit_code != 0:
                all_success = False
            model_identifier = get_model_identifier(args.model_type, args.model_name)
            run_suffix = get_run_suffix(run_number)
            date_str = datetime.now().strftime("%Y%m%d")
            pseudo_suffix = "_pseudo" if args.context == 'all' else ""
            report_path = os.path.join(
                get_evaluation_results_dir(), task_name, model_identifier, "alpha_evolve",
                f"{args.context}_{run_suffix}_pass_{date_str}{pseudo_suffix}.json"
            )
            all_reports.append((run_number, report, report_path))
            if report.get('success'):
                print(f"\n{'='*60}")
                print(f"✅ Base task succeeded (Run {run_number}). Checking for mutation sequence...")
                print(f"{'='*60}\n")
                try:
                    from evaluation.evaluate_mutated import run_mutation_sequence
                    sequence_report = run_mutation_sequence(
                        base_task_name=task_name,
                        model_type=args.model_type,
                        model_name=args.model_name,
                        method=args.method,
                        context=args.context,
                        max_iterations=args.max_iterations,
                        max_steps=max_steps,
                        headless=True,
                        api_key=args.api_key,
                        model_path=args.model_path,
                        device=args.device,
                        output_dir='evaluation_results',
                        initial_code=report.get('best_code'),
                        base_log_path=report_path,
                        run_number=run_number,
                    )
                except Exception as e:
                    print(f"⚠️ Mutation sequence failed: {e}")
            continue

        # ThetaEvolve: test-time RL with evolving gym (local only); run 1st/2nd/3rd
        if args.method == 'theta_evolve':
            if args.model_type != 'local':
                raise ValueError("theta_evolve only supports --model-type local.")
            from methods.Parameter_Policy.theta_evolve import run_single_task as theta_evolve_run_single_task
            from evaluation.utils import get_model_identifier, get_run_suffix, get_evaluation_results_dir, get_gif_base_dir
            scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            exit_code, report = theta_evolve_run_single_task(
                task_name=task_name,
                run_number=run_number,
                model_type=args.model_type,
                model_name=args.model_name,
                context=args.context,
                max_steps=max_steps,
                scripts_dir=scripts_dir,
                output_dir=get_evaluation_results_dir(),
                gif_base_dir=get_gif_base_dir(),
                initial_code=None,
                model_path=args.model_path,
                device=args.device,
                env_overrides=None,
                theta_evolve_num_rollout=getattr(args, 'theta_evolve_num_rollout', 3000),
                theta_evolve_rollout_batch_size=getattr(args, 'theta_evolve_rollout_batch_size', 32),
            )
            if exit_code != 0:
                all_success = False
            model_identifier = get_model_identifier(args.model_type, args.model_name)
            run_suffix = get_run_suffix(run_number)
            date_str = datetime.now().strftime("%Y%m%d")
            pseudo_suffix = "_pseudo" if args.context == 'all' else ""
            report_path = os.path.join(
                get_evaluation_results_dir(), task_name, model_identifier, "theta_evolve",
                f"{args.context}_{run_suffix}_pass_{date_str}{pseudo_suffix}.json"
            )
            all_reports.append((run_number, report, report_path))
            if report.get('success'):
                print(f"\n{'='*60}")
                print(f"✅ Base task succeeded (Run {run_number}). Checking for mutation sequence...")
                print(f"{'='*60}\n")
                try:
                    from evaluation.evaluate_mutated import run_mutation_sequence
                    sequence_report = run_mutation_sequence(
                        base_task_name=task_name,
                        model_type=args.model_type,
                        model_name=args.model_name,
                        method=args.method,
                        context=args.context,
                        max_iterations=args.max_iterations,
                        max_steps=max_steps,
                        headless=True,
                        api_key=args.api_key,
                        model_path=args.model_path,
                        device=args.device,
                        output_dir='evaluation_results',
                        initial_code=report.get('best_code'),
                        base_log_path=report_path,
                        run_number=run_number,
                    )
                except Exception as e:
                    print(f"⚠️ Mutation sequence failed: {e}")
            continue

        # GENOME: ensure Phase 1 cache exists (run GA if missing), then get best LoRA path
        genome_best_lora_path = None
        if args.method == 'genome':
            from evaluation.utils import get_model_identifier
            from methods.Parameter_Policy.genome import get_genome_experts_dir, get_genome_cache_path
            from methods.Parameter_Policy.genome.genome_method import run_genome_phase1
            model_identifier = get_model_identifier(args.model_type, args.model_name)
            lora_dir = get_genome_experts_dir()
            cache_path = get_genome_cache_path(task_name, model_identifier)
            genome_best_lora_path = run_genome_phase1(
                task_name=task_name,
                model_path=args.model_path or args.model_name,
                lora_dir=lora_dir,
                cache_path=cache_path,
                device=args.device,
                max_steps=max_steps,
                population_size=getattr(args, 'genome_population_size', 10),
                genome_iters=getattr(args, 'genome_iters', 50),
            )
            if not genome_best_lora_path:
                raise RuntimeError("GENOME Phase 1 did not return a best LoRA path.")

        # Create fresh evaluator for this round
        evaluator = TaskEvaluator(
            task_name=task_name,
            model_type=args.model_type,
            model_name=args.model_name,
            api_key=args.api_key,
            max_iterations=args.max_iterations,
            max_steps=max_steps,
            headless=True,  # Default to headless mode
            model_path=args.model_path,
            device=args.device,
            method=args.method,
            context=args.context,
            run_number=run_number,  # Pass run number
            reflect_model_name=getattr(args, 'reflect_model_name', None),  # Reflexion method
            textgrad_engine_name=getattr(args, 'textgrad_engine_name', None),  # TextGrad method
            a_mem_sys_llm_model=getattr(args, 'a_mem_sys_llm_model', None),  # A-mem-sys: memory LLM
            initial_playbook=None,  # ACE: set by evaluate_mutated when mutated task
            ace_reflector_model=getattr(args, 'ace_reflector_model', None),  # ACE: Reflector model
            ace_curator_model=getattr(args, 'ace_curator_model', None),  # ACE: Curator model
            n_select_sample=getattr(args, 'n_select_sample', None),  # ToT: b
            n_generate_sample=getattr(args, 'n_generate_sample', None),  # ToT: n
            reasoning_bank_k=getattr(args, 'reasoning_bank_k', None),  # ReasoningBank: parallel K
            genome_best_lora_path=genome_best_lora_path,
            ragen_n_rollouts=getattr(args, 'ragen_n_rollouts', 8),  # RAGEN: rollout episodes
            ragen_ppo_epochs=getattr(args, 'ragen_ppo_epochs', 2),  # RAGEN: PPO epochs
            soar_generations=getattr(args, 'soar_generations', 2),  # SOAR: self-improvement generations
            soar_k_candidates=getattr(args, 'soar_k_candidates', 4),  # SOAR: K candidates per iteration
            discover_num_epochs=getattr(args, 'discover_num_epochs', 50),
            discover_group_size=getattr(args, 'discover_group_size', 8),
            discover_groups_per_batch=getattr(args, 'discover_groups_per_batch', 64),
            discover_learning_rate=getattr(args, 'discover_learning_rate', 4e-5),
            discover_adv_estimator=getattr(args, 'discover_adv_estimator', 'entropic'),
            discover_adv_estimator_beta=getattr(args, 'discover_adv_estimator_beta', 2.0),
            discover_loss_fn=getattr(args, 'discover_loss_fn', 'importance_sampling'),
            discover_lora_rank=getattr(args, 'discover_lora_rank', 32),
            discover_max_tokens=getattr(args, 'discover_max_tokens', 65536),
            discover_temperature=getattr(args, 'discover_temperature', 1.0),
            discover_num_substeps=getattr(args, 'discover_num_substeps', 1),
            discover_max_expansion_rounds=getattr(args, 'discover_max_expansion_rounds', 2),
        )
        
        # Execute evaluation
        try:
            report = evaluator.evaluate()
            
            # Print report
            evaluator.print_report(report)
            
            # Save report
            report_path = evaluator.save_report(report, output_dir='evaluation_results')
            all_reports.append((run_number, report, report_path))
            
            evaluator.verifier.cleanup()
            # If base task succeeded, run mutation sequence BEFORE cleanup.
            # For local/vLLM: reuse the already-loaded model (avoids OOM from reloading).
            if report['success']:
                print(f"\n{'='*60}")
                print(f"✅ Base task succeeded (Run {run_number}). Checking for mutation sequence...")
                print(f"{'='*60}\n")
                try:
                    from evaluation.evaluate_mutated import run_mutation_sequence
                    # Pass solver for local model: reuse vLLM instead of reloading (avoids OOM)
                    solver_to_pass = evaluator.solver if args.model_type == 'local' else None
                    sequence_report = run_mutation_sequence(
                        base_task_name=task_name,
                        model_type=args.model_type,
                        model_name=args.model_name,
                        method=args.method,
                        context=args.context,
                        max_iterations=args.max_iterations,
                        max_steps=args.max_steps,
                        headless=True,
                        api_key=args.api_key,
                        model_path=args.model_path,
                        device=args.device,
                        output_dir='evaluation_results',
                        initial_code=report.get('best_code'),  # Use best_code from report
                        base_log_path=report_path,  # Pass report path for immediate appending
                        run_number=run_number,  # Pass run_number for directory structure
                        reflect_model_name=getattr(args, 'reflect_model_name', None),  # Reflexion method
                        textgrad_engine_name=getattr(args, 'textgrad_engine_name', None),
                        a_mem_sys_llm_model=getattr(args, 'a_mem_sys_llm_model', None),  # A-mem-sys
                        ace_reflector_model=getattr(args, 'ace_reflector_model', None),  # ACE
                        ace_curator_model=getattr(args, 'ace_curator_model', None),  # ACE
                        reasoning_bank_k=getattr(args, 'reasoning_bank_k', None),  # ReasoningBank
                        solver_override=solver_to_pass,  # Reuse vLLM for local model (avoids OOM)
                    )
                    # Print sequence summary
                    if sequence_report.get('total_mutations', 0) > 0:
                        print(f"\n{'='*60}")
                        print("📋 Mutation Sequence Summary")
                        print(f"{'='*60}")
                        print(f"Completed: {sequence_report['completed_mutations']}/{sequence_report['total_mutations']} mutations")
                        print(f"Success rate: {sequence_report['success_rate']*100:.1f}%")
                        print(f"{'='*60}\n")
                        print(f"✅ Mutation sequence results saved incrementally to: {report_path}")
                except Exception as e:
                    if is_cuda_oom(e):
                        print(f"❌ CUDA out of memory in mutation sequence - stopping: {e}")
                        raise
                    print(f"⚠️  Failed to run mutation sequence: {e}")
                    print(f"   You can retry mutations later with: python evaluation/run_all_missing_mutations.py")
                    import traceback
                    traceback.print_exc()
            # Explicitly shut down vLLM engine to release GPU memory (after mutations reused it)
            if hasattr(evaluator, 'solver') and hasattr(evaluator.solver, 'cleanup'):
                evaluator.solver.cleanup()
            del evaluator
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            except Exception:
                pass
            
            if not report['success']:
                all_success = False
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Evaluation interrupted by user")
            return 130
        except Exception as e:
            print(f"\n❌ Evaluation process error for task {task_name} (run {run_number}): {e}")
            import traceback
            traceback.print_exc()
            # Cleanup on error - release vLLM engine and GPU memory
            try:
                if 'evaluator' in locals():
                    evaluator.verifier.cleanup()
                    if hasattr(evaluator, 'solver') and hasattr(evaluator.solver, 'cleanup'):
                        evaluator.solver.cleanup()
            except Exception:
                pass
            try:
                if 'evaluator' in locals():
                    del evaluator
                import gc
                gc.collect()
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            if is_cuda_oom(e):
                print("❌ CUDA out of memory - stopping immediately (will not retry)")
                raise
            all_success = False
    
    # Print summary of all runs
    print(f"\n{'='*80}")
    print(f"📊 Summary of all runs for task: {task_name}")
    print(f"{'='*80}")
    for run_num, report, report_path in all_reports:
        status = "✅ Success" if report['success'] else "❌ Failed"
        print(f"  Run {run_num}: {status} (Score: {report['best_score']:.1f}/100)")
    print(f"{'='*80}\n")
    
    # Return exit code: 0 if all succeeded, 1 otherwise
    return 0 if all_success else 1


def resolve_task_list(task_spec: str) -> List[str]:
    import re
    
    # Check if it's 'all'
    if task_spec.lower() == 'all':
        tasks = get_all_tasks()
        # Always skip category_1_03 and category_1_05 (ignore their results everywhere)
        # skip_tasks = {'category_1_03', 'category_1_05'}
        skip_tasks = {'category_1_04'}
        return [t for t in tasks if t not in skip_tasks]
    
    # Check if it's category_X (category-level)
    category_pattern = re.match(r'^category_(\d+)$', task_spec.lower())
    if category_pattern:
        cat_num = int(category_pattern.group(1))
        tasks = get_all_tasks_in_category(cat_num)
        # Skip category_1_03 and category_1_05 when evaluating category_1
        if cat_num == 1:
            # skip_tasks = {'category_1_03', 'category_1_05'}
            skip_tasks = {}
            tasks = [t for t in tasks if t not in skip_tasks]
        return tasks
    
    # Single task (category_X_YY, legacy format, or path format)
    return [task_spec]


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Task evaluator')
    parser.add_argument('--task', type=str, nargs='+', default=['basic'],
                       metavar='TASK',
                       help='Task(s) to evaluate. Single spec: category_X_YY, category_X, or all (resolved to list). '
                            'Multiple names: pass resolved task names (e.g. category_1_01 category_1_02) for data-parallel runners.')
    parser.add_argument('--model-type', type=str, default='mock',
                       choices=['openai', 'local', 'mock'],
                       help='Model type')
    parser.add_argument('--model-name', type=str, default='deepseek-v3.2',
                       help='Model name (e.g., gpt-4, claude-3-opus, or local model path)')
    parser.add_argument('--api-key', type=str, default=None,
                       help='API key (if not provided, will use environment variable)')
    parser.add_argument('--model-path', type=str, default=None,
                       help='Local model path (if model-type is local and model-name is not a path)')
    parser.add_argument('--device', type=str, default='auto',
                       help='Device type: auto (automatic), cuda (use default GPU), cpu, cuda:1 (single GPU), or cuda:1,2,3 (multiple GPUs)')
    parser.add_argument('--max-iterations', type=int, default=20,
                       help='Maximum number of iterations')
    parser.add_argument('--max-steps', type=int, default=10000,
                       help='Maximum simulation steps per verification')
    parser.add_argument('--method', type=str, default='baseline',
                       choices=['baseline', 'sys_feedback', 'reflexion', 'textgrad', 'self_refine', 'self_refine_inner_only', 'a_mem_sys', 'memento_nonparametric', 'rememberer', 'expel', 'ace', 'tree_of_thought', 'reasoning_bank', 'absolute_zero', 'absolute_zero_iter', 'science_codeevolve', 'alpha_evolve', 'theta_evolve', 'genome', 'seal', 'ragen', 'soar', 'discover'],
                       help='Evaluation method: baseline, sys_feedback, reflexion, textgrad, self_refine, self_refine_inner_only, a_mem_sys, memento_nonparametric, rememberer (read-only memory from same-category rollout), ace, tree_of_thought, reasoning_bank, absolute_zero (initial only, local), absolute_zero_iter (iterative like baseline, local), science_codeevolve, alpha_evolve (OpenEvolve), theta_evolve (test-time RL with evolving gym, local), genome (Phase 1 GA + Phase 2 refinement, local), seal (per-task TTT with LoRA, local), ragen (per-task multi-turn RL with GRPO+PPO, local), soar (evolutionary search + SFT self-improvement, local), discover (TTT-Discover per-task test-time RL, local)')
    parser.add_argument('--n-select-sample', type=int, default=3, dest='n_select_sample',
                       help='ToT: number of beams to keep per round (b). Default: 3')
    parser.add_argument('--n-generate-sample', type=int, default=2, dest='n_generate_sample',
                       help='ToT: number of samples per beam per round (n). Default: 2')
    parser.add_argument('--reasoning-bank-k', type=int, default=2, dest='reasoning_bank_k',
                       help='ReasoningBank: number of parallel trajectories per iteration (k). Default: 2')
    parser.add_argument('--genome-iters', type=int, default=50, dest='genome_iters',
                       help='GENOME Phase 1: GA iterations. Default: 50')
    parser.add_argument('--genome-population-size', type=int, default=10, dest='genome_population_size',
                       help='GENOME Phase 1: population size. Default: 10')
    parser.add_argument('--ace-reflector-model', type=str, default='deepseek-v3.2',
                       dest='ace_reflector_model',
                       help='Model for ACE Reflector (only when method=ace). Default: deepseek-v3.2')
    parser.add_argument('--ace-curator-model', type=str, default='deepseek-v3.2',
                       dest='ace_curator_model',
                       help='Model for ACE Curator (only when method=ace). Default: deepseek-v3.2')
    parser.add_argument('--a-mem-llm-model', type=str, default='deepseek-v3.2',
                       dest='a_mem_sys_llm_model',
                       help='LLM for memory module (only when method=a_mem_sys). Default: deepseek-v3.2')
    parser.add_argument('--reflect-model-name', type=str, default='deepseek-v3.2',
                       help='Model name for reflection LLM (only used when method=reflexion). Default: deepseek-v3.2')
    parser.add_argument('--textgrad-engine-name', type=str, default='deepseek-v3.2',
                       help='Engine for TextGrad backward/optimizer (only used when method=textgrad). Default: deepseek-v3.2')
    parser.add_argument('--context', type=str, default='all',
                       choices=['previous', 'all', 'last_3', 'best_score', 'best_score_plus_previous'],
                       help='Context management strategy: previous (only last iteration, default), all (full conversation history), last_3 (last 3 iterations), best_score (best-scoring attempt), best_score_plus_previous (best + previous)')
    parser.add_argument('--expel-max-rounds', type=int, default=8, dest='expel_max_rounds',
                       help='ExpeL: max insight extraction rounds when insights.json is missing (default 8). Only used when --method expel.')
    parser.add_argument('--expel-max-num-rules', type=int, default=20, dest='expel_max_num_rules',
                       help='ExpeL: target max rules for list_full during extraction (default 20). Only used when --method expel.')
    parser.add_argument('--run-number', type=int, default=None, choices=[1, 2, 3],
                       help='Run only this round (1st/2nd/3rd pass). Used by parallel runner for single (task, run) work items.')
    parser.add_argument('--ragen-n-rollouts', type=int, default=8, dest='ragen_n_rollouts',
                       help='RAGEN: number of rollout episodes per task for RL pre-training. Default: 8')
    parser.add_argument('--ragen-ppo-epochs', type=int, default=2, dest='ragen_ppo_epochs',
                       help='RAGEN: number of PPO epochs per training step. Default: 2')
    parser.add_argument('--soar-generations', type=int, default=2, dest='soar_generations',
                       help='SOAR: number of self-improvement generations. Default: 2')
    parser.add_argument('--soar-k-candidates', type=int, default=4, dest='soar_k_candidates',
                       help='SOAR: K candidates per iteration for test-time search. Default: 4')
    parser.add_argument('--discover-num-epochs', type=int, default=50, dest='discover_num_epochs',
                       help='Discover: TTT epochs (repo default 50). Default: 50')
    parser.add_argument('--discover-group-size', type=int, default=8, dest='discover_group_size',
                       help='Discover: rollouts per group (repo default 8). Default: 8')
    parser.add_argument('--discover-groups-per-batch', type=int, default=64, dest='discover_groups_per_batch',
                       help='Discover: groups per batch (repo default 64). Default: 64')
    parser.add_argument('--discover-learning-rate', type=float, default=4e-5, dest='discover_learning_rate',
                       help='Discover: learning rate (repo default 4e-5). Default: 4e-5')
    parser.add_argument('--discover-adv-estimator', type=str, default='entropic', dest='discover_adv_estimator',
                       choices=['mean_baseline', 'entropic', 'entropic_adaptive_beta'],
                       help='Discover: advantage estimator (repo default entropic). Default: entropic')
    parser.add_argument('--discover-adv-estimator-beta', type=float, default=2.0, dest='discover_adv_estimator_beta',
                       help='Discover: entropic advantage beta (repo default 2.0). Default: 2.0')
    parser.add_argument('--discover-loss-fn', type=str, default='importance_sampling', dest='discover_loss_fn',
                       choices=['importance_sampling', 'ppo'],
                       help='Discover: loss (repo default importance_sampling). Default: importance_sampling')
    parser.add_argument('--discover-lora-rank', type=int, default=32, dest='discover_lora_rank',
                       help='Discover: LoRA rank (repo default 32). Default: 32')
    parser.add_argument('--discover-max-tokens', type=int, default=65536, dest='discover_max_tokens',
                       help='Discover: max tokens per rollout (repo default 26000). Default: 26000')
    parser.add_argument('--discover-temperature', type=float, default=1.0, dest='discover_temperature',
                       help='Discover: sampling temperature (repo default 1.0). Default: 1.0')
    parser.add_argument('--discover-num-substeps', type=int, default=1, dest='discover_num_substeps',
                       help='Discover: optimizer substeps (repo default 1). Default: 1')
    parser.add_argument('--discover-max-expansion-rounds', type=int, default=2, dest='discover_max_expansion_rounds',
                       help='Discover: max feedback expansion rounds when reward constant (default 2: 8->64). Default: 2')
    parser.add_argument('--theta-evolve-num-rollout', type=int, default=3000, dest='theta_evolve_num_rollout',
                       help='ThetaEvolve: number of rollout steps (repo default 3000). Default: 3000')
    parser.add_argument('--theta-evolve-rollout-batch-size', type=int, default=32, dest='theta_evolve_rollout_batch_size',
                       help='ThetaEvolve: rollout batch size (repo default 32). Default: 32')
    
    args = parser.parse_args()

    # ToT: default 10 rounds when user does not pass --max-iterations (parser default is 20)
    if args.method == 'tree_of_thought' and args.max_iterations == 20:
        args.max_iterations = 10

    # Set CUDA_VISIBLE_DEVICES early for multi-GPU device spec, BEFORE any torch import.
    # Only set when not already set (e.g. run_evaluate_parallel.py sets 5,7 for TP2; we must not overwrite with 0,1).
    if args.model_type == 'local' and args.device and args.device.startswith('cuda:'):
        device_str = args.device[5:]
        if ',' in device_str and not os.environ.get('CUDA_VISIBLE_DEVICES'):
            gpu_ids = [int(x.strip()) for x in device_str.split(',')]
            os.environ['CUDA_VISIBLE_DEVICES'] = ','.join(str(x) for x in gpu_ids)
            print(f"Early CUDA_VISIBLE_DEVICES={os.environ['CUDA_VISIBLE_DEVICES']} (GPUs {gpu_ids})")
    
    # Resolve task list: single spec -> resolve; multiple args -> use as explicit task names (for parallel runner)
    if len(args.task) == 1:
        task_list = resolve_task_list(args.task[0])
    else:
        task_list = list(args.task)
    
    if not task_list:
        print(f"❌ No tasks found for specification: {args.task}")
        return 1
    
    print(f"\n📋 Found {len(task_list)} task(s) to evaluate:")
    for i, task in enumerate(task_list, 1):
        print(f"  {i}. {task}")
    print()
    
    # Evaluate each task (optionally only the specified run_number for each)
    results = []
    run_number_override = getattr(args, 'run_number', None)
    for task_name in task_list:
        exit_code = evaluate_single_task(task_name, args, run_number_override=run_number_override)
        results.append((task_name, exit_code))
    
    # Print summary (exit_code 0 = evaluation run finished without crash, not task solved)
    print(f"\n{'='*80}")
    print("📊 Evaluation Summary")
    print(f"{'='*80}")
    completed_count = sum(1 for _, code in results if code == 0)
    total_count = len(results)
    print(f"Runs completed (exit 0): {completed_count}/{total_count}")
    print(f"\nDetailed results (per task, exit code):")
    for task_name, exit_code in results:
        status = "✅ Completed" if exit_code == 0 else "❌ Failed/Crashed"
        print(f"  {task_name}: {status}")
    print(f"{'='*80}\n")
    
    # Return exit code: 0 if all runs completed (exit 0), 1 otherwise
    return 0 if completed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
