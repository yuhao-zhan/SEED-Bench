"""
F-06: The Pipeline task evaluation module (HARD variant)
Failure: delivery efficiency below 85%, structure broken, or particles lost in pit.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class Evaluator:
    """
    Evaluation for F-06: The Pipeline (hard).
    Success: delivery efficiency >= 85%, structure intact. Failure: efficiency < 85% or structure broke.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.initial_joint_count = 0
        self.structure_broken = False
        self.design_constraints_checked = False

        if not environment:
            raise ValueError("Evaluator requires environment instance")
        env_class = type(environment)
        self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', getattr(env_class, 'MAX_STRUCTURE_MASS', 380.0))
        self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', getattr(env_class, 'BUILD_ZONE_X_MIN', 6.0))
        self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', getattr(env_class, 'BUILD_ZONE_X_MAX', 18.0))
        self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', getattr(env_class, 'BUILD_ZONE_Y_MIN', 0.0))
        self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', getattr(env_class, 'BUILD_ZONE_Y_MAX', 6.0))
        self.MIN_DELIVERY_RATIO = getattr(environment, 'MIN_DELIVERY_RATIO', 0.0)

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate pipeline performance. Returns: (done, score, metrics).
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

        done = step_count >= max_steps
        if not done:
            metrics = self._collect_metrics(step_count, success=False, failed=False, failure_reason=None)
            return False, 0.0, metrics

        initial_count = self.environment.get_initial_particle_count()
        in_target = self.environment.get_particles_in_target_count()
        delivery_ratio = self.environment.get_delivery_ratio()

        failed = False
        failure_reason = None

        if delivery_ratio < self.MIN_DELIVERY_RATIO:
            failed = True
            failure_reason = f"Delivery efficiency {delivery_ratio*100:.1f}% below {self.MIN_DELIVERY_RATIO*100:.0f}% target"

        if self.structure_broken:
            failed = True
            failure_reason = (failure_reason or "") + ("; " if failure_reason else "") + "Structure integrity lost (joints broke)"

        success = (delivery_ratio >= self.MIN_DELIVERY_RATIO and not self.structure_broken and not failed)

        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            score = max(0.0, 80.0 * (delivery_ratio / self.MIN_DELIVERY_RATIO))

        metrics = self._collect_metrics(
            step_count,
            success=success,
            failed=failed,
            failure_reason=failure_reason,
            initial_count=initial_count,
            in_target=in_target,
            delivery_ratio=delivery_ratio,
        )
        return True, score, metrics

    def _collect_metrics(self, step_count, success=False, failed=False, failure_reason=None,
                         initial_count=None, in_target=None, delivery_ratio=None):
        if initial_count is None:
            initial_count = self.environment.get_initial_particle_count()
        if in_target is None:
            in_target = self.environment.get_particles_in_target_count()
        if delivery_ratio is None:
            delivery_ratio = self.environment.get_delivery_ratio()

        particles_in_source = getattr(self.environment, "get_particles_in_source_count", lambda: 0)()
        particles_in_build = getattr(self.environment, "get_particles_in_build_zone_count", lambda: 0)()
        particle_stats = getattr(self.environment, "get_particle_stats", lambda: {"mean_x": 0, "mean_y": 0, "active_count": 0})()
        active_count = particle_stats.get("active_count", initial_count)
        particles_lost = initial_count - active_count  # lost in pit or out of world
        return {
            "step_count": step_count,
            "initial_particle_count": initial_count,
            "particles_in_target": in_target,
            "particles_lost": particles_lost,
            "particles_in_source": particles_in_source,
            "particles_in_build_zone": particles_in_build,
            "particle_mean_x": particle_stats.get("mean_x", 0),
            "particle_mean_y": particle_stats.get("mean_y", 0),
            "particle_active_count": active_count,
            "delivery_ratio": delivery_ratio,
            "delivery_ratio_percent": delivery_ratio * 100.0,
            "min_delivery_ratio": self.MIN_DELIVERY_RATIO,
            "min_delivery_ratio_percent": self.MIN_DELIVERY_RATIO * 100.0,
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
            "task": "F-06: The Pipeline (hard)",
            "description": "Transport to very narrow target; avoid three pits; time-varying headwind/gravity well; 90% delivery; 3800 N/step force budget",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": f"Delivery efficiency >= {self.MIN_DELIVERY_RATIO*100:.0f}%",
                "secondary": "Structure intact; avoid all three pits; use apply_force_to_particle (3800 N/step cap)",
            },
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
