"""
Solver Agent interface module
Responsible for interacting with solver agent (LLM), sending prompts and getting code
"""
import re
import os
from typing import Optional, List, Tuple
from evaluation.utils import clean_special_tags, is_cuda_oom


class SolverInterface:
    """Solver Agent interface class"""

    # Unified system instruction for ALL model backends (openai, local, mock).
    # We intentionally allow "explain-then-code": analysis first, then a python code block.
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

    # Maximum number of conversation turns to keep in history (to avoid exceeding context limits)
    # Each turn consists of 2 messages (user + assistant), so MAX_CONVERSATION_TURNS=10 means 20 messages max
    # MAX_CONVERSATION_TURNS = 10  # Commented out - no limit for now

    def reset_conversation(self):
        """Reset multi-turn conversation history (per task)."""
        self._conversation_messages = []
        self._custom_system_prompt = None  # Reset custom system prompt

    def _append_conversation_turn(self, user_content: str, assistant_content: str):
        """
        Append a user/assistant turn to conversation history.
        Note: Sliding window limit is currently disabled (MAX_CONVERSATION_TURNS is commented out).
        """
        if not hasattr(self, "_conversation_messages"):
            self.reset_conversation()
        
        # Add new turn
        self._conversation_messages.append({"role": "user", "content": user_content})
        self._conversation_messages.append({"role": "assistant", "content": assistant_content})
        
        # Implement sliding window: keep only the most recent MAX_CONVERSATION_TURNS turns
        # Each turn = 2 messages (user + assistant), so we keep at most MAX_CONVERSATION_TURNS * 2 messages
        # Commented out - no limit for now
        # max_messages = self.MAX_CONVERSATION_TURNS * 2
        # if len(self._conversation_messages) > max_messages:
        #     # Remove oldest messages (keep the most recent ones)
        #     removed_count = len(self._conversation_messages) - max_messages
        #     self._conversation_messages = self._conversation_messages[removed_count:]
        #     print(f"⚠️  Conversation history exceeded limit, removed {removed_count // 2} oldest turn(s) (keeping last {self.MAX_CONVERSATION_TURNS} turns)")
    
    # API configuration for all OpenAI-compatible models (single gateway)
    API_KEY = 'sk-LRhP4AOlyeHBJh4NiVlg7YYPE8DdUTgykbEsMR7UVoNIQxS3'
    BASE_URL = 'https://yeysai.com/v1'

    def __init__(self, model_type='openai', model_name='gpt-4', api_key=None,
                 model_path: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize solver interface
        Args:
            model_type: Model type ('openai', 'local', 'mock')
            model_name: Model name (for API: e.g. gpt-4, deepseek-v3.2; for local: model path or HuggingFace name)
            api_key: API key (optional override for openai)
            model_path: Local model path (if model_type is local and model_name is not a path)
            device: Device ('cuda', 'cpu', 'auto', 'cuda:0', 'cuda:1', or 'cuda:1,2,3'), default 'auto'
        """
        self.model_type = model_type
        self.model_name = model_name
        self.model_path = model_path
        self.device = device or 'auto'

        # Token usage statistics (for API-based models)
        self.token_usage_history = []  # List of dicts with token usage per call

        # Initialize corresponding client
        if model_type == 'openai':
            try:
                import openai
                final_api_key = api_key or self.API_KEY
                base_url = self.BASE_URL
                self.client = openai.OpenAI(api_key=final_api_key, base_url=base_url)
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        elif model_type == 'local':
            self._init_local_model()
        elif model_type == 'mock':
            self.client = None
            self.model = None
            self.tokenizer = None
        else:
            raise ValueError(f"Unsupported model type: {model_type}. Use openai, local, or mock.")
    
    def _init_local_model(self):
        """Initialize local model using vLLM for fast inference."""
        # Handle CUDA_VISIBLE_DEVICES so vLLM only sees the requested GPU(s) (set before any CUDA init).
        # Do not overwrite if already set (e.g. run_evaluate_parallel.py set 5,7 for TP2; we use cuda:0,1 as logical devices).
        if self.device.startswith('cuda:'):
            device_str = self.device[5:].strip()
            if not os.environ.get('CUDA_VISIBLE_DEVICES'):
                gpu_id_strs = [x.strip() for x in device_str.split(',') if x.strip()]
                if gpu_id_strs:
                    os.environ['CUDA_VISIBLE_DEVICES'] = ','.join(gpu_id_strs)
                    print(f"Using GPU(s): CUDA_VISIBLE_DEVICES={os.environ['CUDA_VISIBLE_DEVICES']}")
            self.device = 'cuda'

        # Determine model path
        if self.model_path:
            model_path = self.model_path
        elif os.path.isdir(self.model_name) or os.path.isfile(self.model_name):
            model_path = self.model_name
        else:
            model_path = self.model_name

        print(f"Loading local model (vLLM): {model_path}")

        try:
            # Disable vLLM's V1 multiprocessing: run EngineCore in-process instead of
            # spawning a separate child process. This avoids IPC/ZMQ issues when evaluate.py
            # is already a subprocess (e.g. launched by run_evaluate_parallel.py).
            os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")

            from vllm import LLM

            # Determine tensor_parallel_size from visible GPUs
            import torch
            self.torch = torch
            tp_size = 1
            if torch.cuda.is_available():
                tp_size = torch.cuda.device_count()
            tp_env = os.environ.get("VLLM_TENSOR_PARALLEL_SIZE", "").strip()
            if tp_env:
                tp_size = int(tp_env)
            # Force single-process path when only one GPU to avoid PyTorch TCPStore connection timeout
            if tp_size <= 1:
                tp_size = 1
                os.environ["VLLM_TENSOR_PARALLEL_SIZE"] = "1"

            # max_model_len: cap to avoid KV-cache OOM; for 32B/30B on single 80G, 32768 leaves too little KV cache
            _env_max = os.environ.get("VLLM_MAX_MODEL_LEN", "").strip()
            if _env_max:
                max_model_len = int(_env_max)
            else:
                _path_lower = (model_path or "").lower()
                if "32b" in _path_lower or "30b" in _path_lower:
                    max_model_len = 16384  # safe for 32B on 80G (KV cache fits)
                else:
                    max_model_len = 32768
            # gpu_memory_utilization: fraction of GPU memory vLLM may use (default 0.9)
            gpu_mem_util = float(os.environ.get("VLLM_GPU_MEMORY_UTILIZATION", "0.9"))

            while True:
                try:
                    print(f"vLLM config: tensor_parallel_size={tp_size}, max_model_len={max_model_len}, gpu_memory_utilization={gpu_mem_util}")
                    self.vllm_engine = LLM(
                        model=model_path,
                        tensor_parallel_size=tp_size,
                        trust_remote_code=True,
                        max_model_len=max_model_len,
                        gpu_memory_utilization=gpu_mem_util,
                        dtype="auto",
                        enforce_eager=True,
                    )
                    break
                except ValueError as e:
                    err_str = str(e)
                    # KV cache too small for max_model_len (e.g. 32B on 80G leaves ~4.6 GiB for KV)
                    if "KV cache" in err_str and "maximum model length is" in err_str:
                        import re
                        m = re.search(r"estimated maximum model length is (\d+)", err_str)
                        fallback = int(m.group(1)) if m else 16384
                        fallback = min(fallback, max_model_len - 1)
                        if fallback < 2048:
                            raise RuntimeError(f"Failed to load local model with vLLM: {e}") from e
                        print(f"⚠️  Reducing max_model_len {max_model_len} -> {fallback} (KV cache too small)")
                        max_model_len = fallback
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        continue
                    raise RuntimeError(f"Failed to load local model with vLLM: {e}") from e

            self.tokenizer = self.vllm_engine.get_tokenizer()
            self.model = None  # Not used with vLLM; kept for attribute compatibility
            print(f"✅ Model loaded successfully (vLLM)")

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to load local model with vLLM: {e}") from e
    
    def cleanup(self):
        """Explicitly shut down the vLLM engine and release GPU memory."""
        if hasattr(self, 'vllm_engine') and self.vllm_engine is not None:
            try:
                # Shutdown the engine core (terminates EngineCore subprocess)
                if hasattr(self.vllm_engine, 'llm_engine'):
                    engine = self.vllm_engine.llm_engine
                    if hasattr(engine, 'engine_core') and hasattr(engine.engine_core, 'shutdown'):
                        engine.engine_core.shutdown()
            except Exception as e:
                print(f"⚠️  vLLM engine_core shutdown warning: {e}")
            try:
                del self.vllm_engine
            except Exception:
                pass
            self.vllm_engine = None
            self.model = None
            self.tokenizer = None
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            print("✅ vLLM engine cleaned up, GPU memory released")

    def __del__(self):
        self.cleanup()

    def set_custom_system_prompt(self, system_prompt: str):
        """
        Set a custom system prompt (used when context='all' to include task info in system prompt).
        Args:
            system_prompt: Custom system prompt string
        """
        self._custom_system_prompt = system_prompt
    
    def get_system_prompt(self) -> str:
        """
        Get the current system prompt (custom or default).
        Returns:
            str: System prompt to use
        """
        return self._custom_system_prompt if hasattr(self, "_custom_system_prompt") and self._custom_system_prompt else self.SYSTEM_PROMPT
    
    def generate_code(self, prompt: str, use_conversation: bool = False, reset_conversation: bool = False,
                     seed: Optional[int] = None) -> tuple[str, str, dict]:
        """
        Send prompt to solver agent and get generated code
        Args:
            prompt: Prompt sent to solver
            use_conversation: If True, keep a multi-turn chat history in a single large context window
            reset_conversation: If True, clears conversation history before sending this prompt
            seed: Optional random seed for sampling (local/vLLM only). Use different seeds per run/iteration for diversity.
        Returns:
            tuple[str, str, dict]: (Extracted Python code, raw LLM output, token_usage_dict)
                token_usage_dict contains: prompt_tokens, completion_tokens, total_tokens
                For non-API models, token_usage_dict will be empty or None
        """
        if self.model_type == 'mock':
            # Mock mode: return a simple example code
            code, raw = self._mock_code_generator()
            return code, raw, {}

        if reset_conversation:
            self.reset_conversation()
        if use_conversation and not hasattr(self, "_conversation_messages"):
            self.reset_conversation()
        
        # Get system prompt (custom or default)
        system_prompt = self.get_system_prompt()
        
        try:
            token_usage = {}
            if self.model_type == 'openai':
                # Special handling for deepseek-v3.2-think: use deepseek-v3.2 with enable_thinking
                if self.model_name == 'deepseek-v3.2-think':
                    actual_model = 'deepseek-v3.2'
                    extra_body = {"enable_thinking": True}
                else:
                    actual_model = self.model_name
                    extra_body = None
                
                create_kwargs = {
                    "model": actual_model,
                    "messages": (
                        [{"role": "system", "content": system_prompt}]
                        + (self._conversation_messages if use_conversation else [])
                        + [{"role": "user", "content": prompt}]
                    ),
                    "temperature": 0.7,
                    "max_tokens": 65536,
                }
                if extra_body is not None:
                    create_kwargs["extra_body"] = extra_body
                
                response = self.client.chat.completions.create(**create_kwargs)
                raw_output = response.choices[0].message.content
                
                if hasattr(response, 'usage') and response.usage:
                    token_usage = {
                        'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0),
                        'completion_tokens': getattr(response.usage, 'completion_tokens', 0),
                        'total_tokens': getattr(response.usage, 'total_tokens', 0)
                    }
                    self.token_usage_history.append(token_usage.copy())
                    print(f"📊 Token usage: {token_usage['total_tokens']} total ({token_usage['prompt_tokens']} prompt + {token_usage['completion_tokens']} completion)")
            elif self.model_type == 'local':
                # Local model inference - no token usage tracking
                raw_output = self._generate_with_local_model(prompt, use_conversation=use_conversation, seed=seed)
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
            
            # Clean special format tags from raw_output before storing in conversation history
            # Some models (like gpt-oss-20b) output <|channel|> tags that cause errors when passed back to the API
            cleaned_output = clean_special_tags(raw_output)
            
            if use_conversation:
                self._append_conversation_turn(prompt, cleaned_output)

            # Extract code
            code = self._extract_code(raw_output)
            # Debug: print extraction result
            if not code or len(code.strip()) < 50:
                print(f"⚠️  Code extraction failed or too short. Extracted length: {len(code) if code else 0}")
                print(f"📝 First 500 chars of extracted code:\n{code[:500] if code else 'None'}")
            return code, raw_output, token_usage
            
        except Exception as e:
            if is_cuda_oom(e):
                print("❌ CUDA out of memory during inference - stopping immediately")
                raise
            raise RuntimeError(f"Failed to call solver agent: {e}")

    def generate_code_from_messages(self, messages: List[dict], temperature: float = 0.7) -> tuple[str, str, dict]:
        """
        One-shot generation from a full messages list. Does not modify conversation state.
        For openai only; used for parallel K generation (ReasoningBank).
        Args:
            messages: Full list of chat messages, e.g. [{"role":"system","content":...}, {"role":"user","content":...}]
            temperature: Sampling temperature.
        Returns:
            tuple[str, str, dict]: (extracted code, raw LLM output, token_usage dict)
        """
        if self.model_type != 'openai':
            raise ValueError("generate_code_from_messages is only supported for model_type='openai'")
        if self.model_name == 'deepseek-v3.2-think':
            actual_model = 'deepseek-v3.2'
            extra_body = {"enable_thinking": True}
        else:
            actual_model = self.model_name
            extra_body = None
        create_kwargs = {
            "model": actual_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 65536,
        }
        if extra_body is not None:
            create_kwargs["extra_body"] = extra_body
        response = self.client.chat.completions.create(**create_kwargs)
        raw_output = response.choices[0].message.content or ""
        token_usage = {}
        if hasattr(response, 'usage') and response.usage:
            token_usage = {
                'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0),
                'completion_tokens': getattr(response.usage, 'completion_tokens', 0),
                'total_tokens': getattr(response.usage, 'total_tokens', 0),
            }
            self.token_usage_history.append(token_usage.copy())
        code = self._extract_code(raw_output)
        return code, raw_output, token_usage

    def get_token_statistics(self) -> dict:
        """
        Get token usage statistics
        Returns:
            dict with total_tokens, total_prompt_tokens, total_completion_tokens, 
            average_tokens, and call_count
        """
        if not self.token_usage_history:
            return {
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'average_tokens': 0.0,
                'call_count': 0
            }
        
        total_tokens = sum(usage.get('total_tokens', 0) for usage in self.token_usage_history)
        total_prompt_tokens = sum(usage.get('prompt_tokens', 0) for usage in self.token_usage_history)
        total_completion_tokens = sum(usage.get('completion_tokens', 0) for usage in self.token_usage_history)
        call_count = len(self.token_usage_history)
        average_tokens = total_tokens / call_count if call_count > 0 else 0.0
        
        return {
            'total_tokens': total_tokens,
            'total_prompt_tokens': total_prompt_tokens,
            'total_completion_tokens': total_completion_tokens,
            'average_tokens': round(average_tokens, 2),
            'call_count': call_count,
            'per_call_usage': self.token_usage_history  # Detailed per-call usage
        }
    
    def _generate_with_local_model(self, prompt: str, use_conversation: bool = False, seed: Optional[int] = None) -> str:
        """Generate code using local model via vLLM. seed: if set, used for sampling (different per run/iteration = more diversity)."""
        from vllm import SamplingParams

        system_prompt = self.get_system_prompt()

        if hasattr(self.tokenizer, 'apply_chat_template'):
            messages = (
                [{"role": "system", "content": system_prompt}]
                + (self._conversation_messages if use_conversation and hasattr(self, "_conversation_messages") else [])
                + [{"role": "user", "content": prompt}]
            )
            input_text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        else:
            conversation_text = ""
            if use_conversation and hasattr(self, "_conversation_messages") and self._conversation_messages:
                for msg in self._conversation_messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        conversation_text += f"\n\nUser:\n{content}\n"
                    elif role == "assistant":
                        conversation_text += f"\n\nAssistant:\n{content}\n"
            input_text = f"{system_prompt}\n{conversation_text}\n\nUser:\n{prompt}\n\nAssistant:\n```python\n"

        sampling_kw = dict(temperature=0.7, top_p=0.9, max_tokens=131072)
        if seed is not None:
            sampling_kw["seed"] = seed
        sampling_params = SamplingParams(**sampling_kw)

        outputs = self.vllm_engine.generate([input_text], sampling_params)
        full_raw_output = outputs[0].outputs[0].text

        print(f"📝 Model generated output (first 1000 chars):\n{full_raw_output[:1000]}")
        print(f"📝 Model generated output length: {len(full_raw_output)} characters")

        return full_raw_output
    

    
    def _extract_code(self, raw_text: str) -> str:
        """
        Extract Python code from raw text
        Simple strategy: Extract code from ```python ... ``` or ``` ... ``` code blocks only
        """
        # Step 1: Handle reasoning tags - find where reasoning ends and code begins
        # Look for common reasoning tags: <think>, <think>, <think>, etc.
        reasoning_end_markers = ['</think>', '</think>', '</think>']
        reasoning_start_markers = ['<think>', '<think>', '<think>']
        
        # First, try to find closing tags
        reasoning_end_pos = -1
        for marker in reasoning_end_markers:
            pos = raw_text.find(marker)
            if pos > reasoning_end_pos:
                reasoning_end_pos = pos + len(marker)
        
        # If we found a closing tag, extract text after it
        if reasoning_end_pos >= 0:
            raw_text = raw_text[reasoning_end_pos:].strip()
        else:
            # No closing tag found, look for opening tags and find code block after them
            reasoning_start_pos = -1
            for marker in reasoning_start_markers:
                pos = raw_text.rfind(marker)
                if pos > reasoning_start_pos:
                    reasoning_start_pos = pos
            
            if reasoning_start_pos >= 0:
                # Find the next code block after the reasoning tag
                code_block_start = raw_text.find('```', reasoning_start_pos)
                if code_block_start >= 0:
                    raw_text = raw_text[code_block_start:].strip()
        
        # Step 2: Find all code blocks (```python ... ``` or ``` ... ```)
        code_block_pattern = r'```(?:python)?\s*\n?(.*?)```'
        matches = list(re.finditer(code_block_pattern, raw_text, re.DOTALL))
        
        if not matches:
            # No complete code blocks found, try to find incomplete code blocks
            # Look for ```python or ``` followed by code (even if not closed)
            incomplete_pattern = r'```(?:python)?\s*\n?(.*)'
            incomplete_match = re.search(incomplete_pattern, raw_text, re.DOTALL)
            if incomplete_match:
                code = incomplete_match.group(1).strip()
                # Remove any trailing incomplete markdown or reasoning tags
                code = re.sub(r'```.*$', '', code, flags=re.DOTALL)
                code = re.sub(r'<think>.*$', '', code, flags=re.DOTALL)
                code = re.sub(r'<think>.*$', '', code, flags=re.DOTALL)
                code = re.sub(r'<think>.*$', '', code, flags=re.DOTALL)
                if len(code.strip()) > 50:  # Only return if substantial code found
                    return code.strip()
            return ""
        
        # Step 3: Extract code from the first code block (or longest if multiple)
        if len(matches) == 1:
            code = matches[0].group(1).strip()
        else:
            # Multiple code blocks, use the longest one
            code = max(matches, key=lambda m: len(m.group(1).strip())).group(1).strip()
        
        # Step 4: Basic cleanup - remove any remaining markdown markers
        code = re.sub(r'```(?:python)?', '', code)
        code = re.sub(r'```', '', code)
        
        return code.strip()
    
    def _mock_code_generator(self) -> tuple[str, str]:
        """Mock code generator (for testing) - returns a simple but stable bridge"""
        code = """def build_agent(sandbox):
    # Mock implementation for Bridge task (Stable version)
    LEFT_CLIFF_X = 10.0
    RIGHT_CLIFF_X = 25.0
    GAP_WIDTH = 15.0
    DECK_TOP_Y = 10.0
    DECK_HEIGHT = 0.6
    DECK_Y = DECK_TOP_Y - DECK_HEIGHT/2
    
    left_cliff = sandbox._terrain_bodies.get("left_cliff")
    right_cliff = sandbox._terrain_bodies.get("right_cliff")
    
    # Simple deck (split into two 10m segments to stay in build zone)
    d1 = sandbox.add_beam(x=15.0, y=DECK_Y, width=10.0, height=DECK_HEIGHT, density=5.0)
    d2 = sandbox.add_beam(x=25.0, y=DECK_Y, width=10.0, height=DECK_HEIGHT, density=5.0)
    for d in [d1, d2]:
        for fixture in d.fixtures: fixture.friction = 0.8
    
    sandbox.add_joint(d1, d2, (20.0, 10.0), type='rigid')
    sandbox.add_joint(left_cliff, d1, (10.0, 10.0), type='rigid')
    sandbox.add_joint(right_cliff, d2, (25.0, 10.0), type='rigid')
    
    # Support layer to prevent collapse
    s1 = sandbox.add_beam(x=15.0, y=8.0, width=10.0, height=0.4, density=3.0)
    s2 = sandbox.add_beam(x=25.0, y=8.0, width=10.0, height=0.4, density=3.0)
    sandbox.add_joint(s1, s2, (20.0, 8.0), type='rigid')
    sandbox.add_joint(left_cliff, s1, (10.0, 8.0), type='rigid')
    sandbox.add_joint(right_cliff, s2, (25.0, 8.0), type='rigid')
    
    # Verticals
    for x in [12.5, 17.5, 22.5]:
        v = sandbox.add_beam(x=x, y=9.0, width=0.3, height=2.0, density=3.0)
        target_d = d1 if x < 20.0 else d2
        target_s = s1 if x < 20.0 else s2
        sandbox.add_joint(target_d, v, (x, 10.0), type='rigid')
        sandbox.add_joint(target_s, v, (x, 8.0), type='rigid')

    return d1

def agent_action(sandbox, agent_body, step_count):
    if hasattr(sandbox, '_terrain_bodies'):
        vehicle = sandbox._terrain_bodies.get("vehicle_chassis")
        if vehicle:
            target_vx = 4.0
            curr_vx = vehicle.linearVelocity.x
            if curr_vx < target_vx:
                vehicle.linearVelocity = (curr_vx + 0.1, vehicle.linearVelocity.y)
"""
        return code, code


def get_aux_llm_credentials(explicit_api_key: Optional[str] = None) -> Tuple[str, str]:
    """
    API key and base URL for auxiliary OpenAI-compatible calls (ACE, A-mem-sys, ReasoningBank,
    ExpeL insights, TextGrad, Reflexion API solver, etc.). Same gateway as the default openai solver.
    Resolution: explicit_api_key → OPENAI_API_KEY → SolverInterface.API_KEY; base_url is always BASE_URL.
    """
    key = explicit_api_key or os.environ.get("OPENAI_API_KEY") or SolverInterface.API_KEY
    return key, SolverInterface.BASE_URL
