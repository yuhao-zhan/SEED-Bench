"""
C-01: Cart-pole balance evaluation (pole starts upright).
Success = consecutive in-band upright hold, then remain on track until horizon with terminal in-band angle.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

# Evaluation Constants
BALANCE_ANGLE_DEG = 45.0
FAILURE_ANGLE_DEG = 90.0
BALANCE_HOLD_EVALS_REQUIRED = 200

class Evaluator:
    def __init__(self, sandbox: Any):
        self.sandbox = sandbox
        self.balance_angle_rad = math.radians(BALANCE_ANGLE_DEG)
        self.failure_angle_rad = math.radians(FAILURE_ANGLE_DEG)
        
        self._balance_achieved = False
        self._consecutive_upright_evals = 0

    def evaluate(self, agent_body: Any, step_count: int, max_steps: int) -> tuple[bool, float, dict]:
        """
        Calculates score and termination status.
        Args:
            agent_body: The agent's body from build_agent.
            step_count: Current simulation step.
            max_steps: Maximum simulation steps.
        Returns:
            (done, score, metrics)
        """
        # Physical failure/success uses ground truth; metrics include both reported (sensor) and true pole state
        pole_angle_true = self.sandbox.get_true_pole_angle()
        pole_omega_true = self.sandbox.get_true_pole_angular_velocity()
        pole_angle_reported = self.sandbox.get_pole_angle()
        pole_omega_reported = self.sandbox.get_pole_angular_velocity()
        cart_pos = self.sandbox.get_cart_position()
        cart_vel = self.sandbox.get_cart_velocity()
        track_center = self.sandbox.TRACK_CENTER_X
        safe_range = self.sandbox.SAFE_HALF_RANGE
        
        dist_from_center = abs(cart_pos - track_center)
        env_limit = getattr(self.sandbox, "MAX_STEPS", max_steps)
        step_limit = min(max_steps, env_limit)
        
        metrics = {
            "pole_angle_deg": math.degrees(pole_angle_reported),
            "pole_angular_velocity": pole_omega_reported,
            "pole_angle_true_deg": math.degrees(pole_angle_true),
            "pole_angular_velocity_true": pole_omega_true,
            "cart_x": cart_pos,
            "cart_velocity_x": cart_vel,
            "dist_from_center": dist_from_center,
            "safe_half_range": safe_range,
            "step_count": step_count,
            "balance_achieved": self._balance_achieved,
            "success": False,
            "failed": False
        }
        
        # 1. Check boundary failure
        if dist_from_center > safe_range:
            metrics.update({"failed": True, "reason": "Cart left safe zone", "failure_reason": "Cart left safe zone"})
            return True, 0.0, metrics
            
        # 2. Check upright condition
        is_upright = abs(pole_angle_true) <= self.balance_angle_rad
        
        if not self._balance_achieved:
            if is_upright:
                self._consecutive_upright_evals += 1
                if self._consecutive_upright_evals >= BALANCE_HOLD_EVALS_REQUIRED:
                    self._balance_achieved = True
                    metrics["balance_achieved"] = True
            else:
                self._consecutive_upright_evals = 0
        else:
            # Once balance is achieved, pole MUST stay within failure angle (90 deg)
            if abs(pole_angle_true) > self.failure_angle_rad:
                metrics.update({"failed": True, "reason": "Pole fell after balancing", "failure_reason": "Pole fell after balancing"})
                return True, 0.0, metrics
        
        # 3. Handle termination (horizon follows sandbox.MAX_STEPS so it matches physics_config / prompt)
        done = step_count >= step_limit
        if done:
            # Per prompt: Success if balance was achieved AND it is currently in the upright region (45 deg)
            if self._balance_achieved and is_upright:
                metrics["success"] = True
                return True, 100.0, metrics
            elif not self._balance_achieved:
                metrics.update({"failed": True, "reason": "Time limit reached without balancing", "failure_reason": "Time limit reached without balancing"})
                return True, 0.0, metrics
            else:
                metrics.update({"failed": True, "reason": "Pole not in upright region at end", "failure_reason": "Pole not in upright region at end"})
                return True, 0.0, metrics
                
        return False, 0.0, metrics

def get_evaluator(sandbox: Any) -> Evaluator:
    return Evaluator(sandbox)

def score_to_metrics(score: float, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """SEED format for leaderboard."""
    return {
        "score": score,
        "success": metrics.get("success", False),
        "balance_achieved": metrics.get("balance_achieved", False),
    }

def get_evaluation_config() -> Dict[str, Any]:
    return {
        "task_name": "Cart-Pole Balance",
        "description": "Keep an upright pole balanced on a cart within track limits until the episode ends",
        "metrics": {"balance_achieved": "Reached upright region", "success": "Passed entire duration"},
        "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
    }
