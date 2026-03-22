"""
GPU placement for parallel evaluation launchers (run_evaluate_parallel*, mutations).

Local subprocesses that run code under ``methods/Parameter_Policy/`` are scheduled with
two physical GPUs per worker (same layout as 32B vLLM TP2): ``--gpus`` lists
``2 × num_workers`` IDs, grouped as consecutive pairs.
"""

from __future__ import annotations

from typing import Any

# Names as evaluate.py ``base_method`` (caller must strip trailing ``_CE`` if present).
PARAMETER_POLICY_LOCAL_METHODS_REQUIRING_DUAL_GPU: frozenset[str] = frozenset(
    {
        "absolute_zero_iter",
        "discover",
        "genome",
        "ragen",
        "seal",
        "soar",
        "theta_evolve",
    }
)


def parallel_local_use_tp2(args: Any, base_method: str) -> bool:
    """
    True if the local parallel launcher should assign two GPUs per worker
    (CUDA_VISIBLE_DEVICES pair; child sees cuda:0,1).
    """
    if getattr(args, "tensor_parallel_2", False):
        return True
    name = (getattr(args, "model_name", None) or "").lower()
    path = (getattr(args, "model_path", None) or "").lower()
    if "32b" in name or "30b" in name or "32b" in path or "30b" in path:
        return True
    return base_method in PARAMETER_POLICY_LOCAL_METHODS_REQUIRING_DUAL_GPU
