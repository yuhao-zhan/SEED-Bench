#!/usr/bin/env python3
"""
AZR-style 2D training: REINFORCE++ with PPO clipping, multi-GPU.
Aligned with Absolute-Zero-Reasoner (arXiv:2505.03335) and official repo:
  baseline/Parameter_Policy/Absolute-Zero-Reasoner/
  - configs/azr_ppo_trainer.yaml (lr 1e-6, clip 0.2, grad_clip 1.0, temp 1.0)
  - scripts/selfplay/*.sh (PROPOSE + SOLVE; TRR++ per task_type and role)
See ALIGNMENT.md and OFFICIAL_WORKFLOW.md in this package.

Algorithm (matching AZR repo: adv_estimator=reinforce_plus_plus, PPO clip=0.2):
  1. Generate responses (model.generate)
  2. Compute old log-probs (forward, no grad)
  3. Verify with 2D CodeVerifier -> rewards (Eq.6: format/correct/wrong)
  4. REINFORCE++ advantage: A = whiten(R) globally (single task type => same as TRR++ with one group)
  5. PPO update (1 epoch): loss = -min(ratio*A, clip(ratio)*A)

Multi-GPU via HuggingFace Accelerate + DeepSpeed ZeRO-2/3.

Launch examples (from scripts/):
  # Single GPU (debug)
  python methods/Parameter_Policy/absolute_zero/training/train.py \\
      --model-name Qwen/Qwen3-8B --task category_1 --steps 50

  # 8x A100, ZeRO-2 (8B / 14B)
  accelerate launch --config_file methods/Parameter_Policy/absolute_zero/training/accelerate_zero2.yaml \\
      methods/Parameter_Policy/absolute_zero/training/train.py \\
      --model-name Qwen/Qwen3-8B --task all --total-batch-size 64 --steps 200

  # 8x A100, ZeRO-3 (32B)
  accelerate launch --config_file methods/Parameter_Policy/absolute_zero/training/accelerate_zero3.yaml \\
      methods/Parameter_Policy/absolute_zero/training/train.py \\
      --model-name Qwen/Qwen3-32B --task all --total-batch-size 32 --steps 200
"""
import os
import sys
import argparse
import random
import math
from typing import List, Tuple, Dict, Any, Optional

import torch
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_AZ_DIR = os.path.dirname(_THIS_DIR)
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(_AZ_DIR)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from methods.Parameter_Policy.absolute_zero.training.task_pool import build_task_pool
from methods.Parameter_Policy.absolute_zero.training.task_proposer import propose_batch, _is_concrete_task_spec
from methods.Parameter_Policy.absolute_zero.training.reward_2d import compute_reward
from methods.Parameter_Policy.absolute_zero.training.logging_utils import (
    ensure_log_dir, log_proposed_tasks, log_verify_results, log_rewards_summary,
)
from methods.Parameter_Policy.absolute_zero.absolute_zero_method import (
    SYSTEM_PROMPT, _extract_code,
)

# Local models: do not download from HuggingFace; load from this directory.
LOCAL_MODELS_DIR = os.environ.get("LOCAL_MODELS_DIR", "/home/test/testdata/models")


def resolve_model_path(
    model_name: str,
    model_path: Optional[str],
    models_root: Optional[str] = None,
) -> str:
    """Resolve to local path under models_root (or LOCAL_MODELS_DIR) when possible. Never hits HF."""
    root = models_root or LOCAL_MODELS_DIR
    base = model_path or model_name
    if os.path.isabs(base) and os.path.isdir(base):
        return base
    # e.g. Qwen/Qwen3-8B -> Qwen3-8B
    local_name = os.path.basename(base.rstrip("/"))
    local_path = os.path.join(root, local_name)
    if os.path.isdir(local_path):
        return local_path
    return base


# ===========================================================================
# Core RL functions (faithful to AZR: REINFORCE++ + PPO clipping)
# ===========================================================================

