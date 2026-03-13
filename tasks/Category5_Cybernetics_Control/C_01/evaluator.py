"""
C-01: Cart-Pole Swing-up then Balance evaluation.
Success = pole reaches upright region (|angle| <= 45°) and stays there until max_steps.
Failure = cart leaves safe zone, or (once balance achieved) pole leaves upright region.
"""

import math
import numpy as np

try:
    from .environment import BALANCE_ANGLE_RAD, TRACK_CENTER_X, SAFE_HALF_RANGE
except ImportError:
    from environment import BALANCE_ANGLE_RAD, TRACK_CENTER_X, SAFE_HALF_RANGE

BALANCE_HOLD_STEPS_REQUIRED = 10 

class Evaluator:
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.balance_angle_rad = BALANCE_ANGLE_RAD
        self.track_center_x = float(terrain_bounds.get("track_center_x", TRACK_CENTER_X))
        self.safe_half_range = float(terrain_bounds.get("safe_half_range", SAFE_HALF_RANGE))
        self._balance_achieved = False
        self._consecutive_upright_steps = 0  
        
    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate the current state of the environment.
        verifier.py calls this with (agent_body, step_count, max_steps)
        """
        pole_angle_true = (
            self.environment.get_true_pole_angle()
            if hasattr(self.environment, "get_true_pole_angle")
            else self.environment.get_pole_angle()
        )
        cart_x = self.environment.get_cart_position()
        
        # 1. Check cart boundaries
        if abs(cart_x - self.track_center_x) > self.safe_half_range:
            metrics = {
                "step_count": step_count,
                "success": False,
                "failed": True,
                "failure_reason": f"Cart left safe zone: position x={cart_x:.2f}m, limit ±{self.safe_half_range}m from center",
            }
            return True, 0.0, metrics

        # 2. Check upright condition
        is_upright = abs(pole_angle_true) <= self.balance_angle_rad
        
        if not self._balance_achieved:
            if is_upright:
                self._consecutive_upright_steps += 1
                if self._consecutive_upright_steps >= BALANCE_HOLD_STEPS_REQUIRED:
                    self._balance_achieved = True
            else:
                self._consecutive_upright_steps = 0
        else:
            # Once balance is achieved, pole MUST stay upright
            if not is_upright:
                metrics = {
                    "step_count": step_count,
                    "success": False,
                    "failed": True,
                    "failure_reason": f"Pole left upright region after achieving balance: |angle|={math.degrees(abs(pole_angle_true)):.1f}°",
                }
                return True, 0.0, metrics

        # 3. Check for successful completion
        if step_count >= max_steps:
            metrics = {
                "step_count": step_count,
                "success": self._balance_achieved,
                "failed": False,
                "balance_achieved": self._balance_achieved
            }
            score = 100.0 if self._balance_achieved else (math.cos(pole_angle_true) + 1.0) * 25.0
            return True, score, metrics

        # Periodic status update (not stopping)
        height_score = (math.cos(pole_angle_true) + 1.0) * 25.0
        if self._balance_achieved:
            height_score = 100.0
            
        metrics = {
            "step_count": step_count,
            "success": False,
            "failed": False,
            "balance_achieved": self._balance_achieved
        }
        return False, height_score, metrics

    def get_info(self):
        return {
            "description": "Swing pole to upright and keep balanced",
            "metrics": {"balance_achieved": "Reached upright region", "stability": "Stayed balanced"},
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
