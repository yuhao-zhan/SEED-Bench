"""
RAGEN (StarPO) — Multi-turn RL Test-Time Training for 2D exploration tasks.

Adapted from DaVinciBench/baseline/Parameter_Policy/RAGEN/

Per-task online multi-turn RL: for each task, collect N rollout episodes
(each a full multi-turn code-refinement trajectory), then train LoRA
via GRPO + PPO-clip.  After training, evaluate with the adapted model.

Algorithm (StarPO / StarPO-S, Wang et al. 2025):
  1. Rollout:  Collect N complete episodes.  Each episode = up to max_turns
     of: generate code → verify with CodeVerifier → get score/feedback.
  2. Filter:   Keep top-p% episodes by total reward (StarPO-S variance filter).
  3. Advantages: GRPO — per-turn advantage = (r - mean) / std across episodes.
  4. Update:   PPO-clip on LoRA parameters (asymmetric clip, no KL penalty).
  5. Evaluate: Run standard iterative evaluation with the trained model.

Key references:
  - RAGEN paper:     arXiv 2504.20073
  - GRPO advantage:  ragen/trainer/core_algos.py  (compute_grpo_outcome_advantage)
  - Rollout filter:  ragen/trainer/rollout_filter.py
  - PPO-clip loss:   absolute_zero/training/train.py (ppo_clip_loss)
  - StarPO-S config: config/base.yaml (clip_ratio_low=0.2, clip_ratio_high=0.28,
                      entropy_coeff=0.001, use_kl_loss=False, rollout_filter_ratio=0.25)
"""

import os
import re
import gc
import sys
import math
import random
import copy
from typing import List, Optional, Dict, Tuple, Any

import numpy as np
import torch
import torch.nn.functional as F

from peft import LoraConfig, get_peft_model

from transformers import AutoModelForCausalLM, AutoTokenizer

# ---------------------------------------------------------------------------
# Import GRPO advantage computation from the RAGEN repo (core_algos.py).
# This function is self-contained (torch + numpy only).  We add the RAGEN
# source tree to sys.path so the import chain resolves.
# ---------------------------------------------------------------------------
_RAGEN_REPO_DIR = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "..",
        "baseline", "Parameter_Policy", "RAGEN",
    )
)
if _RAGEN_REPO_DIR not in sys.path:
    sys.path.insert(0, _RAGEN_REPO_DIR)

try:
    from ragen.trainer.core_algos import (
        compute_grpo_outcome_advantage as _ragen_grpo_advantage,
    )
    _HAS_RAGEN_CORE = True
except ImportError:
    _HAS_RAGEN_CORE = False

# Fallback: import from verl (installed as dependency) if RAGEN tree unavailable.
if not _HAS_RAGEN_CORE:
    try:
        from verl.trainer.ppo.core_algos import (
            compute_grpo_outcome_advantage as _ragen_grpo_advantage,
        )
        _HAS_RAGEN_CORE = True
    except ImportError:
        _HAS_RAGEN_CORE = False

# System prompt — identical to SolverInterface / SEALSolver / AbsoluteZeroSolver.
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
# Core RL functions (from RAGEN / absolute_zero)
# ===========================================================================

def compute_per_token_log_probs(
    model, input_ids: torch.Tensor, attention_mask: torch.Tensor,
) -> torch.Tensor:
    """Forward pass -> per-token log-probs.  logits[t] predicts token[t+1].

    Memory-efficient: uses F.cross_entropy instead of materialising full
    (B, L, V) log-softmax tensor.
    Ref: absolute_zero/training/train.py lines 85-103
    """
    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
    logits = outputs.logits[:, :-1, :]   # (B, L-1, V)
    labels = input_ids[:, 1:]            # (B, L-1)
    token_log_probs = -F.cross_entropy(
        logits.reshape(-1, logits.size(-1)),
        labels.reshape(-1),
        reduction="none",
    ).reshape(labels.shape)              # (B, L-1)
    del logits, outputs
    return token_log_probs


