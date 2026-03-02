"""
Local vLLM LLM adapter for OpenEvolve: implements LLMInterface so alpha_evolve can
load the model in-process via vLLM instead of calling an API.
"""
import asyncio
import os
import sys
from typing import Any, Dict, List

_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

try:
    from openevolve.llm.base import LLMInterface
except ImportError:
    LLMInterface = object


class HuggingFaceLLM:
    """LLM client that loads a model via vLLM and implements OpenEvolve's LLMInterface."""

    def __init__(self, model_cfg: Any):
        self.model_cfg = model_cfg
        self.model = getattr(model_cfg, "name", None) or ""
        self.tokenizer = None
        self._model_path = getattr(model_cfg, "name", None) or ""
        self.system_message = getattr(model_cfg, "system_message", None) or ""
        self.temperature = getattr(model_cfg, "temperature", 0.7)
        self.top_p = getattr(model_cfg, "top_p", 0.95)
        self.max_tokens = getattr(model_cfg, "max_tokens", 65536)
        self._engine = None
        self._load_model()

    def _load_model(self) -> None:
        os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
        from vllm import LLM

        model_path = self._model_path
        if not model_path:
            raise ValueError("HuggingFaceLLM: model_cfg.name (model path) is required for local model")

        import torch
        tp_size = 1
        if torch.cuda.is_available():
            tp_size = torch.cuda.device_count()
        tp_env = os.environ.get("VLLM_TENSOR_PARALLEL_SIZE", "").strip()
        if tp_env:
            tp_size = int(tp_env)

        max_model_len = int(os.environ.get("VLLM_MAX_MODEL_LEN", "32768"))
        gpu_mem_util = float(os.environ.get("VLLM_GPU_MEMORY_UTILIZATION", "0.9"))

        self._engine = LLM(
            model=model_path,
            tensor_parallel_size=tp_size,
            trust_remote_code=True,
            max_model_len=max_model_len,
            gpu_memory_utilization=gpu_mem_util,
            dtype="auto",
        )
        self.tokenizer = self._engine.get_tokenizer()

    def _sync_generate_with_context(self, system_message: str, messages: List[Dict[str, str]], **kwargs) -> str:
        from vllm import SamplingParams

        messages_full = [{"role": "system", "content": system_message}] + list(messages)
        if hasattr(self.tokenizer, "apply_chat_template"):
            input_text = self.tokenizer.apply_chat_template(
                messages_full,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            parts = []
            for m in messages_full:
                role = m.get("role", "")
                content = m.get("content", "")
                parts.append(f"{role.capitalize()}:\n{content}")
            input_text = "\n\n".join(parts) + "\n\nAssistant:\n"

        max_new_tokens = kwargs.get("max_tokens", self.max_tokens) or 65536
        temperature = kwargs.get("temperature", self.temperature)
        top_p = kwargs.get("top_p", self.top_p)

        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_new_tokens,
        )

        outputs = self._engine.generate([input_text], sampling_params)
        return outputs[0].outputs[0].text

    async def generate(self, prompt: str, **kwargs) -> str:
        return await self.generate_with_context(
            system_message=self.system_message or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

    async def generate_with_context(
        self, system_message: str, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync_generate_with_context(system_message, messages, **kwargs),
        )

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
            self.tokenizer = None
            import gc; gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    def __del__(self):
        self.cleanup()


def create_hf_llm(model_cfg: Any) -> HuggingFaceLLM:
    """OpenEvolve init_client: given LLMModelConfig, return an LLMInterface (HuggingFaceLLM) that loads the model via vLLM."""
    return HuggingFaceLLM(model_cfg)
