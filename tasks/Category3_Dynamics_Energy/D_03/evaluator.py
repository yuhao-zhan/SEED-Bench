"""
D-03: Phase-Locked Gate — evaluation.
Success: cart passes gate when open (no collision), reaches target zone, final speed in band.
Failure: gate collision, wrong timing, or design constraints violated.
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation for D-03: Phase-Locked Gate.
    Success: no gate collision; cart first crossed gate (x=10) while gate was open;
             cart reached target_x_min; final speed in [target_speed_min, target_speed_max].
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._gate_pivot_x = float(terrain_bounds.get("gate_pivot_x", 10.0))
        self._gate2_pivot_x = float(terrain_bounds.get("gate2_pivot_x", 13.0))
        self._gate3_pivot_x = float(terrain_bounds.get("gate3_pivot_x", 11.5))
        self._gate4_pivot_x = float(terrain_bounds.get("gate4_pivot_x", 12.5))
        self._target_x_min = float(terrain_bounds.get("target_x_min", 15.0))
        self._target_speed_min = float(terrain_bounds.get("target_speed_min", 2.0))
        self._target_speed_max = float(terrain_bounds.get("target_speed_max", 2.5))

        self._design_constraints_checked = False
        self._gate_crossed = False
        self._gate_was_open_when_crossed = False
        self._gate2_crossed = False
        self._gate2_was_open_when_crossed = False
        self._gate3_crossed = False
        self._gate3_was_open_when_crossed = False
        self._gate4_crossed = False
        self._gate4_was_open_when_crossed = False
        self._target_reached = False
        self._final_speed = None

        if environment is None:
            raise ValueError("Evaluator requires environment instance")
        self.MAX_STRUCTURE_MASS = getattr(environment, "MAX_STRUCTURE_MASS", 14.0)
        self.MAX_BEAM_COUNT = getattr(environment, "MAX_BEAM_COUNT", 5)
        self.MIN_BEAM_COUNT = getattr(environment, "MIN_BEAM_COUNT", 3)
        self.BUILD_ZONE_X_MIN = environment.BUILD_ZONE_X_MIN
        self.BUILD_ZONE_X_MAX = environment.BUILD_ZONE_X_MAX
        self.BUILD_ZONE_Y_MIN = environment.BUILD_ZONE_Y_MIN
        self.BUILD_ZONE_Y_MAX = environment.BUILD_ZONE_Y_MAX

    def evaluate(self, agent_body, step_count, max_steps):
        if self.environment is None:
            return True, 0.0, {"error": "Environment not available"}

        cabin = getattr(self.environment, "get_vehicle_cabin", lambda: None)()
        if cabin is None:
            return True, 0.0, {"error": "Cart not found"}

        pos = (cabin.position.x, cabin.position.y)
        vel = (cabin.linearVelocity.x, cabin.linearVelocity.y)
        px, py = pos[0], pos[1]
        vx, vy = vel[0], vel[1]
        speed = math.sqrt(vx * vx + vy * vy)

        # First time cart center crosses gate 1 pivot x
        if not self._gate_crossed and px >= self._gate_pivot_x:
            self._gate_crossed = True
            self._gate_was_open_when_crossed = self.environment.is_gate_open()
        # First time cart center crosses gate 2 pivot x
        if not self._gate2_crossed and px >= self._gate2_pivot_x:
            self._gate2_crossed = True
            self._gate2_was_open_when_crossed = self.environment.is_gate2_open()
        # First time cart center crosses gate 3 pivot x
        if not self._gate3_crossed and px >= self._gate3_pivot_x:
            self._gate3_crossed = True
            self._gate3_was_open_when_crossed = self.environment.is_gate3_open()
        # First time cart center crosses gate 4 pivot x
        if not self._gate4_crossed and px >= self._gate4_pivot_x:
            self._gate4_crossed = True
            self._gate4_was_open_when_crossed = self.environment.is_gate4_open()

        if px >= self._target_x_min:
            self._target_reached = True
            if self._final_speed is None:
                self._final_speed = speed

        # Design constraints at step 0
        if not self._design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                self._design_constraints_checked = True
                metrics = self._make_metrics(pos, vel, step_count, success=False, failed=True,
                    failure_reason="Design constraint violated: " + "; ".join(violations))
                return True, 0.0, metrics
            self._design_constraints_checked = True

        # Gate collision → immediate fail
        if getattr(self.environment, "_gate_collision_occurred", False):
            metrics = self._make_metrics(pos, vel, step_count, success=False, failed=True,
                failure_reason="Cart or beams collided with the rotating gate — must pass only when gate is open.")
            return True, 0.0, metrics

        # Speed trap fail (speed at x=9 below minimum)
        if getattr(self.environment, "_speed_trap_failed", False):
            metrics = self._make_metrics(pos, vel, step_count, success=False, failed=True,
                failure_reason="Speed trap failed: speed when first crossing x=9 was below required minimum (2.8 m/s).")
            return True, 0.0, metrics

        # Checkpoint at x=11: velocity profile constraint — speed must be in band when first crossing x=11
        if getattr(self.environment, "_checkpoint_11_failed", False):
            cp_lo = getattr(self.environment, "_checkpoint_11_speed_min", 1.1)
            cp_hi = getattr(self.environment, "_checkpoint_11_speed_max", 2.7)
            metrics = self._make_metrics(pos, vel, step_count, success=False, failed=True,
                failure_reason="Velocity profile failed: speed when first crossing x=11 must be in [%.2f, %.2f] m/s (couples to gate phase timing)." % (cp_lo, cp_hi))
            return True, 0.0, metrics

        success = (
            self._gate_crossed
            and self._gate_was_open_when_crossed
            and self._gate2_crossed
            and self._gate2_was_open_when_crossed
            and self._gate3_crossed
            and self._gate3_was_open_when_crossed
            and self._gate4_crossed
            and self._gate4_was_open_when_crossed
            and self._target_reached
            and self._final_speed is not None
            and self._target_speed_min <= self._final_speed <= self._target_speed_max
        )
        failed = (
            (self._gate_crossed and not self._gate_was_open_when_crossed)
            or (self._gate2_crossed and not self._gate2_was_open_when_crossed)
            or (self._gate3_crossed and not self._gate3_was_open_when_crossed)
            or (self._gate4_crossed and not self._gate4_was_open_when_crossed)
            or (self._target_reached and (self._final_speed is None or self._final_speed < self._target_speed_min or self._final_speed > self._target_speed_max))
        )
        failure_reason = None
        if self._gate_crossed and not self._gate_was_open_when_crossed:
            failure_reason = "Cart passed gate 1 (x=10) when it was CLOSED — phase-lock arrival so gate is open."
        elif self._gate2_crossed and not self._gate2_was_open_when_crossed:
            failure_reason = "Cart passed gate 2 (x={}) when it was CLOSED — must pass ALL FOUR gates when open.".format(self._gate2_pivot_x)
        elif self._gate3_crossed and not self._gate3_was_open_when_crossed:
            failure_reason = "Cart passed gate 3 (x={}) when it was CLOSED — must pass ALL FOUR gates when open.".format(self._gate3_pivot_x)
        elif self._gate4_crossed and not self._gate4_was_open_when_crossed:
            failure_reason = "Cart passed gate 4 (x={}) when it was CLOSED — must pass ALL FOUR gates when open.".format(self._gate4_pivot_x)
        elif self._target_reached and self._final_speed is not None:
            if self._final_speed < self._target_speed_min:
                failure_reason = f"Final speed {self._final_speed:.2f} m/s below target band [{self._target_speed_min}, {self._target_speed_max}] m/s."
            elif self._final_speed > self._target_speed_max:
                failure_reason = f"Final speed {self._final_speed:.2f} m/s above target band [{self._target_speed_min}, {self._target_speed_max}] m/s."

        done = False
        if failed:
            done = True
            score = 0.0
        elif step_count >= max_steps - 1:
            done = True
            if not self._gate_crossed:
                success = False
                failed = True
                failure_reason = "Cart never reached gate 1 (x=10)."
            elif not self._gate2_crossed:
                success = False
                failed = True
                failure_reason = "Cart never reached gate 2 (x={}).".format(self._gate2_pivot_x)
            elif not self._gate3_crossed:
                success = False
                failed = True
                failure_reason = "Cart never reached gate 3 (x={}).".format(self._gate3_pivot_x)
            elif not self._gate4_crossed:
                success = False
                failed = True
                failure_reason = "Cart never reached gate 4 (x={}).".format(self._gate4_pivot_x)
            elif not self._target_reached:
                success = False
                failed = True
                failure_reason = f"Cart never reached target zone x>={self._target_x_min}."
            elif not failed:
                success = success and (self._target_speed_min <= self._final_speed <= self._target_speed_max if self._final_speed is not None else False)
            score = 100.0 if success else 0.0
        else:
            score = 100.0 if success else 0.0

        metrics = self._make_metrics(pos, vel, step_count, success=success, failed=failed, failure_reason=failure_reason)
        return done, score, metrics

    def _check_design_constraints(self):
        violations = []
        if self.environment is None:
            return ["Environment not available"]
        ground = self.environment._terrain_bodies.get("ground")
        if ground is not None:
            for joint in self.environment._joints:
                if joint.bodyB == ground:
                    violations.append("Ground anchoring is not allowed. Attach all beams to the cart only.")
                    break
        beam_count = len(self.environment._bodies)
        if beam_count < self.MIN_BEAM_COUNT:
            violations.append(f"Beam count {beam_count} is below minimum {self.MIN_BEAM_COUNT} — at least {self.MIN_BEAM_COUNT} beams required.")
        if beam_count > self.MAX_BEAM_COUNT:
            violations.append(f"Beam count {beam_count} exceeds maximum {self.MAX_BEAM_COUNT}")
        mass = self.environment.get_structure_mass()
        if mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (
                self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX
                and self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX
            ):
                violations.append(
                    f"Beam at ({x:.2f}, {y:.2f}) is outside build zone "
                    f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], "
                    f"y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]"
                )
        return violations

    def _make_metrics(self, pos, vel, step_count, success=False, failed=False, failure_reason=None):
        px, py = pos[0], pos[1]
        vx, vy = vel[0], vel[1]
        speed = math.sqrt(vx * vx + vy * vy)
        return {
            "passenger_x": px,
            "passenger_y": py,
            "passenger_vx": vx,
            "passenger_vy": vy,
            "passenger_speed": speed,
            "gate_crossed": self._gate_crossed,
            "gate_was_open_when_crossed": self._gate_was_open_when_crossed,
            "gate2_crossed": self._gate2_crossed,
            "gate2_was_open_when_crossed": self._gate2_was_open_when_crossed,
            "gate3_crossed": self._gate3_crossed,
            "gate3_was_open_when_crossed": self._gate3_was_open_when_crossed,
            "gate4_crossed": self._gate4_crossed,
            "gate4_was_open_when_crossed": self._gate4_was_open_when_crossed,
            "target_reached": self._target_reached,
            "final_speed": self._final_speed,
            "target_x_min": self._target_x_min,
            "target_speed_min": self._target_speed_min,
            "target_speed_max": self._target_speed_max,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "step_count": step_count,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "beam_count": len(self.environment._bodies),
        }

    def get_task_description(self):
        return {
            "task": "D-03: Phase-Locked Gate",
            "description": "Velocity profile: v(9)≥2.8 m/s (speed trap), v(11) in [1.3, 2.5] m/s (checkpoint), final in [{}, {}] m/s. Decel zone [9.5,11] sheds speed. Pass ALL FOUR gates when open (narrow windows); impulse [8,9]; reach x>={}. ≥{} beams, ≤{} beams, <{} kg.".format(
                self._target_speed_min, self._target_speed_max,
                self._target_x_min,
                self.MIN_BEAM_COUNT, self.MAX_BEAM_COUNT, self.MAX_STRUCTURE_MASS
            ),
            "success_criteria": {
                "primary": "No gate collision; pass gate when open; reach target; final speed in band",
                "failure": "Gate collision, wrong timing, or design constraints violated",
            },
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
