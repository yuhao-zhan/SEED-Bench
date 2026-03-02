"""
TTT-Discover: Learning to Discover at Test Time.

Strictly follows DaVinciBench/baseline/Parameter_Policy/discover:
- Rollout -> compute_advantages (entropic / mean_baseline) -> importance_sampling or PPO.
- When all rewards are constant (e.g. all 0), use feedback-based expansion
  (like baseline revision: feedback -> revision prompt -> more rollouts) before TTT.

Ref: tinker_cookbook/rl/train.py (compute_advantages, do_group_rollout_and_filter_constant_reward)
Ref: tinker_cookbook/recipes/ttt/train.py (CLIConfig defaults)
"""

import os
import re
import gc
import math
from typing import List, Optional, Dict, Tuple, Any

import numpy as np
import torch
import torch.nn.functional as F

from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

# ---------------------------------------------------------------------------
# Advantage computation (from discover tinker_cookbook/rl/train.py)
# ---------------------------------------------------------------------------

def compute_advantages_single_group(
    rewards: List[float],
    adv_estimator: str = "entropic",
    adv_estimator_beta: float = 2.0,
    device: Optional[torch.device] = None,
) -> torch.Tensor:
    """Compute advantages for one group of rewards (discover-style).

    Ref: discover tinker_cookbook/rl/train.py compute_advantages (lines 52-128).
    """
    rewards_G = torch.tensor(rewards, dtype=torch.float, device=device or torch.device("cpu"))

    if adv_estimator == "mean_baseline":
        advantages_G = rewards_G - rewards_G.mean()
    elif adv_estimator == "entropic":
        beta = adv_estimator_beta
        s_safe = rewards_G - rewards_G.max(dim=-1, keepdim=True)[0]
        e = torch.exp(beta * s_safe)
        k = e.shape[0]
        if k == 1:
            Z = e
        else:
            Z = (e.sum() - e) / (k - 1)
        w = e / (Z + 1e-12)
        advantages_G = w - 1.0
    elif adv_estimator == "entropic_adaptive_beta":
        delta = math.log(2)
        beta_max = 1e6
        iters = 60
        eps = 1e-12
        r = rewards_G.float()
        k = r.shape[0]
        if k < 2:
            beta = r.new_tensor(0.0)
        else:
            logK = math.log(k)

            def kl_hat(beta_scalar: float) -> float:
                b = r.new_tensor(beta_scalar)
                logits = b * (r - r.max(dim=0, keepdim=True).values)
                logq = logits - torch.logsumexp(logits, dim=0, keepdim=True)
                q = torch.exp(logq)
                kl = (q * (logq + logK)).sum(dim=0)
                return float(kl.mean().item())

            lo, hi = 0.0, 1.0
            if kl_hat(hi) < delta:
                while hi < beta_max and kl_hat(hi) < delta:
                    hi *= 2.0
                if kl_hat(hi) >= delta:
                    for _ in range(iters):
                        mid = 0.5 * (lo + hi)
                        if kl_hat(mid) < delta:
                            lo = mid
                        else:
                            hi = mid
                    hi = 0.5 * (lo + hi)
            beta = r.new_tensor(hi)

        e = torch.exp(beta * (r - r.max(dim=0, keepdim=True).values))
        if k == 1:
            Z = e
        else:
            Z = (e.sum(dim=0, keepdim=True) - e) / (k - 1)
        w = e / (Z + eps)
        advantages_G = w - 1.0
    else:
        raise ValueError(f"Invalid advantage estimator: {adv_estimator}")

    return advantages_G


def _all_same(rewards: List[float]) -> bool:
    if not rewards:
        return True
    return all(r == rewards[0] for r in rewards)


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

def _extract_code(raw_text: str) -> Optional[str]:
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


# ---------------------------------------------------------------------------
# Per-token log probs (for importance_sampling loss)
# ---------------------------------------------------------------------------

def compute_per_token_log_probs(
    model, input_ids: torch.Tensor, attention_mask: torch.Tensor,
) -> torch.Tensor:
    """Per-token log-probs; logits[t] predicts token[t+1]."""
    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
    logits = outputs.logits[:, :-1, :]
    labels = input_ids[:, 1:]
    token_log_probs = -F.cross_entropy(
        logits.reshape(-1, logits.size(-1)),
        labels.reshape(-1),
        reduction="none",
    ).reshape(labels.shape)
    del logits, outputs
    return token_log_probs


