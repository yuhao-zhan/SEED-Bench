"""
SOAR (Self-improving Operators for Automated program Refinements)
Test-time evolutionary search + SFT self-improvement for 2D exploration tasks.

Adapted from DaVinciBench/baseline/Parameter_Policy/SOAR/
Paper: "Self-Improving Language Models for Evolutionary Program Synthesis"
       (Pourcel et al., ICML 2025, arXiv 2507.14172)

Algorithm (per task, per generation g = 1..G):
  1. SEARCH:  Run 20-iter episode with K candidates per iteration.
             Best-of-K selection (adapted majority voting for continuous scores).
             REX Thompson sampling to select past solutions as refinement context.
  2. LEARN:   Build training data from accumulated archive:
             - Sampling data: (prompt, good_code) via greedy-div strategy.
             - Repair data: (revision_prompt, improved_code) from improvement pairs.
             SFT fine-tune LoRA from base weights.
  3. IMPROVE: Next generation uses the improved model for search.

Key SOAR-specific features vs RAGEN/SEAL:
  - K candidates per iteration (test-time search, not single candidate).
  - REX Thompson sampling for exploration/exploitation balance in refinement.
  - SFT training (not RL) with dual data streams (sampling + repair).
  - Generational self-improvement loop (search → learn → better search).

References:
  - soar/inference/sample_phase.py  (K-candidate sampling)
  - soar/repair/rex.py              (REX Thompson sampling, C=20)
  - soar/training/train_unsloth.py  (SFT with LoRA r=256, alpha=32, lr=5e-5)
  - soar/post_process/process_sample_for_training.py  (greedy_div data selection)
  - soar/post_process/process_repair_for_training.py  (repair data by correctness)
  - soar/llm_utils.py               (majority voting, evaluation metrics)
"""

import os
import re
import gc
import sys
import copy
import math
import random
from typing import List, Optional, Dict, Tuple, Any, Callable

import numpy as np
import torch

from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    TrainerCallback,
)
from datasets import Dataset

# System prompt — identical to SolverInterface / SEALSolver / RAGENSolver.
SYSTEM_PROMPT = (
    "You are a physics-based agent designer for a 2D physics simulation.\n\n"
    "When given a task:\n"
    "1) FIRST: analyze the physical situation and reason about a design/strategy\n"
    "2) THEN: output the final implementation code\n\n"
    "Output requirements:\n"
    "- You MAY include analysis text BEFORE the code\n"
    "- You MUST include the code inside ONE fenced block: ```python ... ```\n"
    "- The code MUST define `build_agent(sandbox)` (return the main body)\n"
    "- Optionally define `agent_action(sandbox, agent_body, step_count)` for control\n"
    "- Do NOT include any text AFTER the code block"
)


# ---------------------------------------------------------------------------
# Utility: resolve local model paths
# ---------------------------------------------------------------------------
_LOCAL_MODEL_PREFIXES = [
    "/home/test/testdata/models/",
    os.path.expanduser("~/models/"),
]


def _resolve_model_path(model_name: str, model_path: Optional[str] = None) -> str:
    """Return the first existing path for *model_name*."""
    if model_path and os.path.exists(model_path):
        return model_path
    if os.path.exists(model_name):
        return model_name
    for prefix in _LOCAL_MODEL_PREFIXES:
        candidate = os.path.join(prefix, os.path.basename(model_name))
        if os.path.exists(candidate):
            return candidate
    return model_path or model_name


# ---------------------------------------------------------------------------
# Code extraction — mirrors solver_interface._extract_code
# ---------------------------------------------------------------------------
def _extract_code(raw_text: str) -> Optional[str]:
    """Extract Python code from raw LLM output."""
    if not raw_text:
        return None
    for marker in ("</think>", "</think>", "</think>"):
        pos = raw_text.find(marker)
        if pos >= 0:
            raw_text = raw_text[pos + len(marker):].strip()
            break
    code_block_pattern = r"```(?:python)?\s*\n?(.*?)```"
    matches = list(re.finditer(code_block_pattern, raw_text, re.DOTALL))
    if not matches:
        incomplete = re.search(r"```(?:python)?\s*\n?(.*)", raw_text, re.DOTALL)
        if incomplete:
            code = incomplete.group(1).strip()
            code = re.sub(r"```.*$", "", code, flags=re.DOTALL)
            if len(code.strip()) > 50:
                return code.strip()
        return None
    if len(matches) == 1:
        code = matches[0].group(1).strip()
    else:
        code = max(matches, key=lambda m: len(m.group(1).strip())).group(1).strip()
    code = re.sub(r"```(?:python)?", "", code)
    code = re.sub(r"```", "", code)
    return code.strip() or None


# ===========================================================================
# REX Thompson Sampling (from soar/repair/rex.py)
# ===========================================================================

