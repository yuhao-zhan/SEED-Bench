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
from evaluation.feedback import format_feedback, format_granular_feedback
from evaluation.solver_interface import SolverInterface, get_aux_llm_credentials
from evaluation.verifier import CodeVerifier
from evaluation.utils import (
    get_model_identifier, get_gif_path,
    get_gif_base_dir, get_evaluation_results_dir,
    get_evaluation_results_scratch_dir,
    get_training_log_dir,
    run_is_complete, is_cuda_oom, clean_special_tags,
    get_max_steps_for_task, load_task_stages_module,
)


def get_effective_result_method(method: str, granularity: str) -> str:
    g = (granularity or "outcome-based").strip().lower()
    if g == "outcome-based":
        return method
    return f"{method}_{g}"


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
                 save_gif: bool = True, source_env: Optional[str] = None,
                 output_dir: Optional[str] = None,
                 result_method: Optional[str] = None,
                 granularity: str = "outcome-based",
                 theta_evolve_num_rollout: Optional[int] = None,
                 theta_evolve_rollout_batch_size: Optional[int] = None):
        self.task_name = task_name
        self.save_gif = save_gif
        self.output_dir = output_dir
        self.result_method = result_method or method
        self.granularity = granularity or "outcome-based"
        self.theta_evolve_num_rollout = theta_evolve_num_rollout if theta_evolve_num_rollout is not None else 10000
        self.theta_evolve_rollout_batch_size = theta_evolve_rollout_batch_size if theta_evolve_rollout_batch_size is not None else 32
        self.base_task_name_for_memory = base_task_name_for_memory
        self.source_env = source_env

        self.max_steps = max_steps
        self.max_iterations = max_iterations
        self.headless = headless
        self.method = method
        self.base_method = method[:-3] if method.endswith('_CE') else method
        # All auxiliary LLM calls (Reflexion, ACE, memory, ReasoningBank, TextGrad, …): same as SolverInterface openai defaults
        self._llm_aux_api_key, self._llm_aux_base_url = get_aux_llm_credentials(api_key)
        self.context = context
        self.env_overrides = env_overrides
        self.is_mutated_task = is_mutated_task
        self.mutated_task_name = None  # Set by evaluate_mutated
        self.reasoning_bank_k = reasoning_bank_k if reasoning_bank_k is not None else 2
        
        # Initialize solver (Parameter_Policy methods use custom solver)
        if solver_override:
            self.solver = solver_override
        elif self.base_method == 'absolute_zero_iter':
            # Absolute-Zero: iteration-based evaluation with AZR solver (local only).
            if model_type != 'local':
                raise ValueError(
                    "absolute_zero_iter only supports --model-type local. "
                    "Use baseline or sys_feedback for API models."
                )
            from methods.Parameter_Policy.absolute_zero.absolute_zero_method import get_azr_solver
            self.solver = get_azr_solver(
                model_name=model_name,
                model_path=model_path,
                device=device or 'auto',
            )
        elif self.base_method == 'genome':
            if model_type != 'local':
                raise ValueError(
                    "genome only supports --model-type local. Run bootstrap_lora_dir.py first (creates genome/experts/)."
                )
            if not genome_best_lora_path:
                raise ValueError(
                    "genome requires genome_best_lora_path (Phase 1 best LoRA). "
                    "Run from-scratch with method=genome once to populate Phase 1 cache, or pass --genome-best-lora-path."
                )
            from methods.Parameter_Policy.genome.genome_method import get_genome_solver
            self.solver = get_genome_solver(
                model_name=model_name,
                model_path=model_path,
                best_lora_path=genome_best_lora_path,
                device=device or 'auto',
            )
            self.genome_best_lora_path = genome_best_lora_path
            self.max_iterations = min(self.max_iterations, 20)  # Phase 2: cap at 20 refinement iterations
        elif self.base_method == 'seal':
            # SEAL: per-task test-time LoRA adaptation (local only)
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
        elif self.base_method == 'ragen':
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
        elif self.base_method == 'soar':
            # SOAR: per-task evolutionary search + SFT self-improvement (local only)
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
        elif self.base_method == 'discover':
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
        self._stop_reason = None   # 'success' | 'error_generating_code' | None (exhausted iterations)
        self._stop_error = None    # exception message when stopped due to error

        # Reflexion method: initialize reflection buffer (FIFO queue, max 3) and reflection LLM
        self.reflections = deque(maxlen=3) if self.base_method == 'reflexion' else []
        self.reflections_str = ''
        self.reflect_solver = None
        self.reflect_model_name = reflect_model_name or 'deepseek-v3.2'
        if self.base_method == 'reflexion':
            print(f"🔄 Reflexion method: initializing reflection LLM ({self.reflect_model_name}), experience buffer max 3...")
            self.reflect_solver = SolverInterface(
                model_type='openai',
                model_name=self.reflect_model_name,
                api_key=self._llm_aux_api_key,
            )
            self.reflect_solver.set_custom_system_prompt(REFLEXION_SYSTEM_PROMPT)
        
        if self.base_method == 'tree_of_thought':
            self.max_iterations = max_iterations
            self.n_select_sample = n_select_sample if n_select_sample is not None else 3
            self.n_generate_sample = n_generate_sample if n_generate_sample is not None else 2
        else:
            self.max_iterations = max_iterations
            self.n_select_sample = None
            self.n_generate_sample = None
            
        if self.base_method == 'self_refine':
            self.max_iterations = min(self.max_iterations, 20)
        if self.base_method == 'self_refine_inner_only':
            self.max_iterations = 1
        if self.base_method == 'genome':
            self.max_iterations = min(self.max_iterations, 20)  # Phase 2: cap at 20 refinement iterations

        self._setup_gif_directory()

        # REMEMBERER / EXPEL (pair-based): load memory from rememberer/expel (filled from evaluation_results_scratch)
        self._rememberer_items = []
        self._rememberer_candidates = []
        self._expel_items = []
        self._expel_rules = []
        self._expel_embedder = None
        if self.base_method == 'rememberer':
            from methods.Memory.rememberer_method import load_rememberer_memory_for_task, get_rememberer_root
            model_id = get_model_identifier(self.solver.model_type, self.solver.model_name)
            root = get_rememberer_root()
            self._rememberer_items, self._rememberer_candidates = load_rememberer_memory_for_task(
                task_name, model_id, rememberer_root=root, source_env=self.source_env
            )
            if self._rememberer_items or self._rememberer_candidates:
                print(f"🧠 Rememberer: read-only memory ({len(self._rememberer_items)} entries)")
        if self.base_method == 'expel':
            if model_type == 'mock':
                # Avoid embedder + heavy category JSON load; smoke tests use mock solver only.
                print("🧠 ExpeL: mock mode, skipping memory/embedder load.")
            else:
                from methods.Memory.expel_method import load_expel_memory_for_task
                model_id = get_model_identifier(self.solver.model_type, self.solver.model_name)
                self._expel_items, self._expel_rules, self._expel_embedder = load_expel_memory_for_task(
                    task_name, model_id, source_env=self.source_env
                )
                if self.source_env:
                    print(
                        f"🧠 ExpeL: pair memory ({self.source_env}) — "
                        f"{len(self._expel_items)} trajectories, {len(self._expel_rules)} rules"
                    )
                else:
                    print(
                        f"🧠 ExpeL: same-category memory ({len(self._expel_items)} trajectories, {len(self._expel_rules)} rules)"
                    )
        # ReasoningBank: load or create bank path; inject retrieved memory into prompt each iteration
        self._reasoning_bank_path = None
        self._reasoning_bank_items = []
        if self.base_method == 'reasoning_bank':
            from methods.Memory.reasoning_bank_method import get_memory_path, load_bank
            model_id = get_model_identifier(self.solver.model_type, self.solver.model_name)
            if isinstance(initial_memory_system, str) and initial_memory_system:
                self._reasoning_bank_path = initial_memory_system
                self._reasoning_bank_items = load_bank(self._reasoning_bank_path)
                if self._reasoning_bank_items:
                    print(f"🧠 ReasoningBank: loaded {len(self._reasoning_bank_items)} items from base task")
            else:
                try:
                    task_path, _ = parse_task_name(task_name)
                    results_base = os.path.join(output_dir or get_evaluation_results_scratch_dir(), *task_path.split("/"))
                    self._reasoning_bank_path = get_memory_path(results_base, task_name, model_id, None)
                    self._reasoning_bank_items = load_bank(self._reasoning_bank_path)
                except Exception as e:
                    print(f"⚠️  ReasoningBank: could not init bank path ({e}), will run with empty bank")
            if not self._reasoning_bank_items:
                print("🧠 ReasoningBank: starting with empty bank (memory will grow each iteration)")
        # Memento non-parametric: load or create memory path; inject retrieved cases into prompt
        self._memento_memory_path = None
        self._memento_items = []
        self._memento_pairs = []
        if self.base_method == 'memento_nonparametric':
            from methods.Memory.memento_nonparametric_method import get_memory_path, load_memory
            model_id = get_model_identifier(self.solver.model_type, self.solver.model_name)
            if isinstance(initial_memory_system, str) and initial_memory_system:
                self._memento_memory_path = initial_memory_system
                self._memento_items, self._memento_pairs = load_memory(self._memento_memory_path)
                if self._memento_items:
                    print(f"🧠 Memento non-parametric: loaded {len(self._memento_items)} entries from base task")
            else:
                try:
                    task_path, _ = parse_task_name(task_name)
                    results_base = os.path.join(output_dir or get_evaluation_results_scratch_dir(), *task_path.split("/"))
                    self._memento_memory_path = get_memory_path(results_base, task_name, model_id, None)
                    self._memento_items, self._memento_pairs = load_memory(self._memento_memory_path)
                except Exception as e:
                    print(f"⚠️  Memento non-parametric: could not init memory path ({e}), will run with empty memory")
            if not self._memento_items:
                print("🧠 Memento non-parametric: starting with empty memory (will grow each iteration)")
        # A-mem-sys: create or use provided memory system; inject retrieved memories into prompt
        self._a_mem_sys_memory = None
        if self.base_method == 'a_mem_sys':
            from methods.Memory.a_mem_sys_method import get_memory_system
            if initial_memory_system is not None and not isinstance(initial_memory_system, str):
                self._a_mem_sys_memory = initial_memory_system
                print("🧠 A-mem-sys: using restored memory system from base task")
            else:
                try:
                    self._a_mem_sys_memory = get_memory_system(
                        llm_backend="openai",
                        llm_model=a_mem_sys_llm_model or "deepseek-v3.2",
                        api_key=self._llm_aux_api_key,
                        base_url=self._llm_aux_base_url,
                    )
                    print("🧠 A-mem-sys: created fresh memory system")
                except Exception as e:
                    print(f"⚠️  A-mem-sys: could not create memory system ({e}), will run without memory")
        self._ace_playbook = None
        self._ace_reflector = None
        self._ace_curator = None
        self._ace_next_global_id = 1
        # TextGrad: engine for gradient + optimizer; tg_code_var/tg_optimizer set after first code gen
        self.tg_engine = None
        self.tg_code_var = None
        self.tg_optimizer = None
        self.textgrad_engine_name = textgrad_engine_name or 'deepseek-v3.2'
        if self.base_method == 'textgrad':
            from methods.Context.textgrad_method import create_textgrad_engine
            self.tg_engine = create_textgrad_engine(self.textgrad_engine_name, api_key=self._llm_aux_api_key)
            print(f"🧮 TextGrad method: engine={self.textgrad_engine_name} (backward + optimizer)")
        # ACE: playbook + reflector/curator; inject playbook into prompt each iteration
        if self.base_method == 'ace':
            from methods.Memory.ace_method import get_initial_playbook, build_ace_reflector_curator
            self._ace_playbook = (initial_playbook or get_initial_playbook()).strip()
            try:
                self._ace_reflector, self._ace_curator, self._ace_next_global_id = build_ace_reflector_curator(
                    reflector_model=ace_reflector_model or "deepseek-v3.2",
                    curator_model=ace_curator_model or "deepseek-v3.2",
                    api_key=self._llm_aux_api_key,
                    base_url=self._llm_aux_base_url,
                )
                print("🧠 ACE: playbook + Reflector/Curator initialized")
            except Exception as e:
                print(f"⚠️  ACE: could not init Reflector/Curator ({e}), will run with playbook only")

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
            self.result_method
        )
        
        if self.save_gif:
            os.makedirs(self.gif_dir, exist_ok=True)

    def _get_gif_path(self, iteration: int) -> str:
        """Get GIF file path for current iteration"""
        task_label = self.mutated_task_name if self.is_mutated_task and self.mutated_task_name else "raw"
        # task_label is often "source_to_target" for cross-mutation
        filename = f"{self.context}_{task_label}_iter_{iteration}.gif"
        return os.path.join(self.gif_dir, filename)

    def _get_training_log_dir(self):
        """Return directory for Parameter_Policy training logs: scripts/training_log/{category}/{task}/{model}/{method}/"""
        model_id = get_model_identifier(self.solver.model_type, self.solver.model_name)
        return get_training_log_dir(self.task_name, model_id, self.method)

    def _compose_feedback(self, metrics, score, success, failed, failure_reason, iteration, error, include_suggestions=False):
        granular_snapshots = (metrics or {}).get("granular_snapshots", [])
        g = (self.granularity or "outcome-based")
        if g != "outcome-based" and not granular_snapshots:
            import re as _re
            m = _re.fullmatch(r"process_(\d+)", g.strip().lower())
            n = int(m.group(1)) if m else 1
            if n > 1:
                effective_max_steps = int((metrics or {}).get("step_count") or self.max_steps or 1)
                effective_max_steps = max(1, effective_max_steps)
                granular_snapshots = []
                for i in range(1, n + 1):
                    step_i = int(round((i * effective_max_steps) / n))
                    step_i = max(1, min(effective_max_steps, step_i))
                    granular_snapshots.append({
                        "moment_index": i,
                        "total_moments": n,
                        "step_count": step_i,
                        "max_steps": effective_max_steps,
                        "metrics": dict(metrics or {}),
                        "score": score,
                        "success": success,
                        "failed": failed,
                        "failure_reason": failure_reason,
                        "error": error,
                    })

        if g != "outcome-based" and granular_snapshots:
            entries = []
            total = int(granular_snapshots[0].get("total_moments", len(granular_snapshots)))
            for idx, snap in enumerate(granular_snapshots, start=1):
                entries.append({
                    "moment_index": int(snap.get("moment_index", idx)),
                    "total_moments": total,
                    "step_count": snap.get("step_count", 0),
                    "max_steps": snap.get("max_steps", self.max_steps),
                    "metrics": snap.get("metrics", {}),
                    "score": snap.get("score", 0.0),
                    "success": snap.get("success", False),
                    "failed": snap.get("failed", False),
                    "failure_reason": snap.get("failure_reason"),
                    "error": snap.get("error"),
                })
            return format_granular_feedback(
                entries,
                iteration=iteration,
                task_name=self.task_name,
                include_suggestions=include_suggestions,
            )
        return format_feedback(
            metrics,
            score,
            success,
            failed,
            failure_reason,
            iteration,
            error=error,
            task_name=self.task_name,
            include_suggestions=include_suggestions,
        )

    def _generate_reflection(self, code: str, feedback: str, iteration: int) -> str:
        """
        Call the reflection LLM to generate a diagnostic reflection after a failed iteration.
        Used by reflexion method; called from evaluate_cross_mutated.run_single_pair (and evaluate_mutated).
        """
        if getattr(self, 'reflect_solver', None) is None:
            return ''
        code_str = code if code else '(No code was generated - code generation failed)'
        reflection_prompt = format_reflection_prompt(
            self.task_prompt, code_str, feedback, iteration
        )
        try:
            print(f"🔄 Generating reflection (iteration {iteration})...")
            _, raw_output, _ = self.reflect_solver.generate_code(reflection_prompt)
            reflection = (raw_output or '').strip()
            max_reflection_len = 1000
            if len(reflection) > max_reflection_len:
                reflection = reflection[:max_reflection_len] + '...'
            print(f"💭 Reflection (iteration {iteration}): {reflection[:200]}...")
            return reflection
        except Exception as e:
            print(f"⚠️  Failed to generate reflection: {e}")
            return f"(Reflection generation failed: {str(e)})"

    def _seal_ttt_step(self):
        """SEAL: collect positive-score solutions from iteration_history and run TTT (train_on_solutions)."""
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
                training_log_dir = self._get_training_log_dir()
                self.solver.train_on_solutions(
                    solutions,
                    training_log_dir=training_log_dir,
                    max_iterations=self.max_iterations,
                    max_steps_verifier=self.max_steps,
                )
            except Exception as exc:
                if is_cuda_oom(exc):
                    print(f"🛑 SEAL TTT failed with CUDA OOM (fatal): {exc}")
                    raise SystemExit(1) from exc
                print(f"⚠️  SEAL TTT training failed: {exc}")
                import traceback
                traceback.print_exc()
        else:
            print("🔧 SEAL: no positive-score solutions yet, skipping TTT")
            # Write a minimal "skipped" log once so training_log/{...}/seal/ exists and run can be verified
            try:
                training_log_dir = self._get_training_log_dir()
                summary_path = os.path.join(training_log_dir, "training_summary.txt")
                if not os.path.exists(summary_path):
                    from methods.Parameter_Policy.common.training_logger import TrainingLogger
                    logger = TrainingLogger(
                        training_log_dir, method_name="seal", task_name=self.task_name or "",
                        max_iterations=self.max_iterations, max_steps_verifier=self.max_steps,
                    )
                    logger.log_config(
                        prompt_format="format_initial_prompt / format_revision_prompt (or format_mutated_* for cross-mutation)",
                        n_solutions=0,
                    )
                    logger.log_warning("TTT skipped: no positive-score solutions in iteration_history yet.")
                    logger.finalize({"skipped": True, "reason": "no positive-score solutions"})
            except Exception as e:
                print(f"🔧 SEAL: could not write skipped log: {e}")

    def evaluate(self):
        """Run iterative evaluation process"""
        print(f"🚀 Starting evaluation for task: {self.task_name}")
        print(f"Method: {self.method}, Context: {self.context}, Max Iterations: {self.max_iterations}")
        
        # ThetaEvolve: run official ThetaEvolve train.py via run_single_task (from-scratch and single task-stage)
        if self.base_method == 'theta_evolve':
            if self.solver.model_type != 'local':
                raise ValueError("theta_evolve only supports --model-type local")
            # TaskEvaluator always builds SolverInterface (vLLM) for local models; ThetaEvolve train.py
            # colocates Megatron+SGLang on the same GPU(s). Drop vLLM first or the subprocess OOMs.
            _cleanup = getattr(self.solver, "cleanup", None)
            if callable(_cleanup):
                print("[theta_evolve] Releasing evaluation vLLM before ThetaEvolve (Megatron+SGLang need VRAM)...")
                _cleanup()
            from methods.Parameter_Policy.theta_evolve import run_single_task as theta_evolve_run_single_task
            scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            out_dir = self.output_dir or get_evaluation_results_dir()
            training_log_dir = self._get_training_log_dir()
            _exit_code, report = theta_evolve_run_single_task(
                task_name=self.task_name,
                run_number=1,
                model_type=self.solver.model_type,
                model_name=self.solver.model_name,
                context=self.context,
                max_steps=self.max_steps,
                scripts_dir=scripts_dir,
                output_dir=out_dir,
                gif_base_dir=get_gif_base_dir(),
                initial_code=None,
                model_path=getattr(self.solver, 'model_path', None),
                device=getattr(self.solver, 'device', None),
                env_overrides=self.env_overrides or {},
                theta_evolve_num_rollout=self.theta_evolve_num_rollout,
                theta_evolve_rollout_batch_size=self.theta_evolve_rollout_batch_size,
                training_log_dir=training_log_dir,
            )
            report['iterations'] = len(report.get('iteration_history', []))
            return report

        current_code = None
        
        # Reset solver conversation for new task
        self.solver.reset_conversation()
        
        # RAGEN: run per-task pretrain (rollout + GRPO + PPO) once, then evaluate with tuned LoRA
        if self.base_method == 'ragen':
            try:
                print("[RAGEN] Running per-task pretrain (rollout + GRPO + PPO-clip)...")
                self._ragen_pretrain_stats = self.solver.run_pretrain(
                    task_prompt=self.task_prompt,
                    verifier=self.verifier,
                    training_log_dir=self._get_training_log_dir(),
                    max_iterations=self.max_iterations,
                    max_steps_verifier=self.max_steps,
                )
                print(f"[RAGEN] Pretrain complete: {self._ragen_pretrain_stats}")
            except Exception as exc:
                if is_cuda_oom(exc):
                    print(f"🛑 [RAGEN] CUDA OOM during pretrain (fatal): {exc}")
                    raise SystemExit(1) from exc
                print(f"[RAGEN] Pretrain failed: {exc}")
                import traceback
                traceback.print_exc()
                self._ragen_pretrain_stats = {"error": str(exc)}
        # Discover: run per-task pretrain (TTT) once, then evaluate with tuned LoRA
        elif self.base_method == 'discover':
            try:
                print("[Discover] Running per-task pretrain (rollout + advantage + LoRA update)...")
                self._discover_pretrain_stats = self.solver.run_pretrain(
                    task_prompt=self.task_prompt,
                    verifier=self.verifier,
                    training_log_dir=self._get_training_log_dir(),
                    max_iterations=self.max_iterations,
                    max_steps_verifier=self.max_steps,
                )
                print(f"[Discover] Pretrain complete: {self._discover_pretrain_stats}")
            except Exception as exc:
                if is_cuda_oom(exc):
                    print(f"🛑 [Discover] CUDA OOM during pretrain (fatal): {exc}")
                    raise SystemExit(1) from exc
                print(f"[Discover] Pretrain failed: {exc}")
                import traceback
                traceback.print_exc()
                self._discover_pretrain_stats = {"error": str(exc)}
        # SOAR: run full multi-generation loop (search + SFT per gen), then use result (skip normal loop)
        elif self.base_method == 'soar':
            try:
                print("[SOAR] Running full SOAR (generations × search + SFT)...")
                self._soar_pretrain_stats = self.solver.run_pretrain(
                    task_prompt=self.task_prompt,
                    verifier=self.verifier,
                    max_iterations=self.max_iterations,
                    task_name=self.task_name,
                    training_log_dir=self._get_training_log_dir(),
                    max_steps_verifier=self.max_steps,
                )
                if self._soar_pretrain_stats.get("iteration_history") is not None:
                    self.iteration_history = self._soar_pretrain_stats["iteration_history"]
                    self.best_score = self._soar_pretrain_stats.get("best_score", -1.0)
                    self.best_code = self._soar_pretrain_stats.get("best_code")
                    self.best_metrics = self._soar_pretrain_stats.get("best_metrics", {})
                    self._stop_reason = self._soar_pretrain_stats.get("stop_reason", "exhausted")
                    if self.best_score >= 100.0:
                        self._stop_reason = "success"
                    print(f"[SOAR] Complete: best_score={self.best_score:.1f}, generations={self._soar_pretrain_stats.get('soar_generations')}, sft_runs={self._soar_pretrain_stats.get('soar_sft_runs')}")
                    return self._generate_report()
                self._soar_pretrain_stats["error"] = "run_pretrain returned no iteration_history"
            except Exception as exc:
                if is_cuda_oom(exc):
                    print(f"🛑 [SOAR] CUDA OOM during run_pretrain (fatal): {exc}")
                    raise SystemExit(1) from exc
                print(f"[SOAR] run_pretrain failed: {exc}")
                import traceback
                traceback.print_exc()
                self._soar_pretrain_stats = {"error": str(exc)}
            # No fallback: return report with error instead of running baseline loop
            return self._generate_report()

        # Special case for context='all': include task info in system prompt if needed
        if self.context == 'all':
            sys_prompt = format_system_prompt_with_task(self.task_prompt)
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
                if self.base_method == 'ace' and getattr(self, '_ace_playbook', None):
                    prompt = prompt + "\n\n## Current Playbook\n\n" + (self._ace_playbook or "")
            else:
                last_feedback = self.iteration_history[-1]['feedback']
                # When context='all', use best_score_plus_previous (same as evaluation_backup/evaluate.py)
                effective_context = 'best_score_plus_previous' if self.context == 'all' else self.context
                if effective_context == 'best_score_plus_previous':
                    best_item = None
                    best_score = -1.0
                    best_iteration = None
                    for item in self.iteration_history:
                        sc = item.get('score', 0.0)
                        if sc > best_score:
                            best_score = sc
                            best_item = item
                            best_iteration = item.get('iteration')
                    prev_item = self.iteration_history[-1] if self.iteration_history else None
                    prev_iteration = prev_item.get('iteration') if prev_item else None
                    prev_code = prev_item.get('code', '') if prev_item else ''
                    prev_feedback = prev_item.get('feedback', '') if prev_item else ''
                    cur_iteration = iteration
                    memory_block = None
                    if self.base_method == 'rememberer' and (getattr(self, '_rememberer_items', None) or getattr(self, '_rememberer_candidates', None)):
                        from methods.Memory.rememberer_method import retrieve_for_prompt as rememberer_retrieve
                        memory_block = rememberer_retrieve(
                            self.task_prompt, last_feedback,
                            getattr(self, '_rememberer_items', []),
                            getattr(self, '_rememberer_candidates', []),
                        )
                    elif self.base_method == 'reasoning_bank':
                        from methods.Memory.reasoning_bank_method import retrieve_for_prompt as reasoning_bank_retrieve
                        bank_items = getattr(self, '_reasoning_bank_items', []) or []
                        memory_block = reasoning_bank_retrieve(
                            self.task_prompt, last_feedback, bank_items,
                        )
                    elif self.base_method == 'memento_nonparametric' and (getattr(self, '_memento_items', None) or getattr(self, '_memento_pairs', None)):
                        from methods.Memory.memento_nonparametric_method import retrieve_for_prompt as memento_retrieve
                        memory_block = memento_retrieve(
                            self.task_prompt, last_feedback,
                            getattr(self, '_memento_items', []),
                            getattr(self, '_memento_pairs', []),
                        )
                    elif self.base_method == 'a_mem_sys' and getattr(self, '_a_mem_sys_memory', None):
                        from methods.Memory.a_mem_sys_method import retrieve_for_prompt as a_mem_sys_retrieve
                        memory_block = a_mem_sys_retrieve(
                            self.task_prompt, last_feedback, self._a_mem_sys_memory,
                        )
                    elif self.base_method == 'ace' and getattr(self, '_ace_playbook', None):
                        memory_block = "\n\n## Current Playbook\n\n" + (self._ace_playbook or "")
                    if best_item and best_item.get('code') and prev_code:
                        best_code = best_item.get('code', '')
                        best_feedback = best_item.get('feedback', '')
                        if best_iteration == prev_iteration:
                            prompt = format_revision_prompt_best_plus_previous(
                                self.task_prompt, best_code, best_feedback,
                                '', '', last_feedback, best_iteration, prev_iteration, cur_iteration,
                                memory_block=memory_block,
                            )
                        else:
                            prompt = format_revision_prompt_best_plus_previous(
                                self.task_prompt, best_code, best_feedback,
                                prev_code, prev_feedback, last_feedback, best_iteration, prev_iteration, cur_iteration,
                                memory_block=memory_block,
                            )
                    elif prev_code:
                        prompt = format_revision_prompt(self.task_prompt, prev_code, last_feedback)
                        if memory_block:
                            prompt = prompt + "\n\n---\n## Relevant experience from memory\n\n" + memory_block + "\n\nProvide an improved solution."
                    else:
                        prompt = format_initial_prompt(self.task_prompt)
                elif self.context == 'previous':
                    prompt = format_revision_prompt(self.task_prompt, current_code, last_feedback)
                else:
                    prompt = format_revision_prompt(self.task_prompt, current_code, last_feedback)
            # ExpeL: append retrieved rules + trajectories every iteration (evaluation_backup parity)
            if self.base_method == "expel":
                from methods.Memory.expel_method import retrieve_for_prompt as expel_retrieve
                last_fb = (
                    (self.iteration_history[-1].get("feedback", "") if self.iteration_history else "")
                    or ""
                )
                _pair_expel = bool(self.source_env)
                expel_mem = expel_retrieve(
                    self.task_prompt,
                    last_fb,
                    getattr(self, "_expel_items", []),
                    getattr(self, "_expel_rules", []),
                    getattr(self, "_expel_embedder"),
                    top_k_rules=8,
                    top_k_trajectories=0 if _pair_expel else 3,
                    rules_only=_pair_expel,
                )
                if _pair_expel:
                    expel_suffix = "\n\n---\n\n## ExpeL insights (distilled rules from your rollout)\n\n"
                else:
                    expel_suffix = "\n\n---\n\n## ExpeL: insights + related trajectories\n\n"
                expel_suffix += (expel_mem.strip() or "(No relevant insights yet.)") + "\n\n"
                prompt = prompt + expel_suffix
            # ACE (official): ask model to output bullet_ids + code so Reflector gets bullets_used
            if self.base_method == 'ace' and getattr(self, '_ace_playbook', None):
                from methods.Memory.ace_method import get_playbook_bullet_ids
                ids = get_playbook_bullet_ids(self._ace_playbook)
                prompt = prompt + "\n\n**Output format (ACE):** When you use playbook strategies, cite their bullet IDs. Prefer a JSON block: {\"bullet_ids\": [\"id1\", ...], \"code\": \"...\"}. Available bullet IDs: " + (", ".join(ids) if ids else "(none yet)") + "\n"
            
            _reasoning_bank_matts_done = False
            if self.base_method == 'reasoning_bank' and getattr(self, 'reasoning_bank_k', 1) > 1:
                # MaTTS (paper-aligned): K parallel trajectories, then contrast_and_distill, pick best
                from methods.Memory.reasoning_bank_method import contrast_and_distill, store_after_iteration
                k = self.reasoning_bank_k
                codes_and_outputs = []
                for _ in range(k):
                    try:
                        nc, raw, tok = self.solver.generate_code(prompt, use_conversation=False)
                        if nc:
                            codes_and_outputs.append((nc, raw or "", tok or {}))
                    except Exception:
                        pass
                if not codes_and_outputs:
                    try:
                        new_code, raw_output, token_usage = self.solver.generate_code(prompt, use_conversation=False)
                        if new_code:
                            current_code = new_code
                    except Exception as e:
                        self._stop_reason = 'error_generating_code'
                        self._stop_error = str(e)
                        print(f"❌ Error generating code: {e}")
                        break
                else:
                    trajectories = []
                    for (code, raw, tok) in codes_and_outputs:
                        succ, sc, met, err = self.verifier.verify_code(
                            code, headless=self.headless,
                            save_gif_path=None,
                        )
                        fb = format_feedback(met, sc, succ, met.get('failed', False), met.get('failure_reason', ''),
                                             codes_and_outputs.index((code, raw, tok)) + 1, error=err, task_name=self.task_name)
                        trajectories.append({
                            "code": code, "feedback": fb, "score": sc, "success": succ,
                            "metrics": met, "error": err, "raw_output": raw, "token_usage": tok,
                        })
                    task_desc = (self.task_prompt.get("task_description") or "") if isinstance(self.task_prompt, dict) else str(self.task_prompt)
                    new_items = contrast_and_distill(
                        trajectories, task_desc,
                        api_key=self._llm_aux_api_key,
                        base_url=self._llm_aux_base_url,
                        judge_model=os.environ.get("REASONING_BANK_INDUCE_MODEL", "deepseek-v3.2"),
                        use_llm_judge=False,
                    )
                    if new_items and getattr(self, '_reasoning_bank_path', None):
                        self._reasoning_bank_items = store_after_iteration(
                            self._reasoning_bank_path, self._reasoning_bank_items, new_items,
                        )
                        self._last_reasoning_bank_stored = new_items
                    else:
                        self._last_reasoning_bank_stored = []
                    best_t = max(trajectories, key=lambda t: (t["success"], t["score"]))
                    current_code = best_t["code"]
                    raw_output = best_t.get("raw_output", "")
                    token_usage = best_t.get("token_usage", {})
                    success = best_t["success"]
                    score = best_t["score"]
                    metrics = best_t["metrics"]
                    error = best_t["error"]
                    feedback = format_feedback(
                        metrics, score, success, metrics.get('failed', False),
                        metrics.get('failure_reason', ''), iteration, error=error, task_name=self.task_name,
                    )
                    gif_path = None  # MaTTS did not save a single gif for the chosen best
                    _reasoning_bank_matts_done = True
            if not _reasoning_bank_matts_done:
                try:
                    # When context='all' we use best_score_plus_previous (prompt is self-contained: best + previous), so no conversation buffer
                    use_conversation = False
                    new_code, raw_output, token_usage = self.solver.generate_code(
                        prompt,
                        use_conversation=use_conversation
                    )
                    if new_code:
                        current_code = new_code
                except Exception as e:
                    if is_cuda_oom(e) and self.base_method in ("seal", "ragen", "soar", "discover", "genome", "absolute_zero_iter", "theta_evolve"):
                        print(f"🛑 CUDA OOM during Parameter_Policy generation (fatal): {e}")
                        raise SystemExit(1) from e
                    self._stop_reason = 'error_generating_code'
                    self._stop_error = str(e)
                    print(f"❌ Error generating code: {e}")
                    break
                
            # 2. Verify code (skip if MaTTS already ran verify for all K)
            if not _reasoning_bank_matts_done:
                if self.mutated_task_name:
                    gif_path = self._get_gif_path(iteration)
                else:
                    gif_path = get_gif_path(self.gif_dir, self.context, iteration)
                success, score, metrics, error = self.verifier.verify_code(
                    current_code, 
                    headless=self.headless,
                    save_gif_path=gif_path if self.save_gif else None,
                    granularity=self.granularity,
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
            feedback = self._compose_feedback(
                metrics, score, success, failed, failure_reason, iteration, error
            )
            
            # 4. Record iteration
            hist_entry = {
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
            }
            if _reasoning_bank_matts_done and getattr(self, '_last_reasoning_bank_stored', None):
                hist_entry["reasoning_bank_stored_items"] = self._last_reasoning_bank_stored
            self.iteration_history.append(hist_entry)
            # ReasoningBank: after each iteration, extract memory items and append to bank (single trajectory; MaTTS already stored above)
            if self.base_method == 'reasoning_bank' and getattr(self, '_reasoning_bank_path', None) and not _reasoning_bank_matts_done:
                try:
                    from methods.Memory.reasoning_bank_method import (
                        extract_memory_items_llm, store_after_iteration, judge_success_llm,
                    )
                    task_desc = (self.task_prompt.get("task_description") or "") if isinstance(self.task_prompt, dict) else str(self.task_prompt)
                    if os.environ.get("REASONING_BANK_LLM_JUDGE", "").lower() in ("1", "true", "yes"):
                        success_for_memory = judge_success_llm(
                            task_desc, current_code, feedback, score,
                            api_key=self._llm_aux_api_key,
                            base_url=self._llm_aux_base_url,
                        )
                    else:
                        success_for_memory = bool(success)
                    new_items = extract_memory_items_llm(
                        task_desc, current_code, feedback, score, success_for_memory,
                        api_key=self._llm_aux_api_key,
                        base_url=self._llm_aux_base_url,
                        raw_reasoning=(raw_output or None),
                    )
                    if new_items:
                        self._reasoning_bank_items = store_after_iteration(
                            self._reasoning_bank_path, self._reasoning_bank_items, new_items,
                        )
                        hist_entry["reasoning_bank_stored_items"] = new_items
                except Exception as e:
                    print(f"⚠️  ReasoningBank store after iter failed (non-fatal): {e}", flush=True)
            # Memento non-parametric: append this attempt to memory JSONL and reload for next iteration
            if self.base_method == 'memento_nonparametric' and getattr(self, '_memento_memory_path', None):
                try:
                    from methods.Memory.memento_nonparametric_method import store_after_iteration as memento_store, load_memory
                    task_desc = (self.task_prompt.get("task_description") or "") if isinstance(self.task_prompt, dict) else str(self.task_prompt)
                    entry = memento_store(
                        self.task_name, iteration, score, feedback, current_code,
                        self._memento_memory_path, task_desc, success=success,
                        base_task_name=getattr(self, 'base_task_name_for_memory', None),
                    )
                    hist_entry["memory_stored_entry"] = entry
                    self._memento_items, self._memento_pairs = load_memory(self._memento_memory_path)
                except Exception as e:
                    print(f"⚠️  Memento store after iter failed (non-fatal): {e}", flush=True)
            # A-mem-sys: store this attempt in memory system
            if self.base_method == 'a_mem_sys' and getattr(self, '_a_mem_sys_memory', None):
                try:
                    from methods.Memory.a_mem_sys_method import store_after_iteration as a_mem_sys_store
                    stored = a_mem_sys_store(
                        self.task_name, iteration, score, feedback, current_code,
                        self._a_mem_sys_memory,
                    )
                    hist_entry["a_mem_sys_stored"] = stored[:200] + "..." if len(stored) > 200 else stored
                except Exception as e:
                    print(f"⚠️  A-mem-sys store after iter failed (non-fatal): {e}", flush=True)
            # ACE: reflect then curator update playbook for next iteration (official: bullets_used from generator output)
            if self.base_method == 'ace' and getattr(self, '_ace_reflector', None) and getattr(self, '_ace_curator', None):
                try:
                    from methods.Memory.ace_method import (
                        reflect_on_iteration, update_playbook_after_iteration,
                        parse_bullet_ids_from_output, extract_playbook_bullets,
                    )
                    task_desc = (self.task_prompt.get("task_description") or "") if isinstance(self.task_prompt, dict) else str(self.task_prompt)
                    raw_out = hist_entry.get("raw_llm_output") or ""
                    bullet_ids = parse_bullet_ids_from_output(raw_out)
                    bullets_used = extract_playbook_bullets(self._ace_playbook or "", bullet_ids) if bullet_ids else "(No bullets used by generator)"
                    reflection_content, bullet_tags, _ = reflect_on_iteration(
                        self._ace_reflector,
                        question=task_desc,
                        reasoning_trace=current_code or "",
                        predicted_answer=current_code or "",
                        environment_feedback=feedback,
                        bullets_used=bullets_used,
                    )
                    self._ace_playbook, self._ace_next_global_id = update_playbook_after_iteration(
                        self._ace_playbook or "",
                        reflection_content,
                        question_context=task_desc,
                        iteration=iteration,
                        max_iterations=self.max_iterations,
                        token_budget=8000,
                        curator=self._ace_curator,
                        bullet_tags=bullet_tags,
                        next_global_id=self._ace_next_global_id,
                    )
                    hist_entry["ace_reflection_len"] = len(reflection_content)
                except Exception as e:
                    print(f"⚠️  ACE reflect/curate after iter failed (non-fatal): {e}", flush=True)
            
            # 5. Update best
            if score > self.best_score:
                self.best_score = score
                self.best_code = current_code
                self.best_metrics = metrics
                print(f"🎯 New best score: {score:.1f}/100")
            
            # 6. SEAL TTT: after each iteration, train LoRA on accumulated positive-score solutions
            if self.method == 'seal':
                self._seal_ttt_step()
            
            if success:
                self._stop_reason = 'success'
                print(f"✅ Task solved in {iteration} iterations!")
                break
                
        if self._stop_reason is None and len(self.iteration_history) < self.max_iterations:
            self._stop_reason = 'error_generating_code'
        return self._generate_report()

    def _generate_report(self):
        """Generate final evaluation report"""
        report = {
            'task_name': self.task_name,
            'method': self.result_method,
            'base_method': self.method,
            'granularity': self.granularity,
            'context': self.context,
            'success': self.best_score >= 100.0,
            'best_score': self.best_score,
            'best_code': self.best_code,
            'best_metrics': self.best_metrics,
            'iterations': len(self.iteration_history),
            'history': self.iteration_history
        }
        if self._stop_reason is not None:
            report['stop_reason'] = self._stop_reason
        if self._stop_error is not None:
            report['stop_error'] = self._stop_error
        if self.base_method == 'genome' and getattr(self, 'genome_best_lora_path', None):
            report['genome_best_lora_path'] = self.genome_best_lora_path
        if self.base_method == 'ragen':
            ragen_stats = getattr(self, '_ragen_pretrain_stats', {})
            report['ragen_skipped'] = ragen_stats.get('skipped', False)
            report['ragen_n_episodes'] = ragen_stats.get('n_episodes', 0)
            report['ragen_n_filtered'] = ragen_stats.get('n_filtered', 0)
            report['ragen_mean_reward'] = ragen_stats.get('mean_reward', 0.0)
            report['ragen_ppo_epochs'] = ragen_stats.get('ppo_epochs', 0)
        if self.base_method == 'discover':
            discover_stats = getattr(self, '_discover_pretrain_stats', {})
            report['discover_pretrain_epochs'] = discover_stats.get('n_epochs', 0)
            report['discover_mean_reward'] = discover_stats.get('mean_reward', 0.0)
            report['discover_expansion_rounds_used'] = discover_stats.get('expansion_rounds_used', 0)
            report['discover_expansion_total_trajectories'] = discover_stats.get('expansion_total_trajectories', 0)
            report['discover_train_steps_done'] = discover_stats.get('train_steps_done', 0)
        if self.base_method == 'seal':
            stats = getattr(self.solver, 'get_token_statistics', lambda: {})()
            report['seal_ttt_train_count'] = stats.get('seal_train_count', 0)
        if self.base_method == 'soar':
            soar_stats = getattr(self, '_soar_pretrain_stats', {})
            report['soar_generations'] = soar_stats.get('soar_generations', 0)
            report['soar_sft_runs'] = soar_stats.get('soar_sft_runs', 0)
            if 'error' in soar_stats:
                report['soar_error'] = soar_stats['error']
        if self.base_method == 'ace' and getattr(self, '_ace_playbook', None):
            report['final_playbook'] = self._ace_playbook
        if self.base_method == 'reasoning_bank':
            report['reasoning_bank_k'] = getattr(self, 'reasoning_bank_k', 2)
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
        task_dir = os.path.join(output_dir, cat_dir, task_subdir, model_id, self.result_method)
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

    # For non-default granularity, persist results under method_granularity.
    effective_method = getattr(args, "result_method", None) or get_effective_result_method(
        args.method, getattr(args, "granularity", "outcome-based")
    )

    # Check if complete
    if getattr(args, "skip_complete", True) and run_is_complete(
        task_name=task_name,
        model_type=args.model_type,
        model_name=args.model_name,
        method=effective_method,
        context=args.context,
        mutated_task_name=current_mutated_name
    ):
        pair_label = f" [{current_mutated_name}]" if current_mutated_name else ""
        print(f"✅ Task {task_name}{pair_label}: Already complete. Skipping.")
        return 0

    # Determine task-specific max_steps
    if args.max_steps == 10000: # If at default, use task-specific default
        max_steps = get_max_steps_for_task(task_name)
    else:
        max_steps = args.max_steps

    base_method = args.method[:-3] if args.method.endswith('_CE') else args.method

    # ExpeL: pair eval (source_env × target_env) = same as Rememberer — only
    # expel/.../{task}__{source_env}.json + optional pair .insights.json from evaluation_results_scratch.
    # Non-pair category eval still uses category-wide rollouts + category insights.json.
    if base_method == "expel":
        from evaluation.utils import get_model_identifier
        _expel_mid = get_model_identifier(args.model_type, args.model_name)
        _expel_dev = getattr(args, "device", None) or (
            "cpu" if args.model_type == "openai" else "cuda:0"
        )
        if args.model_type == "mock":
            print("[ExpeL] mock mode: skipping memory prep.", flush=True)
        elif getattr(args, "source_env", None) and getattr(args, "target_env", None):
            from methods.Memory.expel_method import ensure_expel_data_from_scratch
            from evaluation.solver_interface import get_aux_llm_credentials

            _ek, _eu = get_aux_llm_credentials(args.api_key)
            ensure_expel_data_from_scratch(
                task_name,
                args.source_env,
                _expel_mid,
                api_key=_ek,
                base_url=_eu,
                insight_model=os.environ.get("EXPEL_INSIGHT_MODEL"),
            )
        else:
            from methods.Memory.expel_method import ensure_expel_data

            ensure_expel_data(
                [task_name],
                _expel_mid,
                model_type=args.model_type,
                model_name=args.model_name,
                max_iterations=20,
                context=getattr(args, "context", "all"),
                model_path=getattr(args, "model_path", None),
                api_key=getattr(args, "api_key", None),
                device=_expel_dev,
                max_steps=max_steps,
                expel_max_rounds=getattr(args, "expel_max_rounds", None),
                expel_max_num_rules=getattr(args, "expel_max_num_rules", None),
            )

    # GENOME: resolve genome_best_lora_path from cache or Phase 1 when not provided
    genome_best_lora_path = getattr(args, 'genome_best_lora_path', None)
    if base_method == 'genome' and not genome_best_lora_path and args.model_type == 'local':
        from evaluation.utils import get_model_identifier, get_training_log_dir
        from methods.Parameter_Policy.genome import get_genome_experts_dir, get_genome_cache_path
        from methods.Parameter_Policy.genome.genome_method import run_genome_phase1
        model_identifier = get_model_identifier(args.model_type, args.model_name)
        lora_dir = get_genome_experts_dir()
        cache_path = get_genome_cache_path(task_name, model_identifier)
        training_log_dir = get_training_log_dir(task_name, model_identifier, "genome")
        genome_best_lora_path = run_genome_phase1(
            task_name=task_name,
            model_path=getattr(args, 'model_path', None) or args.model_name,
            lora_dir=lora_dir,
            cache_path=cache_path,
            device=getattr(args, 'device', 'auto'),
            max_steps=max_steps,
            population_size=getattr(args, 'genome_population_size', 10),
            genome_iters=getattr(args, 'genome_iters', 50),
            training_log_dir=training_log_dir,
        )

    # Execute evaluation
    try:
        is_category_task = task_name.startswith('category_')
        base_method = args.method[:-3] if args.method.endswith('_CE') else args.method
        # All methods use task-pair evaluation for category tasks (output: all_Initial_to_Stage-1.json etc.).
        is_mutation_capable = is_category_task
        
        if is_mutation_capable:
            from evaluation.evaluate_cross_mutated import run_cross_mutation_evaluation, run_single_pair, get_all_stages, get_reference_solution
            
            if getattr(args, 'source_env', None) and getattr(args, 'target_env', None):
                source_env = args.source_env
                target_env = args.target_env
                if source_env != "Initial":
                    print(
                        f"❌ Cross-mutation requires T0=Initial; got source_env={source_env!r}. "
                        f"Use --source-env Initial --target-env <Stage-N>."
                    )
                    return 1
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
                task_path, _ = parse_task_name(task_name)
                script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                task_dir = os.path.join(script_dir, 'tasks', task_path)
                stages_file = os.path.join(task_dir, 'stages.py')
                
                update_desc_func = None
                update_criteria_func = None
                if os.path.exists(stages_file):
                    stages_mod = load_task_stages_module(stages_file)
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
                target_physics = env_j.get("physics_config", {})
                base_physics = env_i.get("physics_config", {})

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
                    
                if args.method.endswith('_CE'):
                    suffix = f'## Environmental Anomalies Detected\n + "terrain_config": {json.dumps(target_terrain)}, \n"physics_config": {json.dumps(env_j.get("physics_config", {}))}'
                else:
                    suffix = env_j.get("task_description_suffix", "")
                    
                task_prompt_override["task_description"] = desc
                task_prompt_override["success_criteria"] = criteria
                if suffix:
                    task_prompt_override["prompt_trailer"] = suffix
                else:
                    task_prompt_override.pop("prompt_trailer", None)
                
                # Same evaluation as test_reference_solutions: get_all_stages(), get_max_steps_for_task(), env_overrides from stage only; run_single_pair sets random.seed(123) for non-C_02.
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
                    save_gif=args.save_gif,
                    source_env=source_env,
                    result_method=effective_method,
                    granularity=getattr(args, "granularity", "outcome-based"),
                    model_path=getattr(args, 'model_path', None),
                    device=getattr(args, 'device', None),
                    reflect_model_name=getattr(args, 'reflect_model_name', None),
                    soar_generations=getattr(args, 'soar_generations', 2),
                    soar_k_candidates=getattr(args, 'soar_k_candidates', 4),
                    genome_best_lora_path=genome_best_lora_path,
                    theta_evolve_num_rollout=getattr(args, 'theta_evolve_num_rollout', None),
                    theta_evolve_rollout_batch_size=getattr(args, 'theta_evolve_rollout_batch_size', None),
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
                    result_method=effective_method,
                    granularity=getattr(args, "granularity", "outcome-based"),
                    context=args.context,
                    max_iterations=args.max_iterations,
                    max_steps=max_steps,
                    headless=True,
                    api_key=args.api_key,
                    output_dir='evaluation_results',
                    save_gif=args.save_gif,
                    reflect_model_name=getattr(args, 'reflect_model_name', None),
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
                save_gif=args.save_gif,
                result_method=effective_method,
                granularity=getattr(args, "granularity", "outcome-based"),
                soar_generations=getattr(args, 'soar_generations', 2),
                soar_k_candidates=getattr(args, 'soar_k_candidates', 4),
                genome_best_lora_path=genome_best_lora_path,
                model_path=getattr(args, 'model_path', None),
                device=getattr(args, 'device', None),
                theta_evolve_num_rollout=getattr(args, 'theta_evolve_num_rollout', None),
                theta_evolve_rollout_batch_size=getattr(args, 'theta_evolve_rollout_batch_size', None),
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
    parser.add_argument('--method', type=str, default='baseline')
    parser.add_argument('--context', type=str, default='all',
                       choices=['previous', 'all', 'last_3', 'best_score', 'best_score_plus_previous'])
    parser.add_argument('--source-env', type=str, default=None)
    parser.add_argument('--target-env', type=str, default=None)
    parser.add_argument('--save-gif', action='store_true', default=True, help='Save GIF animations of simulations')
    parser.add_argument('--no-save-gif', action='store_false', dest='save_gif', help='Disable saving GIF animations')
    parser.add_argument(
        '--skip-complete', action='store_true', default=True, dest='skip_complete',
        help='Skip task/pair if a result JSON already exists (default: on).',
    )
    parser.add_argument(
        '--no-skip-complete', action='store_false', dest='skip_complete',
        help='Re-run even when a result JSON already exists.',
    )
    parser.add_argument('--soar-generations', type=int, default=2, dest='soar_generations', help='SOAR: number of generations (search+SFT)')
    parser.add_argument('--soar-k-candidates', type=int, default=4, dest='soar_k_candidates', help='SOAR: candidates per first iteration')
    parser.add_argument('--genome-best-lora-path', type=str, default=None, dest='genome_best_lora_path',
                        help='GENOME: path to Phase 1 best LoRA. If omitted, resolved from cache or run Phase 1 once.')
    parser.add_argument('--reflect-model-name', type=str, default=None, dest='reflect_model_name',
                        help='Reflexion: model name for reflection LLM (API only). Default: deepseek-v3.2.')
    parser.add_argument('--expel-max-rounds', type=int, default=None, dest='expel_max_rounds',
                        help='ExpeL: insight extraction rounds when category insights.json is built (default: 3 in expel_method).')
    parser.add_argument('--expel-max-num-rules', type=int, default=None, dest='expel_max_num_rules',
                        help='ExpeL: max rules when building category insights.json.')
    parser.add_argument(
        '--theta-evolve-num-rollout', type=int, default=10000, dest='theta_evolve_num_rollout',
        help='ThetaEvolve: num_rollout passed to slime train (default 10000; use a small value e.g. 12 for smoke tests).',
    )
    parser.add_argument(
        '--theta-evolve-rollout-batch-size', type=int, default=32, dest='theta_evolve_rollout_batch_size',
        help='ThetaEvolve: rollout_batch_size (default 32).',
    )
    parser.add_argument(
        '--granularity',
        type=str,
        default='outcome-based',
        help="Feedback granularity: outcome-based (default) or process_n (e.g., process_3, process_5).",
    )
    parser.add_argument(
        '--result-method',
        type=str,
        default=None,
        dest='result_method',
        help='Optional output method name used only for result directory naming.',
    )

    args = parser.parse_args()
    g = (args.granularity or "outcome-based").strip().lower()
    if g != "outcome-based":
        import re as _re
        m = _re.fullmatch(r"process_(\d+)", g)
        if not m or int(m.group(1)) <= 0:
            raise ValueError(f"Invalid --granularity: {args.granularity}. Use outcome-based or process_n (n>=1).")
    args.granularity = g
    if not getattr(args, "result_method", None):
        args.result_method = get_effective_result_method(args.method, args.granularity)

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