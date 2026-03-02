"""
SEAL (Self-Evolving Adaptive Learning) — Test-Time Training for 2D exploration tasks.

Adapted from DaVinciBench/baseline/Parameter_Policy/SEAL/few-shot/arclib/update_model.py

Per-task test-time training: each task gets a temporary LoRA adapter trained
on the task's own successful iteration trajectories.

Algorithm:
  Iteration 1:  Generate code with base model (LoRA=0). Verify. Record.
  Iteration 2+: Reset LoRA, retrain on best accumulated solutions, then generate.
"""

import os
import re
import gc
import sys
import torch
from typing import List, Optional, Dict, Tuple, Any

from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
)
from datasets import Dataset

# ---------------------------------------------------------------------------
# We import SEAL's TTT class if possible (for provenance), but fall back to
# a compatible re-implementation when the original repo's ARC-specific
# dependencies are not available.
# ---------------------------------------------------------------------------
_SEAL_FEWSHOT_DIR = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "..",
        "baseline", "Parameter_Policy", "SEAL", "few-shot",
    )
)

# System prompt — identical to the one used by SolverInterface / AbsoluteZeroSolver.
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

    # Strip reasoning tags (<think> … </think>)
    for marker in ("</think>", "</think>", "</think>"):
        pos = raw_text.find(marker)
        if pos >= 0:
            raw_text = raw_text[pos + len(marker):].strip()
            break

    # Find code blocks ```python … ``` or ``` … ```
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


# ============================================================================
# SEALSolver — per-task TTT solver
# ============================================================================

