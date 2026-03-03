"""
D-03: Phase-Locked Gate — evaluation.
"""
import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation for D-03: Phase-Locked Gate.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        # Aligned with environment.py defaults
        self._target_x_min = 11.75
        self._target_speed_min = 0.45
        self._target_speed_max = 2.6
        
        self.design_constraints_checked = False
        self.initial_joint_count = 0
        self.structure_broken = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        if not self.design_constraints_checked and step_count == 0:
            self.initial_joint_count = len(self.environment._joints)
            self.design_constraints_checked = True

        # Collision with gate check
        if getattr(self.environment, "get_gate_collision", lambda: False)():
            return True, 0.0, {"failed": True, "failure_reason": "Gate collision"}

        cabin_pos = self.environment.get_vehicle_position()
        cabin_vel = self.environment.get_vehicle_velocity()
        if cabin_pos is None or cabin_vel is None:
            return False, 0.0, {"error": "Vehicle not found"}

        current_x, current_y = cabin_pos
        vx, vy = cabin_vel
        speed = math.sqrt(vx*vx + vy*vy)

        failed = False
        failure_reason = None
        
        if len(self.environment._joints) < self.initial_joint_count:
            self.structure_broken = True
            failed, failure_reason = True, "Structure broken"

        # Determine success at end
        is_end = (step_count >= max_steps - 1)
        success = False
        if is_end and not failed:
            if current_x < self._target_x_min:
                failed, failure_reason = True, f"Did not reach target zone (x={current_x:.2f} < {self._target_x_min})"
            elif not (self._target_speed_min <= speed <= self._target_speed_max):
                failed, failure_reason = True, f"Final speed out of band ({speed:.2f} m/s)"
            else:
                success = True

        done = failed or success or is_end
        score = 100.0 if success else 0.0
        if not done:
            score = min(current_x / self._target_x_min, 1.0) * 80.0

        return done, score, {
            "x": current_x, "speed": speed, "success": success, "failed": failed, "failure_reason": failure_reason
        }

    def _check_design_constraints(self):
        return []

    def get_task_description(self):
        return {
            "task": "D-03: Phase-Locked Gate",
            "success_criteria": {
                "primary": f"Pass gate and reach x >= {self._target_x_min}m",
                "secondary": f"Final speed in [{self._target_speed_min}, {self._target_speed_max}] m/s"
            }
        }
