"""
F-02: The Amphibian task evaluation module
Failure: sink, unable to reach shore.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class Evaluator:
    """
    Evaluation for F-02: The Amphibian.
    Success: vehicle reaches x >= 26m without sinking. Failure: sink (y < -0.5) or timeout.
    """

    SINK_Y_THRESHOLD = -0.5

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.initial_joint_count = 0
        self.structure_broken = False
        self.design_constraints_checked = False

        if not environment:
            raise ValueError("Evaluator requires environment instance")
        env_class = type(environment)
        # Prefer instance (mutated) values, then class defaults
        self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', getattr(env_class, 'MAX_STRUCTURE_MASS', 600.0))
        self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', getattr(env_class, 'BUILD_ZONE_X_MIN', 2.0))
        self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', getattr(env_class, 'BUILD_ZONE_X_MAX', 8.0))
        self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', getattr(env_class, 'BUILD_ZONE_Y_MIN', 0.0))
        self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', getattr(env_class, 'BUILD_ZONE_Y_MAX', 4.0))
        self.TARGET_X = getattr(environment, 'TARGET_X', 26.0)

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate amphibian performance. agent_body may be the first body; we use vehicle front x and lowest y.
        Returns: (done, score, metrics).
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        if not self.design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                self.design_constraints_checked = True
                return True, 0.0, {
                    "success": False,
                    "failed": True,
                    "failure_reason": "Design constraint violated: " + "; ".join(violations),
                    "step_count": step_count,
                    "constraint_violations": violations,
                }
            self.design_constraints_checked = True
            self.initial_joint_count = len(self.environment._joints)

        current_joint_count = len(self.environment._joints)
        if current_joint_count < self.initial_joint_count:
            self.structure_broken = True

        front_x = self.environment.get_vehicle_front_x()
        lowest_y = self.environment.get_vehicle_lowest_y()
        done = step_count >= max_steps

        if not done:
            metrics = self._collect_metrics(step_count, front_x, lowest_y, success=False, failed=False, failure_reason=None)
            return False, 0.0, metrics

        failed = False
        failure_reason = None

        if lowest_y is not None and lowest_y < self.SINK_Y_THRESHOLD:
            failed = True
            failure_reason = "Vehicle sank (lowest point y < -0.5)"

        if front_x is not None and front_x < self.TARGET_X:
            if not failed:
                failed = True
                failure_reason = f"Did not reach right bank (front x={front_x:.2f}m, target x={self.TARGET_X}m)"
            else:
                failure_reason += "; did not reach right bank"

        if self.structure_broken:
            failed = True
            failure_reason = (failure_reason or "") + ("; " if failure_reason else "") + "Structure integrity lost (joints broke)"

        success = (front_x is not None and front_x >= self.TARGET_X and
                   (lowest_y is None or lowest_y >= self.SINK_Y_THRESHOLD) and not self.structure_broken and not failed)

        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = (front_x - 2.0) / (self.TARGET_X - 2.0) if front_x is not None and self.TARGET_X > 2 else 0.0
            score = max(0.0, min(80.0, progress * 80.0))

        metrics = self._collect_metrics(
            step_count, front_x, lowest_y,
            success=success, failed=failed, failure_reason=failure_reason,
        )
        return True, score, metrics

    def _collect_metrics(self, step_count, front_x, lowest_y, success=False, failed=False, failure_reason=None):
        velocity = self.environment.get_vehicle_velocity() if hasattr(self.environment, 'get_vehicle_velocity') else None
        velocity_x = velocity[0] if velocity else None
        velocity_y = velocity[1] if velocity else None
        progress = None
        if front_x is not None and self.TARGET_X > 2:
            progress = 100.0 * (front_x - 2.0) / (self.TARGET_X - 2.0)
        return {
            "step_count": step_count,
            "vehicle_front_x": front_x,
            "vehicle_lowest_y": lowest_y,
            "target_x": self.TARGET_X,
            "progress": progress,
            "velocity_x": velocity_x,
            "velocity_y": velocity_y,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "structure_broken": self.structure_broken,
            "joint_count": len(self.environment._joints),
        }

    def _check_design_constraints(self):
        violations = []
        if not self.environment:
            return ["Environment not available"]
        structure_mass = self.environment.get_structure_mass()
        if structure_mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {structure_mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(
                    f"Beam at ({x:.2f}, {y:.2f}) is outside build zone "
                    f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]"
                )
        return violations

    def get_task_description(self):
        return {
            "task": "F-02: The Amphibian",
            "description": "Design an amphibian vehicle to cross water and reach the right bank; must not sink",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": f"Vehicle reaches x >= {self.TARGET_X}m",
                "secondary": "Vehicle does not sink (lowest y >= -0.5)",
                "tertiary": "Structure remains intact",
            },
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
