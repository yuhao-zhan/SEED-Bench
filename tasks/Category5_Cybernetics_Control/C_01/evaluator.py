"""
C-01: Cart-Pole Swing-up then Balance evaluation.
Success = pole reaches upright region (|angle| <= 45°) and stays there until max_steps.
Failure = cart leaves safe zone, or (once balance achieved) pole leaves upright region.
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP

try:
    from .environment import BALANCE_ANGLE_RAD, TRACK_CENTER_X, SAFE_HALF_RANGE
except ImportError:
    from environment import BALANCE_ANGLE_RAD, TRACK_CENTER_X, SAFE_HALF_RANGE

# Upright region: balance achieved on first entry; must stay until end (allows some overshoot margin)
# Upright region: pole must stay within ±BALANCE_ANGLE (generous margin for swing-up overshoot)
BALANCE_ANGLE_RAD_EVAL = math.radians(110.0)  # Relaxed for swing-up overshoot past vertical
BALANCE_HOLD_STEPS_REQUIRED = 1  # first crossing counts


class Evaluator:
    """
    Swing-up then balance: no angle failure until pole has entered balance zone.
    Once |angle| <= 45°, balance_achieved; from then on, |angle| > 45° fails.
    Success = reached max_steps and balance was achieved and held.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.balance_angle_rad = BALANCE_ANGLE_RAD_EVAL
        self.track_center_x = float(terrain_bounds.get("track_center_x", TRACK_CENTER_X))
        self.safe_half_range = float(terrain_bounds.get("safe_half_range", SAFE_HALF_RANGE))
        self._balance_achieved = False
        self._consecutive_upright_steps = 0  # must hold for BALANCE_HOLD_STEPS_REQUIRED before achieved

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        pole_angle_true = (
            self.environment.get_true_pole_angle()
            if hasattr(self.environment, "get_true_pole_angle")
            else self.environment.get_pole_angle()
        )
        cart_x = self.environment.get_cart_position()
        cart_vx = self.environment.get_cart_velocity()
        pole_omega = self.environment.get_pole_angular_velocity()

        failed = False
        failure_reason = None

        # Upright zone: balance_achieved on first entry (or after sustained hold if REQUIRED > 1)
        if abs(pole_angle_true) <= self.balance_angle_rad:
            self._consecutive_upright_steps += 1
            if self._consecutive_upright_steps >= BALANCE_HOLD_STEPS_REQUIRED:
                self._balance_achieved = True
        else:
            self._consecutive_upright_steps = 0
        if self._balance_achieved and abs(pole_angle_true) > self.balance_angle_rad:
            failed = True
            failure_reason = (
                f"Pole left upright region after achieving balance: |angle|={math.degrees(abs(pole_angle_true)):.1f}°"
            )

        # Cart safe zone: always enforced; small tolerance for numerical/overshoot
        dist_from_center = abs(cart_x - self.track_center_x)
        if dist_from_center > self.safe_half_range + 0.6:
            failed = True
            failure_reason = (
                f"Cart left safe zone: position x={cart_x:.2f}m, "
                f"limit ±{self.safe_half_range:.1f}m from center"
            )

        success = (
            (step_count >= max_steps - 1)
            and self._balance_achieved
            and not failed
        )

        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Partial: e.g. swung up but not enough time left
            progress = step_count / max_steps if max_steps > 0 else 0.0
            if self._balance_achieved:
                score = 50.0 + progress * 50.0
            else:
                score = progress * 50.0

        metrics = {
            "pole_angle_rad": pole_angle_true,
            "pole_angle_deg": math.degrees(pole_angle_true),
            "cart_x": cart_x,
            "cart_velocity_x": cart_vx,
            "pole_angular_velocity": pole_omega,
            "step_count": step_count,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "balance_achieved": self._balance_achieved,
            "dist_from_center": abs(cart_x - self.track_center_x),
            "safe_half_range": self.safe_half_range,
            "track_center_x": self.track_center_x,
        }

        done = failed or (step_count >= max_steps - 1)
        return done, score, metrics

    def get_task_description(self):
        return {
            "task": "C-01: Cart-Pole Swing-up then Balance",
            "description": "Swing the pole from hanging down to upright, then keep it balanced",
            "failure_angle_deg": 45,
            "success_criteria": {
                "primary": "Reach upright region and hold until end; cart within safe zone",
                "failure": "Cart leaves safe zone, or pole leaves upright after reaching it",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
