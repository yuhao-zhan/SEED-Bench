"""
TTT-Discover: Learning to Discover at Test Time.

Per-task test-time RL: rollouts -> compute advantages (entropic/mean_baseline)
-> importance_sampling or PPO update on LoRA.
When all rewards are constant (e.g. all 0), use feedback-based expansion
(like baseline revision) before TTT.
"""

from .discover_method import (
    get_discover_solver,
    DiscoverSolver,
)

__all__ = ["get_discover_solver", "DiscoverSolver"]
