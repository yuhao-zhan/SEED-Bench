"""
C-03: The Seeker task evaluation module (Heading-Aligned Rendezvous in Slotted Windows)
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP

# Default constants
RENDEZVOUS_DISTANCE_DEF = 6.0   
RENDEZVOUS_REL_SPEED_DEF = 1.8  
TRACK_DISTANCE_DEF = 8.5        
RENDEZVOUS_HEADING_TOLERANCE_RAD = math.radians(55)  
SLOTS_PHASE1 = [(3700, 3800), (4200, 4300), (4700, 4800)]   
SLOTS_PHASE2 = [(6200, 6300), (6700, 6800), (7200, 7300)]
RENDEZVOUS_ZONE_X_MIN = 10.0
RENDEZVOUS_ZONE_X_MAX = 20.0

RENDEZVOUS_WINDOW1_HI = 4800
RENDEZVOUS_WINDOW2_HI = 7300
RENDEZVOUS_WINDOW1_LO = 3700
RENDEZVOUS_WINDOW2_LO = 6200


class Evaluator:
    """
    Evaluation for C-03: The Seeker (Two Rendezvous then Track).
    """

    def __init__(self, terrain_bounds, environment=None):
        # terrain_bounds might be a Sandbox instance or a dict
        self.environment = environment
        if hasattr(terrain_bounds, "get_terrain_bounds"):
            self.terrain_bounds = terrain_bounds.get_terrain_bounds()
            if self.environment is None:
                self.environment = terrain_bounds
        else:
            self.terrain_bounds = terrain_bounds or {}

        self.rendezvous_distance = float(
            self.terrain_bounds.get("rendezvous_distance", RENDEZVOUS_DISTANCE_DEF)
        )
        self.rendezvous_rel_speed = float(
            self.terrain_bounds.get("rendezvous_rel_speed", RENDEZVOUS_REL_SPEED_DEF)
        )
        self.window1_lo = RENDEZVOUS_WINDOW1_LO
        self.window1_hi = RENDEZVOUS_WINDOW1_HI
        self.window2_lo = RENDEZVOUS_WINDOW2_LO
        self.window2_hi = RENDEZVOUS_WINDOW2_HI
        self.slots_phase1 = SLOTS_PHASE1
        self.slots_phase2 = SLOTS_PHASE2
        self.heading_tolerance_rad = RENDEZVOUS_HEADING_TOLERANCE_RAD
        self.track_distance = float(
            self.terrain_bounds.get("track_distance", TRACK_DISTANCE_DEF)
        )
        self._rendezvous_count = 0  # 0, 1, or 2

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        distance = self.environment.get_distance_to_target()
        sx, sy = self.environment.get_seeker_position()
        vx, vy = self.environment.get_seeker_velocity()
        tx, ty = (
            self.environment.get_target_position_true()
            if hasattr(self.environment, "get_target_position_true")
            else self.environment.get_target_position()
        )
        tvx, tvy = (
            self.environment.get_target_velocity_true()
            if hasattr(self.environment, "get_target_velocity_true")
            else (0.0, 0.0)
        )

        rel_vx = vx - tvx
        rel_vy = vy - tvy
        relative_speed = math.sqrt(rel_vx * rel_vx + rel_vy * rel_vy)

        activation_achieved = getattr(
            self.environment, "get_activation_achieved", lambda: False
        )()
        in_rendezvous_zone = (
            RENDEZVOUS_ZONE_X_MIN <= sx <= RENDEZVOUS_ZONE_X_MAX
        )
        in_any_slot1 = any(lo <= step_count <= hi for (lo, hi) in self.slots_phase1)
        in_any_slot2 = any(lo <= step_count <= hi for (lo, hi) in self.slots_phase2)
        seeker_heading = getattr(self.environment, "get_seeker_heading", lambda: 0.0)()
        target_speed = math.sqrt(tvx * tvx + tvy * tvy)
        if target_speed >= 0.15:
            target_dir = math.atan2(tvy, tvx)
        else:
            target_dir = math.atan2(ty - sy, tx - sx)
        angle_diff = seeker_heading - target_dir
        while angle_diff > math.pi: angle_diff -= 2 * math.pi
        while angle_diff < -math.pi: angle_diff += 2 * math.pi
        heading_aligned = abs(angle_diff) <= self.heading_tolerance_rad
        conditions_met = (
            activation_achieved
            and distance <= self.rendezvous_distance
            and relative_speed <= self.rendezvous_rel_speed
            and in_rendezvous_zone
            and heading_aligned
        )
        if conditions_met and in_any_slot1:
            self._rendezvous_count = max(self._rendezvous_count, 1)
        if conditions_met and in_any_slot2 and self._rendezvous_count >= 1:
            self._rendezvous_count = 2

        failed = False
        failure_reason = None

        if getattr(self.environment, "get_out_of_fuel", lambda: False)():
            failed = True
            failure_reason = "Thrust budget exceeded (out of fuel)"
        elif getattr(self.environment, "get_corridor_violation", lambda: False)():
            failed = True
            failure_reason = "Left the allowed moving corridor"
        elif step_count > self.window1_hi and self._rendezvous_count < 1:
            failed = True
            if not activation_achieved:
                failure_reason = "First rendezvous missed: activation not achieved."
            else:
                failure_reason = "First rendezvous slot missed."
        elif self._rendezvous_count >= 2 and distance > self.track_distance:
            failed = True
            failure_reason = f"Target lost after rendezvous: distance {distance:.2f} m exceeds track limit {self.track_distance:.1f} m"

        success = (step_count >= max_steps - 1) and self._rendezvous_count >= 2 and not failed

        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = step_count / max_steps if max_steps > 0 else 0.0
            if self._rendezvous_count >= 2:
                score = 90.0 + progress * 10.0
            elif self._rendezvous_count >= 1:
                score = 50.0 + progress * 40.0
            else:
                score = progress * 50.0

        metrics = {
            "seeker_x": sx,
            "seeker_y": sy,
            "seeker_vx": vx,
            "seeker_vy": vy,
            "target_x": tx,
            "target_y": ty,
            "distance_to_target": distance,
            "relative_speed": relative_speed,
            "rendezvous_distance": self.rendezvous_distance,
            "rendezvous_rel_speed": self.rendezvous_rel_speed,
            "track_distance": self.track_distance,
            "step_count": step_count,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "rendezvous_count": self._rendezvous_count,
            "heading_aligned": heading_aligned,
            "heading_error_deg": math.degrees(abs(angle_diff)),
        }
        if hasattr(self.environment, "get_remaining_impulse_budget"):
            metrics["remaining_impulse_budget"] = self.environment.get_remaining_impulse_budget()
        if hasattr(self.environment, "get_out_of_fuel"):
            metrics["out_of_fuel"] = self.environment.get_out_of_fuel()
        if hasattr(self.environment, "get_corridor_violation"):
            metrics["corridor_violation"] = self.environment.get_corridor_violation()
        if hasattr(self.environment, "get_activation_achieved"):
            metrics["activation_achieved"] = self.environment.get_activation_achieved()

        done = failed or (step_count >= max_steps - 1)
        return done, score, metrics

    def get_task_description(self):
        return {
            "task": "C-03: The Seeker (Slotted Rendezvous)",
            "description": "Achieve at least one rendezvous in a time slot then track",
            "rendezvous_distance": self.rendezvous_distance,
            "rendezvous_rel_speed": self.rendezvous_rel_speed,
            "track_distance": self.track_distance,
            "success_criteria": {
                "phase1": "Achieve first rendezvous in a first time slot",
                "phase2": "Achieve second rendezvous in a later time slot (optional for ref)",
                "phase3": f"After rendezvous, keep distance <= {self.track_distance} m",
                "failure": "Miss slots or lose target",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