def compute_per_token_log_probs(
    model, input_ids: torch.Tensor, attention_mask: torch.Tensor
) -> torch.Tensor:
    """Forward pass -> per-token log-probs.  logits[t] predicts token[t+1].

    Memory-efficient: uses F.cross_entropy instead of materialising full
    (B, L, V) log-softmax tensor.
    """
    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
    logits = outputs.logits[:, :-1, :]   # (B, L-1, V)
    labels = input_ids[:, 1:]            # (B, L-1)
    # cross_entropy computes -log p(label) without materialising the full softmax
    token_log_probs = -F.cross_entropy(
        logits.reshape(-1, logits.size(-1)),
        labels.reshape(-1),
        reduction="none",
    ).reshape(labels.shape)              # (B, L-1)
    del logits, outputs                  # free VRAM immediately
    return token_log_probs


def reinforce_pp_advantages(
    rewards: torch.Tensor, accelerator=None
) -> torch.Tensor:
    """REINFORCE++ advantage: global whitening of outcome rewards.

    AZR uses gamma=1.0 with outcome reward -> R_t = r for all response tokens.
    Advantage = (r - mean(r)) / (std(r) + eps), computed globally across all ranks.
    """
    if accelerator is not None and accelerator.num_processes > 1:
        all_rewards = accelerator.gather(rewards.detach())
    else:
        all_rewards = rewards.detach()
    mean_r = all_rewards.mean()
    std_r = all_rewards.std().clamp(min=1e-8)
    advantages = (rewards - mean_r) / std_r
    return advantages


def ppo_clip_loss(
    new_log_probs: torch.Tensor,
    old_log_probs: torch.Tensor,
    advantages: torch.Tensor,
    response_mask: torch.Tensor,
    clip_ratio: float = 0.2,
) -> torch.Tensor:
    """PPO clipped surrogate loss (per-token, matching AZR clip_ratio=0.2, 1 epoch).

    Clamp log probs to avoid -inf at padding/non-response positions (which would make
    ratio=exp(new-old) explode to inf and produce nan loss, corrupting the model).
    """
    LOG_PROB_CLAMP = -50.0  # avoid -inf so ratio stays finite
    new_lp = new_log_probs.clamp(min=LOG_PROB_CLAMP, max=0.0)
    old_lp = old_log_probs.clamp(min=LOG_PROB_CLAMP, max=0.0)
    ratio = torch.exp(new_lp - old_lp)
    surr1 = ratio * advantages
    surr2 = torch.clamp(ratio, 1.0 - clip_ratio, 1.0 + clip_ratio) * advantages
    token_loss = -torch.min(surr1, surr2)
    # Only response positions contribute; zero elsewhere and replace any nan/inf
    token_loss = token_loss * response_mask
    token_loss = torch.nan_to_num(token_loss, nan=0.0, posinf=0.0, neginf=0.0)
    resp_sum = response_mask.sum().clamp(min=1.0)
    loss = token_loss.sum() / resp_sum
    return loss


def azr_reward(
    code: Optional[str],
    task_name: str,
    max_steps: int,
    env_overrides: Optional[Dict[str, Any]] = None,
) -> Tuple[float, bool, float, Optional[str]]:
    """Reward aligned with AZR paper Eq.6 (format -1, wrong-but-formatted -0.5, correct r_role).

    Official: format error -> -1; wrong but well-formatted -> -0.5; correct -> 0--1.
    We use tiered shaping for 2D (denser signal):

    -1.0  : no code extracted / no build_agent / empty  (format_error)
    -0.8  : code too short or trivially broken  (format_error)
    -0.5  : syntax error or import error        (code_error; aligns with -0.5 wrong-but-formatted)
    -0.3  : runtime error during simulation     (runtime_error)
     0→1  : score / 100  (partial or full success)
    """
    if not code:
        return -1.0, False, 0.0, "format_error: no code extracted"
    if "def build_agent" not in code:
        return -1.0, False, 0.0, "format_error: missing build_agent"
    if len(code.strip()) < 30:
        return -0.8, False, 0.0, "format_error: code too short"

    # Try compile as syntax check
    try:
        compile(code, "<agent>", "exec")
    except SyntaxError as e:
        return -0.5, False, 0.0, f"syntax_error: {e}"

    raw_reward, success, score, metrics, error = compute_reward(
        task_name, code, max_steps=max_steps, headless=True, scale_to_01=True,
        env_overrides=env_overrides,
    )

    if error:
        err_lower = (error or "").lower()
        # Distinguish syntax/import errors from runtime errors
        if any(k in err_lower for k in ("syntax", "import", "indentation", "name")):
            return -0.5, False, score, error
        if any(k in err_lower for k in ("runtime", "exception", "error", "traceback")):
            return -0.3, False, score, error
        # Generic error but code was well-formatted
        if score == 0.0:
            return -0.3, False, score, error

    # Partial or full success: reward = score / 100 (0→1)
    return raw_reward, success, score, error