# ---------------------------------------------------------------------------
# System prompt (same as SEAL/RAGEN)
# ---------------------------------------------------------------------------

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
# Model path resolution
# ---------------------------------------------------------------------------

_LOCAL_MODEL_PREFIXES = [
    "/home/test/testdata/models/",
    os.path.expanduser("~/models/"),
]


def _resolve_model_path(model_name: str, model_path: Optional[str] = None) -> str:
    if model_path and os.path.exists(model_path):
        return model_path
    if os.path.exists(model_name):
        return model_name
    for prefix in _LOCAL_MODEL_PREFIXES:
        candidate = os.path.join(prefix, os.path.basename(model_name))
        if os.path.exists(candidate):
            return candidate
    return model_path or model_name


# ============================================================================
# DiscoverSolver
# ============================================================================

class DiscoverSolver:
    """
    TTT-Discover solver for 2D exploration tasks.

    Per-task: num_epochs of (group_size rollouts -> [optional expansion if constant reward]
             -> compute_advantages -> importance_sampling/PPO update).
    Then evaluation loop uses the trained LoRA (frozen).
    """

    def __init__(
        self,
        model_name: str,
        model_path: Optional[str] = None,
        device: str = "cuda:0",
        # Discover CLIConfig defaults (tinker_cookbook/recipes/ttt/train.py)
        num_epochs: int = 50,
        group_size: int = 8,
        groups_per_batch: int = 64,
        learning_rate: float = 4e-5,
        adv_estimator: str = "entropic",
        adv_estimator_beta: float = 2.0,
        loss_fn: str = "importance_sampling",
        lora_rank: int = 32,
        max_tokens: int = 65536,
        temperature: float = 1.0,
        num_substeps: int = 1,
        max_expansion_rounds: int = 2,
        micro_batch_size: int = 2,
        grad_clip: float = 1.0,
    ):
        self.model_type = "local"
        self.model_name = model_name
        self.device = device

        self.num_epochs = num_epochs
        self.group_size = group_size
        self.groups_per_batch = groups_per_batch
        self.learning_rate = learning_rate
        self.adv_estimator = adv_estimator
        self.adv_estimator_beta = adv_estimator_beta
        self.loss_fn = loss_fn
        self.lora_rank = lora_rank
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.num_substeps = num_substeps
        self.max_expansion_rounds = max_expansion_rounds
        self.micro_batch_size = micro_batch_size
        self.grad_clip = grad_clip

        self._custom_system_prompt: Optional[str] = None
        self._pretrain_stats: Dict[str, Any] = {}

        resolved = _resolve_model_path(model_name, model_path)
        print(f"[Discover] Loading model from {resolved} on {device}")

        self.tokenizer = AutoTokenizer.from_pretrained(resolved, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        self.model = AutoModelForCausalLM.from_pretrained(
            resolved,
            torch_dtype=torch.bfloat16,
            device_map={"": device},
            trust_remote_code=True,
        )

        lora_cfg = LoraConfig(
            r=lora_rank,
            lora_alpha=16,
            lora_dropout=0.0,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "v_proj", "gate_proj", "down_proj", "up_proj"],
        )
        self.model = get_peft_model(self.model, lora_cfg)
        print(f"[Discover] LoRA applied (r={lora_rank})")
        self.model.print_trainable_parameters()

        self.initial_lora_A: Dict[str, torch.Tensor] = {}
        for name, param in self.model.named_parameters():
            if "lora_A" in name:
                self.initial_lora_A[name] = param.data.clone().detach()

        self._assistant_header_ids = self._detect_assistant_header_ids()

    def get_system_prompt(self) -> str:
        return self._custom_system_prompt or SYSTEM_PROMPT

    def set_custom_system_prompt(self, prompt: str):
        self._custom_system_prompt = prompt

    def reset_conversation(self):
        self._custom_system_prompt = None

    def get_token_statistics(self) -> dict:
        return self._pretrain_stats

    def cleanup(self):
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

    def reset_lora(self):
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
        temperature: float = 1.0,
        max_new_tokens: int = 65536,
    ) -> Tuple[str, int, int]:
        input_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        inputs = self.tokenizer(
            input_text, return_tensors="pt", truncation=True,
            max_length=min(65536, 2048 + max_new_tokens),
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
        self.model.eval()
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": prompt},
        ]
        raw_output, p_len, r_len = self._generate_text(
            messages, temperature=0.7, max_new_tokens=self.max_tokens,
        )
        code = _extract_code(raw_output)
        return code, raw_output, {"prompt_tokens": p_len, "completion_tokens": r_len, "total_tokens": p_len + r_len}

    def generate_code_from_messages(self, messages: list) -> Tuple[Optional[str], Optional[str], Dict]:
        self.model.eval()
        raw_output, p_len, r_len = self._generate_text(
            messages, temperature=0.7, max_new_tokens=self.max_tokens,
        )
        code = _extract_code(raw_output)
        return code, raw_output, {"prompt_tokens": p_len, "completion_tokens": r_len, "total_tokens": p_len + r_len}

    # ------------------------------------------------------------------
    # Single rollout: prompt -> generate -> verify -> (reward, feedback)
    # ------------------------------------------------------------------

    def _do_single_rollout(
        self,
        prompt_text: str,
        task_prompt: Dict[str, Any],
        verifier: Any,
    ) -> Dict[str, Any]:
        """One rollout: generate from prompt_text, verify, return trajectory dict."""
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": prompt_text},
        ]
        raw_output, _, _ = self._generate_text(
            messages, temperature=self.temperature, max_new_tokens=self.max_tokens,
        )
        code = _extract_code(raw_output)

        score = 0.0
        success = False
        error = None
        metrics = {}
        if code and "def build_agent" in (code or "") and len((code or "").strip()) >= 30:
            try:
                success, score, metrics, error = verifier.verify_code(code, headless=True, save_gif_path=None)
            except Exception as exc:
                error = str(exc)
                score = 0.0
                metrics = {"error_type": "verification_error", "error_message": str(exc)}
        else:
            error = "missing build_agent or code too short" if code else "no code extracted"
            metrics = {"error_type": "code_validation", "error_message": error}

        from evaluation.feedback import format_feedback
        failed = metrics.get("failed", False)
        failure_reason = metrics.get("failure_reason")
        feedback_text = format_feedback(
            metrics, score, success, failed, failure_reason, 0,
            error=error, task_name="(discover)", include_suggestions=False,
        )

        reward = score / 100.0  # 0-1

        return {
            "prompt_text": prompt_text,
            "messages": messages,
            "raw_output": raw_output,
            "code": code,
            "score": score,
            "reward": reward,
            "feedback": feedback_text,
            "success": success,
        }

    # ------------------------------------------------------------------
    # Feedback-based expansion (when all rewards same, e.g. all 0)
    # ------------------------------------------------------------------

    def _expand_with_feedback(
        self,
        trajectories: List[Dict[str, Any]],
        task_prompt: Dict[str, Any],
        verifier: Any,
    ) -> List[Dict[str, Any]]:
        """For each trajectory, build revision prompt from feedback, do group_size rollouts. Return extended list."""
        from evaluation.prompt import format_revision_prompt

        extended: List[Dict[str, Any]] = []
        for traj in trajectories:
            code = traj.get("code") or ""
            feedback = traj.get("feedback") or ""
            revision_prompt = format_revision_prompt(task_prompt, code, feedback)
            for _ in range(self.group_size):
                new_traj = self._do_single_rollout(revision_prompt, task_prompt, verifier)
                extended.append(new_traj)
        return extended

    # ------------------------------------------------------------------
    # Run pretrain: num_epochs of (rollout [ + expansion ] -> advantage -> train)
    # ------------------------------------------------------------------

    def run_pretrain(
        self,
        task_prompt: Dict[str, Any],
        verifier: Any,
    ) -> Dict[str, Any]:
        from evaluation.prompt import format_initial_prompt

        self.reset_lora()
        initial_prompt = format_initial_prompt(task_prompt)

        total_trajectories = 0
        expansion_rounds_used = 0
        train_steps_done = 0
        mean_rewards_list: List[float] = []

        print(f"[Discover] Pretrain starting: {self.num_epochs} epochs, group_size={self.group_size} rollouts/epoch")
        for epoch in range(self.num_epochs):
            print(f"  [Discover] Epoch {epoch + 1}/{self.num_epochs}: running {self.group_size} rollouts ...", flush=True)
            # 1) Rollout: group_size samples from initial prompt (or from previous expansion)
            trajectories: List[Dict[str, Any]] = []
            for _ in range(self.group_size):
                traj = self._do_single_rollout(initial_prompt, task_prompt, verifier)
                trajectories.append(traj)

            rewards = [t["reward"] for t in trajectories]
            expansion_round = 0

            # 2) If all same reward (e.g. all 0), do feedback-based expansion (max max_expansion_rounds)
            while _all_same(rewards) and expansion_round < self.max_expansion_rounds:
                expansion_round += 1
                expansion_rounds_used = max(expansion_rounds_used, expansion_round)
                more = self._expand_with_feedback(trajectories, task_prompt, verifier)
                trajectories = more
                rewards = [t["reward"] for t in trajectories]
                if any(r > 0 for r in rewards):
                    break

            total_trajectories += len(trajectories)
            mean_rewards_list.append(sum(rewards) / len(rewards) if rewards else 0.0)

            # 3) Compute advantages (one group = all current trajectories)
            advantages = compute_advantages_single_group(
                rewards,
                adv_estimator=self.adv_estimator,
                adv_estimator_beta=self.adv_estimator_beta,
                device=self.model.device,
            )

            # 4) importance_sampling update: loss = -mean(advantage * log_prob)
            if advantages.abs().max().item() < 1e-9:
                # No gradient signal; skip update
                continue

            samples = [
                {"messages": t["messages"], "response": t["raw_output"], "advantage": advantages[i].item()}
                for i, t in enumerate(trajectories) if t.get("raw_output")
            ]
            if len(samples) < 2:
                continue

            tokenized = self._tokenize_training_samples(samples)
            if tokenized is None:
                continue

            input_ids = tokenized["input_ids"]
            attention_mask = tokenized["attention_mask"]
            response_mask = tokenized["response_mask"]
            adv_tensor = tokenized["advantages"]

            self.model.config.use_cache = False
            self.model.train()
            if hasattr(self.model, "gradient_checkpointing_enable"):
                self.model.gradient_checkpointing_enable()

            optimizer = torch.optim.AdamW(
                [p for p in self.model.parameters() if p.requires_grad],
                lr=self.learning_rate,
                betas=(0.9, 0.95),
                weight_decay=0.0,
            )

            n_samples = input_ids.shape[0]
            for mb_start in range(0, n_samples, self.micro_batch_size):
                mb_end = min(mb_start + self.micro_batch_size, n_samples)
                mb_ids = input_ids[mb_start:mb_end]
                mb_mask = attention_mask[mb_start:mb_end]
                mb_resp = response_mask[mb_start:mb_end]
                mb_adv = adv_tensor[mb_start:mb_end]

                log_probs = compute_per_token_log_probs(self.model, mb_ids, mb_mask)
                # Sum log probs on response tokens only -> trajectory log prob
                traj_log_prob = (log_probs * mb_resp).sum(dim=1)  # (B,)
                loss = -(mb_adv * traj_log_prob).mean()
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    [p for p in self.model.parameters() if p.requires_grad],
                    self.grad_clip,
                )
                optimizer.step()
                train_steps_done += 1

            self.model.eval()
            self.model.config.use_cache = True
            if hasattr(self.model, "gradient_checkpointing_disable"):
                self.model.gradient_checkpointing_disable()

            if (epoch + 1) % 10 == 0 or epoch == 0:
                print(f"  [Discover] Epoch {epoch + 1}/{self.num_epochs}: "
                      f"trajectories={len(trajectories)}, mean_reward={mean_rewards_list[-1]:.4f}")

        torch.cuda.empty_cache()

        mean_reward = float(np.mean(mean_rewards_list)) if mean_rewards_list else 0.0
        self._pretrain_stats = {
            "n_epochs": self.num_epochs,
            "mean_reward": mean_reward,
            "expansion_rounds_used": expansion_rounds_used,
            "expansion_total_trajectories": total_trajectories,
            "train_steps_done": train_steps_done,
        }
        print(f"[Discover] Pretrain complete: {self._pretrain_stats}")
        return self._pretrain_stats

    # ------------------------------------------------------------------
    # Tokenization for training (response mask only on assistant tokens)
    # ------------------------------------------------------------------

    def _detect_assistant_header_ids(self) -> Optional[List[int]]:
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
            if probe_ids[i : i + len(marker_ids)] == marker_ids:
                header_start = max(0, i - 4)
                header_ids = probe_ids[header_start:i]
                if header_ids:
                    return header_ids
        return None

    def _find_assistant_response_range(self, token_ids: List[int]) -> Tuple[int, int]:
        header = self._assistant_header_ids
        if header:
            hlen = len(header)
            for i in range(len(token_ids) - hlen, -1, -1):
                if token_ids[i : i + hlen] == header:
                    return i + hlen, len(token_ids)
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
        start = int(len(token_ids) * 0.4)
        return start, len(token_ids)

    def _tokenize_training_samples(
        self,
        samples: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        all_input_ids = []
        all_attention_masks = []
        all_response_masks = []
        all_advantages = []

        for sample in samples:
            messages = sample["messages"]
            response = sample["response"]
            adv = sample["advantage"]

            full_messages = list(messages) + [{"role": "assistant", "content": response}]
            full_text = self.tokenizer.apply_chat_template(full_messages, tokenize=False)

            enc = self.tokenizer(
                full_text, truncation=True, max_length=16384, return_tensors="pt",
            )
            ids = enc["input_ids"][0]
            mask = enc["attention_mask"][0]

            resp_start, resp_end = self._find_assistant_response_range(ids.tolist())
            resp_mask = torch.zeros(len(ids) - 1, dtype=torch.float)
            if resp_start > 0 and resp_end > resp_start:
                mask_start = max(resp_start - 1, 0)
                mask_end = min(resp_end - 1, len(ids) - 1)
                resp_mask[mask_start:mask_end] = 1.0

            all_input_ids.append(ids)
            all_attention_masks.append(mask)
            all_response_masks.append(resp_mask)
            all_advantages.append(adv)

        if not all_input_ids:
            return None

        device = self.model.device
        max_len = max(ids.shape[0] for ids in all_input_ids)

        padded_ids = torch.full(
            (len(all_input_ids), max_len), self.tokenizer.pad_token_id,
            dtype=torch.long, device=device,
        )
        padded_attn = torch.zeros((len(all_input_ids), max_len), dtype=torch.long, device=device)
        padded_resp = torch.zeros((len(all_input_ids), max_len - 1), dtype=torch.float, device=device)

        for i, (ids, attn, resp) in enumerate(zip(all_input_ids, all_attention_masks, all_response_masks)):
            L = ids.shape[0]
            padded_ids[i, :L] = ids.to(device)
            padded_attn[i, :L] = attn.to(device)
            padded_resp[i, : L - 1] = resp.to(device)

        advantages = torch.tensor(all_advantages, dtype=torch.float, device=device)

        return {
            "input_ids": padded_ids,
            "attention_mask": padded_attn,
            "response_mask": padded_resp,
            "advantages": advantages,
        }


# ============================================================================
# Factory
# ============================================================================

def get_discover_solver(
    model_name: str,
    model_path: Optional[str] = None,
    device: str = "cuda:0",
    discover_num_epochs: int = 50,
    discover_group_size: int = 8,
    discover_groups_per_batch: int = 64,
    discover_learning_rate: float = 4e-5,
    discover_adv_estimator: str = "entropic",
    discover_adv_estimator_beta: float = 2.0,
    discover_loss_fn: str = "importance_sampling",
    discover_lora_rank: int = 32,
    discover_max_tokens: int = 65536,
    discover_temperature: float = 1.0,
    discover_num_substeps: int = 1,
    discover_max_expansion_rounds: int = 2,
    **kwargs,
) -> DiscoverSolver:
    return DiscoverSolver(
        model_name=model_name,
        model_path=model_path,
        device=device,
        num_epochs=discover_num_epochs,
        group_size=discover_group_size,
        groups_per_batch=discover_groups_per_batch,
        learning_rate=discover_learning_rate,
        adv_estimator=discover_adv_estimator,
        adv_estimator_beta=discover_adv_estimator_beta,
        loss_fn=discover_loss_fn,
        lora_rank=discover_lora_rank,
        max_tokens=discover_max_tokens,
        temperature=discover_temperature,
        num_substeps=discover_num_substeps,
        max_expansion_rounds=discover_max_expansion_rounds,
        **kwargs,
    )