def grpo_advantages(
    rewards: torch.Tensor,
    episode_indices: np.ndarray,
    epsilon: float = 1e-6,
) -> torch.Tensor:
    """GRPO outcome advantage: normalise rewards within each prompt group.

    Faithful to RAGEN core_algos.compute_grpo_outcome_advantage (lines 26-76).
    For per-task RL (single prompt), this reduces to global mean/std whitening
    (identical to REINFORCE++).

    Args:
        rewards:  (N,)  total episode reward per rollout.
        episode_indices: (N,) group/prompt index (all same for per-task RL).
        epsilon:  stability constant.
    Returns:
        advantages: (N,)
    """
    from collections import defaultdict
    id2score: Dict[Any, list] = defaultdict(list)
    id2mean: Dict[Any, torch.Tensor] = {}
    id2std: Dict[Any, torch.Tensor] = {}

    with torch.no_grad():
        for i in range(len(rewards)):
            id2score[episode_indices[i]].append(rewards[i])
        for idx in id2score:
            if len(id2score[idx]) == 1:
                id2mean[idx] = torch.tensor(0.0, device=rewards.device)
                id2std[idx] = torch.tensor(1.0, device=rewards.device)
            elif len(id2score[idx]) > 1:
                stacked = torch.stack(id2score[idx])
                id2mean[idx] = stacked.mean()
                id2std[idx] = stacked.std()
            else:
                raise ValueError(f"no score in prompt index: {idx}")
        adv = rewards.clone()
        for i in range(len(adv)):
            adv[i] = (adv[i] - id2mean[episode_indices[i]]) / (
                id2std[episode_indices[i]] + epsilon
            )
    return adv


def ppo_clip_loss(
    new_log_probs: torch.Tensor,
    old_log_probs: torch.Tensor,
    advantages: torch.Tensor,
    response_mask: torch.Tensor,
    clip_ratio_low: float = 0.2,
    clip_ratio_high: float = 0.28,
) -> torch.Tensor:
    """PPO clipped surrogate loss with asymmetric clipping (StarPO-S / DAPO).

    Ref: RAGEN config/base.yaml  clip_ratio_low=0.2, clip_ratio_high=0.28
    Ref: absolute_zero/training/train.py lines 124-138
    """
    ratio = torch.exp(new_log_probs - old_log_probs)
    surr1 = ratio * advantages
    surr2 = torch.clamp(ratio, 1.0 - clip_ratio_low, 1.0 + clip_ratio_high) * advantages
    token_loss = -torch.min(surr1, surr2)
    loss = (token_loss * response_mask).sum() / response_mask.sum().clamp(min=1.0)
    return loss


def _ragen_reward(code: Optional[str], score: float) -> float:
    """Compute RAGEN-style reward for a single turn.

    Ref: RAGEN es_manager format_penalty = -0.1
    Ref: absolute_zero/training/train.py azr_reward (tiered shaping)
    """
    if not code:
        return -1.0
    if "def build_agent" not in code:
        return -1.0
    if len(code.strip()) < 30:
        return -0.8
    try:
        compile(code, "<agent>", "exec")
    except SyntaxError:
        return -0.5
    # Normalise verifier score (0-100) to 0-1 range.
    return max(score / 100.0, -0.3)


# ===========================================================================
# Rollout filtering (faithful to RAGEN rollout_filter.py)
# ===========================================================================

def filter_rollouts_by_reward(
    episode_rewards: List[float],
    keep_ratio: float = 0.25,
    filter_type: str = "largest",
) -> List[int]:
    """Return indices of episodes to keep, filtering by total reward.

    In RAGEN, filtering is done at the *group* level (multiple prompts, each
    with N rollouts).  For per-task RL (single prompt), we filter individual
    episodes instead (keep top-p% by total reward).

    Ref: ragen/trainer/rollout_filter.py  RewardRolloutFilter._select_top_groups
    """
    n = len(episode_rewards)
    k = max(int(keep_ratio * n), 2)  # keep at least 2 for GRPO std
    indexed = list(enumerate(episode_rewards))
    if filter_type == "largest":
        indexed.sort(key=lambda x: x[1], reverse=True)
    else:
        indexed.sort(key=lambda x: x[1])
    return [idx for idx, _ in indexed[:k]]


# ============================================================================
# RAGENSolver — per-task multi-turn RL solver
# ============================================================================