def thompson_sample_score(score: float, n_selected: int, C: float = 20.0) -> float:
    """REX Thompson sampling: draw from Beta posterior given solution quality.

    Ref: soar/repair/rex.py  REX.thompson_sampling (lines 78-82)
    h = heuristic_train(response_dict) = mean(correct_train_input)
    theta ~ Beta(1 + C*h, 1 + C*(1-h) + N)

    For our continuous scores (0-100), h = score/100.

    Args:
        score:      Solution score (0-100).
        n_selected: Number of times this solution was selected (discount).
        C:          Thompson sampling concentration parameter.
    Returns:
        Sampled priority value (higher = more likely to be selected).
    """
    h = max(min(score / 100.0, 1.0), 0.0)
    alpha = 1.0 + C * h
    beta_param = 1.0 + C * (1.0 - h) + n_selected
    return np.random.beta(alpha, beta_param)


# ===========================================================================
# Training data selection (from soar/post_process/)
# ===========================================================================

def select_sampling_data_greedy_div(
    archive: List[Dict[str, Any]],
    max_samples: int = 50,
) -> List[Dict[str, Any]]:
    """Greedy-diverse data selection for SFT sampling training.

    Ref: soar/post_process/process_sample_for_training.py
         get_sample_task_greedy_div() — 50% top-quality + 50% diverse

    Args:
        archive:     List of archive entries with 'score', 'prompt', 'raw_output'.
        max_samples: Maximum training samples.
    Returns:
        Selected entries for sampling SFT.
    """
    valid = [e for e in archive if e.get("raw_output") and e.get("code")]
    if not valid:
        return []

    n_greedy = max_samples // 2
    n_diverse = max_samples - n_greedy

    # Greedy: top by score, then by shorter code
    sorted_by_quality = sorted(
        valid,
        key=lambda e: (-e.get("score", 0), len(e.get("code", ""))),
    )
    greedy = sorted_by_quality[:n_greedy]
    greedy_ids = {id(e) for e in greedy}

    # Diverse: remaining entries, prefer lower scores for diversity
    remaining = [e for e in valid if id(e) not in greedy_ids]
    # Categorize: zero (score=0), low (0, 34], medium (34, 98), high [98, 100]
    # Ref: process_sample_for_training.py greedy_div; process_repair_for_training.py uses 0, 0.34, 0.98
    zero = [e for e in remaining if e.get("score", 0) == 0]
    low = [e for e in remaining if 0 < e.get("score", 0) <= 34]
    medium = [e for e in remaining if 34 < e.get("score", 0) <= 98]
    high = [e for e in remaining if e.get("score", 0) > 98]

    diverse: List[Dict[str, Any]] = []
    for bucket in [zero, low, medium, high]:
        random.shuffle(bucket)
        diverse.extend(bucket)
        if len(diverse) >= n_diverse:
            break
    diverse = diverse[:n_diverse]

    result = greedy + diverse
    random.shuffle(result)
    return result[:max_samples]


