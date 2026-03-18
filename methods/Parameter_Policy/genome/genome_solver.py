"""
GenomeSolver: load base model + best LoRA (from Phase 1) and generate code.
Same interface as AbsoluteZeroSolver: generate_code(prompt, ...) -> (code, raw, token_usage).
Uses HuggingFace + PEFT; supports GENOME-format adapter (keys starting with 'a' and 'b').
"""
import os
import re
import sys
from typing import Optional, Tuple

_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

LOCAL_MODELS_DIR = os.environ.get("LOCAL_MODELS_DIR", "/home/test/testdata/models")


def _resolve_model_path(model_name: str, model_path: Optional[str]) -> str:
    base = model_path or model_name
    if os.path.isabs(base) and os.path.isdir(base):
        return base
    local_name = os.path.basename(base.rstrip("/"))
    local_path = os.path.join(LOCAL_MODELS_DIR, local_name)
    if os.path.isdir(local_path):
        return local_path
    return base


def _extract_code(raw_text: str) -> str:
    """Extract Python code from raw text (same logic as SolverInterface / absolute_zero.absolute_zero_method)."""
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


def _genome_sd_to_peft_sd(genome_sd: dict, peft_state_dict: dict) -> dict:
    """
    Map GENOME-format state dict (keys 'a.xxx', 'b.xxx') to PEFT state dict keys.
    peft_state_dict is from the PEFT model so we know the key names.
    """
    out = {}
    def core_from_peft(k):
        if ".lora_A.default" in k:
            c = k.split(".lora_A.default")[0]
        elif ".lora_B.default" in k:
            c = k.split(".lora_B.default")[0]
        else:
            return None
        for p in ("base_model.model.", "base_model."):
            if c.startswith(p):
                c = c[len(p):]
                break
        return c

    core_to_peft_a = {core_from_peft(pk): pk for pk in peft_state_dict if ".lora_A.default" in pk}
    core_to_peft_b = {core_from_peft(pk): pk for pk in peft_state_dict if ".lora_B.default" in pk}
    core_to_peft_a = {k: v for k, v in core_to_peft_a.items() if k}
    core_to_peft_b = {k: v for k, v in core_to_peft_b.items() if k}

    for gk, v in genome_sd.items():
        if gk.startswith("a."):
            core = gk[2:]
            pk = core_to_peft_a.get(core) or core_to_peft_a.get("model." + core) or core_to_peft_a.get(core.replace("model.", "", 1) if core.startswith("model.") else None)
            if pk:
                out[pk] = v
        elif gk.startswith("b."):
            core = gk[2:]
            pk = core_to_peft_b.get(core) or core_to_peft_b.get("model." + core) or core_to_peft_b.get(core.replace("model.", "", 1) if core.startswith("model.") else None)
            if pk:
                out[pk] = v
    return out


class GenomeSolver:
    """
    Solver that uses base model + best LoRA (HF + PEFT).
    Interface: generate_code(prompt, ...) -> (code, raw, token_usage).
    """

    def __init__(
        self,
        model_name: str,
        model_path: Optional[str] = None,
        best_lora_path: str = None,
        device: Optional[str] = None,
    ):
        self.model_type = "local"
        self.model_name = model_name
        self.model_path = model_path or model_name
        self.best_lora_path = best_lora_path
        self._resolved_path = _resolve_model_path(model_name, model_path)
        self.device = device or "auto"
        self._model = None
        self._tokenizer = None

    def _ensure_loaded(self):
        if self._model is not None and self._tokenizer is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel, LoraConfig

        device_map = "auto"
        if self.device.startswith("cuda:") and "," not in self.device:
            try:
                gpu_id = int(self.device.split(":")[1])
                device_map = {"": gpu_id}
            except (IndexError, ValueError):
                pass
        self._tokenizer = AutoTokenizer.from_pretrained(
            self._resolved_path, trust_remote_code=True, local_files_only=True
        )
        if self._tokenizer.pad_token is None and self._tokenizer.eos_token:
            self._tokenizer.pad_token = self._tokenizer.eos_token
            self._tokenizer.pad_token_id = self._tokenizer.eos_token_id

        self._model = AutoModelForCausalLM.from_pretrained(
            self._resolved_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map=device_map,
            trust_remote_code=True,
            local_files_only=True,
        )

        if self.best_lora_path and os.path.isdir(self.best_lora_path):
            adapter_path = os.path.join(self.best_lora_path, "adapter_model.safetensors")
            if os.path.isfile(adapter_path):
                from safetensors.torch import load_file
                genome_sd = load_file(adapter_path)
                # Check if GENOME format (keys start with 'a' and 'b')
                is_genome = any(k.startswith("a") or k.startswith("b") for k in genome_sd.keys())
                if is_genome:
                    # Add LoRA with same config then load converted state
                    config_path = os.path.join(self.best_lora_path, "adapter_config.json")
                    if os.path.isfile(config_path):
                        lora_config = LoraConfig.from_pretrained(self.best_lora_path)
                        from peft import get_peft_model, TaskType
                        self._model = get_peft_model(self._model, lora_config)
                    peft_sd = self._model.state_dict()
                    mapped = _genome_sd_to_peft_sd(dict(genome_sd), peft_sd)
                    if mapped:
                        self._model.load_state_dict(mapped, strict=False)
                else:
                    self._model = PeftModel.from_pretrained(self._model, self.best_lora_path)
            else:
                self._model = PeftModel.from_pretrained(self._model, self.best_lora_path)

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def set_custom_system_prompt(self, prompt: str):
        pass

    def reset_conversation(self):
        pass

    def get_token_statistics(self) -> dict:
        return getattr(self, "_token_stats", {})

    def generate_code(
        self,
        prompt: str,
        use_conversation: bool = False,
        reset_conversation: bool = False,
        seed: Optional[int] = None,
    ) -> Tuple[str, str, dict]:
        self._ensure_loaded()
        import torch
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)
        with torch.no_grad():
            out = self._model.generate(
                **inputs,
                max_new_tokens=65536,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self._tokenizer.pad_token_id or self._tokenizer.eos_token_id,
            )
        raw = self._tokenizer.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        code = _extract_code(raw)
        return code, raw, {}


