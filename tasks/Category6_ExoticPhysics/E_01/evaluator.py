"""
E-01: Inverted Gravity task evaluation module.
Success: no body leaves the arena boundary. Failure: any body out of bounds or structure broken.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation for E-01: Inverted Gravity.
    Primary failure: any dynamic body leaves the arena (flying out of bounds).
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        arena = terrain_bounds.get("arena", {})
        self.arena_x_min = float(arena.get("x_min", 0.0))
        self.arena_x_max = float(arena.get("x_max", 40.0))
        self.arena_y_min = float(arena.get("y_min", 0.0))
        self.arena_y_max = float(arena.get("y_max", 20.0))

        self.initial_joint_count = 0
        self.structure_broken = False
        self.design_constraints_checked = False

        if environment is None:
            raise ValueError("Evaluator requires environment instance")
        # Use instance attrs (mutated) when available; else class attrs
        self.MAX_STRUCTURE_MASS = getattr(environment, "MAX_STRUCTURE_MASS", type(environment).MAX_STRUCTURE_MASS)
        build_zone = terrain_bounds.get("build_zone", {})
        build_y = build_zone.get("y", [6.0, 18.0])
        self.BUILD_ZONE_X_MIN = float(build_zone.get("x", [12.0, 28.0])[0])
        self.BUILD_ZONE_X_MAX = float(build_zone.get("x", [12.0, 28.0])[1])
        self.BUILD_ZONE_Y_MIN = float(build_y[0])
        self.BUILD_ZONE_Y_MAX = float(build_y[1])
        self.MAX_BEAM_COUNT = getattr(environment, "MAX_BEAM_COUNT", getattr(type(environment), "MAX_BEAM_COUNT", 99))
        # Obstacle zones (list): agent body center in any zone -> failure
        obs_list = terrain_bounds.get("obstacles", [])
        self.obstacle_zones = []
        for obs in obs_list:
            self.obstacle_zones.append({
                "x_min": float(obs.get("x_min", 0)),
                "x_max": float(obs.get("x_max", 0)),
                "y_min": float(obs.get("y_min", 0)),
                "y_max": float(obs.get("y_max", 0)),
            })
        # Forbidden zones (list): no beam center allowed; agent must infer from feedback
        fz_list = terrain_bounds.get("forbidden_zones", [])
        self.forbidden_zones = []
        for fz in fz_list:
            self.forbidden_zones.append({
                "x_min": float(fz.get("x_min", 0)),
                "x_max": float(fz.get("x_max", 0)),
                "y_min": float(fz.get("y_min", 0)),
                "y_max": float(fz.get("y_max", 0)),
            })

    def _get_all_dynamic_bodies(self):
        """All dynamic bodies that must stay in bounds: agent bodies + demonstrators."""
        bodies = list(self.environment._bodies)
        for key, body in self.environment._terrain_bodies.items():
            if key.startswith("demonstrator_"):
                bodies.append(body)
        return bodies

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate: success if no body is out of bounds and structure intact.
        Returns: (done, score, metrics)
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        # Design constraints only at step 0
        if not self.design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                return True, 0.0, {
                    "success": False,
                    "failed": True,
                    "failure_reason": "Design constraint violated: " + "; ".join(violations),
                    "step_count": step_count,
                    "out_of_bounds": False,
                    "structure_broken": False,
                    "joint_count": len(self.environment._joints),
                    "structure_mass": self.environment.get_structure_mass(),
                    "max_structure_mass": self.MAX_STRUCTURE_MASS,
                    "arena_x_min": self.arena_x_min,
                    "arena_x_max": self.arena_x_max,
                    "arena_y_min": self.arena_y_min,
                    "arena_y_max": self.arena_y_max,
                    "offending_positions": [],
                }
            self.design_constraints_checked = True

        if step_count == 0:
            self.initial_joint_count = len(self.environment._joints)

        current_joint_count = len(self.environment._joints)
        if current_joint_count < self.initial_joint_count:
            self.structure_broken = True

        # Check every dynamic body for out-of-bounds
        out_of_bounds = False
        offending_positions = []
        for body in self._get_all_dynamic_bodies():
            try:
                x, y = body.position.x, body.position.y
                if x < self.arena_x_min or x > self.arena_x_max or y < self.arena_y_min or y > self.arena_y_max:
                    out_of_bounds = True
                    offending_positions.append((x, y))
            except Exception:
                continue

        # Check agent bodies only: center inside any obstacle zone -> failure
        obstacle_overlap = False
        obstacle_offending = []
        for body in self.environment._bodies:
            try:
                x, y = body.position.x, body.position.y
                for zone in self.obstacle_zones:
                    if (zone["x_min"] <= x <= zone["x_max"] and
                            zone["y_min"] <= y <= zone["y_max"]):
                        obstacle_overlap = True
                        obstacle_offending.append((x, y))
                        break
            except Exception:
                continue

        # Check agent bodies: center inside any forbidden zone -> failure (rule-only, no physical body)
        forbidden_zone_violation = False
        forbidden_offending = []
        for body in self.environment._bodies:
            try:
                x, y = body.position.x, body.position.y
                for zone in self.forbidden_zones:
                    if (zone["x_min"] <= x <= zone["x_max"] and
                            zone["y_min"] <= y <= zone["y_max"]):
                        forbidden_zone_violation = True
                        forbidden_offending.append((x, y))
                        break
            except Exception:
                continue

        failed = out_of_bounds or self.structure_broken or obstacle_overlap or forbidden_zone_violation
        success = (not failed) and (step_count >= max_steps - 1)

        if out_of_bounds:
            failure_reason = f"Flying out of bounds: at least one body left the arena (x in [{self.arena_x_min:.1f}, {self.arena_x_max:.1f}], y in [{self.arena_y_min:.1f}, {self.arena_y_max:.1f}])"
        elif forbidden_zone_violation:
            failure_reason = "Structure enters a forbidden zone; no beam center may lie there (infer from feedback)"
        elif obstacle_overlap:
            failure_reason = "Structure overlaps an obstacle; design must avoid all obstacle zones"
        elif self.structure_broken:
            failure_reason = "Structure integrity lost (joints broke)"
        else:
            failure_reason = None

        # Score: 100 if success, 0 if failed, else partial by progress
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = step_count / max(max_steps, 1)
            score = progress * 80.0

        # Physical state for feedback: body extent and gravity
        body_positions = []
        for body in self._get_all_dynamic_bodies():
            try:
                body_positions.append((body.position.x, body.position.y))
            except Exception:
                continue
        x_min_b = min(p[0] for p in body_positions) if body_positions else None
        x_max_b = max(p[0] for p in body_positions) if body_positions else None
        y_min_b = min(p[1] for p in body_positions) if body_positions else None
        y_max_b = max(p[1] for p in body_positions) if body_positions else None
        gravity_current = None
        if hasattr(self.environment, "get_gravity_at_time"):
            gravity_current = self.environment.get_gravity_at_time()
        
        joint_forensics = None
        if hasattr(self.environment, "get_joint_forensics"):
            joint_forensics = self.environment.get_joint_forensics()

        metrics = {
            "step_count": step_count,
            "success": success and not failed,
            "failed": failed,
            "failure_reason": failure_reason,
            "out_of_bounds": out_of_bounds,
            "obstacle_overlap": obstacle_overlap,
            "obstacle_offending": obstacle_offending[:5],
            "forbidden_zone_violation": forbidden_zone_violation,
            "forbidden_offending": forbidden_offending[:5],
            "structure_broken": self.structure_broken,
            "joint_count": current_joint_count,
            "joint_forensics": joint_forensics,
            "beam_count": len(self.environment._bodies),
            "max_beam_count": self.MAX_BEAM_COUNT,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "arena_x_min": self.arena_x_min,
            "arena_x_max": self.arena_x_max,
            "arena_y_min": self.arena_y_min,
            "arena_y_max": self.arena_y_max,
            "offending_positions": offending_positions[:5],
            "body_count": len(body_positions),
            "body_x_min": x_min_b,
            "body_x_max": x_max_b,
            "body_y_min": y_min_b,
            "body_y_max": y_max_b,
            "gravity_current": gravity_current,
            "progress_pct": 100.0 * step_count / max(max_steps, 1),
        }
        return success or failed, score, metrics

    def _check_design_constraints(self):
        """Check build zone, mass, and beam count. Return list of violation strings."""
        violations = []
        if not self.environment:
            return ["Environment not available"]
        mass = self.environment.get_structure_mass()
        if mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        beam_count = len(self.environment._bodies)
        if beam_count > self.MAX_BEAM_COUNT:
            violations.append(f"Structure has {beam_count} beams, exceeds maximum {self.MAX_BEAM_COUNT} beams")
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(f"Beam at ({x:.2f}, {y:.2f}) is outside build zone")
        return violations

    def get_task_description(self):
        return {
            "task": "E-01: Inverted Gravity",
            "description": "Design a structure that stays within the arena under time-varying or inverted gravity",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": f"No body leaves the arena (x in [{self.arena_x_min:.1f}, {self.arena_x_max:.1f}], y in [{self.arena_y_min:.1f}, {self.arena_y_max:.1f}])",
                "secondary": "Structure joints remain intact",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
