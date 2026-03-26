"""
C-03: The Seeker task evaluation module (Heading-Aligned Rendezvous in Slotted Windows)
"""
import math
import sys
import os
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

_c03_eval_dir = os.path.dirname(os.path.abspath(__file__))
_spec_c03_env = importlib.util.spec_from_file_location(
    "c03_environment_eval", os.path.join(_c03_eval_dir, "environment.py")
)
_c03_environment = importlib.util.module_from_spec(_spec_c03_env)
_spec_c03_env.loader.exec_module(_c03_environment)
ACTIVATION_ZONE_X_MIN = _c03_environment.ACTIVATION_ZONE_X_MIN
ACTIVATION_ZONE_X_MAX = _c03_environment.ACTIVATION_ZONE_X_MAX
ACTIVATION_REQUIRED_STEPS = _c03_environment.ACTIVATION_REQUIRED_STEPS
SLOTS_PHASE1 = _c03_environment.SLOTS_PHASE1
SLOTS_PHASE2 = _c03_environment.SLOTS_PHASE2
RENDEZVOUS_ZONE_X_MIN = _c03_environment.RENDEZVOUS_ZONE_X_MIN
RENDEZVOUS_ZONE_X_MAX = _c03_environment.RENDEZVOUS_ZONE_X_MAX
RENDEZVOUS_DISTANCE_DEFAULT = _c03_environment.RENDEZVOUS_DISTANCE_DEFAULT
RENDEZVOUS_REL_SPEED_DEFAULT = _c03_environment.RENDEZVOUS_REL_SPEED_DEFAULT
TRACK_DISTANCE_DEFAULT = _c03_environment.TRACK_DISTANCE_DEFAULT
RENDEZVOUS_HEADING_TOLERANCE_DEG_DEFAULT = _c03_environment.RENDEZVOUS_HEADING_TOLERANCE_DEG_DEFAULT
# Single source of truth (environment.py); re-export for feedback / callers
HEADING_REFERENCE_MIN_TARGET_SPEED = _c03_environment.HEADING_REFERENCE_MIN_TARGET_SPEED

