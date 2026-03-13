"""
K-04: The Pusher task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system for K-04: The Pusher
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        self.target_distance = float(terrain_bounds.get("target_distance", 10.0))
        self.min_simulation_time = 12.0 # seconds (aligned with prompt description)
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)
        
        self.initial_object_x = 8.0
        self.max_x_reached = 8.0
        self.max_pusher_tilt = 0.0
        
        # Design constraints from environment
        if environment:
            self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', 40.0)
            self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', 0.0)
            self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', 15.0)
            self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', 1.5)
            self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', 8.0)
        
        self.design_constraints_checked = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return (False, 0.0, {"error": "Environment not available"})
        
        # 0. Check design constraints at start
        failed = False
        failure_reason = None
        
        if not self.design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                failed = True
                failure_reason = "Design constraint violated: " + "; ".join(violations)
            self.design_constraints_checked = True

        # Get object position from environment
        object_pos = self.environment.get_object_position()
        if object_pos is None:
            return (False, 0.0, {"error": "Object to push not found"})
            
        current_object_x, current_object_y = object_pos
        self.max_x_reached = max(self.max_x_reached, current_object_x)
        
        # Robust pusher tracking
        pusher = agent_body
        if pusher is None and self.environment._bodies:
            pusher = self.environment._bodies[0]
            
        pusher_x, pusher_y, pusher_angle = 0.0, 0.0, 0.0
        if pusher:
            pusher_x = pusher.position.x
            pusher_y = pusher.position.y
            pusher_angle = pusher.angle
            # Normalize angle to [-pi, pi]
            while pusher_angle > math.pi: pusher_angle -= 2 * math.pi
            while pusher_angle < -math.pi: pusher_angle += 2 * math.pi
            self.max_pusher_tilt = max(self.max_pusher_tilt, abs(pusher_angle))

        if not failed:
            # Failure: Object fell off the platform (ground level is y=1.0)
            if current_object_y < 0.5:
                failed = True
                failure_reason = "Object fell off the platform"
                
            # Failure: Pusher tipped over (tilt > 30 degrees = pi/6 radians)
            elif abs(pusher_angle) > math.pi / 6:
                failed = True
                failure_reason = f"Pusher tipped over: tilt angle {abs(pusher_angle):.3f} rad exceeds limit \u00b1\u03c0/6 (\u00b130\u00b0)"

            # Failure: Detection for wheel-specific failures (aligned with feedback.py)
            else:
                wheel_failure = self._check_wheel_states()
                if wheel_failure:
                    # We only report these if they persist or represent a terminal state
                    # For this task, we'll use them as warnings unless they stop progress
                    pass

        # Success if pushed target distance and survived minimum time
        distance_pushed = current_object_x - self.initial_object_x
        success = distance_pushed >= self.target_distance and step_count >= self.min_simulation_steps
        
        # Detection for wheel-specific states (aligned with feedback.py suggestions)
        # We check these regardless of failure to provide metrics for feedback
        wheel_state = self._check_wheel_states()
        
        # Check if object is actually being pushed (motion correlation)
        # If pusher is moving but object is static
        if pusher and self.environment._object_to_push:
            pusher_vx = pusher.linearVelocity.x
            object_vx = self.environment._object_to_push.linearVelocity.x
            if pusher_vx > 0.5 and object_vx < 0.05:
                if not hasattr(self, 'not_pushed_counter'): self.not_pushed_counter = 0
                self.not_pushed_counter += 1
            else:
                self.not_pushed_counter = 0
        
        is_end = (step_count >= max_steps - 1)
        # Early termination on success or failure
        done = failed or success or is_end

        # Progress (0–1) for metrics; always compute so metrics are consistent on success/failure
        progress = min(max(0, distance_pushed) / self.target_distance, 1.0) if self.target_distance > 0 else 0.0
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            score = progress * 70.0
            if step_count > 0:
                score += (min(step_count, self.min_simulation_steps) / self.min_simulation_steps) * 30.0
                
        metrics = {
            'object_x': current_object_x,
            'object_y': current_object_y,
            'pusher_x': pusher_x,
            'pusher_y': pusher_y,
            'pusher_angle': pusher_angle,
            'pusher_velocity_x': pusher.linearVelocity.x if pusher else 0.0,
            'pusher_velocity_y': pusher.linearVelocity.y if pusher else 0.0,
            'object_velocity_x': self.environment._object_to_push.linearVelocity.x if self.environment._object_to_push else 0.0,
            'distance_pushed': distance_pushed,
            'max_distance_pushed': self.max_x_reached - self.initial_object_x,
            'max_pusher_tilt': self.max_pusher_tilt,
            'pusher_tipped': abs(pusher_angle) > math.pi / 6,
            'target_object_x': self.initial_object_x + self.target_distance,
            'progress': progress * 100.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason or (wheel_state if step_count > 100 else None) or ("not pushed effectively" if getattr(self, 'not_pushed_counter', 0) > 200 else None),
            'step_count': step_count,
            'min_simulation_steps_required': self.min_simulation_steps,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': self.MAX_STRUCTURE_MASS,
        }
        
        return done, score, metrics

    def _check_design_constraints(self):
        """Verify mass and build zone constraints"""
        violations = []
        mass = self.environment.get_structure_mass()
        if mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {mass:.2f}kg exceeds limit {self.MAX_STRUCTURE_MASS}kg")
        
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            # Check if any part of the body is outside. For simplicity, check center.
            if not (self.BUILD_ZONE_X_MIN - 0.01 <= x <= self.BUILD_ZONE_X_MAX + 0.01 and
                    self.BUILD_ZONE_Y_MIN - 0.01 <= y <= self.BUILD_ZONE_Y_MAX + 0.01):
                violations.append(f"Component at ({x:.2f}, {y:.2f}) is outside build zone x:[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], y:[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]")
        return violations

    def _check_wheel_states(self):
        """Detect wheel spinning or suspension for richer metrics"""
        from Box2D.b2 import circleShape
        wheels = []
        for body in self.environment._bodies:
            for fixture in body.fixtures:
                if isinstance(fixture.shape, circleShape):
                    wheels.append(body)
                    break
        
        if not wheels: return None
        
        ground_y = 1.0
        all_suspended = True
        for w in wheels:
            # Check if bottom of wheel is near ground
            radius = w.fixtures[0].shape.radius
            if w.position.y - radius < ground_y + 0.15:
                all_suspended = False
                break
        
        if all_suspended:
            return "wheels suspended"
            
        # Detect spinning: High angular velocity but low linear velocity
        spinning_count = 0
        for w in wheels:
            v = w.linearVelocity.length
            omega = abs(w.angularVelocity)
            radius = w.fixtures[0].shape.radius
            # If tangential speed (omega*r) >> linear speed
            if omega * radius > 2.0 and v < 0.5:
                spinning_count += 1
        
        if spinning_count >= len(wheels) / 2:
            return "wheel spinning"
            
        return None

    def get_task_description(self):
        return {
            'task': 'K-04: The Pusher',
            'success_criteria': {
                'distance': f'Push object {self.target_distance}m',
                'time': f'Push for {self.min_simulation_time}s'
            }
        }
