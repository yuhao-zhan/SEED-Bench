"""
D-05: The Hammer task evaluation module
Success: shell is broken. Failure: shell not broken.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


class Evaluator:
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._design_constraints_checked = False
        if environment is None:
            raise ValueError("Evaluator requires environment instance")
        self.MAX_STRUCTURE_MASS = getattr(environment, "MAX_STRUCTURE_MASS", 250.0)
        self.BUILD_ZONE_X_MIN = environment.BUILD_ZONE_X_MIN
        self.BUILD_ZONE_X_MAX = environment.BUILD_ZONE_X_MAX
        self.BUILD_ZONE_Y_MIN = environment.BUILD_ZONE_Y_MIN
        self.BUILD_ZONE_Y_MAX = environment.BUILD_ZONE_Y_MAX

    def evaluate(self, agent_body, step_count, max_steps):
        if self.environment is None:
            return True, 0.0, {"error": "Environment not available"}
        if not self._design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                self._design_constraints_checked = True
                metrics = self._make_metrics(step_count, False, True,
                    "Design constraint violated: " + "; ".join(violations), agent_body)
                return True, 0.0, metrics
            self._design_constraints_checked = True
        shell_broken = self.environment.is_shell_broken()
        hit_pendulum = getattr(self.environment, "hammer_hit_pendulum_before_shell", lambda: False)
        hit_pendulum = hit_pendulum() if callable(hit_pendulum) else hit_pendulum
        hit_gate = getattr(self.environment, "hammer_hit_gate_before_shell", lambda: False)
        hit_gate = hit_gate() if callable(hit_gate) else hit_gate
        hit_gate2 = getattr(self.environment, "hammer_hit_gate2_before_shell", lambda: False)
        hit_gate2 = hit_gate2() if callable(hit_gate2) else hit_gate2
        hit_wall = getattr(self.environment, "hammer_hit_wall_before_shell", lambda: False)
        hit_wall = hit_wall() if callable(hit_wall) else hit_wall
        hit_slot_wall = getattr(self.environment, "hammer_hit_slot_wall_before_shell", lambda: False)
        hit_slot_wall = hit_slot_wall() if callable(hit_slot_wall) else hit_slot_wall
        hit_slot_bar = getattr(self.environment, "hammer_hit_slot_bar_before_shell", lambda: False)
        hit_slot_bar = hit_slot_bar() if callable(hit_slot_bar) else hit_slot_bar
        success = shell_broken and not hit_pendulum and not hit_gate and not hit_gate2 and not hit_wall and not hit_slot_wall and not hit_slot_bar
        failed = False
        failure_reason = None
        if hit_slot_bar:
            failed = True
            failure_reason = "Hammer hit the oscillating bar inside the slot; the slot has a bar that moves up and down—you must time your swing so the head passes through when the bar is away (geometry + timing)"
        elif hit_slot_wall:
            failed = True
            failure_reason = "Hammer hit the slot barrier (wall) before reaching the shell; the path has a narrow vertical GAP—you must design a trajectory that passes through the gap (thread the needle)"
        elif hit_pendulum:
            failed = True
            failure_reason = "Hammer hit a pendulum before reaching the shell; must pass when both pendulums have cleared"
        elif hit_gate:
            failed = True
            failure_reason = "Hammer hit the first gate before reaching the shell; must pass through only when both gates are open"
        elif hit_gate2:
            failed = True
            failure_reason = "Hammer hit the second gate before reaching the shell; both gates must be open when you pass"
        elif hit_wall:
            failed = True
            failure_reason = "Hammer hit the central wall before reaching the shell; the path to the shell is blocked—you must swing OVER the wall (high arc) to hit the shell above"
        elif step_count >= max_steps - 1 and not shell_broken:
            failed = True
            failure_reason = "Shell not broken: the hammer did not deliver enough force to break the shell, or hit the slot barrier / pendulum / wrong trajectory"
        done = failed or success or step_count >= max_steps - 1
        score = 100.0 if success else (0.0 if failed else 0.0)
        metrics = self._make_metrics(step_count, success, failed, failure_reason, agent_body)
        return done, score, metrics

    def _check_design_constraints(self):
        violations = []
        if self.environment is None:
            return ["Environment not available"]
        mass = self.environment.get_structure_mass()
        if mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(
                    f"Beam at ({x:.2f}, {y:.2f}) is outside build zone "
                    f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], "
                    f"y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]"
                )
        return violations

    def _make_metrics(self, step_count, success=False, failed=False, failure_reason=None, agent_body=None):
        hit_pendulum = getattr(self.environment, "hammer_hit_pendulum_before_shell", lambda: False)
        hit_pendulum = hit_pendulum() if callable(hit_pendulum) else hit_pendulum
        hit_gate = getattr(self.environment, "hammer_hit_gate_before_shell", lambda: False)
        hit_gate = hit_gate() if callable(hit_gate) else hit_gate
        hit_gate2 = getattr(self.environment, "hammer_hit_gate2_before_shell", lambda: False)
        hit_gate2 = hit_gate2() if callable(hit_gate2) else hit_gate2
        hit_wall = getattr(self.environment, "hammer_hit_wall_before_shell", lambda: False)
        hit_wall = hit_wall() if callable(hit_wall) else hit_wall
        hit_slot_wall = getattr(self.environment, "hammer_hit_slot_wall_before_shell", lambda: False)
        hit_slot_wall = hit_slot_wall() if callable(hit_slot_wall) else hit_slot_wall
        hit_slot_bar = getattr(self.environment, "hammer_hit_slot_bar_before_shell", lambda: False)
        hit_slot_bar = hit_slot_bar() if callable(hit_slot_bar) else hit_slot_bar
        metrics = {
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "step_count": step_count,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "shell_broken": self.environment.is_shell_broken(),
            "hammer_hit_pendulum": hit_pendulum,
            "hammer_hit_gate": hit_gate,
            "hammer_hit_gate2": hit_gate2,
            "hammer_hit_wall": hit_wall,
            "hammer_hit_slot_wall": hit_slot_wall,
            "hammer_hit_slot_bar": hit_slot_bar,
        }
        # Add shell/terrain info for feedback
        tb = self.terrain_bounds if hasattr(self, "terrain_bounds") else {}
        if tb:
            metrics["shell_x"] = tb.get("shell_x", 18.0)
            metrics["shell_y"] = tb.get("shell_y", 1.0)
            metrics["shell_break_force"] = tb.get("shell_break_force", 1800.0)
            if "pendulum_pivot" in tb:
                metrics["pendulum_pivot"] = tb["pendulum_pivot"]
                metrics["pendulum_rod_length"] = tb.get("pendulum_rod_length", 5.5)
            if "shield_has_window" in tb:
                metrics["shield_has_window"] = tb["shield_has_window"]
            if tb.get("central_wall"):
                metrics["central_wall"] = True
        # Add hammer head physical state (position, velocity, kinetic energy)
        if agent_body is not None:
            metrics["hammer_x"] = float(agent_body.position.x)
            metrics["hammer_y"] = float(agent_body.position.y)
            vx = float(agent_body.linearVelocity.x)
            vy = float(agent_body.linearVelocity.y)
            metrics["velocity_x"] = vx
            metrics["velocity_y"] = vy
            speed = (vx**2 + vy**2) ** 0.5
            metrics["speed"] = speed
            metrics["angular_velocity"] = float(agent_body.angularVelocity)
            metrics["kinetic_energy"] = 0.5 * agent_body.mass * (speed**2) + 0.5 * agent_body.inertia * (metrics["angular_velocity"]**2)
        return metrics

    def get_task_description(self):
        return {
            "task": "D-05: The Hammer",
            "description": "Design a hammer to break the hard shell with a large instantaneous force",
            "success_criteria": {"primary": "Shell is broken", "failure": "Shell not broken"},
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
