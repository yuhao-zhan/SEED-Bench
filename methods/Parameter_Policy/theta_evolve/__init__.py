"""
ThetaEvolve method for 2D_exploration: test-time RL with Ray/slime/sglang + evolving gym.
Uses DaVinciBench/baseline/Parameter_Policy/ThetaEvolve; local model only.
"""
from .theta_evolve_method import run_single_task

__all__ = ["run_single_task"]
