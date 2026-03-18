#!/usr/bin/env python3
"""
Create genome/experts/ and optionally populate it so get_lora_pools() finds at least 2 expert LoRAs.

Official get_lora_pools (baseline/Parameter_Policy/GENOME/src/utils.py) only recognizes these
subdir names under lora_dir: code_alpaca, gpt4_alpaca, cot, lima, oasst1, open_orca,
flan_v2, science_literature, wizardlm, sharegpt.

Usage (run from this directory, methods/Parameter_Policy/genome/):
  python bootstrap_lora_dir.py
    -> creates experts/ and one placeholder subdir (README only). Add a second expert manually.

  python bootstrap_lora_dir.py --link-dir /path/to/parent
    -> creates experts/ and symlinks into it any of the known subdir names found under
       /path/to/parent (e.g. parent/code_alpaca, parent/gpt4_alpaca). Use this if you
       already have expert LoRAs elsewhere.
"""
from __future__ import annotations

import argparse
import os

# Subdir names recognized by official get_lora_pools (GENOME/src/utils.py)
EXPERT_NAMES = [
    "code_alpaca", "gpt4_alpaca", "cot", "lima", "oasst1", "open_orca",
    "flan_v2", "science_literature", "wizardlm", "sharegpt",
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPERTS_DIR = os.path.join(SCRIPT_DIR, "experts")


def main():
    ap = argparse.ArgumentParser(description="Create genome/experts/ for GENOME Phase 1.")
    ap.add_argument(
        "--link-dir",
        type=str,
        default=None,
        help="Parent directory containing subdirs with expert names (e.g. code_alpaca). Symlink them into experts/.",
    )
    args = ap.parse_args()

    os.makedirs(EXPERTS_DIR, exist_ok=True)

    if args.link_dir:
        link_dir = os.path.abspath(args.link_dir)
        if not os.path.isdir(link_dir):
            print(f"Error: --link-dir is not a directory: {link_dir}")
            return 1
        for name in EXPERT_NAMES:
            src = os.path.join(link_dir, name)
            dst = os.path.join(EXPERTS_DIR, name)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    print(f"Skip (already exists): {name}")
                    continue
                try:
                    os.symlink(src, dst)
                    print(f"Linked: {name} -> {src}")
                except OSError as e:
                    print(f"Warning: could not symlink {name}: {e}")
        print(f"Experts dir: {EXPERTS_DIR}")
        return 0

    # No --link-dir: create one placeholder so structure is clear
    placeholder = os.path.join(EXPERTS_DIR, "code_alpaca")
    if not os.path.exists(placeholder):
        os.makedirs(placeholder, exist_ok=True)
        readme = os.path.join(placeholder, "README.txt")
        with open(readme, "w") as f:
            f.write(
                "Place a LoRA adapter here: adapter_model.safetensors and adapter_config.json.\n"
                "You need at least two expert subdirs under experts/ (names: code_alpaca, gpt4_alpaca, cot, lima, oasst1, open_orca, flan_v2, science_literature, wizardlm, sharegpt).\n"
                "See README.md in the genome directory.\n"
            )
        print(f"Created placeholder: {placeholder}")
    print(f"Experts dir: {EXPERTS_DIR}")
    print("Add at least one more expert subdir (with adapter_model.safetensors + adapter_config.json) or run with --link-dir /path/to/parent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
