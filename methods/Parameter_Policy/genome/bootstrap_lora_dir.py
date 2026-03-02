#!/usr/bin/env python3
"""
Create a minimal lora_dir compatible with GENOME raw repo (get_lora_pools).
Creates at least 2 expert subdirs (code_alpaca, gpt4_alpaca) each with:
  adapter_model.safetensors, adapter_config.json, tokenizer (same layout as save_lora_weight).
Saved under genome/experts/ by default. Run once before method=genome.
"""
import os
import sys
import argparse

# Scripts dir = parent of methods/
_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Default subdir names that GENOME get_lora_pools scans (raw repo utils.py)
DEFAULT_EXPERT_NAMES = ["code_alpaca", "gpt4_alpaca"]


def _resolve_model_path(model_name: str, model_path: str = None) -> str:
    base = model_path or model_name
    if os.path.isabs(base) and os.path.isdir(base):
        return base
    local_name = os.path.basename(base.rstrip("/"))
    local_models = os.environ.get("LOCAL_MODELS_DIR", "/home/test/testdata/models")
    local_path = os.path.join(local_models, local_name)
    if os.path.isdir(local_path):
        return local_path
    return base


def _peft_state_to_genome_ab_format(state_dict: dict) -> dict:
    """
    Convert PEFT LoRA state dict to GENOME format (keys starting with 'a' and 'b').
    PEFT keys: base_model.model.model.layers.0....lora_A.default -> a.layers.0....
    """
    out = {}
    for key, tensor in state_dict.items():
        if ".lora_A." in key:
            prefix = key.split(".lora_A.")[0]
            # strip base_model.model. or model. for short path
            for p in ("base_model.model.", "base_model."):
                if prefix.startswith(p):
                    prefix = prefix[len(p):]
                    break
            if prefix.startswith("model."):
                prefix = prefix[6:]
            out["a." + prefix] = tensor.detach().clone()
        elif ".lora_B." in key:
            prefix = key.split(".lora_B.")[0]
            for p in ("base_model.model.", "base_model."):
                if prefix.startswith(p):
                    prefix = prefix[len(p):]
                    break
            if prefix.startswith("model."):
                prefix = prefix[6:]
            out["b." + prefix] = tensor.detach().clone()
    return out


def create_bootstrap_lora_dir(
    base_model: str,
    lora_dir: str,
    expert_names: list = None,
    r: int = 8,
    alpha: int = 16,
    seed_base: int = 42,
) -> None:
    """
    Create lora_dir with at least 2 expert subdirs. Each subdir has adapter_model.safetensors
    in GENOME format (keys starting with 'a' and 'b'), adapter_config.json, and tokenizer.
    """
    import torch
    from safetensors.torch import save_file
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, TaskType

    expert_names = expert_names or DEFAULT_EXPERT_NAMES
    if len(expert_names) < 2:
        raise ValueError("Need at least 2 expert subdirs for GENOME (pairs for merge).")

    resolved = _resolve_model_path(base_model)
    print(f"Loading base model from {resolved} ...")
    tokenizer = AutoTokenizer.from_pretrained(resolved, trust_remote_code=True, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        resolved,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
        local_files_only=True,
    )

    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    module_names = {n for n, _ in model.named_modules()}
    target_modules = [m for m in target_modules if any(m in n for n in module_names)]
    if not target_modules:
        target_modules = ["q_proj", "v_proj"]

    lora_config = LoraConfig(
        r=r,
        lora_alpha=alpha,
        target_modules=target_modules,
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    os.makedirs(lora_dir, exist_ok=True)

    for i, name in enumerate(expert_names):
        expert_path = os.path.join(lora_dir, name)
        os.makedirs(expert_path, exist_ok=True)
        peft_model = get_peft_model(model, lora_config)
        if seed_base is not None:
            torch.manual_seed(seed_base + i)
            for n, p in peft_model.named_parameters():
                if "lora" in n.lower() and p.requires_grad:
                    p.data.normal_(0, 0.01)
        # Convert to GENOME "a"/"b" key format and save
        sd = peft_model.state_dict()
        genome_sd = _peft_state_to_genome_ab_format(sd)
        if not genome_sd:
            raise RuntimeError("No LoRA keys found in state dict; check _peft_state_to_genome_ab_format.")
        save_file(genome_sd, os.path.join(expert_path, "adapter_model.safetensors"))
        lora_config.save_pretrained(expert_path)
        tokenizer.save_pretrained(expert_path)
        print(f"  Created {expert_path} ({len(genome_sd)} keys)")
        del peft_model, sd, genome_sd
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    print(f"Done. lora_dir = {os.path.abspath(lora_dir)}")


def main():
    parser = argparse.ArgumentParser(description="Create bootstrap lora_dir for GENOME (raw repo layout).")
    parser.add_argument("--base-model", type=str, required=True, help="Base model path (e.g. Qwen3-8B or /path/to/model)")
    parser.add_argument("--lora-dir", type=str, default=None, help="Output directory for LoRA adapters (default: genome/experts/)")
    parser.add_argument("--experts", type=str, nargs="+", default=DEFAULT_EXPERT_NAMES, help="Expert subdir names (default: code_alpaca gpt4_alpaca)")
    parser.add_argument("--r", type=int, default=8, help="LoRA r")
    parser.add_argument("--alpha", type=int, default=16, help="LoRA alpha")
    parser.add_argument("--seed", type=int, default=42, help="Base seed for init")
    args = parser.parse_args()
    lora_dir = args.lora_dir
    if lora_dir is None:
        from methods.Parameter_Policy.genome import get_genome_experts_dir
        lora_dir = get_genome_experts_dir()
    create_bootstrap_lora_dir(
        base_model=args.base_model,
        lora_dir=lora_dir,
        expert_names=args.experts,
        r=args.r,
        alpha=args.alpha,
        seed_base=args.seed,
    )


if __name__ == "__main__":
    main()
