"""
F-06: The Pipeline task evaluation module (HARD variant)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class Evaluator:
    """
    Evaluation for F-06: The Pipeline (hard).
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
        
        # Use 0.90 as the default if environment doesn't specify
        self.MIN_DELIVERY_RATIO = getattr(environment, 'MIN_DELIVERY_RATIO', 0.90)
        self.FORCE_BUDGET = getattr(environment, 'FORCE_BUDGET_PER_STEP', 12000.0)

    def evaluate(self, agent_body, step_count, max_steps):
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
            return False, 0.0, {}

        delivery_ratio = self.environment.get_delivery_ratio()
        failed = False
        failure_reason = None

        if delivery_ratio < self.MIN_DELIVERY_RATIO:
            failed = True
            failure_reason = f"Delivery efficiency {delivery_ratio*100:.1f}% below {self.MIN_DELIVERY_RATIO*100:.0f}% target"
        
        if self.structure_broken:
            failed = True
            failure_reason = (failure_reason or "") + ("; " if failure_reason else "") + "Structure integrity lost"

        success = (not failed)
        score = 100.0 if success else 0.0
        
        return True, score, {
            "delivery_ratio": delivery_ratio, "success": success, "failed": failed, "failure_reason": failure_reason,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "structure_broken": self.structure_broken,
        }

    def _check_design_constraints(self):
        violations = []
        if not self.environment: return ["Environment not available"]
        mass = self.environment.get_structure_mass()
        if mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Mass {mass:.2f}kg exceeds {self.MAX_STRUCTURE_MASS}kg")
        return violations

    def get_task_description(self):
        return {
            "task": "F-06: The Pipeline (hard)",
            "description": f"Transport fluid to target; 90% delivery; {self.FORCE_BUDGET} N/step force budget",
            "success_criteria": {
                "primary": f"Delivery efficiency >= {self.MIN_DELIVERY_RATIO*100:.0f}%",
                "secondary": "Structure intact"
            }
        }