# Default constants (aliases for Evaluator init / external imports)
RENDEZVOUS_DISTANCE_DEF = RENDEZVOUS_DISTANCE_DEFAULT
RENDEZVOUS_REL_SPEED_DEF = RENDEZVOUS_REL_SPEED_DEFAULT
TRACK_DISTANCE_DEF = TRACK_DISTANCE_DEFAULT
RENDEZVOUS_HEADING_TOLERANCE_DEG_DEF = RENDEZVOUS_HEADING_TOLERANCE_DEG_DEFAULT


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
        self.slots_phase1 = self.terrain_bounds.get("slots_phase1", SLOTS_PHASE1)
        self.slots_phase2 = self.terrain_bounds.get("slots_phase2", SLOTS_PHASE2)
        self.window1_lo = min(s[0] for s in self.slots_phase1)
        self.window1_hi = max(s[1] for s in self.slots_phase1)
        self.window2_lo = min(s[0] for s in self.slots_phase2)
        self.window2_hi = max(s[1] for s in self.slots_phase2)
        heading_deg = float(
            self.terrain_bounds.get(
                "rendezvous_heading_tolerance_deg", RENDEZVOUS_HEADING_TOLERANCE_DEG_DEF
            )
        )
        self.heading_tolerance_rad = math.radians(heading_deg)
        self.heading_tolerance_deg = heading_deg
        self.track_distance = float(
            self.terrain_bounds.get("track_distance", TRACK_DISTANCE_DEF)
        )
        self.rendezvous_zone_x_min = float(
            self.terrain_bounds.get("rendezvous_zone_x_min", RENDEZVOUS_ZONE_X_MIN)
        )
        self.rendezvous_zone_x_max = float(
            self.terrain_bounds.get("rendezvous_zone_x_max", RENDEZVOUS_ZONE_X_MAX)
        )
        self.activation_zone_x_min = float(
            self.terrain_bounds.get("activation_zone_x_min", ACTIVATION_ZONE_X_MIN)
        )
        self.activation_zone_x_max = float(
            self.terrain_bounds.get("activation_zone_x_max", ACTIVATION_ZONE_X_MAX)
        )
        self.activation_required_steps = int(
            self.terrain_bounds.get("activation_required_steps", ACTIVATION_REQUIRED_STEPS)
        )
        self.heading_ref_min_target_speed = float(
            self.terrain_bounds.get(
                "heading_reference_min_target_speed", HEADING_REFERENCE_MIN_TARGET_SPEED
            )
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
            self.rendezvous_zone_x_min <= sx <= self.rendezvous_zone_x_max
        )
        in_any_slot1 = any(lo <= step_count <= hi for (lo, hi) in self.slots_phase1)
        in_any_slot2 = any(lo <= step_count <= hi for (lo, hi) in self.slots_phase2)
        seeker_heading = getattr(self.environment, "get_seeker_heading", lambda: 0.0)()
        target_speed = math.sqrt(tvx * tvx + tvy * tvy)
        if target_speed >= self.heading_ref_min_target_speed:
            target_dir = math.atan2(tvy, tvx)
        else:
            target_dir = math.atan2(ty - sy, tx - sx)
        angle_diff = seeker_heading - target_dir
        while angle_diff > math.pi: angle_diff -= 2 * math.pi
        while angle_diff < -math.pi: angle_diff += 2 * math.pi
        heading_aligned = abs(angle_diff) <= self.heading_tolerance_rad
        # Strict < for relative speed (matches prompt: "relative speed < X m/s")
        conditions_met = (
            activation_achieved
            and distance <= self.rendezvous_distance
            and relative_speed < self.rendezvous_rel_speed
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
        elif getattr(self.environment, "get_obstacle_collision", lambda: False)():
            failed = True
            failure_reason = "Obstacle collision (penetration at or beyond the stated threshold)"
        elif step_count > self.window1_hi and self._rendezvous_count < 1:
            failed = True
            if not activation_achieved:
                failure_reason = "First rendezvous missed: activation not achieved."
            else:
                failure_reason = (
                    "First rendezvous missed: phase-1 window ended without a qualifying capture "
                    f"(simultaneously: inside a phase-1 slot, seeker x in "
                    f"[{self.rendezvous_zone_x_min:g},{self.rendezvous_zone_x_max:g}] m, distance to true target "
                    f"≤{self.rendezvous_distance:.1f} m, relative speed <{self.rendezvous_rel_speed:.2f} m/s, "
                    "heading aligned)."
                )
        elif step_count > self.window2_hi and self._rendezvous_count < 2:
            failed = True
            failure_reason = (
                "Second rendezvous missed: phase-2 window ended without a qualifying capture "
                "(same capture rules as phase 1, after first rendezvous, inside a phase-2 slot)."
            )
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
        if hasattr(self.environment, "get_obstacle_collision"):
            metrics["obstacle_collision"] = self.environment.get_obstacle_collision()
        metrics["activation_zone_x_min"] = self.activation_zone_x_min
        metrics["activation_zone_x_max"] = self.activation_zone_x_max
        metrics["activation_required_steps"] = self.activation_required_steps
        metrics["heading_reference_min_target_speed"] = self.heading_ref_min_target_speed

        done = failed or (step_count >= max_steps - 1)
        return done, score, metrics

    def get_task_description(self):
        return {
            "task": "C-03: The Seeker (Slotted Rendezvous)",
            "description": (
                "Two heading-aligned rendezvous in phase-1 and phase-2 designated slots, then track; "
                f"activation (≥{self.activation_required_steps} steps, "
                f"x∈[{self.activation_zone_x_min:g},{self.activation_zone_x_max:g}] m) required before rendezvous register; "
                f"capture needs x∈[{self.rendezvous_zone_x_min:g},{self.rendezvous_zone_x_max:g}] m, "
                f"distance≤{self.rendezvous_distance:g} m, "
                f"relative speed<{self.rendezvous_rel_speed:g} m/s threshold, heading within "
                f"{self.heading_tolerance_deg:g}° of reference (target velocity if |v|≥"
                f"{self.heading_ref_min_target_speed:g} m/s, else seeker→target)."
            ),
            "rendezvous_distance": self.rendezvous_distance,
            "rendezvous_rel_speed": self.rendezvous_rel_speed,
            "track_distance": self.track_distance,
            "activation_zone_x": [self.activation_zone_x_min, self.activation_zone_x_max],
            "activation_required_consecutive_steps": self.activation_required_steps,
            "rendezvous_zone_x": [self.rendezvous_zone_x_min, self.rendezvous_zone_x_max],
            "heading_tolerance_deg": self.heading_tolerance_deg,
            "heading_reference_min_target_speed": self.heading_ref_min_target_speed,
            "success_criteria": {
                "phase1": "First rendezvous in a phase-1 slot before phase-1 window ends",
                "phase2": "Second rendezvous in a phase-2 slot before phase-2 window ends",
                "phase3": f"After second rendezvous, distance <= {self.track_distance} m until episode end",
                "capture": (
                    f"distance<={self.rendezvous_distance} m, relative_speed<{self.rendezvous_rel_speed} m/s, "
                    f"heading within {self.heading_tolerance_deg:g}° of reference direction, seeker x in "
                    f"[{self.rendezvous_zone_x_min:g},{self.rendezvous_zone_x_max:g}] m, activation satisfied"
                ),
                "failure": "Miss slots, obstacles, corridor exit, impulse budget, or lose target after rendezvous",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
