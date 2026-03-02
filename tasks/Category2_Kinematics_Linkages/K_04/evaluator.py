"""
K-04: The Pusher task evaluation module
Defines task objectives and success criteria
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system: Defines task objectives and success criteria for K-04: The Pusher
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        # Target: object must be pushed forward at least 8 meters
        self.start_object_x = 8.0  # Object starting position
        self.target_object_x = self.start_object_x + 8.0  # Must reach x=16m
        self.max_tilt_angle = math.pi / 6  # 30 degrees in radians
        self.min_simulation_time = 0.05  # at least 3 eval intervals with motion (motors must contribute)
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)
        
        # Track pusher and object state (initial object x is fixed at task start position)
        self.initial_object_x = self.start_object_x  # 8.0
        self.max_distance_pushed = 0.0
        self.max_pusher_tilt = 0.0
        self.pusher_tipped = False
        self.steps_with_motion = 0
        self.last_object_x = None
        # Wheel spinning: track consecutive evals with wheels spinning but no forward motion
        self.consecutive_spinning_count = 0
        self.wheel_spinning_threshold_steps = 30  # ~3s at eval every 100 steps
        # Wheel suspended (轮子悬空): track consecutive evals with wheels off ground
        self.consecutive_suspended_count = 0
        self.wheel_suspended_threshold_steps = 80  # ~8s - allow brief lift during heavy push
        
        # Design constraints (use instance values - build zone y starts at 1.0 for ground)
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        try:
            self.MAX_STRUCTURE_MASS = environment.MAX_STRUCTURE_MASS
            self.BUILD_ZONE_X_MIN = environment.BUILD_ZONE_X_MIN
            self.BUILD_ZONE_X_MAX = environment.BUILD_ZONE_X_MAX
            self.BUILD_ZONE_Y_MIN = environment.BUILD_ZONE_Y_MIN
            self.BUILD_ZONE_Y_MAX = environment.BUILD_ZONE_Y_MAX
        except AttributeError as e:
            raise AttributeError(f"Environment missing required attribute: {e}")
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate pusher performance
        Returns: (success, score, metrics)
        """
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get object position
        object_pos = self.environment.get_object_position()
        if object_pos is None:
            return False, 0.0, {"error": "Object not found"}
        
        current_object_x, current_object_y = object_pos
        
        # Get pusher position and angle (use agent_body if provided)
        if agent_body:
            pusher_x, pusher_y = agent_body.position.x, agent_body.position.y
            pusher_angle = agent_body.angle
        else:
            pusher_pos = self.environment.get_pusher_position()
            if pusher_pos is None:
                pusher_x, pusher_y = 3.0, 2.5  # Default position
                pusher_angle = 0.0
            else:
                pusher_x, pusher_y = pusher_pos
                # Get angle from first body
                if self.environment._bodies:
                    pusher_angle = self.environment._bodies[0].angle
                else:
                    pusher_angle = 0.0
        
        # Initialize last_object_x for motion tracking on first evaluation
        if self.last_object_x is None:
            self.last_object_x = current_object_x
        
        # Track maximum distance pushed
        distance_pushed = current_object_x - self.initial_object_x
        if distance_pushed > self.max_distance_pushed:
            self.max_distance_pushed = distance_pushed
        
        # Track pusher tilt angle
        normalized_angle = (pusher_angle + math.pi) % (2 * math.pi) - math.pi
        abs_angle = abs(normalized_angle)
        if abs_angle > self.max_pusher_tilt:
            self.max_pusher_tilt = abs_angle
        
        # Check if pusher tipped over (翻车)
        if abs_angle > self.max_tilt_angle:
            self.pusher_tipped = True
        
        # Wheel spinning (轮子空转): wheels rotate but pusher/object barely move
        wheel_spinning = False
        if hasattr(self.environment, '_pusher_joints') and self.environment._pusher_joints:
            wheel_omega_sum = 0.0
            wheel_count = 0
            pusher_vx = agent_body.linearVelocity.x if agent_body else 0.0
            for joint in self.environment._pusher_joints:
                if joint is None:
                    continue
                # Wheel is the body with circle fixture
                wheel_body = None
                for body in (joint.bodyA, joint.bodyB):
                    for fix in body.fixtures:
                        if hasattr(fix.shape, 'radius'):
                            wheel_body = body
                            break
                    if wheel_body:
                        break
                if wheel_body is None:
                    continue
                wheel_omega_sum += abs(wheel_body.angularVelocity)
                wheel_count += 1
            avg_wheel_omega = wheel_omega_sum / wheel_count if wheel_count else 0.0
            obj = getattr(self.environment, '_object_to_push', None)
            obj_vx = obj.linearVelocity.x if obj else 0.0
            # Spinning: wheels fast (>1.5 rad/s) but forward motion slow (<0.03 m/s)
            if avg_wheel_omega > 1.5 and abs(pusher_vx) < 0.03 and abs(obj_vx) < 0.03:
                self.consecutive_spinning_count += 1
                if self.consecutive_spinning_count >= self.wheel_spinning_threshold_steps:
                    wheel_spinning = True
            else:
                self.consecutive_spinning_count = 0
        
        # Wheel suspended (轮子悬空): wheels off ground - wheel bottom above ground
        # Grace period: skip first 10000 steps (allow time to reach object and sustained push)
        wheel_suspended = False
        ground_y = getattr(self.environment, '_ground_y', 1.0)
        lift_threshold = 0.12  # Only count as suspended when wheel clearly lifted (12cm)
        if (step_count > 10000 and hasattr(self.environment, '_pusher_joints') and
                self.environment._pusher_joints):
            suspended_count = 0
            total_wheels = 0
            for joint in self.environment._pusher_joints:
                if joint is None:
                    continue
                # Wheel is the body with circle fixture (works for chassis-wheel or plate-wheel joints)
                wheel_body = None
                for body in (joint.bodyA, joint.bodyB):
                    for fix in body.fixtures:
                        if hasattr(fix.shape, 'radius'):
                            wheel_body = body
                            break
                    if wheel_body:
                        break
                if wheel_body is None:
                    continue
                wheel_radius = 0.22
                for fix in wheel_body.fixtures:
                    if hasattr(fix.shape, 'radius'):
                        wheel_radius = fix.shape.radius
                        break
                wheel_bottom_y = wheel_body.position.y - wheel_radius
                # Suspended: wheel bottom more than lift_threshold above ground (clear lift)
                if wheel_bottom_y > ground_y + lift_threshold:
                    suspended_count += 1
                total_wheels += 1
            if total_wheels > 0 and suspended_count >= total_wheels:
                self.consecutive_suspended_count += 1
                if self.consecutive_suspended_count >= self.wheel_suspended_threshold_steps:
                    wheel_suspended = True
            else:
                self.consecutive_suspended_count = 0
        
        # Track motion (check if object position changed forward)
        # 0.001m threshold: capture sustained motion (evaluation every 100 steps)
        if self.last_object_x is not None:
            position_change = current_object_x - self.last_object_x
            if position_change > 0.001:  # Moved forward at least 1mm per eval interval
                self.steps_with_motion += 1
        self.last_object_x = current_object_x
        
        # Check if successful
        reached_target = current_object_x >= self.target_object_x
        maintained_stability = not self.pusher_tipped
        maintained_motion = self.steps_with_motion >= self.min_simulation_steps
        # Success: target reached + stability + meaningful sustained motion
        # maintained_motion: at least 30 eval intervals with forward motion (motors must contribute)
        success = (reached_target and maintained_stability and distance_pushed >= 8.0 and
                   maintained_motion)
        
        # Check if failed
        failed = False
        failure_reason = None
        
        # Failure condition 0: Check design constraints (only at step 0)
        if not self.design_constraints_checked and step_count == 0:
            constraint_violations = self._check_design_constraints()
            if constraint_violations:
                failed = True
                failure_reason = "Design constraint violated: " + "; ".join(constraint_violations)
            self.design_constraints_checked = True
        
        # Failure condition 1: Pusher tipped over
        if self.pusher_tipped:
            failed = True
            failure_reason = f"Pusher tipped over (tilt angle {self.max_pusher_tilt * 180 / math.pi:.1f}° exceeds {self.max_tilt_angle * 180 / math.pi:.0f}° limit)"
        
        # Failure condition 2: No forward movement (timeout)
        if step_count >= max_steps and distance_pushed < 1.0:
            failed = True
            failure_reason = "Object was not pushed forward (distance pushed < 1.0m)"
        # Failure condition 3: Object left ground (must be pushed along ground, not launched)
        ground_y = getattr(self.environment, '_ground_y', 1.0)
        if current_object_y < ground_y - 0.1:
            failed = True
            failure_reason = "Object left ground (must push along ground, not launch)"
        
        # Failure condition 4: Wheel spinning (轮子空转) - wheels rotate but no forward motion
        if wheel_spinning:
            failed = True
            failure_reason = "Wheel spinning (wheels rotate but pusher/object barely move - loss of traction)"
        
        # Failure condition 5: Wheel suspended (轮子悬空) - wheels off ground
        if wheel_suspended:
            failed = True
            failure_reason = "Wheels suspended (wheels off ground - pusher tilted/lifted rear)"
        
        # Calculate score (0-100)
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Partial score based on distance pushed and stability
            distance_score = min(distance_pushed / 8.0, 1.0) * 50.0  # Max 50 points for distance
            stability_score = 0.0
            if not self.pusher_tipped:
                stability_score = 30.0  # 30 points for maintaining stability
            motion_score = min(self.steps_with_motion / self.min_simulation_steps, 1.0) * 20.0  # Max 20 points for sustained motion
            score = distance_score + stability_score + motion_score
        
        # Physical state for feedback (velocities)
        pusher_vx = pusher_vy = pusher_omega = 0.0
        obj_vx = obj_vy = obj_omega = 0.0
        if agent_body:
            pusher_vx = agent_body.linearVelocity.x
            pusher_vy = agent_body.linearVelocity.y
            pusher_omega = agent_body.angularVelocity
        if getattr(self.environment, '_object_to_push', None):
            obj = self.environment._object_to_push
            obj_vx = obj.linearVelocity.x
            obj_vy = obj.linearVelocity.y
            obj_omega = obj.angularVelocity

        # Collect metrics
        metrics = {
            'pusher_x': pusher_x,
            'pusher_y': pusher_y,
            'pusher_angle': pusher_angle,
            'pusher_velocity_x': pusher_vx,
            'pusher_velocity_y': pusher_vy,
            'pusher_angular_velocity': pusher_omega,
            'object_x': current_object_x,
            'object_y': current_object_y,
            'object_velocity_x': obj_vx,
            'object_velocity_y': obj_vy,
            'object_angular_velocity': obj_omega,
            'target_object_x': self.target_object_x,
            'distance_pushed': distance_pushed,
            'max_distance_pushed': self.max_distance_pushed,
            'progress': min(distance_pushed / 8.0, 1.0) * 100 if distance_pushed >= 0 else 0.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': self.MAX_STRUCTURE_MASS,
            'max_pusher_tilt': self.max_pusher_tilt,
            'pusher_tipped': self.pusher_tipped,
            'wheel_spinning': wheel_spinning,
            'wheel_suspended': wheel_suspended,
            'consecutive_spinning_count': self.consecutive_spinning_count,
            'consecutive_suspended_count': self.consecutive_suspended_count,
            'steps_with_motion': self.steps_with_motion,
            'min_simulation_steps_required': self.min_simulation_steps,
        }
        
        return success or failed, score, metrics
    
    def _check_design_constraints(self):
        """
        Check all design constraints
        Returns: List of violation messages (empty if all constraints met)
        """
        violations = []
        
        if not self.environment:
            return ["Environment not available"]
        
        # Constraint 1: Check structure mass
        structure_mass = self.environment.get_structure_mass()
        if structure_mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {structure_mass:.2f}kg exceeds maximum {self.MAX_STRUCTURE_MASS}kg")
        
        # Constraint 2: Check build zone (all beams must be in build zone)
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(f"Beam at ({x:.2f}, {y:.2f}) is outside build zone x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]")
        
        return violations
    
    def get_task_description(self):
        """Return task description"""
        return {
            'task': 'K-04: The Pusher',
            'description': 'Design a pusher mechanism that pushes heavy objects across high-friction ground using motor rotation',
            'target_position': self.target_object_x,
            'terrain': {
                'ground': self.terrain_bounds.get('ground', {}),
            },
            'success_criteria': {
                'primary': f'Object is pushed forward at least 8 meters (reaches x={self.target_object_x}m)',
                'secondary': 'Pusher never tips over (tilt angle stays within ±30°)',
                'tertiary': 'Pusher maintains forward motion for at least 5 seconds',
            },
            'evaluation': {
                'score_range': '0-100',
                'success_score': 100,
                'partial_score': 'Based on distance pushed (max 50), stability (max 30), and sustained motion (max 20)',
                'failure_score': 0
            }
        }