class SEALSolver:
    """
    SEAL Test-Time Training solver for 2D exploration tasks.

    Lifecycle (managed by ``evaluate.py``):
        1. ``__init__``: loads base model + blank LoRA  (LoRA B=0 → base-model behaviour)
        2. ``generate_code()``: inference with current LoRA state
        3. ``train_on_solutions()``: reset LoRA → retrain on best solutions → ready for next generate
        4. ``cleanup()``: free GPU memory

    The LoRA reset-and-retrain pattern follows SEAL's ``TTT.update_model`` from
    ``DaVinciBench/baseline/Parameter_Policy/SEAL/few-shot/arclib/update_model.py``.
    """

    def __init__(
        self,
        model_name: str,
        model_path: Optional[str] = None,
        device: str = "cuda:0",
        lora_rank: int = 128,
        lora_alpha: int = 16,
        learning_rate: float = 1e-4,
        num_train_epochs: int = 2,
        train_batch_size: int = 2,
        gradient_accumulation_steps: int = 1,
        lr_scheduler_type: str = "cosine",
        min_score_threshold: float = 0.0,
        max_training_samples: int = 16,
    ):
        self.model_type = "local"
        self.model_name = model_name
        self.device = device

        # Training hyper-params (SEAL defaults)
        self.learning_rate = learning_rate
        self.num_train_epochs = num_train_epochs
        self.train_batch_size = train_batch_size
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.lr_scheduler_type = lr_scheduler_type
        self.min_score_threshold = min_score_threshold
        self.max_training_samples = max_training_samples

        self._custom_system_prompt: Optional[str] = None
        self._conversation_messages: list = []
        self._train_count = 0

        # Resolve path
        resolved = _resolve_model_path(model_name, model_path)
        print(f"🔧 SEAL: loading model from {resolved} on {device}")

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(resolved, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Model (bf16, single device) — same pattern as SEAL's TTT.__init__
        self.model = AutoModelForCausalLM.from_pretrained(
            resolved,
            torch_dtype=torch.bfloat16,
            device_map={"": device},
            trust_remote_code=True,
        )

        # Apply LoRA — same config as SEAL few-shot (ttt.py lines 354-361)
        lora_cfg = LoraConfig(
            r=lora_rank,
            lora_alpha=lora_alpha,
            lora_dropout=0.0,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "v_proj", "gate_proj", "down_proj", "up_proj"],
        )
        self.model = get_peft_model(self.model, lora_cfg)
        print(f"🔧 SEAL: LoRA applied (r={lora_rank}, α={lora_alpha})")
        self.model.print_trainable_parameters()

        # Store initial LoRA-A values for reset (SEAL update_model.py lines 67-72)
        self.initial_lora_A: Dict[str, torch.Tensor] = {}
        for name, param in self.model.named_parameters():
            if "lora_A" in name:
                self.initial_lora_A[name] = param.data.clone().detach()

        # Pre-compute assistant-header token pattern for loss masking
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
        return {"seal_train_count": self._train_count}

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
    # Inference
    # ------------------------------------------------------------------
    def generate_code(
        self,
        prompt: str,
        use_conversation: bool = False,
        reset_conversation: bool = False,
        seed: Optional[int] = None,
    ) -> Tuple[Optional[str], Optional[str], Dict]:
        """Generate code using the current model+LoRA state (SolverInterface API)."""
        system_prompt = self.get_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        input_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        inputs = self.tokenizer(
            input_text, return_tensors="pt", truncation=True, max_length=16384,
        )
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        self.model.config.use_cache = True
        self.model.eval()

        if seed is not None:
            torch.manual_seed(seed)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=65536,
                temperature=0.7,
                top_p=0.95,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        input_len = inputs["input_ids"].shape[1]
        new_tokens = outputs[0][input_len:]
        raw_output = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        code = _extract_code(raw_output)

        if code is None and raw_output:
            # Debug: help distinguish "model didn't output code block" vs "extraction bug"
            preview = (raw_output[:400] + "…") if len(raw_output) > 400 else raw_output
            print(f"⚠️  SEAL: no code block extracted (raw len={len(raw_output)}). First 400 chars:\n{preview}")

        token_usage = {
            "prompt_tokens": input_len,
            "completion_tokens": len(new_tokens),
            "total_tokens": input_len + len(new_tokens),
        }
        return code, raw_output, token_usage

    def generate_code_from_messages(self, messages: list) -> Tuple[Optional[str], Optional[str], Dict]:
        """Generate code from explicit chat messages."""
        input_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        inputs = self.tokenizer(
            input_text, return_tensors="pt", truncation=True, max_length=16384,
        )
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        self.model.config.use_cache = True
        self.model.eval()

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=65536,
                temperature=0.7,
                top_p=0.95,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        input_len = inputs["input_ids"].shape[1]
        new_tokens = outputs[0][input_len:]
        raw_output = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        code = _extract_code(raw_output)

        token_usage = {
            "prompt_tokens": input_len,
            "completion_tokens": len(new_tokens),
            "total_tokens": input_len + len(new_tokens),
        }
        return code, raw_output, token_usage

    # ------------------------------------------------------------------
    # LoRA reset (SEAL update_model.py TTT.reset_lora, lines 133-140)
    # ------------------------------------------------------------------
    def reset_lora(self):
        """Reset LoRA-B to zero, LoRA-A to initial values."""
        for name, param in self.model.named_parameters():
            if "lora_B" in name:
                param.data.fill_(0.0)
            elif "lora_A" in name and name in self.initial_lora_A:
                param.data.copy_(self.initial_lora_A[name])

    # ------------------------------------------------------------------
    # TTT training step
    # ------------------------------------------------------------------
    def train_on_solutions(
        self,
        solutions: List[Dict[str, Any]],
        output_dir: Optional[str] = None,
    ) -> bool:
        """
        SEAL TTT step: reset LoRA, retrain on accumulated best solutions.

        Follows SEAL ``TTT.update_model`` pattern:
            1. reset_lora()
            2. tokenize + mask labels
            3. Trainer.train()

        Args:
            solutions: list of dicts with keys ``prompt``, ``code``/``raw_output``, ``score``
            output_dir: optional directory to persist LoRA weights

        Returns:
            True if training ran, False if skipped (no valid data).
        """
        # Filter by score threshold
        valid = [s for s in solutions if s.get("score", 0) > self.min_score_threshold]
        if not valid:
            print("🔧 SEAL TTT: no positive-score solutions, skipping training")
            return False

        # Sort descending by score; cap at max_training_samples
        valid.sort(key=lambda s: s.get("score", 0), reverse=True)
        valid = valid[: self.max_training_samples]

        # Build chat-formatted training texts
        system_prompt = self.get_system_prompt()
        training_texts: List[str] = []
        for sol in valid:
            # Use raw_llm_output (analysis + code) when available; fall back to code-only
            assistant_content = sol.get("raw_output") or sol.get("code", "")
            if not assistant_content:
                continue
            msgs = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": sol["prompt"]},
                {"role": "assistant", "content": assistant_content},
            ]
            text = self.tokenizer.apply_chat_template(msgs, tokenize=False)
            training_texts.append(text)

        if not training_texts:
            print("🔧 SEAL TTT: no training texts after formatting, skipping")
            return False

        scores_str = ", ".join(f'{s["score"]:.1f}' for s in valid[:5])
        print(
            f"🔧 SEAL TTT: training on {len(training_texts)} solution(s) "
            f"(top scores: {scores_str})"
        )

        # 1. Reset LoRA (SEAL pattern)
        self.reset_lora()

        # 2. Tokenize + mask (loss only on assistant response tokens)
        tokenized = self._tokenize_and_mask(training_texts)

        # 3. Train
        self.model.config.use_cache = False
        self.model.train()
        torch.cuda.empty_cache()

        ds = Dataset.from_dict(tokenized)
        effective_dir = output_dir or "/tmp/seal_ttt_temp"
        os.makedirs(effective_dir, exist_ok=True)

        # SEAL's training args (update_model.py lines 227-241)
        training_args = TrainingArguments(
            output_dir=effective_dir,
            per_device_train_batch_size=self.train_batch_size,
            gradient_accumulation_steps=self.gradient_accumulation_steps,
            learning_rate=self.learning_rate,
            num_train_epochs=self.num_train_epochs,
            lr_scheduler_type=self.lr_scheduler_type,
            logging_steps=1,
            save_strategy="no",
            report_to="none",
            bf16=True,
            remove_unused_columns=False,
            optim="adamw_torch",
            warmup_steps=min(11, len(training_texts)),
            gradient_checkpointing=True,
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=ds,
        )
        trainer.train()
        self._train_count += 1

        # Restore inference mode
        self.model.config.use_cache = True
        self.model.eval()

        print(f"🔧 SEAL TTT: training complete (step {self._train_count})")

        # Optionally persist LoRA adapter
        if output_dir:
            self.model.save_pretrained(output_dir)
            self.tokenizer.save_pretrained(output_dir)
            print(f"🔧 SEAL TTT: LoRA saved to {output_dir}")

        return True

    # ------------------------------------------------------------------
    # Loss masking — model-agnostic approach
    # ------------------------------------------------------------------
    def _detect_assistant_header_ids(self) -> Optional[List[int]]:
        """
        Detect the token-ID pattern that marks the start of an assistant turn
        for the loaded tokenizer's chat template.  Returns a short list of IDs
        or ``None`` if detection fails.
        """
        # Build a tiny 2-turn message and find the assistant-response boundary
        probe_msgs = [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "U"},
            {"role": "assistant", "content": "ASSISTANT_MARKER_XYZ"},
        ]
        try:
            probe_text = self.tokenizer.apply_chat_template(probe_msgs, tokenize=False)
        except Exception:
            return None

        # Tokenize
        probe_ids = self.tokenizer.encode(probe_text, add_special_tokens=False)

        # Tokenize the marker to find where assistant body starts
        marker_ids = self.tokenizer.encode("ASSISTANT_MARKER_XYZ", add_special_tokens=False)

        # Find marker in probe_ids
        for i in range(len(probe_ids) - len(marker_ids) + 1):
            if probe_ids[i : i + len(marker_ids)] == marker_ids:
                # The assistant header ends just before the marker
                # Grab a few tokens before the marker as the header pattern
                header_start = max(0, i - 4)
                header_ids = probe_ids[header_start:i]
                if header_ids:
                    return header_ids
        return None

    def _find_last_assistant_start(self, token_ids: List[int]) -> Optional[int]:
        """
        Find the token index where the **last** assistant response begins.
        Returns the index of the first token of the response body (after the
        header), or ``None`` on failure.
        """
        header = self._assistant_header_ids
        if header:
            hlen = len(header)
            # Scan backwards for the last occurrence
            for i in range(len(token_ids) - hlen, -1, -1):
                if token_ids[i : i + hlen] == header:
                    return i + hlen  # first response-body token
        # Fallback: decode and search for common markers
        text = self.tokenizer.decode(token_ids, skip_special_tokens=False)
        for marker in (
            "<|im_start|>assistant\n",        # Qwen / ChatML
            "<|start_header_id|>assistant<|end_header_id|>\n\n",  # Llama-3
        ):
            pos = text.rfind(marker)
            if pos >= 0:
                prefix_text = text[: pos + len(marker)]
                prefix_ids = self.tokenizer.encode(prefix_text, add_special_tokens=False)
                return len(prefix_ids)
        return None

    def _tokenize_and_mask(self, texts: List[str]) -> Dict[str, Any]:
        """
        Tokenize texts and create labels with loss masking.
        Only tokens belonging to the last assistant turn are trained on;
        everything else is set to ``-100``.

        Follows the masking strategy from SEAL ``TTT._tokenize_and_process``
        (update_model.py lines 142-195) but uses a model-agnostic header detector.
        """
        outputs = self.tokenizer(
            texts,
            truncation=True,
            max_length=65536,
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
                # Fallback: mask first 80 % (same spirit as SEAL)
                cutoff = int(len(sample_ids) * 0.8)
                for j in range(cutoff):
                    labels[i, j] = -100
                print(f"⚠️  SEAL: assistant-start not found in sample {i}, using 80 % fallback mask")

            # Mask padding
            pad_id = self.tokenizer.pad_token_id
            for j in range(input_ids.shape[1]):
                if input_ids[i, j] == pad_id and labels[i, j] != -100:
                    labels[i, j] = -100

        outputs["labels"] = labels
        return {k: v for k, v in outputs.items()}


# ============================================================================
# Factory
# ============================================================================

def get_seal_solver(
    model_name: str,
    model_path: Optional[str] = None,
    device: str = "cuda:0",
    **kwargs,
) -> SEALSolver:
    """Create and return a :class:`SEALSolver` instance."""
    return SEALSolver(
        model_name=model_name,
        model_path=model_path,
        device=device,
        **kwargs,
    )