# ===========================================================================
# Prompt helpers
# ===========================================================================

def build_prompt(tokenizer, prompt_str: str) -> str:
    """Build full prompt using chat template (if available) or plain format."""
    if hasattr(tokenizer, "chat_template") and tokenizer.chat_template:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_str},
        ]
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    return f"{SYSTEM_PROMPT}\n\nUser:\n{prompt_str}\n\nAssistant:\n"


def make_propose_generate_fn(
    model,
    tokenizer,
    device,
    accelerator=None,
    max_new_tokens: int = 1024,
    temperature: float = 0.7,
    max_prompt_length: int = 4096,
):
    """Return a callable (prompt_text: str) -> str for LLM-based task proposal (no grad)."""
    def generate_fn(prompt_text: str) -> str:
        unwrapped = accelerator.unwrap_model(model) if accelerator else model
        unwrapped.eval()
        messages = [{"role": "user", "content": prompt_text}]
        if hasattr(tokenizer, "apply_chat_template") and tokenizer.apply_chat_template:
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            text = f"User:\n{prompt_text}\n\nAssistant:\n"
        enc = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=max_prompt_length,
            padding=True,
        )
        input_ids = enc.input_ids.to(device)
        attn = enc.attention_mask.to(device) if enc.attention_mask is not None else None
        with torch.no_grad():
            out = unwrapped.generate(
                input_ids=input_ids,
                attention_mask=attn,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=temperature,
                top_p=1.0,
                pad_token_id=tokenizer.pad_token_id,
            )
        response = tokenizer.decode(
            out[0][input_ids.shape[1]:], skip_special_tokens=True
        )
        unwrapped.train()
        return response.strip()
    return generate_fn


# ===========================================================================
# Main training loop
# ===========================================================================

def parse_args():
    p = argparse.ArgumentParser(
        description="AZR 2D training: REINFORCE++ / PPO, multi-GPU via Accelerate+DeepSpeed"
    )
    # Task source: "all" = template proposer; "category_1_01" = propose from S_01's stages (concrete task).
    # Prefix "fixed:" to use benchmark task pool (debug only, data leakage!).
    p.add_argument("--task", type=str, default="all",
                   help="'all' = template proposer. Concrete task e.g. 'category_1_01' = propose from that task's stages (S_01). 'fixed:category_1' = benchmark pool (data leakage!)")
    p.add_argument("--llm-propose", action="store_true",
                   help="When --task is a concrete task (e.g. category_1_01), use the model to propose related task variations (official AZR: LLM proposes from reference). Else sample stages programmatically.")
    # Model (local only: resolved under --models-root, no HuggingFace download)
    p.add_argument("--model-name", type=str, required=True,
                   help="Short name e.g. Qwen/Qwen3-8B -> loads from {models-root}/Qwen3-8B")
    p.add_argument("--model-path", type=str, default=None,
                   help="Override: exact path to model dir (still local_files_only)")
    p.add_argument("--models-root", type=str, default=LOCAL_MODELS_DIR,
                   help="Local models directory (default: env LOCAL_MODELS_DIR or /home/test/testdata/models)")
    # Training (matching AZR hyperparams)
    p.add_argument("--total-batch-size", type=int, default=64,
                   help="Total batch size across all GPUs (AZR 14b: 64)")
    p.add_argument("--micro-batch-size", type=int, default=1,
                   help="Micro-batch for PPO forward (per GPU). Grad-accum = local_batch / micro")
    p.add_argument("--steps", type=int, default=200, help="Training steps")
    p.add_argument("--lr", type=float, default=1e-6, help="Learning rate (AZR: 1e-6)")
    p.add_argument("--clip-ratio", type=float, default=0.2, help="PPO clip (AZR: 0.2)")
    p.add_argument("--grad-clip", type=float, default=1.0, help="Gradient norm clip")
    p.add_argument("--temperature", type=float, default=1.0, help="Generation temp (AZR: 1.0)")
    p.add_argument("--top-p", type=float, default=1.0, help="AZR: 1.0 (full diversity)")
    p.add_argument("--max-prompt-length", type=int, default=8096, help="AZR: 8096")
    p.add_argument("--max-response-length", type=int, default=8096,
                   help="Max new tokens for generation (AZR default: 8096). Ample for reasoning+code.")
    # Verifier
    p.add_argument("--max-steps-verifier", type=int, default=10000)
    # Logging & checkpoints
    _default_runs = os.path.join(_AZ_DIR, "runs")
    p.add_argument("--log-dir", type=str, default=_default_runs,
                   help="Log/run directory (default: absolute_zero/runs/)")
    p.add_argument("--save-dir", type=str, default=None)
    p.add_argument("--save-every", type=int, default=10, help="Save checkpoint every N steps (AZR: 10)")
    p.add_argument("--seed", type=int, default=1, help="Random seed (official AZR: 1)")
    p.add_argument("--propose-max-tokens", type=int, default=1024,
                   help="Max new tokens for LLM proposal step (--llm-propose); default 1024")
    return p.parse_args()