def get_genome_solver(
    model_name: str,
    model_path: Optional[str] = None,
    best_lora_path: str = None,
    device: Optional[str] = None,
) -> GenomeSolver:
    """Factory: return a GenomeSolver for use as self.solver in TaskEvaluator."""
    return GenomeSolver(
        model_name=model_name,
        model_path=model_path,
        best_lora_path=best_lora_path,
        device=device,
    )


class VLLMGenomeSolver:
    """
    vLLM-based solver for GENOME Phase 2 (refinement with best LoRA).
    Converts GENOME-format adapter weights to standard PEFT format, saves to temp dir,
    then loads via vLLM with enable_lora=True and LoRARequest.
    """

    def __init__(self, model_name, model_path=None, best_lora_path=None, device=None):
        self.model_type = "local"
        self.model_name = model_name
        self.model_path = model_path or model_name
        self.best_lora_path = best_lora_path
        self._resolved_path = _resolve_model_path(model_name, model_path)
        self.device = device or "auto"
        self._engine = None
        self._tokenizer = None
        self._lora_req = None

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

        has_lora = self.best_lora_path and os.path.isdir(self.best_lora_path)
        lora_path_for_vllm = None

        if has_lora:
            lora_path_for_vllm = self._prepare_lora_for_vllm()

        self._engine = LLM(
            model=self._resolved_path,
            tensor_parallel_size=tp_size,
            trust_remote_code=True,
            max_model_len=max_model_len,
            gpu_memory_utilization=gpu_mem_util,
            dtype="auto",
            enable_lora=has_lora,
            max_lora_rank=64 if has_lora else None,
        )
        self._tokenizer = self._engine.get_tokenizer()

        if has_lora and lora_path_for_vllm:
            from vllm.lora.request import LoRARequest
            self._lora_req = LoRARequest(
                lora_name="genome_best",
                lora_int_id=1,
                lora_path=lora_path_for_vllm,
            )

    def _prepare_lora_for_vllm(self):
        """Convert GENOME adapter to standard PEFT format if needed. Returns path to valid PEFT adapter dir."""
        import json
        import tempfile
        import shutil

        adapter_safetensors = os.path.join(self.best_lora_path, "adapter_model.safetensors")
        adapter_config = os.path.join(self.best_lora_path, "adapter_config.json")

        if not os.path.isfile(adapter_safetensors):
            return self.best_lora_path

        from safetensors.torch import load_file, save_file
        sd = load_file(adapter_safetensors)

        is_genome_fmt = any(k.startswith("a.") or k.startswith("b.") for k in sd.keys())
        if not is_genome_fmt:
            return self.best_lora_path

        if not os.path.isfile(adapter_config):
            return self.best_lora_path

        with open(adapter_config, "r") as f:
            config = json.load(f)

        converted_sd = {}
        for gk, v in sd.items():
            if gk.startswith("a."):
                core = gk[2:]
                peft_key = f"base_model.model.{core}.lora_A.default.weight"
                converted_sd[peft_key] = v
            elif gk.startswith("b."):
                core = gk[2:]
                peft_key = f"base_model.model.{core}.lora_B.default.weight"
                converted_sd[peft_key] = v
            else:
                converted_sd[gk] = v

        tmp_dir = tempfile.mkdtemp(prefix="genome_vllm_lora_")
        save_file(converted_sd, os.path.join(tmp_dir, "adapter_model.safetensors"))
        shutil.copy2(adapter_config, os.path.join(tmp_dir, "adapter_config.json"))
        return tmp_dir

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
            self._lora_req = None
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
        """Generate code via vLLM with optional LoRA."""
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
        sampling_params = SamplingParams(temperature=0.7, top_p=0.9, max_tokens=65536)
        gen_kwargs = {"prompts": [input_text], "sampling_params": sampling_params}
        if self._lora_req:
            gen_kwargs["lora_request"] = self._lora_req
        outputs = self._engine.generate(**gen_kwargs)
        raw_output = outputs[0].outputs[0].text.strip() if outputs else ""
        code = _extract_code(raw_output)
        return code, raw_output, {}


def get_vllm_genome_solver(model_name, model_path=None, best_lora_path=None, device=None):
    """Factory: return a VLLMGenomeSolver for Phase 2 (used by evaluate.py)."""
    return VLLMGenomeSolver(
        model_name=model_name, model_path=model_path,
        best_lora_path=best_lora_path, device=device,
    )