class RAGENSolver:
    """
    RAGEN (StarPO) Test-Time Training solver for 2D exploration tasks.

    Lifecycle (managed by evaluate.py):
        1. __init__:           Load base model + blank LoRA.
        2. run_pretrain():     Collect N rollout episodes, train via GRPO + PPO.
        3. generate_code():    Inference with trained LoRA (frozen after pretrain).
        4. cleanup():          Free GPU memory.

    Config defaults follow RAGEN config/base.yaml and the StarPO-S paper.
    For large models or OOM, set micro_batch_size=1.
    """

    def __init__(
        self,
        model_name: str,
        model_path: Optional[str] = None,
        device: str = "cuda:0",
        # LoRA config (base.yaml has rank=0; we use 64 for per-task LoRA adaptation)
        lora_rank: int = 64,
        lora_alpha: int = 64,
        lora_target_modules: str = "all-linear",
        # Rollout config (official agent_proxy.max_turn: 5)
        n_rollout_episodes: int = 8,
        max_turns_per_episode: int = 5,
        rollout_temperature: float = 1.0,
        # RL training config (StarPO-S defaults; official micro_batch_size_per_gpu: 4)
        ppo_epochs: int = 2,
        learning_rate: float = 1e-6,
        clip_ratio_low: float = 0.2,
        clip_ratio_high: float = 0.28,
        entropy_coeff: float = 0.001,
        micro_batch_size: int = 4,
        grad_clip: float = 1.0,
        # StarPO-S rollout filtering (official config/base.yaml: rollout_filter_ratio: 0.25)
        rollout_filter_ratio: float = 0.25,
        rollout_filter_type: str = "largest",
        # RAGEN format penalty (es_manager.format_penalty)
        format_penalty: float = -0.1,
        # Evaluation generation config (official val_kwargs.temperature: 0.5)
        eval_temperature: float = 0.5,
    ):
        self.model_type = "local"
        self.model_name = model_name
        self.device = device

        # Rollout config
        self.n_rollout_episodes = n_rollout_episodes
        self.max_turns_per_episode = max_turns_per_episode
        self.rollout_temperature = rollout_temperature

        # RL training config
        self.ppo_epochs = ppo_epochs
        self.learning_rate = learning_rate
        self.clip_ratio_low = clip_ratio_low
        self.clip_ratio_high = clip_ratio_high
        self.entropy_coeff = entropy_coeff
        self.micro_batch_size = micro_batch_size
        self.grad_clip = grad_clip

        # Rollout filtering
        self.rollout_filter_ratio = rollout_filter_ratio
        self.rollout_filter_type = rollout_filter_type

        self.format_penalty = format_penalty
        self.eval_temperature = eval_temperature

        self._custom_system_prompt: Optional[str] = None
        self._conversation_messages: list = []
        self._pretrain_stats: Dict[str, Any] = {}

        # Resolve path
        resolved = _resolve_model_path(model_name, model_path)
        print(f"[RAGEN] Loading model from {resolved} on {device}")

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

        # Apply LoRA (RAGEN config/base.yaml: rank=64, alpha=64, all-linear)
        if lora_target_modules == "all-linear":
            # Detect all linear modules (faithful to RAGEN's target_modules: all-linear)
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
        )
        self.model = get_peft_model(self.model, lora_cfg)
        print(f"[RAGEN] LoRA applied (r={lora_rank}, alpha={lora_alpha}, "
              f"targets={len(target_mods)} module types)")
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
            "ragen_pretrain_episodes": self._pretrain_stats.get("n_episodes", 0),
            "ragen_mean_rollout_reward": self._pretrain_stats.get("mean_reward", 0.0),
            "ragen_ppo_epochs": self._pretrain_stats.get("ppo_epochs", 0),
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
    # LoRA reset (same as SEAL, from SEAL/few-shot/arclib/update_model.py)
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
        seed: Optional[int] = None,
    ) -> Tuple[Optional[str], Optional[str], Dict]:
        """Generate code (SolverInterface API). Uses eval_temperature."""
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

    # ==================================================================
    # Multi-turn Rollout Collection
    # ==================================================================
    def run_rollout_episode(
        self,
        task_prompt: Dict[str, Any],
        verifier: Any,
        max_turns: int = 5,
        enable_feedback: bool = False,
        rollout_logger: Optional[Any] = None,
        episode_idx: int = 0,
    ) -> Dict[str, Any]:
        """Run one complete multi-turn episode (faithful to RAGEN's K-turn rollout).

        Each turn: build prompt -> model.generate -> extract code -> verify -> feedback.
        The episode mirrors our baseline evaluation loop but collects the full trajectory.

        Ref: ragen/llm_agent/agent_proxy.py  rollout() lines 194-267
        Ref: ragen/llm_agent/es_manager.py   step()

        Returns dict with:
            turns: list of per-turn data
            total_reward: sum of turn rewards
            success: whether task was solved
        """
        # Lazy import prompt formatters (they live in the evaluation package)
        from evaluation.prompt import (
            format_initial_prompt,
            format_revision_prompt_best_plus_previous,
        )
        from evaluation.feedback import format_feedback

        self.model.eval()
        turns: List[Dict[str, Any]] = []
        best_score = 0.0
        best_code = None
        best_feedback = None
        best_iteration = None
        previous_code = None
        total_reward = 0.0
        penalty = 0.0

        for turn_idx in range(1, max_turns + 1):
            # 1. Build prompt (same logic as evaluate.py)
            if turn_idx == 1:
                prompt_text = format_initial_prompt(task_prompt)
            else:
                previous_feedback = turns[-1].get("feedback", "")
                prompt_text = format_revision_prompt_best_plus_previous(
                    task_prompt,
                    best_code=best_code or "",
                    best_feedback=best_feedback or "",
                    previous_code=previous_code or "",
                    previous_feedback=previous_feedback,
                    current_feedback=previous_feedback,
                    best_iteration=best_iteration,
                    previous_iteration=turn_idx - 1,
                    current_iteration=turn_idx,
                )

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": prompt_text},
            ]

            # 2. Generate (rollout temperature = 1.0 for exploration, RAGEN default)
            try:
                raw_output, p_len, r_len = self._generate_text(
                    messages, temperature=self.rollout_temperature,
                )
                code = _extract_code(raw_output)
            except Exception as exc:
                print(f"  [RAGEN rollout] Turn {turn_idx} generation failed: {exc}")
                code, raw_output = None, ""
                p_len, r_len = 0, 0

            # 3. Verify (CodeVerifier.verify_code returns (success, score, metrics, error))
            score = 0.0
            success = False
            error = None
            feedback_text = ""
            metrics = {}
            if code and "def build_agent" in code and len(code.strip()) >= 30:
                try:
                    success, score, metrics, error = verifier.verify_code(
                        code, headless=True, save_gif_path=None,
                    )
                except Exception as exc:
                    error = str(exc)
                    score = 0.0
                    metrics = {"error_type": "verification_error", "error_message": str(exc)}
            elif code:
                error = "missing build_agent or code too short"
                metrics = {"error_type": "code_validation", "error_message": error}
            else:
                error = "no code extracted"
                metrics = {"error_type": "code_extraction", "error_message": error}

            # 4. Compute turn reward (RAGEN-style)
            turn_reward = _ragen_reward(code, score)
            # Format penalty for invalid code (RAGEN es_manager.format_penalty)
            if not code or "def build_agent" not in (code or ""):
                penalty += self.format_penalty

            failed = metrics.get("failed", False)
            failure_reason = metrics.get("failure_reason", None)
            feedback_text = format_feedback(
                metrics, score, success, failed, failure_reason, turn_idx,
                error=error, task_name="(rollout)",
                include_suggestions=enable_feedback,
            )

            # 5. Record turn
            turn_data = {
                "turn": turn_idx,
                "messages": messages,
                "prompt_text": prompt_text,
                "raw_output": raw_output,
                "code": code,
                "score": score,
                "reward": turn_reward,
                "success": success,
                "feedback": feedback_text,
                "error": error,
                "prompt_tokens": p_len,
                "response_tokens": r_len,
            }
            turns.append(turn_data)
            if rollout_logger:
                rollout_logger.log_rollout_llm_call(
                    episode=episode_idx,
                    turn=turn_idx,
                    prompt_text=prompt_text,
                    messages=messages,
                    raw_output=raw_output,
                    extracted_code=code,
                    score=score,
                    success=success,
                    error=error,
                    feedback=feedback_text,
                    token_usage={"prompt_tokens": p_len, "response_tokens": r_len},
                )
            total_reward += turn_reward

            # 6. Update best
            if score > best_score:
                best_score = score
                best_code = code
                best_feedback = feedback_text
                best_iteration = turn_idx

            previous_code = code

            # 7. Check done
            if success:
                break

        total_reward += penalty

        return {
            "turns": turns,
            "total_reward": total_reward,
            "best_score": best_score,
            "best_code": best_code,
            "success": any(t["success"] for t in turns),
            "n_turns": len(turns),
            "penalty": penalty,
        }

    def collect_rollouts(
        self,
        task_prompt: Dict[str, Any],
        verifier: Any,
        n_episodes: Optional[int] = None,
        max_turns: Optional[int] = None,
        training_logger: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Collect N complete rollout episodes.

        Ref: ragen/llm_agent/agent_proxy.py  rollout() — generates N trajectories
             per prompt (group), each up to max_turn turns.
        """
        n = n_episodes or self.n_rollout_episodes
        mt = max_turns or self.max_turns_per_episode
        episodes: List[Dict[str, Any]] = []

        print(f"[RAGEN] Collecting {n} rollout episodes (max {mt} turns each)...")

        for ep_idx in range(n):
            print(f"  [RAGEN rollout] Episode {ep_idx + 1}/{n}")
            episode = self.run_rollout_episode(
                task_prompt, verifier, max_turns=mt,
                rollout_logger=training_logger,
                episode_idx=ep_idx,
            )
            episode["episode_idx"] = ep_idx
            episodes.append(episode)
            if training_logger:
                training_logger.log_rollout_episode(ep_idx, episode)

            # Print summary
            print(f"    reward={episode['total_reward']:.3f}  "
                  f"best_score={episode['best_score']:.1f}  "
                  f"turns={episode['n_turns']}  "
                  f"success={episode['success']}")

        rewards = [ep["total_reward"] for ep in episodes]
        print(f"[RAGEN] Rollout complete: mean_reward={np.mean(rewards):.3f}, "
              f"std={np.std(rewards):.3f}, "
              f"success_rate={sum(1 for ep in episodes if ep['success'])}/{n}")

        return episodes

    # ==================================================================
    # RL Training (GRPO + PPO-clip on LoRA)
    # ==================================================================
    def rl_train(
        self,
        episodes: List[Dict[str, Any]],
        training_logger: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Train LoRA using GRPO + PPO-clip on collected rollout episodes.

        Algorithm (StarPO / StarPO-S):
            1. Filter episodes (keep top-p% by total reward).
            2. Build training samples: each turn becomes a (prompt, response) pair.
               Response mask covers only assistant tokens.
            3. Compute episode-level GRPO advantages.
            4. Expand per-episode advantages to per-token.
            5. Compute old log-probs (forward, no grad).
            6. PPO-clip update on LoRA for E epochs.

        Ref: ragen/trainer/agent_trainer.py  fit() lines 484-799
        Ref: ragen/trainer/core_algos.py     compute_grpo_outcome_advantage
        Ref: config/base.yaml                (all hyperparameters)

        Returns training statistics dict.
        """
        if len(episodes) < 2:
            if training_logger:
                training_logger.log_warning("Need at least 2 episodes for GRPO; skipping training.")
            print("[RAGEN] Need at least 2 episodes for GRPO; skipping training.")
            return {"skipped": True}

        # 1. Rollout filtering (StarPO-S: keep top-p% by reward)
        #    Ref: ragen/trainer/rollout_filter.py  RewardRolloutFilter.filter
        episode_rewards = [ep["total_reward"] for ep in episodes]
        keep_indices = filter_rollouts_by_reward(
            episode_rewards,
            keep_ratio=self.rollout_filter_ratio,
            filter_type=self.rollout_filter_type,
        )
        filtered = [episodes[i] for i in keep_indices]
        print(f"[RAGEN] Filtered {len(episodes)} -> {len(filtered)} episodes "
              f"(keep_ratio={self.rollout_filter_ratio})")

        if len(filtered) < 2:
            if training_logger:
                training_logger.log_warning("Too few episodes after filtering; skipping training.")
            print("[RAGEN] Too few episodes after filtering; skipping training.")
            return {"skipped": True}

        # 2. Build per-turn training samples
        #    Ref: ragen/llm_agent/ctx_manager.py  _build_single_turn_samples
        #    Each turn's (messages, response) becomes one training sample.
        #    The per-episode reward is assigned to all turns in the episode (GRPO).
        samples = []
        for ep in filtered:
            ep_reward = ep["total_reward"]
            for turn in ep["turns"]:
                if not turn.get("raw_output"):
                    continue
                messages = turn["messages"]
                raw_response = turn["raw_output"]
                samples.append({
                    "messages": messages,
                    "response": raw_response,
                    "episode_reward": ep_reward,
                    "turn_reward": turn["reward"],
                    "episode_idx": ep["episode_idx"],
                })

        if len(samples) < 2:
            if training_logger:
                training_logger.log_warning("Too few valid training samples; skipping training.")
            print("[RAGEN] Too few valid training samples; skipping training.")
            return {"skipped": True}

        print(f"[RAGEN] Built {len(samples)} training samples from "
              f"{len(filtered)} episodes")

        # 3. Tokenize all samples
        #    Full conversation (prompt + response) in one sequence.
        #    Response mask = 1 for assistant response tokens, 0 for prompt tokens.
        tokenized = self._tokenize_training_samples(samples)
        if tokenized is None:
            if training_logger:
                training_logger.log_warning("Tokenization returned None; skipping training.")
            return {"skipped": True}

        input_ids = tokenized["input_ids"]        # (N, L)
        attention_mask = tokenized["attention_mask"]  # (N, L)
        response_mask = tokenized["response_mask"]    # (N, L-1)
        episode_rewards = tokenized["episode_rewards"]  # (N,)
        episode_indices = tokenized["episode_indices"]   # (N,)  np array

        n_samples = input_ids.shape[0]

        # 4. GRPO advantages (per-episode, expanded to per-token)
        #    Use official ragen.trainer.core_algos.compute_grpo_outcome_advantage when available
        if _HAS_RAGEN_CORE:
            token_level_rewards = episode_rewards.unsqueeze(1)  # (N, 1) for official API
            resp_mask_1 = torch.ones_like(token_level_rewards, device=episode_rewards.device, dtype=torch.float)
            advantages, _ = _ragen_grpo_advantage(
                token_level_rewards, resp_mask_1, episode_indices, epsilon=1e-6,
            )
            advantages = advantages.squeeze(-1)  # (N,)
        else:
            advantages = grpo_advantages(episode_rewards, episode_indices)
        # Expand per-sample advantage to per-token
        token_advantages = advantages.unsqueeze(1).expand_as(response_mask) * response_mask

        # 5. Compute old log-probs (forward pass, no grad)
        print("[RAGEN] Computing old log-probs...")
        self.model.eval()
        self.model.config.use_cache = False
        old_log_probs_list = []
        with torch.no_grad():
            for i in range(0, n_samples, self.micro_batch_size):
                j = min(i + self.micro_batch_size, n_samples)
                chunk_lp = compute_per_token_log_probs(
                    self.model,
                    input_ids[i:j],
                    attention_mask[i:j],
                )
                old_log_probs_list.append(chunk_lp.detach())
        old_log_probs = torch.cat(old_log_probs_list, dim=0)

        # Free KV-cache memory before training
        torch.cuda.empty_cache()

        # 6. PPO-clip update on LoRA
        #    Ref: ragen/workers/actor/dp_actor.py update_actor
        #    Ref: config/base.yaml (lr=1e-6, entropy_coeff=0.001, no KL)
        optimizer = torch.optim.AdamW(
            [p for p in self.model.parameters() if p.requires_grad],
            lr=self.learning_rate,
            betas=(0.9, 0.999),
            weight_decay=0.0,
        )

        self.model.train()
        self.model.gradient_checkpointing_enable()
        total_loss_sum = 0.0
        n_updates = 0

        for epoch in range(self.ppo_epochs):
            # Shuffle sample order each epoch
            perm = torch.randperm(n_samples)
            epoch_loss = 0.0
            n_micro_steps = max(1, n_samples // self.micro_batch_size)

            optimizer.zero_grad()
            for mb_idx in range(0, n_samples, self.micro_batch_size):
                mb_end = min(mb_idx + self.micro_batch_size, n_samples)
                idx = perm[mb_idx:mb_end]

                mb_ids = input_ids[idx]
                mb_mask = attention_mask[idx]
                mb_old_lp = old_log_probs[idx]
                mb_resp_mask = response_mask[idx]
                mb_adv = token_advantages[idx]

                new_lp = compute_per_token_log_probs(self.model, mb_ids, mb_mask)

                mb_loss = ppo_clip_loss(
                    new_lp, mb_old_lp, mb_adv, mb_resp_mask,
                    self.clip_ratio_low, self.clip_ratio_high,
                )
                # Entropy bonus (RAGEN config: entropy_coeff=0.001)
                if self.entropy_coeff > 0:
                    # Approximate entropy from log-probs
                    entropy = -(new_lp * mb_resp_mask).sum() / mb_resp_mask.sum().clamp(min=1.0)
                    mb_loss = mb_loss - self.entropy_coeff * entropy

                mb_loss = mb_loss / n_micro_steps
                # When all advantages are zero (e.g. all rollouts failed), loss can be constant
                # and lose grad_fn under gradient checkpointing. Tie loss to new_lp so backward() works.
                if not mb_loss.requires_grad:
                    mb_loss = mb_loss + 0.0 * new_lp.sum()
                mb_loss.backward()
                epoch_loss += mb_loss.item() * n_micro_steps

            torch.nn.utils.clip_grad_norm_(
                [p for p in self.model.parameters() if p.requires_grad],
                self.grad_clip,
            )
            optimizer.step()
            optimizer.zero_grad()
            n_updates += 1
            total_loss_sum += epoch_loss
            if training_logger:
                training_logger.log_loss_step(step=epoch + 1, loss=epoch_loss, epoch=epoch + 1)
            print(f"  [RAGEN PPO] Epoch {epoch + 1}/{self.ppo_epochs}: "
                  f"loss={epoch_loss:.4f}")

        # Restore inference mode
        self.model.gradient_checkpointing_disable()
        self.model.config.use_cache = True
        self.model.eval()
        torch.cuda.empty_cache()

        stats = {
            "skipped": False,
            "n_episodes": len(episodes),
            "n_filtered": len(filtered),
            "n_samples": n_samples,
            "ppo_epochs": self.ppo_epochs,
            "mean_loss": total_loss_sum / max(n_updates, 1),
            "mean_reward": float(np.mean(episode_rewards.cpu().numpy())),
            "reward_std": float(np.std(episode_rewards.cpu().numpy())),
        }
        self._pretrain_stats = stats
        print(f"[RAGEN] RL training complete: {stats}")
        return stats

    # ==================================================================
    # Full pre-training pipeline (collect + train)
    # ==================================================================
    def run_pretrain(
        self,
        task_prompt: Dict[str, Any],
        verifier: Any,
        n_episodes: Optional[int] = None,
        max_turns: Optional[int] = None,
        training_log_dir: Optional[str] = None,
        max_iterations: Optional[int] = None,
        max_steps_verifier: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Full RAGEN pre-training: reset LoRA, collect rollouts, train, return stats.

        This is called once per task before the standard evaluation loop.
        """
        logger = None
        if training_log_dir:
            try:
                from methods.Parameter_Policy.common.training_logger import TrainingLogger
                task_name = task_prompt.get("task_name") or task_prompt.get("name") or ""
                logger = TrainingLogger(
                    training_log_dir, method_name="ragen", task_name=task_name,
                    max_iterations=max_iterations, max_steps_verifier=max_steps_verifier,
                )
                logger.log_config(
                    n_rollouts=n_episodes or self.n_rollout_episodes,
                    max_turns=max_turns or self.max_turns_per_episode,
                    ppo_epochs=self.ppo_epochs,
                    rollout_filter_ratio=self.rollout_filter_ratio,
                    clip_ratio_low=self.clip_ratio_low,
                    clip_ratio_high=self.clip_ratio_high,
                )
                if task_prompt.get("initial_prompt_text") or task_prompt.get("description"):
                    from evaluation.prompt import format_initial_prompt
                    prompt_sample = format_initial_prompt(task_prompt)
                    logger.log_prompt_sample("initial_prompt", prompt_sample)
            except Exception as e:
                print(f"[RAGEN] Could not init training logger: {e}")

        # Reset LoRA to blank state
        self.reset_lora()
        print("[RAGEN] LoRA reset for fresh per-task training")

        # Collect rollout episodes
        episodes = self.collect_rollouts(
            task_prompt, verifier,
            n_episodes=n_episodes,
            max_turns=max_turns,
            training_logger=logger,
        )

        # RL training
        stats = self.rl_train(episodes, training_logger=logger)
        if logger:
            try:
                logger.finalize(summary_extra=stats)
            except Exception:
                pass
        return stats

    # ==================================================================
    # Tokenization & response masking for RL training
    # ==================================================================
    def _detect_assistant_header_ids(self) -> Optional[List[int]]:
        """Detect token-ID pattern that marks assistant turn start.
        Same as SEAL's detection logic.
        """
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

    def _find_assistant_response_range(self, token_ids: List[int]) -> Tuple[int, int]:
        """Find start and end indices of the LAST assistant response in token_ids.

        Returns (start, end) where start is the first response-body token index
        and end is the last+1 index.  For response masking in RL training.

        Ref: RAGEN ctx_manager uses enable_response_mask to mask out non-response tokens.
        """
        header = self._assistant_header_ids
        if header:
            hlen = len(header)
            # Find last occurrence
            for i in range(len(token_ids) - hlen, -1, -1):
                if token_ids[i: i + hlen] == header:
                    return i + hlen, len(token_ids)

        # Fallback: decode and search for common markers
        text = self.tokenizer.decode(token_ids, skip_special_tokens=False)
        for marker in (
            "<|im_start|>assistant\n",
            "<|start_header_id|>assistant<|end_header_id|>\n\n",
        ):
            pos = text.rfind(marker)
            if pos >= 0:
                prefix_text = text[: pos + len(marker)]
                prefix_ids = self.tokenizer.encode(prefix_text, add_special_tokens=False)
                return len(prefix_ids), len(token_ids)

        # Last resort: assume last 60% is response
        start = int(len(token_ids) * 0.4)
        return start, len(token_ids)

    def _tokenize_training_samples(
        self, samples: List[Dict[str, Any]],
    ) -> Optional[Dict[str, torch.Tensor]]:
        """Tokenize training samples and build response masks.

        Each sample: messages (prompt) + response (assistant text).
        The response mask covers only the assistant response tokens.

        Ref: RAGEN config/base.yaml  enable_response_mask: True
        Ref: ragen/llm_agent/ctx_manager.py  get_masks_and_scores
        """
        all_input_ids = []
        all_attention_masks = []
        all_response_masks = []
        all_episode_rewards = []
        all_episode_indices = []

        for sample in samples:
            messages = sample["messages"]
            response = sample["response"]

            # Build full conversation text (prompt + assistant response)
            full_messages = list(messages) + [
                {"role": "assistant", "content": response},
            ]
            full_text = self.tokenizer.apply_chat_template(
                full_messages, tokenize=False,
            )

            enc = self.tokenizer(
                full_text, truncation=True, max_length=65536,
                return_tensors="pt",
            )
            ids = enc["input_ids"][0]      # (L,)
            mask = enc["attention_mask"][0]  # (L,)

            # Build response mask (1 for assistant response tokens, 0 elsewhere)
            resp_start, resp_end = self._find_assistant_response_range(ids.tolist())
            # response_mask is for log-probs: shifted by 1 (logits[t] -> token[t+1])
            resp_mask = torch.zeros(len(ids) - 1, dtype=torch.float)
            if resp_start > 0 and resp_end > resp_start:
                # Token t's log-prob predicts token t+1, so mask index = resp_start-1..resp_end-2
                mask_start = max(resp_start - 1, 0)
                mask_end = min(resp_end - 1, len(ids) - 1)
                resp_mask[mask_start:mask_end] = 1.0

            all_input_ids.append(ids)
            all_attention_masks.append(mask)
            all_response_masks.append(resp_mask)
            all_episode_rewards.append(sample["episode_reward"])
            all_episode_indices.append(sample["episode_idx"])

        if not all_input_ids:
            return None

        # Pad to same length
        max_len = max(ids.shape[0] for ids in all_input_ids)
        device = self.model.device

        padded_ids = torch.full((len(all_input_ids), max_len),
                                self.tokenizer.pad_token_id, dtype=torch.long, device=device)
        padded_attn = torch.zeros((len(all_input_ids), max_len),
                                  dtype=torch.long, device=device)
        padded_resp = torch.zeros((len(all_input_ids), max_len - 1),
                                  dtype=torch.float, device=device)

        for i, (ids, attn, resp) in enumerate(
            zip(all_input_ids, all_attention_masks, all_response_masks)
        ):
            L = ids.shape[0]
            padded_ids[i, :L] = ids
            padded_attn[i, :L] = attn
            padded_resp[i, :L - 1] = resp

        episode_rewards = torch.tensor(all_episode_rewards, dtype=torch.float, device=device)
        episode_indices = np.array(all_episode_indices)

        return {
            "input_ids": padded_ids,
            "attention_mask": padded_attn,
            "response_mask": padded_resp,
            "episode_rewards": episode_rewards,
            "episode_indices": episode_indices,
        }


# ============================================================================
# Factory
# ============================================================================

def get_ragen_solver(
    model_name: str,
    model_path: Optional[str] = None,
    device: str = "cuda:0",
    ragen_n_rollouts: int = 8,
    ragen_ppo_epochs: int = 2,
    **kwargs,
) -> RAGENSolver:
    """Create and return a :class:`RAGENSolver` instance."""
    return RAGENSolver(
        model_name=model_name,
        model_path=model_path,
        device=device,
        n_rollout_episodes=ragen_n_rollouts,
        ppo_epochs=ragen_ppo_epochs,
        **kwargs,
    )
