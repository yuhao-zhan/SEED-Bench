"""
Absolute-Zero-Reasoner style inference for 2D_exploration.
Uses AZR repo's model_utils (HF load + generate_completions) with our prompt and code extraction.
Only supports local models (--model-type local). Loads from LOCAL_MODELS_DIR, no HuggingFace download.
"""
import os
import re
import sys
from typing import Optional, Tuple

# Local models: do not download from HuggingFace; load from this directory.
LOCAL_MODELS_DIR = os.environ.get("LOCAL_MODELS_DIR", "/home/test/testdata/models")


def _resolve_model_path(model_name: str, model_path: Optional[str]) -> str:
    """Resolve to local path under LOCAL_MODELS_DIR when possible."""
    base = model_path or model_name
    if os.path.isabs(base) and os.path.isdir(base):
        return base
    local_name = os.path.basename(base.rstrip("/"))
    local_path = os.path.join(LOCAL_MODELS_DIR, local_name)
    if os.path.isdir(local_path):
        return local_path
    return base

# Resolve paths: this file is at methods/Parameter_Policy/absoulute_zero/absolute_zero_method.py
# _SCRIPTS_DIR = scripts/
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_AZR_EVAL_ROOT = os.path.join(
    _SCRIPTS_DIR, "..", "..", "baseline", "Parameter_Policy",
    "Absolute-Zero-Reasoner", "evaluation", "math_eval", "eval"
)
_AZR_EVAL_ROOT = os.path.normpath(os.path.abspath(_AZR_EVAL_ROOT))
if _AZR_EVAL_ROOT not in sys.path:
    sys.path.insert(0, _AZR_EVAL_ROOT)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Same code extraction logic as SolverInterface._extract_code (evaluation/solver_interface.py)
def _extract_code(raw_text: str) -> str:
    """Extract Python code from raw text (```python ... ``` or ``` ... ```)."""
    reasoning_end_markers = ["</think>", "</think>", "</think>"]
    reasoning_start_markers = ["<think>", "<think>", "<think>"]

    reasoning_end_pos = -1
    for marker in reasoning_end_markers:
        pos = raw_text.find(marker)
        if pos > reasoning_end_pos:
            reasoning_end_pos = pos + len(marker)

    if reasoning_end_pos >= 0:
        raw_text = raw_text[reasoning_end_pos:].strip()
    else:
        reasoning_start_pos = -1
        for marker in reasoning_start_markers:
            pos = raw_text.rfind(marker)
            if pos > reasoning_start_pos:
                reasoning_start_pos = pos
        if reasoning_start_pos >= 0:
            code_block_start = raw_text.find("```", reasoning_start_pos)
            if code_block_start >= 0:
                raw_text = raw_text[code_block_start:].strip()

    code_block_pattern = r"```(?:python)?\s*\n?(.*?)```"
    matches = list(re.finditer(code_block_pattern, raw_text, re.DOTALL))

    if not matches:
        incomplete_pattern = r"```(?:python)?\s*\n?(.*)"
        incomplete_match = re.search(incomplete_pattern, raw_text, re.DOTALL)
        if incomplete_match:
            code = incomplete_match.group(1).strip()
            code = re.sub(r"```.*$", "", code, flags=re.DOTALL)
            code = re.sub(r"<think>.*$", "", code, flags=re.DOTALL)
            code = re.sub(r"<think>.*$", "", code, flags=re.DOTALL)
            code = re.sub(r"<think>.*$", "", code, flags=re.DOTALL)
            if len(code.strip()) > 50:
                return code.strip()
        return ""

    if len(matches) == 1:
        code = matches[0].group(1).strip()
    else:
        code = max(matches, key=lambda m: len(m.group(1).strip())).group(1).strip()

    code = re.sub(r"```(?:python)?", "", code)
    code = re.sub(r"```", "", code)
    return code.strip()


# System prompt aligned with SolverInterface (2D physics agent design)
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



class AbsoluteZeroSolver:
    """Solver that uses vLLM for inference."""

    def __init__(self, model_name, model_path=None, device=None):
        self.model_type = "local"
        self.model_name = model_name
        self.model_path = model_path or model_name
        self._resolved_path = _resolve_model_path(model_name, model_path)
        self.device = device or "auto"
        self._engine = None
        self._tokenizer = None

    def _ensure_loaded(self):
        if self._engine is not None:
            return
        os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
        from vllm import LLM
        import torch
        tp_size = 1
        if torch.cuda.is_available():
            tp_size = torch.cuda.device_count()
        tp_env = os.environ.get("VLLM_TENSOR_PARALLEL_SIZE", "").strip()
        if tp_env:
            tp_size = int(tp_env)
        max_model_len = int(os.environ.get("VLLM_MAX_MODEL_LEN", "32768"))
        gpu_mem_util = float(os.environ.get("VLLM_GPU_MEMORY_UTILIZATION", "0.9"))
        # enforce_eager=True avoids torch.compile and corrupted compile cache (checksum errors)
        self._engine = LLM(
            model=self._resolved_path, tensor_parallel_size=tp_size,
            trust_remote_code=True, max_model_len=max_model_len,
            gpu_memory_utilization=gpu_mem_util, dtype="auto",
            enforce_eager=True,
        )
        self._tokenizer = self._engine.get_tokenizer()

    def get_system_prompt(self):
        return SYSTEM_PROMPT

    def set_custom_system_prompt(self, prompt):
        pass

    def reset_conversation(self):
        pass

    def get_token_statistics(self):
        return {}

    def cleanup(self):
        """Shut down vLLM engine and release GPU memory."""
        if self._engine is not None:
            try:
                if hasattr(self._engine, 'llm_engine'):
                    engine = self._engine.llm_engine
                    if hasattr(engine, 'engine_core') and hasattr(engine.engine_core, 'shutdown'):
                        engine.engine_core.shutdown()
            except Exception:
                pass
            del self._engine
            self._engine = None
            self._tokenizer = None
            import gc; gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    def __del__(self):
        self.cleanup()

    def generate_code(self, prompt, use_conversation=False, reset_conversation=False, seed=None):
        """Generate code via vLLM. seed is optional for reproducibility."""
        self._ensure_loaded()
        from vllm import SamplingParams
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        if hasattr(self._tokenizer, "apply_chat_template"):
            input_text = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )
        else:
            input_text = f"{SYSTEM_PROMPT}\n\nUser:\n{prompt}\n\nAssistant:\n"
        max_tokens = int(os.environ.get("VLLM_MAX_TOKENS", "131072"))  # default 128k; set env to override
        kwargs = {"temperature": 0.7, "top_p": 0.9, "max_tokens": max_tokens}
        if seed is not None:
            kwargs["seed"] = int(seed)
        sampling_params = SamplingParams(**kwargs)
        outputs = self._engine.generate([input_text], sampling_params)
        raw_output = outputs[0].outputs[0].text.strip() if outputs else ""
        code = _extract_code(raw_output)
        return code, raw_output, {}


def get_azr_solver(model_name, model_path=None, device=None):
    """Factory: return an AbsoluteZeroSolver."""
    return AbsoluteZeroSolver(model_name=model_name, model_path=model_path, device=device)