def main():
    args = parse_args()

    # ----- Accelerator (handles DeepSpeed / multi-GPU) -----
    try:
        from accelerate import Accelerator
        from accelerate.utils import set_seed
        accelerator = Accelerator(
            gradient_accumulation_steps=1,
            mixed_precision="bf16",
        )
        set_seed(args.seed)
        is_main = accelerator.is_main_process
        device = accelerator.device
        num_procs = accelerator.num_processes
        local_rank = accelerator.local_process_index
    except ImportError:
        # Fallback: single GPU
        accelerator = None
        is_main = True
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        num_procs = 1
        local_rank = 0
        random.seed(args.seed)
        torch.manual_seed(args.seed)

    # Local batch size
    assert args.total_batch_size % num_procs == 0, \
        f"total-batch-size ({args.total_batch_size}) must be divisible by num GPUs ({num_procs})"
    local_batch_size = args.total_batch_size // num_procs

    # Build log directory.
    # If --log-dir is the default (absolute_zero/runs/), auto-create a descriptive
    # subdirectory: runs/{model}_{task}_{date}/.  Otherwise use the path as-is.
    from datetime import datetime
    _default_runs = os.path.join(_AZ_DIR, "runs")
    if os.path.abspath(args.log_dir) == os.path.abspath(_default_runs):
        model_short = os.path.basename(args.model_name).replace("/", "_")
        task_short = args.task.replace(",", "-")
        run_name = f"{model_short}_{task_short}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        log_dir = os.path.join(os.path.abspath(args.log_dir), run_name)
    else:
        log_dir = os.path.abspath(args.log_dir)
    save_dir = args.save_dir or os.path.join(log_dir, "checkpoints")
    if is_main:
        ensure_log_dir(log_dir)
        ensure_log_dir(save_dir)

    # ----- Task source -----
    # fixed:<spec> = use benchmark task pool (debug/ablation only, data leakage).
    # Otherwise: use proposer. If --task is a concrete task (e.g. category_1_01 for S_01),
    # propose related tasks from that task's curriculum stages (AZR: reference → variations).
    # If --task is "all", use template-based proposer (demo/basic variations).
    use_proposer = not args.task.startswith("fixed:")
    proposer_base_task = None  # concrete task for propose_batch (e.g. category_1_01)
    pool = None
    if not use_proposer:
        fixed_spec = args.task.split(":", 1)[1]
        pool = build_task_pool(fixed_spec, shuffle=True, seed=args.seed)
        if not pool:
            if is_main:
                print("ERROR: No tasks in pool. Check --task.")
            return 1
        if is_main:
            print(f"[WARN] Using FIXED benchmark tasks (data leakage!) pool={len(pool)}")
    else:
        if _is_concrete_task_spec(args.task):
            proposer_base_task = args.task.strip()
            if is_main:
                print(f"Task source: proposer from concrete task {proposer_base_task!r} (stages as variations)")
        else:
            if is_main:
                print("Task source: proposer (template-based demo variations)")
    if is_main and use_proposer and proposer_base_task and getattr(args, "llm_propose", False):
        print("Task proposal: LLM-based (model proposes related variations from reference task; official AZR style)")
    if is_main:
        print(f"GPUs: {num_procs}, local_batch_size: {local_batch_size}, "
              f"total_batch_size: {args.total_batch_size}")

    # ----- Model + Tokenizer (local only: no HuggingFace download) -----
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_path = resolve_model_path(args.model_name, args.model_path, args.models_root)
    if is_main:
        print(f"Loading model (local): {model_path}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=True,
        padding_side="left",
        local_files_only=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # Pick best available attention implementation (flash_attention_2 > sdpa > eager)
    _attn_impl = None
    if torch.cuda.is_available():
        try:
            import flash_attn  # noqa: F401
            _attn_impl = "flash_attention_2"
        except ImportError:
            _attn_impl = "sdpa"  # PyTorch scaled-dot-product fallback
    if is_main:
        print(f"Attention implementation: {_attn_impl or 'default'}")

    model_kwargs = dict(
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        local_files_only=True,
    )
    if _attn_impl is not None:
        model_kwargs["attn_implementation"] = _attn_impl

    model = AutoModelForCausalLM.from_pretrained(model_path, **model_kwargs)
    model.gradient_checkpointing_enable()

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.0)

    # Prepare with accelerator (wraps model in DeepSpeed / FSDP)
    if accelerator is not None:
        # DeepSpeed needs train_micro_batch_size_per_gpu when no DataLoader is passed
        if hasattr(accelerator.state, "deepspeed_plugin") and accelerator.state.deepspeed_plugin is not None:
            ds_plugin = accelerator.state.deepspeed_plugin
            ds_plugin.deepspeed_config["train_micro_batch_size_per_gpu"] = args.micro_batch_size
            if is_main:
                print(f"DeepSpeed train_micro_batch_size_per_gpu = {args.micro_batch_size}")
        model, optimizer = accelerator.prepare(model, optimizer)
    else:
        model = model.to(device)

    if is_main:
        total_params = sum(p.numel() for p in model.parameters())
        print(f"Model params: {total_params / 1e9:.1f}B, device: {device}")

    # ==================================================================
    # Training loop
    # ==================================================================
    for step in range(1, args.steps + 1):
        model.train()

        # --- 1. Sample local batch (each rank gets different samples) ---
        if use_proposer:
            # Propose: from concrete task's stages (if proposer_base_task) or from templates.
            # With --llm-propose, the model proposes related variations (official AZR: LLM proposes from reference).
            propose_seed = args.seed + step * num_procs + local_rank
            generate_fn = None
            if proposer_base_task and getattr(args, "llm_propose", False):
                generate_fn = make_propose_generate_fn(
                    model, tokenizer, device, accelerator,
                    max_new_tokens=getattr(args, "propose_max_tokens", 1024),
                    temperature=0.7,
                    max_prompt_length=min(args.max_prompt_length, 4096),
                )
            proposed = propose_batch(
                local_batch_size,
                seed=propose_seed,
                rank=local_rank,
                step=step,
                base_task_name=proposer_base_task,
                generate_fn=generate_fn,
            )
            # proposed: list of (task_name, base_task, prompt_str, variation_dict, env_overrides)
            task_batch = [
                # (display_name, base_task_for_verifier, variation, prompt_str, env_overrides)
                (p[0], p[1], p[3], p[2], p[4])
                for p in proposed
            ]
        else:
            # Fixed tasks (debug / ablation only, has data leakage)
            offset = (step - 1) * args.total_batch_size + local_rank * local_batch_size
            fixed_batch = [pool[(offset + i) % len(pool)] for i in range(local_batch_size)]
            task_batch = [
                # (display_name, verifier_task, variation, prompt_str, env_overrides)
                (t[0], t[0], {}, t[2], None)
                for t in fixed_batch
            ]

        if is_main:
            log_proposed_tasks(log_dir, step, [
                {"task_name": t[0], "prompt_str": t[3],
                 "variation": t[2] if use_proposer else None,
                 "source": "proposer" if use_proposer else "fixed"}
                for t in task_batch
            ])

        # --- 2. Build prompts & tokenize (left-padding for generation) ---
        prompt_texts = [build_prompt(tokenizer, t[3]) for t in task_batch]
        enc = tokenizer(
            prompt_texts, return_tensors="pt", padding=True,
            truncation=True, max_length=args.max_prompt_length,
        )
        prompt_ids = enc.input_ids.to(device)
        prompt_mask = enc.attention_mask.to(device)
        prompt_len = prompt_ids.shape[1]

        # --- 3. Generate (no grad) ---
        unwrapped = accelerator.unwrap_model(model) if accelerator else model
        unwrapped.eval()  # disable dropout for generation
        with torch.no_grad():
            gen_out = unwrapped.generate(
                input_ids=prompt_ids,
                attention_mask=prompt_mask,
                max_new_tokens=args.max_response_length,
                do_sample=True,
                temperature=args.temperature,
                top_p=args.top_p,
                pad_token_id=tokenizer.pad_token_id,
            )
        model.train()

        # Separate response tokens
        full_ids = gen_out                              # (B, prompt_len + resp_len)
        resp_ids = gen_out[:, prompt_len:]              # (B, resp_len)
        full_len = full_ids.shape[1]

        # Build attention mask for full sequence (prompt mask + response mask)
        full_mask = torch.ones(full_ids.shape, dtype=torch.long, device=device)
        full_mask[:, :prompt_len] = prompt_mask
        # Mask out padding in response (pad tokens after EOS)
        resp_mask_2d = torch.ones_like(resp_ids, dtype=torch.float)
        for i in range(resp_ids.shape[0]):
            eos_positions = (resp_ids[i] == tokenizer.eos_token_id).nonzero(as_tuple=True)[0]
            if len(eos_positions) > 0:
                first_eos = eos_positions[0].item() + 1  # include EOS
                resp_mask_2d[i, first_eos:] = 0.0
                full_mask[i, prompt_len + first_eos:] = 0
            pad_positions = (resp_ids[i] == tokenizer.pad_token_id).nonzero(as_tuple=True)[0]
            if len(pad_positions) > 0:
                first_pad = pad_positions[0].item()
                resp_mask_2d[i, first_pad:] = 0.0
                full_mask[i, prompt_len + first_pad:] = 0

        # Response mask shifted for log-prob alignment (logits[t] -> token[t+1])
        # response_mask_shifted[t] = 1 iff token[t+1] is a response token
        response_mask = torch.zeros(full_ids.shape[0], full_len - 1, device=device)
        if resp_ids.shape[1] > 0:
            response_mask[:, prompt_len - 1: prompt_len - 1 + resp_ids.shape[1]] = resp_mask_2d[
                :, :min(resp_ids.shape[1], full_len - prompt_len)
            ]

        # Free generation KV-cache memory before forward passes
        torch.cuda.empty_cache()

        # --- 4. Old log-probs (no grad, micro-batched for memory) ---
        old_lp_model = unwrapped if accelerator is None else model
        old_lp_chunks = []
        with torch.no_grad():
            for mb_i in range(0, local_batch_size, args.micro_batch_size):
                mb_j = min(mb_i + args.micro_batch_size, local_batch_size)
                chunk_lp = compute_per_token_log_probs(
                    old_lp_model,
                    full_ids[mb_i:mb_j],
                    full_mask[mb_i:mb_j],
                )
                old_lp_chunks.append(chunk_lp.detach())
            old_token_lp = torch.cat(old_lp_chunks, dim=0)

        # --- 5. Decode, extract code, verify -> rewards ---
        rewards_list = []
        results = []
        for i in range(local_batch_size):
            display_name = task_batch[i][0]    # unique proposed name (for logging)
            verifier_task = task_batch[i][1]   # e.g. "demo/basic" (for CodeVerifier)
            env_overrides = task_batch[i][4]   # terrain/physics overrides (or None)
            # Decode only the response part
            resp_tok = resp_ids[i]
            # Remove pad/eos for decoding
            valid_mask = resp_mask_2d[i].bool()
            valid_tokens = resp_tok[valid_mask] if valid_mask.any() else resp_tok[:0]
            resp_text = tokenizer.decode(valid_tokens, skip_special_tokens=True)
            code = _extract_code(resp_text)

            reward_val, success, score, error = azr_reward(
                code, verifier_task, max_steps=args.max_steps_verifier,
                env_overrides=env_overrides,
            )
            rewards_list.append(reward_val)
            results.append({
                "task_name": display_name,         # unique proposed name
                "verifier_task": verifier_task,    # base task used for verification
                "success": success, "score": score,
                "reward": reward_val, "error": error,
                "code": code or "",                # full code, no truncation
                "raw_response": resp_text,         # full model response
            })

        reward_tensor = torch.tensor(rewards_list, device=device, dtype=torch.float)

        # --- 6. REINFORCE++ advantages (global whitening) ---
        advantages = reinforce_pp_advantages(reward_tensor, accelerator)
        # Expand per-sample advantage to per-token
        # advantages: (B,) -> (B, L-1) broadcast
        token_advantages = advantages.unsqueeze(1).expand_as(response_mask) * response_mask

        # --- 7. PPO update (1 epoch, matching AZR ppo_epochs=1) ---
        # Micro-batch with gradient accumulation for memory efficiency
        n_micro = max(1, local_batch_size // args.micro_batch_size)
        total_loss = 0.0
        optimizer.zero_grad()

        for mb_idx in range(n_micro):
            mb_start = mb_idx * args.micro_batch_size
            mb_end = min(mb_start + args.micro_batch_size, local_batch_size)
            mb_full_ids = full_ids[mb_start:mb_end]
            mb_full_mask = full_mask[mb_start:mb_end]
            mb_old_lp = old_token_lp[mb_start:mb_end]
            mb_resp_mask = response_mask[mb_start:mb_end]
            mb_adv = token_advantages[mb_start:mb_end]

            # Forward pass for new log probs
            new_token_lp = compute_per_token_log_probs(model, mb_full_ids, mb_full_mask)
            mb_loss = ppo_clip_loss(new_token_lp, mb_old_lp, mb_adv, mb_resp_mask, args.clip_ratio)
            mb_loss = mb_loss / n_micro  # scale for accumulation

            # Skip backward if loss is nan/inf to avoid corrupting the model
            if torch.isfinite(mb_loss):
                if accelerator is not None:
                    accelerator.backward(mb_loss)
                else:
                    mb_loss.backward()
            total_loss += mb_loss.item() if torch.isfinite(mb_loss) else 0.0

        # Gradient clipping + optimizer step
        if accelerator is not None:
            accelerator.clip_grad_norm_(model.parameters(), args.grad_clip)
        else:
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        optimizer.step()

        # --- 8. Logging (rank 0 only) ---
        mean_reward = reward_tensor.mean().item()
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        if is_main:
            log_verify_results(log_dir, step, results)
            log_rewards_summary(log_dir, step, mean_reward, success_rate, len(results),
                               extra={"loss": total_loss, "advantages_std": advantages.std().item()})
            print(f"[Step {step}/{args.steps}]  reward={mean_reward:.4f}  "
                  f"success={success_rate:.1%}  loss={total_loss:.4f}  "
                  f"n={len(results)}")

        # --- 9. Checkpoint ---
        if args.save_every and step % args.save_every == 0:
            if accelerator is not None:
                accelerator.wait_for_everyone()
                unwrapped_save = accelerator.unwrap_model(model)
                if is_main:
                    ckpt_path = os.path.join(save_dir, f"step_{step}")
                    os.makedirs(ckpt_path, exist_ok=True)
                    unwrapped_save.save_pretrained(
                        ckpt_path, save_function=accelerator.save,
                    )
                    tokenizer.save_pretrained(ckpt_path)
                    print(f"  Saved checkpoint: {ckpt_path}")
            else:
                ckpt_path = os.path.join(save_dir, f"step_{step}")
                os.makedirs(ckpt_path, exist_ok=True)
                model.save_pretrained(ckpt_path)
                tokenizer.save_pretrained(ckpt_path)
                print(f"  Saved checkpoint: {ckpt_path}")

    if is_main:
        print(f"\nTraining complete. Logs: {log_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
