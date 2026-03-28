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
        
        # Read from terrain_bounds so mutated stages stay in sync (aligned with environment.py defaults)
        self._target_x_min = float(terrain_bounds.get("target_x_min", 11.75))
        self._target_speed_min = float(terrain_bounds.get("target_speed_min", 0.45))
        self._target_speed_max = float(terrain_bounds.get("target_speed_max", 2.6))
        self._speed_trap_x = float(terrain_bounds.get("speed_trap_x", 9.0))
        self._checkpoint_11_x = float(terrain_bounds.get("checkpoint_11_x", 11.0))
        
        self.design_constraints_checked = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        if not self.design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                self.design_constraints_checked = True
                return True, 0.0, {"failed": True, "failure_reason": "Design constraint violated: " + "; ".join(violations)}
            self.design_constraints_checked = True

        cabin_pos = self.environment.get_vehicle_position()
        cabin_vel = self.environment.get_vehicle_velocity()
        if cabin_pos is None or cabin_vel is None:
            return False, 0.0, {"failed": True, "failure_reason": "Cart not found"}

        current_x, current_y = cabin_pos
        vx, vy = cabin_vel
        speed = math.sqrt(vx*vx + vy*vy)

        failed = False
        failure_reason = None

        # Gate collision check
        if getattr(self.environment, "get_gate_collision", lambda: False)():
            return True, 0.0, {"failed": True, "failure_reason": "Gate collision"}

        if getattr(self.environment, "_speed_trap_failed", False):
            return True, 0.0, {"failed": True, "failure_reason": f"Speed trap failed (too slow at x={self._speed_trap_x:.1f})"}

        # Checkpoint failed check
        if getattr(self.environment, "_checkpoint_11_failed", False):
            return True, 0.0, {"failed": True, "failure_reason": f"Checkpoint failed (speed at x={self._checkpoint_11_x:.1f} out of band)"}

        # Determine success
        is_end = (step_count >= max_steps - 1)
        success = False
        if not failed:
            if current_x >= self._target_x_min:
                if self._target_speed_min <= speed <= self._target_speed_max:
                    success = True
                    print(f"SUCCESS at step {step_count}: x={current_x:.2f}, speed={speed:.2f}")
                elif is_end:
                    failed, failure_reason = True, f"Final speed out of band ({speed:.2f} m/s)"
            elif is_end:
                failed, failure_reason = True, f"Did not reach target zone (x={current_x:.2f} < {self._target_x_min})"

        done = failed or success or is_end
        score = 100.0 if success else 0.0
        if not done:
            score = min(current_x / self._target_x_min, 1.0) * 80.0

        return done, score, {
            "x": current_x, "speed": speed, "success": success, "failed": failed, "failure_reason": failure_reason
        }

    def _check_design_constraints(self):
        violations = []
        if self.environment is None:
            return ["Environment not available"]
        
        # Beam count check
        min_beams = self.terrain_bounds.get("min_beam_count", 4)
        max_beams = self.terrain_bounds.get("max_beam_count", 5)
        num_beams = len(self.environment._bodies)
        if num_beams < min_beams or num_beams > max_beams:
            violations.append(f"Beam count {num_beams} is outside allowed range [{min_beams}, {max_beams}]")
            
        # Build zone check
        bz = self.terrain_bounds.get("build_zone", {})
        bx_min, bx_max = bz.get("x", [4.8, 9.0])
        by_min, by_max = bz.get("y", [2.0, 3.2])
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (bx_min <= x <= bx_max and by_min <= y <= by_max):
                violations.append(f"Beam at ({x:.2f}, {y:.2f}) is outside build zone")
                
        # Mass check
        max_mass = self.terrain_bounds.get("max_structure_mass", 14.0)
        mass = self.environment.get_structure_mass()
        if mass > max_mass:
            violations.append(f"Structure mass {mass:.2f} kg exceeds limit {max_mass} kg")
            
        return violations

    def get_task_description(self):
        return {
            "task": "D-03: Phase-Locked Gate",
            "success_criteria": {
                "primary": f"Pass gate and reach x >= {self._target_x_min}m",
                "secondary": f"Final speed in [{self._target_speed_min}, {self._target_speed_max}] m/s"
            }
        }
