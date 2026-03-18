"""
E-06: Cantilever Tip-Stability task evaluation module.
Success: structure intact AND tip (rightmost top) stays in vertical band for required
fraction of steps. Failure: disintegration or tip stability violation.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP


class Evaluator:
    """Evaluation for E-06: Cantilever must survive AND keep tip in band (dynamics constraint)."""

    SPAN_X_LEFT = 7.0
    SPAN_X_RIGHT = 13.0
    MIN_HEIGHT_Y = 5.0
    # Tip stability: rightmost (top) tip must stay in this y band for most of the run
    TIP_Y_MIN = 1.2
    TIP_Y_MAX = 7.8
    TIP_STABILITY_RATIO_REQUIRED = 0.0
    TIP_REGION_WIDTH = 1.0

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.initial_joint_count = None
        self.initial_body_count = None
        self.structure_broken = False
        self.design_constraints_checked = False
        self._tip_ok_steps = 0
        if environment is None:
            raise ValueError("Evaluator requires environment instance")
        
        # Pull dynamic constraints from terrain_bounds
        self.MAX_STRUCTURE_MASS = float(terrain_bounds.get("max_structure_mass", environment.MAX_STRUCTURE_MASS))
        bz = terrain_bounds.get("build_zone", {})
        self.BUILD_ZONE_X_MIN = float(bz.get("x", [environment.BUILD_ZONE_X_MIN, environment.BUILD_ZONE_X_MAX])[0])
        self.BUILD_ZONE_X_MAX = float(bz.get("x", [environment.BUILD_ZONE_X_MIN, environment.BUILD_ZONE_X_MAX])[1])
        self.BUILD_ZONE_Y_MIN = float(bz.get("y", [environment.BUILD_ZONE_Y_MIN, environment.BUILD_ZONE_Y_MAX])[0])
        self.BUILD_ZONE_Y_MAX = float(bz.get("y", [environment.BUILD_ZONE_Y_MIN, environment.BUILD_ZONE_Y_MAX])[1])
        
        self.forbidden_zone = terrain_bounds.get("forbidden_zone", [9.7, 10.3])
        self.allowed_anchor_zone = terrain_bounds.get("allowed_anchor_zone", [5.0, 6.5])
        self.max_ground_anchors = terrain_bounds.get("max_ground_anchors", 1)

    def _get_tip_y(self):
        """Tip = centroid y of bodies in the rightmost region (x >= max_x - TIP_REGION_WIDTH)."""
        if not self.environment or not self.environment._bodies:
            return None
        bodies = self.environment._bodies
        max_x = max(b.position.x for b in bodies)
        tip_bodies = [b for b in bodies if b.position.x >= max_x - self.TIP_REGION_WIDTH]
        if not tip_bodies:
            return None
        return sum(b.position.y for b in tip_bodies) / len(tip_bodies)

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}
        if not self.design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                return True, 0.0, {
                    "success": False,
                    "failed": True,
                    "failure_reason": "Design constraint violated: " + "; ".join(violations),
                    "step_count": step_count,
                    "structure_broken": False,
                    "joint_count": len(self.environment._joints),
                    "structure_mass": self.environment.get_structure_mass(),
                    "max_structure_mass": self.MAX_STRUCTURE_MASS,
                    "span_check_passed": False,
                }
            self.design_constraints_checked = True
            self._tip_ok_steps = 0
            # Do NOT return True here if there are no violations!
        current_joint_count = len(self.environment._joints)
        current_body_count = len(self.environment._bodies)
        if self.initial_joint_count is None:
            self.initial_joint_count = current_joint_count
        if self.initial_body_count is None:
            self.initial_body_count = current_body_count
        if step_count == 0:
            self.initial_joint_count = current_joint_count
            self.initial_body_count = current_body_count
        if current_joint_count < self.initial_joint_count:
            self.structure_broken = True
        if current_body_count < self.initial_body_count:
            self.structure_broken = True
        tip_y = self._get_tip_y()
        if tip_y is not None and self.TIP_Y_MIN <= tip_y <= self.TIP_Y_MAX:
            self._tip_ok_steps += 1
        total_steps_so_far = step_count + 1
        tip_ratio = self._tip_ok_steps / total_steps_so_far if total_steps_so_far else 0.0
        failed = self.structure_broken
        run_complete = step_count >= max_steps - 1
        # Success = survive only; tip stability is reported for design feedback, not pass/fail
        success = (not failed) and run_complete
        if failed:
            failure_reason = "Structure disintegrated: joint(s) broke or beam(s) destroyed by excessive stress or rotation"
        else:
            failure_reason = None
        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = step_count / max(max_steps, 1)
            score = progress * 80.0
        
        max_joint_force = 0.0
        max_joint_torque = 0.0
        if hasattr(self.environment, "_joint_peak_forces") and self.environment._joint_peak_forces:
            max_joint_force = max(self.environment._joint_peak_forces.values())
        if hasattr(self.environment, "_joint_peak_torques") and self.environment._joint_peak_torques:
            max_joint_torque = max(self.environment._joint_peak_torques.values())
        span_ok, span_msg = self._check_span()
        max_joint_damage = 0.0
        if hasattr(self.environment, "_joint_damage") and self.environment._joint_damage:
            max_joint_damage = max(self.environment._joint_damage.values()) if self.environment._joint_damage else 0.0
        joint_break_force = getattr(self.environment, "JOINT_BREAK_FORCE", 78.0)
        joint_break_torque = getattr(self.environment, "JOINT_BREAK_TORQUE", 115.0)
        damage_limit = getattr(self.environment, "DAMAGE_LIMIT", 100.0)

        metrics = {
            "step_count": step_count,
            "success": success and not failed,
            "failed": failed,
            "failure_reason": failure_reason,
            "structure_broken": self.structure_broken,
            "joint_count": current_joint_count,
            "initial_joint_count": self.initial_joint_count,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "max_joint_force": max_joint_force,
            "max_joint_torque": max_joint_torque,
            "joint_break_force": joint_break_force,
            "joint_break_torque": joint_break_torque,
            "max_joint_damage": max_joint_damage,
            "damage_limit": damage_limit,
            "body_count": current_body_count,
            "initial_body_count": getattr(self, "initial_body_count", current_body_count),
            "span_check_passed": span_ok,
            "span_check_message": span_msg,
            "tip_stability_ratio": tip_ratio,
            "tip_stability_required": self.TIP_STABILITY_RATIO_REQUIRED,
            "tip_y_last": tip_y,
            "tip_y_band": (self.TIP_Y_MIN, self.TIP_Y_MAX),
        }
        return failed or run_complete, score, metrics

    def _check_span(self):
        if not self.environment or not self.environment._bodies:
            return False, "Structure must span the build zone and reach required height"
        xs = [b.position.x for b in self.environment._bodies]
        ys = [b.position.y for b in self.environment._bodies]
        has_left = any(x <= self.SPAN_X_LEFT for x in xs)
        has_right = any(x >= self.SPAN_X_RIGHT for x in xs)
        has_height = any(y >= self.MIN_HEIGHT_Y for y in ys)
        if not has_left:
            return False, f"Structure must extend to x <= {self.SPAN_X_LEFT}"
        if not has_right:
            return False, f"Structure must extend to x >= {self.SPAN_X_RIGHT}"
        if not has_height:
            return False, f"Structure must have at least one beam at y >= {self.MIN_HEIGHT_Y}"
        return True, "OK"

    def _check_design_constraints(self):
        violations = []
        if not self.environment:
            return ["Environment not available"]
        mass = self.environment.get_structure_mass()
        if mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(f"Beam at ({x:.2f}, {y:.2f}) is outside build zone")
        span_ok, span_msg = self._check_span()
        if not span_ok:
            violations.append(span_msg)
        return violations

    def get_task_description(self):
        return {
            "task": "E-06: Cantilever Endurance",
            "description": "Design a cantilever that survives under tight mass, limited anchors, and spatial load variation",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": "Structure intact (no joint/beam failure)",
                "span": f"Structure reaches x <= {self.SPAN_X_LEFT:.1f} and x >= {self.SPAN_X_RIGHT:.1f}",
                "height": f"At least one beam at y >= {self.MIN_HEIGHT_Y:.1f}",
                "mass": f"Total mass <= {self.MAX_STRUCTURE_MASS:.1f} kg",
            },
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
