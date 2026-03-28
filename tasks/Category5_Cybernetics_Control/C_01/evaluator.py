"""
C-01: Cart-pole balance evaluation (pole starts upright; grading uses true pole angle).

Rules (see TASK_PROMPT for full detail):
- Track: fail if |cart_x - TRACK_CENTER_X| > SAFE_HALF_RANGE (anytime).
- Lock-in: need BALANCE_HOLD_EVALS_REQUIRED consecutive **simulation** steps with |true angle| ≤ BALANCE_ANGLE_DEG;
  counted in the sandbox after each `environment.step` (not per `evaluate` call).
- Before lock-in: |true angle| > BALANCE_ANGLE_DEG resets the sandbox consecutive counter; no angle-only early failure.
- After lock-in: |true angle| > FAILURE_ANGLE_DEG fails; BALANCE_ANGLE_DEG < |angle| ≤ FAILURE_ANGLE_DEG does not end the episode by itself.
- Horizon: step_limit = min(max_steps, sandbox.MAX_STEPS). At the final step, success requires
  lock-in achieved and |true angle| ≤ BALANCE_ANGLE_DEG; otherwise time-out or “pole not upright at end” failure.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

try:
    from .environment import (
        BALANCE_ANGLE_DEG,
        BALANCE_HOLD_STEPS_REQUIRED,
        FAILURE_ANGLE_DEG,
    )
except ImportError:
    from environment import (
        BALANCE_ANGLE_DEG,
        BALANCE_HOLD_STEPS_REQUIRED,
        FAILURE_ANGLE_DEG,
    )

# Backward-compatible name used throughout this module and tests
BALANCE_HOLD_EVALS_REQUIRED = BALANCE_HOLD_STEPS_REQUIRED

class Evaluator:
    def __init__(self, sandbox: Any):
        self.sandbox = sandbox
        self.balance_angle_rad = math.radians(
            float(getattr(self.sandbox, "balance_angle_deg", BALANCE_ANGLE_DEG))
        )
        self.failure_angle_rad = math.radians(
            float(getattr(self.sandbox, "failure_angle_deg", FAILURE_ANGLE_DEG))
        )
        self._balance_hold_required = int(
            getattr(self.sandbox, "balance_hold_steps_required", BALANCE_HOLD_STEPS_REQUIRED)
        )

        self._balance_achieved = False

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
            "grading_balance_angle_deg": float(
                getattr(self.sandbox, "balance_angle_deg", BALANCE_ANGLE_DEG)
            ),
            "grading_failure_angle_deg": float(
                getattr(self.sandbox, "failure_angle_deg", FAILURE_ANGLE_DEG)
            ),
            "success": False,
            "failed": False
        }
        
        # 1. Check boundary failure
        if dist_from_center > safe_range:
            metrics.update({"failed": True, "reason": "Cart left safe zone", "failure_reason": "Cart left safe zone"})
            return True, 0.0, metrics
            
        # 2. Check upright condition (lock-in only after real steps: step_count 0 is pre-loop probe)
        is_upright = abs(pole_angle_true) <= self.balance_angle_rad

        if step_count > 0:
            if not self._balance_achieved:
                n_up = self.sandbox.get_consecutive_upright_sim_steps()
                if n_up >= self._balance_hold_required:
                    self._balance_achieved = True
                    metrics["balance_achieved"] = True
            else:
                # Once balance is achieved, pole MUST stay within failure angle (90 deg)
                if abs(pole_angle_true) > self.failure_angle_rad:
                    metrics.update(
                        {
                            "failed": True,
                            "reason": "Pole fell after balancing",
                            "failure_reason": "Pole fell after balancing",
                        }
                    )
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
        "description": (
            f"Balance using true pole angle: ≥{int(BALANCE_HOLD_EVALS_REQUIRED)} consecutive simulation steps with "
            f"|angle| ≤ {int(BALANCE_ANGLE_DEG)}° (after step 0), stay on track, after lock-in survive until "
            f"horizon unless |angle| > {int(FAILURE_ANGLE_DEG)}° or track/time failure; "
            f"final success requires |angle| ≤ {int(BALANCE_ANGLE_DEG)}° at last step."
        ),
        "metrics": {
            "balance_achieved": f"≥{int(BALANCE_HOLD_EVALS_REQUIRED)} consecutive in-band (≤{int(BALANCE_ANGLE_DEG)}°) true-angle steps",
            "success": f"Lock-in achieved, on track, terminal |true angle| ≤ {int(BALANCE_ANGLE_DEG)}° at horizon",
        },
        "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
    }