def select_repair_data(
    archive: List[Dict[str, Any]],
    max_samples: int = 50,
) -> List[Dict[str, Any]]:
    """Select repair (refinement) training data from archive.

    For each pair of consecutive iterations where the child scores higher
    than the parent, create a repair training sample.

    Ref: soar/post_process/process_repair_for_training.py
         sampling_given_initial_correctness() — sample by parent correctness

    Returns list of dicts with 'parent_prompt', 'parent_code', 'parent_feedback',
    'child_raw_output', 'child_score', 'parent_score'.
    """
    # Group archive entries by generation, then sort by iteration
    by_gen: Dict[int, List[Dict]] = {}
    for entry in archive:
        gen = entry.get("generation", 0)
        by_gen.setdefault(gen, []).append(entry)

    pairs: List[Dict[str, Any]] = []
    for gen, entries in by_gen.items():
        sorted_entries = sorted(entries, key=lambda e: e.get("iteration", 0))
        for i in range(1, len(sorted_entries)):
            parent = sorted_entries[i - 1]
            child = sorted_entries[i]
            # Only keep improvement pairs (child score > parent score)
            if child.get("score", 0) > parent.get("score", 0):
                pairs.append({
                    "parent_prompt": parent.get("prompt", ""),
                    "parent_code": parent.get("code", ""),
                    "parent_feedback": parent.get("feedback", ""),
                    "parent_score": parent.get("score", 0),
                    "child_raw_output": child.get("raw_output", ""),
                    "child_code": child.get("code", ""),
                    "child_score": child.get("score", 0),
                    "child_prompt": child.get("prompt", ""),
                })

    if not pairs:
        return []

    # Sample by parent correctness category (SOAR: sampling_given_initial_correctness)
    # Ref: process_repair_for_training.py get_category_correctness — 0, 0.34, 0.98 (score/100 → 0, 34, 98)
    zero = [p for p in pairs if p["parent_score"] == 0]
    low = [p for p in pairs if 0 < p["parent_score"] <= 34]
    medium = [p for p in pairs if 34 < p["parent_score"] <= 98]
    high = [p for p in pairs if p["parent_score"] > 98]

    selected: List[Dict[str, Any]] = []
    per_cat = max(max_samples // 4, 1)
    for bucket in [zero, low, medium, high]:
        random.shuffle(bucket)
        selected.extend(bucket[:per_cat])

    # Fill remaining from all pairs
    remaining = max_samples - len(selected)
    if remaining > 0:
        selected_ids = {id(p) for p in selected}
        leftover = [p for p in pairs if id(p) not in selected_ids]
        random.shuffle(leftover)
        selected.extend(leftover[:remaining])

    random.shuffle(selected)
    return selected[:max_samples]


# ============================================================================
# SOARSolver — per-task evolutionary search + SFT self-improvement solver
# ============================================================================

class SOARSolver:
    """
    SOAR (Self-improving Operators for Automated program Refinements)
    Test-time evolutionary search solver for 2D exploration tasks.

    Lifecycle (managed by evaluate.py via _run_soar_evaluation):
        1. __init__:                  Load base model + blank LoRA.
        2. run_soar_generation():     Run one generation (20-iter episode, K candidates).
        3. sft_train_on_archive():    SFT train LoRA on accumulated archive.
        4. reset_lora():              Reset LoRA for next generation (SOAR always
                                      fine-tunes from base weights).
        5. cleanup():                 Free GPU memory.

    Config defaults follow SOAR paper and soar/training/train_unsloth.py.

    GPU: Official SOAR uses 1 GPU for inference (sglang/vLLM) and 1 GPU for training (Unsloth).
    This reimplementation uses a single device (e.g. cuda:0) for both. For 14B/32B with SFT,
    reduce gradient_accumulation_steps (e.g. to 4) or use a machine with more VRAM.
    """

    def __init__(
        self,
        model_name: str,
        model_path: Optional[str] = None,
        device: str = "cuda:0",
        # LoRA config (SOAR defaults: train_unsloth.py lora_r=256, alpha=32)
        lora_rank: int = 256,
        lora_alpha: int = 32,
        lora_target_modules: str = "all-linear",
        # SFT training config (SOAR defaults)
        sft_epochs: int = 3,
        learning_rate: float = 5e-5,
        train_batch_size: int = 1,
        gradient_accumulation_steps: int = 32,  # Official train_unsloth.py --grad_acc 32; use 4 if OOM
        lr_scheduler_type: str = "cosine",
        warmup_ratio: float = 0.1,
        weight_decay: float = 0.05,
        max_training_samples: int = 50,  # N_sample_task in official process_*_for_training.py
        # Test-time search config
        k_candidates: int = 4,
        search_temperature: float = 1.0,
        # REX Thompson sampling (soar/repair/rex.py C=20)
        thompson_C: float = 20.0,
        # Evaluation
        eval_temperature: float = 0.7,
        soar_generations: int = 2,
    ):
        self.model_type = "local"
        self.model_name = model_name
        self.device = device
        self.soar_generations = soar_generations

        # SFT training config
        self.sft_epochs = sft_epochs
        self.learning_rate = learning_rate
        self.train_batch_size = train_batch_size
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.lr_scheduler_type = lr_scheduler_type
        self.warmup_ratio = warmup_ratio
        self.weight_decay = weight_decay
        self.max_training_samples = max_training_samples

        # Test-time search
        self.k_candidates = k_candidates
        self.search_temperature = search_temperature
        self.thompson_C = thompson_C
        self.eval_temperature = eval_temperature

        self._custom_system_prompt: Optional[str] = None
        self._conversation_messages: list = []
        self._train_count = 0

        # Solution archive (accumulated across generations)
        self.archive: List[Dict[str, Any]] = []
        self._next_uid = 0

        # Resolve path
        resolved = _resolve_model_path(model_name, model_path)
        print(f"[SOAR] Loading model from {resolved} on {device}")

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            resolved, trust_remote_code=True,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        # Model (bf16, single device)
        _attn_impl = None
        if torch.cuda.is_available():
            try:
                import flash_attn  # noqa: F401
                _attn_impl = "flash_attention_2"
            except ImportError:
                _attn_impl = "sdpa"
        model_kwargs = dict(
            torch_dtype=torch.bfloat16,
            device_map={"": device},
            trust_remote_code=True,
        )
        if _attn_impl is not None:
            model_kwargs["attn_implementation"] = _attn_impl
        self.model = AutoModelForCausalLM.from_pretrained(resolved, **model_kwargs)

        # Apply LoRA (SOAR: r=256, alpha=32, all-linear)
        if lora_target_modules == "all-linear":
            target_mods = set()
            for name, mod in self.model.named_modules():
                if isinstance(mod, torch.nn.Linear):
                    short = name.split(".")[-1]
                    if short not in ("lm_head",):
                        target_mods.add(short)
            target_mods = sorted(target_mods) if target_mods else [
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ]
        else:
            target_mods = lora_target_modules.split(",")

        lora_cfg = LoraConfig(
            r=lora_rank,
            lora_alpha=lora_alpha,
            lora_dropout=0.0,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=list(target_mods),
            use_rslora=True,  # SOAR: use_rslora=True (rank-stabilized LoRA)
        )
        self.model = get_peft_model(self.model, lora_cfg)
        print(f"[SOAR] LoRA applied (r={lora_rank}, alpha={lora_alpha}, "
              f"RS-LoRA=True, targets={len(target_mods)} module types)")
        self.model.print_trainable_parameters()

        # Store initial LoRA-A values for reset
        self.initial_lora_A: Dict[str, torch.Tensor] = {}
        for name, param in self.model.named_parameters():
            if "lora_A" in name:
                self.initial_lora_A[name] = param.data.clone().detach()

        # Pre-compute assistant-header tokens for response masking
        self._assistant_header_ids = self._detect_assistant_header_ids()

    # ------------------------------------------------------------------
    # SolverInterface-compatible API
    # ------------------------------------------------------------------
    def get_system_prompt(self) -> str:
        return self._custom_system_prompt or SYSTEM_PROMPT

    def set_custom_system_prompt(self, prompt: str):
        self._custom_system_prompt = prompt

    def reset_conversation(self):
        self._conversation_messages = []
        self._custom_system_prompt = None

    def get_token_statistics(self) -> dict:
        return {
            "soar_train_count": self._train_count,
            "soar_archive_size": len(self.archive),
        }

    def cleanup(self):
        """Release GPU memory."""
        if hasattr(self, "model") and self.model is not None:
            del self.model
            self.model = None
        if hasattr(self, "tokenizer"):
            del self.tokenizer
            self.tokenizer = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # LoRA reset (SOAR always fine-tunes from base: Algorithm 1 line 3)
    # ------------------------------------------------------------------
    def reset_lora(self):
        """Reset LoRA-B to zero, LoRA-A to initial values."""
        for name, param in self.model.named_parameters():
            if "lora_B" in name:
                param.data.fill_(0.0)
            elif "lora_A" in name and name in self.initial_lora_A:
                param.data.copy_(self.initial_lora_A[name])

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def _generate_text(
        self,
        messages: list,
        temperature: float = 0.7,
        max_new_tokens: int = 65536,
    ) -> Tuple[str, int, int]:
        """Generate text from chat messages. Returns (text, prompt_len, resp_len)."""
        input_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        inputs = self.tokenizer(
            input_text, return_tensors="pt", truncation=True, max_length=65536,
        )
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        self.model.config.use_cache = True

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=max(temperature, 0.01),
                top_p=0.95,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        input_len = inputs["input_ids"].shape[1]
        new_tokens = outputs[0][input_len:]
        raw_output = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return raw_output, input_len, len(new_tokens)

    def generate_code(
        self,
        prompt: str,
        use_conversation: bool = False,
        reset_conversation: bool = False,
    ) -> Tuple[Optional[str], Optional[str], Dict]:
        """Generate single code solution (SolverInterface API)."""
        self.model.eval()
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": prompt},
        ]
        raw_output, p_len, r_len = self._generate_text(
            messages, temperature=self.eval_temperature,
        )
        code = _extract_code(raw_output)
        token_usage = {
            "prompt_tokens": p_len,
            "completion_tokens": r_len,
            "total_tokens": p_len + r_len,
        }
        return code, raw_output, token_usage

    def generate_code_from_messages(self, messages: list) -> Tuple[Optional[str], Optional[str], Dict]:
        """Generate code from explicit chat messages."""
        self.model.eval()
        raw_output, p_len, r_len = self._generate_text(
            messages, temperature=self.eval_temperature,
        )
        code = _extract_code(raw_output)
        token_usage = {
            "prompt_tokens": p_len,
            "completion_tokens": r_len,
            "total_tokens": p_len + r_len,
        }
        return code, raw_output, token_usage

    def generate_k_candidates(
        self,
        prompt: str,
        k: Optional[int] = None,
    ) -> List[Tuple[Optional[str], Optional[str], Dict]]:
        """Generate K candidate solutions for test-time search.

        Ref: soar/inference/sample_phase.py — generates k candidates per task
        Ref: soar/repair/rex.py — n_completions=4 for refinement

        Returns list of (code, raw_output, token_usage).
        """
        k = k or self.k_candidates
        self.model.eval()
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": prompt},
        ]
        candidates = []
        for _ in range(k):
            try:
                raw_output, p_len, r_len = self._generate_text(
                    messages, temperature=self.search_temperature,
                )
                code = _extract_code(raw_output)
                token_usage = {
                    "prompt_tokens": p_len,
                    "completion_tokens": r_len,
                    "total_tokens": p_len + r_len,
                }
                candidates.append((code, raw_output, token_usage))
            except Exception as exc:
                print(f"  [SOAR] Candidate generation failed: {exc}")
                candidates.append((None, None, {}))
        return candidates

    # ==================================================================
    # Archive Management
    # ==================================================================
    def add_to_archive(
        self,
        code: Optional[str],
        raw_output: Optional[str],
        score: float,
        success: bool,
        prompt: str,
        feedback: str,
        iteration: int,
        generation: int,
        parent_uid: Optional[int] = None,
    ) -> int:
        """Add a solution to the archive. Returns unique_id.

        Ref: soar/repair/rex.py — archive entry structure with unique_id,
             parents, type, N (selection count).
        """
        uid = self._next_uid
        self._next_uid += 1
        entry = {
            "unique_id": uid,
            "iteration": iteration,
            "generation": generation,
            "code": code,
            "raw_output": raw_output,
            "score": score,
            "success": success,
            "prompt": prompt,
            "feedback": feedback,
            "parents": [parent_uid] if parent_uid is not None else [],
            "type": "refined" if iteration > 1 else "initial_solution",
            "N": 0,  # Selection count for Thompson sampling
        }
        self.archive.append(entry)
        return uid

    def thompson_select_best(self) -> Optional[Dict[str, Any]]:
        """Use REX Thompson sampling to select a solution from the archive.

        Ref: soar/repair/rex.py  REX.sample_program_2_refine()
        Each solution gets a sampled priority:
            theta ~ Beta(1 + C*h, 1 + C*(1-h) + N)
        where h = score/100 (heuristic), N = selection count.
        The solution with highest theta is selected.

        Returns the selected archive entry (or None if archive is empty).
        """
        valid = [e for e in self.archive if e.get("code")]
        if not valid:
            return None

        best_entry = None
        best_theta = -1.0
        for entry in valid:
            theta = thompson_sample_score(
                entry.get("score", 0),
                entry.get("N", 0),
                C=self.thompson_C,
            )
            if theta > best_theta:
                best_theta = theta
                best_entry = entry

        # Increment selection count (discount for over-sampled programs)
        if best_entry is not None:
            best_entry["N"] = best_entry.get("N", 0) + 1

        return best_entry

    # ==================================================================
    # run_pretrain — full SOAR loop (G generations × search + SFT), align with official
    # ==================================================================
    def run_pretrain(
        self,
        task_prompt: Dict[str, Any],
        verifier: Any,
        max_iterations: int = 20,
        task_name: Optional[str] = None,
        get_initial_prompt: Optional[Callable[[], str]] = None,
        get_revision_prompt: Optional[Callable[[Dict, List, int], str]] = None,
        training_log_dir: Optional[str] = None,
        max_steps_verifier: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run full SOAR algorithm: G generations, each with search (K candidates + REX refinement) then SFT.

        Official flow (qwen.sh): sample → refine (REX) → process → train → next gen.
        This runs in-process: for each generation, max_iterations search steps (iter 1: K candidates;
        iter 2+: Thompson select → 1 refinement), then sft_train_on_archive().

        Optional get_initial_prompt / get_revision_prompt: when provided (e.g. cross-mutation path
        via run_single_pair), use them instead of format_initial_prompt/format_revision_prompt so
        the same SOAR loop runs with mutation prompts.
        get_initial_prompt() -> str.
        get_revision_prompt(selected_entry, iteration_history, step) -> str.

        Returns dict with success, best_score, best_code, best_metrics, iteration_history,
        stop_reason, soar_generations, soar_sft_runs.
        """
        from evaluation.prompt import format_initial_prompt, format_revision_prompt
        from evaluation.feedback import format_feedback

        logger = None
        if training_log_dir:
            try:
                from methods.Parameter_Policy.common.training_logger import TrainingLogger
                logger = TrainingLogger(
                    training_log_dir, method_name="soar", task_name=task_name or "",
                    max_iterations=max_iterations, max_steps_verifier=max_steps_verifier,
                )
                logger.log_config(
                    soar_generations=self.soar_generations,
                    k_candidates=self.k_candidates,
                    sft_epochs=self.sft_epochs,
                    max_iterations=max_iterations,
                )
            except Exception as e:
                print(f"[SOAR] Could not init training logger: {e}")

        self.reset_conversation()
        self.archive = []
        self._next_uid = 0

        best_score = -1.0
        best_code: Optional[str] = None
        best_metrics: Dict[str, Any] = {}
        iteration_history: List[Dict[str, Any]] = []
        step = 0
        sft_runs = 0
        task_label = task_name or ""

        for gen in range(1, self.soar_generations + 1):
            print(f"[SOAR] Generation {gen}/{self.soar_generations} (archive size {len(self.archive)})")
            for iteration in range(1, max_iterations + 1):
                step += 1
                if iteration == 1:
                    if get_initial_prompt is not None:
                        prompt = get_initial_prompt()
                    else:
                        prompt = format_initial_prompt(task_prompt)
                    candidates = self.generate_k_candidates(prompt, k=self.k_candidates)
                    best_this_round_score = -1.0
                    best_this_round = None
                    for cand_idx, (code, raw_output, token_usage) in enumerate(candidates):
                        if not code:
                            if logger:
                                logger.log_rollout_llm_call(
                                    generation=gen, iteration=iteration, candidate_idx=cand_idx,
                                    prompt_text=prompt, raw_output=raw_output or "", extracted_code=None,
                                    score=None, success=False, error="no code extracted",
                                    token_usage=token_usage,
                                )
                            continue
                        success, score, metrics, error = verifier.verify_code(
                            code, headless=True, save_gif_path=None
                        )
                        failed = metrics.get("failed", False)
                        failure_reason = metrics.get("failure_reason", "Unknown failure")
                        feedback = format_feedback(
                            metrics, score, success, failed, failure_reason,
                            iteration=step, error=error, task_name=task_label,
                        )
                        if logger:
                            logger.log_rollout_llm_call(
                                generation=gen, iteration=iteration, candidate_idx=cand_idx,
                                prompt_text=prompt, raw_output=raw_output, extracted_code=code,
                                score=score, success=success, error=error, feedback=feedback,
                                token_usage=token_usage,
                            )
                        uid = self.add_to_archive(
                            code=code,
                            raw_output=raw_output,
                            score=score,
                            success=success,
                            prompt=prompt,
                            feedback=feedback,
                            iteration=iteration,
                            generation=gen,
                            parent_uid=None,
                        )
                        if score > best_this_round_score:
                            best_this_round_score = score
                            best_this_round = {
                                "iteration": step,
                                "prompt": prompt,
                                "code": code,
                                "success": success,
                                "score": score,
                                "metrics": metrics,
                                "error": error,
                                "feedback": feedback,
                                "raw_llm_output": raw_output,
                                "token_usage": token_usage or {},
                            }
                    if best_this_round is not None:
                        iteration_history.append(best_this_round)
                        if best_this_round_score > best_score:
                            best_score = best_this_round_score
                            best_code = best_this_round["code"]
                            best_metrics = best_this_round.get("metrics", {})
                            print(f"  [SOAR] Step {step} (gen {gen} iter {iteration}): best of K → {best_score:.1f}/100")
                        if best_this_round.get("success"):
                            break
                else:
                    selected = self.thompson_select_best()
                    if selected is None:
                        break
                    if get_revision_prompt is not None:
                        rev_prompt = get_revision_prompt(selected, iteration_history, step)
                    else:
                        rev_prompt = format_revision_prompt(
                            task_prompt, selected["code"], selected["feedback"]
                        )
                    code, raw_output, token_usage = self.generate_code(rev_prompt)
                    if not code:
                        if logger:
                            logger.log_rollout_llm_call(
                                generation=gen, iteration=iteration,
                                prompt_text=rev_prompt, raw_output=raw_output or "", extracted_code=None,
                                score=None, success=False, error="no code extracted",
                                token_usage=token_usage,
                            )
                        continue
                    success, score, metrics, error = verifier.verify_code(
                        code, headless=True, save_gif_path=None
                    )
                    failed = metrics.get("failed", False)
                    failure_reason = metrics.get("failure_reason", "Unknown failure")
                    feedback = format_feedback(
                        metrics, score, success, failed, failure_reason,
                        iteration=step, error=error, task_name=task_label,
                    )
                    if logger:
                        logger.log_rollout_llm_call(
                            generation=gen, iteration=iteration,
                            prompt_text=rev_prompt, raw_output=raw_output, extracted_code=code,
                            score=score, success=success, error=error, feedback=feedback,
                            token_usage=token_usage,
                        )
                    self.add_to_archive(
                        code=code,
                        raw_output=raw_output,
                        score=score,
                        success=success,
                        prompt=rev_prompt,
                        feedback=feedback,
                        iteration=iteration,
                        generation=gen,
                        parent_uid=selected.get("unique_id"),
                    )
                    iteration_history.append({
                        "iteration": step,
                        "prompt": rev_prompt,
                        "code": code,
                        "success": success,
                        "score": score,
                        "metrics": metrics,
                        "error": error,
                        "feedback": feedback,
                        "raw_llm_output": raw_output,
                        "token_usage": token_usage or {},
                    })
                    if score > best_score:
                        best_score = score
                        best_code = code
                        best_metrics = metrics
                        print(f"  [SOAR] Step {step} (gen {gen} iter {iteration}): refinement → {best_score:.1f}/100")
                    if success:
                        break
            if best_score >= 100.0:
                break
            if logger:
                logger.log_rollout_generation(gen, iteration_history)
            # SFT on archive after each generation (sft_train_on_archive resets LoRA then trains)
            if self.archive:
                stats = self.sft_train_on_archive(
                    training_logger=logger,
                    sft_run_index=sft_runs,
                )
                if not stats.get("skipped", True):
                    sft_runs += 1

        stop_reason = "success" if (best_code and best_score >= 100.0) else "exhausted"
        result = {
            "success": best_score >= 100.0,
            "best_score": best_score,
            "best_code": best_code,
            "best_metrics": best_metrics,
            "iteration_history": iteration_history,
            "stop_reason": stop_reason,
            "soar_generations": self.soar_generations,
            "soar_sft_runs": sft_runs,
        }
        if logger:
            try:
                logger.finalize(summary_extra=result)
            except Exception:
                pass
        return result

    # ==================================================================
    # SFT Training (from soar/training/train_unsloth.py)
    # ==================================================================
    def sft_train_on_archive(
        self,
        output_dir: Optional[str] = None,
        training_logger: Optional[Any] = None,
        sft_run_index: int = 0,
    ) -> Dict[str, Any]:
        """SFT fine-tune LoRA on accumulated archive data.

        Builds two data streams:
          1. Sampling data: (prompt, good_code) via greedy-div strategy.
          2. Repair data: (revision_prompt, improved_code) from improvement pairs.
        Combines and trains via HuggingFace Trainer.

        Ref: soar/training/train_unsloth.py — SFT with train_on_responses_only
        Ref: soar/training/utils_process_data.py — get_dataset_HER, get_her_repair_sft

        Returns training statistics dict.
        """
        # 1. Select sampling data (greedy-div)
        sampling_data = select_sampling_data_greedy_div(
            self.archive, max_samples=self.max_training_samples,
        )

        # 2. Select repair data (by parent correctness)
        repair_data = select_repair_data(
            self.archive, max_samples=self.max_training_samples,
        )

        if not sampling_data and not repair_data:
            if training_logger:
                training_logger.log_warning("No training data available; skipping SFT.")
            print("[SOAR] No training data available; skipping SFT.")
            return {"skipped": True}

        # 3. Build training texts
        system_prompt = self.get_system_prompt()
        training_texts: List[str] = []

        # Sampling data: (prompt → code/raw_output) pairs
        for entry in sampling_data:
            assistant_content = entry.get("raw_output") or entry.get("code", "")
            if not assistant_content:
                continue
            msgs = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": entry["prompt"]},
                {"role": "assistant", "content": assistant_content},
            ]
            text = self.tokenizer.apply_chat_template(msgs, tokenize=False)
            training_texts.append(text)

        # Repair data: (revision_prompt → improved_code) pairs
        for pair in repair_data:
            assistant_content = pair.get("child_raw_output") or pair.get("child_code", "")
            if not assistant_content:
                continue
            # Use the child's prompt (which includes prev_code + feedback context)
            user_prompt = pair.get("child_prompt", "")
            if not user_prompt:
                continue
            msgs = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_content},
            ]
            text = self.tokenizer.apply_chat_template(msgs, tokenize=False)
            training_texts.append(text)

        if not training_texts:
            if training_logger:
                training_logger.log_warning("No training texts after formatting; skipping SFT.")
            print("[SOAR] No training texts after formatting; skipping SFT.")
            return {"skipped": True}

        print(f"[SOAR] SFT training on {len(training_texts)} samples "
              f"({len(sampling_data)} sampling + {len(repair_data)} repair)")

        # 4. Reset LoRA (SOAR: always fine-tune from base, Algorithm 1 line 3)
        self.reset_lora()

        # 5. Tokenize + mask (loss only on assistant response tokens)
        tokenized = self._tokenize_and_mask(training_texts)

        # 6. Train via HuggingFace Trainer
        self.model.config.use_cache = False
        self.model.train()
        torch.cuda.empty_cache()

        ds = Dataset.from_dict(tokenized)
        effective_dir = output_dir or "/tmp/soar_sft_temp"
        os.makedirs(effective_dir, exist_ok=True)

        class _LossCallback(TrainerCallback):
            def __init__(self, tl, run_offset):
                self.tl = tl
                self.run_offset = run_offset
            def on_log(self, args, state, control, logs=None, **kwargs):
                if logs and "loss" in logs and self.tl:
                    self.tl.log_loss_step(
                        step=self.run_offset + state.global_step,
                        loss=float(logs["loss"]),
                        sft_run=sft_run_index,
                    )
        callbacks = [_LossCallback(training_logger, sft_run_index * 1000)] if training_logger else []

        # SOAR training args (train_unsloth.py defaults)
        training_args = TrainingArguments(
            output_dir=effective_dir,
            per_device_train_batch_size=self.train_batch_size,
            gradient_accumulation_steps=self.gradient_accumulation_steps,
            learning_rate=self.learning_rate,
            num_train_epochs=self.sft_epochs,
            lr_scheduler_type=self.lr_scheduler_type,
            warmup_ratio=self.warmup_ratio,
            weight_decay=self.weight_decay,
            logging_steps=1,
            save_strategy="no",
            report_to="none",
            bf16=True,
            remove_unused_columns=False,
        optim="adamw_torch",  # Official uses adamw_8bit (Unsloth); we use HF Trainer without Unsloth
        gradient_checkpointing=True,
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=ds,
            callbacks=callbacks,
        )
        trainer.train()
        self._train_count += 1

        # Restore inference mode
        self.model.config.use_cache = True
        self.model.eval()
        torch.cuda.empty_cache()

        stats = {
            "skipped": False,
            "n_sampling_data": len(sampling_data),
            "n_repair_data": len(repair_data),
            "n_total_texts": len(training_texts),
            "train_count": self._train_count,
        }
        print(f"[SOAR] SFT training complete (generation {self._train_count})")
        return stats

    # ------------------------------------------------------------------
    # Tokenization & response masking (same as SEAL, for SFT loss masking)
    # ------------------------------------------------------------------
    def _detect_assistant_header_ids(self) -> Optional[List[int]]:
        """Detect token-ID pattern that marks assistant turn start."""
        probe_msgs = [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "U"},
            {"role": "assistant", "content": "ASSISTANT_MARKER_XYZ"},
        ]
        try:
            probe_text = self.tokenizer.apply_chat_template(probe_msgs, tokenize=False)
        except Exception:
            return None
        probe_ids = self.tokenizer.encode(probe_text, add_special_tokens=False)
        marker_ids = self.tokenizer.encode("ASSISTANT_MARKER_XYZ", add_special_tokens=False)
        for i in range(len(probe_ids) - len(marker_ids) + 1):
            if probe_ids[i: i + len(marker_ids)] == marker_ids:
                header_start = max(0, i - 4)
                header_ids = probe_ids[header_start:i]
                if header_ids:
                    return header_ids
        return None

    def _find_last_assistant_start(self, token_ids: List[int]) -> Optional[int]:
        """Find token index where the last assistant response begins."""
        header = self._assistant_header_ids
        if header:
            hlen = len(header)
            for i in range(len(token_ids) - hlen, -1, -1):
                if token_ids[i: i + hlen] == header:
                    return i + hlen
        text = self.tokenizer.decode(token_ids, skip_special_tokens=False)
        for marker in (
            "<|im_start|>assistant\n",
            "<|start_header_id|>assistant<|end_header_id|>\n\n",
        ):
            pos = text.rfind(marker)
            if pos >= 0:
                prefix_text = text[: pos + len(marker)]
                prefix_ids = self.tokenizer.encode(prefix_text, add_special_tokens=False)
                return len(prefix_ids)
        return None

    def _tokenize_and_mask(self, texts: List[str]) -> Dict[str, Any]:
        """Tokenize texts and create labels with loss masking.

        Loss only on assistant response tokens (SOAR: train_on_responses_only=True).
        Ref: soar/training/train_unsloth.py — train_on_responses_only()
        """
        outputs = self.tokenizer(
            texts,
            truncation=True,
            max_length=8192,
            padding="longest",
            return_tensors="pt",
        )
        input_ids = outputs["input_ids"]
        labels = input_ids.clone()

        for i in range(input_ids.shape[0]):
            sample_ids = input_ids[i].tolist()
            resp_start = self._find_last_assistant_start(sample_ids)
            if resp_start is not None:
                for j in range(resp_start):
                    labels[i, j] = -100
            else:
                cutoff = int(len(sample_ids) * 0.8)
                for j in range(cutoff):
                    labels[i, j] = -100

            pad_id = self.tokenizer.pad_token_id
            for j in range(input_ids.shape[1]):
                if input_ids[i, j] == pad_id and labels[i, j] != -100:
                    labels[i, j] = -100

        outputs["labels"] = labels
        return {k: v for k, v in outputs.items()}


# ============================================================================
# Factory
# ============================================================================

def get_soar_solver(
    model_name: str,
    model_path: Optional[str] = None,
    device: str = "cuda:0",
    soar_generations: int = 2,
    soar_k_candidates: int = 4,
    **kwargs,
) -> SOARSolver:
    """Create and return a :class:`SOARSolver` instance.

    Pipeline passes soar_generations and soar_k_candidates from evaluate.py.
    The evaluator calls run_pretrain() to run the full SOAR loop (G generations × search + SFT).
    """
    return SOARSolver(
        model_name=model_name,
        model_path=model_path,
        device=device,
        k_candidates=soar_k_candidates,
        soar_generations=soar_generations,
        **kwargs,
    )
