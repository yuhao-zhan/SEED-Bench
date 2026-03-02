"""
S-01: The Bridge task evaluation module
Defines task objectives and success criteria
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system: Defines task objectives and success criteria for S-01: The Bridge
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        # Target x is right cliff start + 5m (vehicle must fully cross the bridge)
        gap_info = terrain_bounds.get("gap", {})
        right_cliff_start = gap_info.get("x_end", 25.0)
        self.target_x = right_cliff_start + 5.0  # Vehicle must reach 5m past right cliff
        self.max_vertical_acceleration = 2.0 * 9.8  # 2g in m/s²
        
        # Stability tracking for anti-flip checks (similar to basic task)
        self.high_angular_velocity_count = 0  # Count consecutive evaluations with excessive angular velocity
        self.MAX_ANGULAR_VELOCITY = 2.0  # rad/s - reasonable limit for stable vehicle
        self.STABILITY_CHECK_START_STEP = 200  # Start checking after initial stabilization
        self.UNSTABLE_THRESHOLD = 5  # If unstable for this many consecutive evaluations (500 steps), fail
        
        # Air rotation tracking: cannot rotate more than 180 degrees while airborne
        self.MAX_AIRBORNE_ROTATION = math.pi  # 180 degrees in radians
        self.AIRBORNE_THRESHOLD = 0.5  # Consider airborne if y > cliff_top + this threshold
        self._rotation_tracking_initialized = False  # Flag to initialize tracking once
        
        # Track vehicle state
        self.vehicle_previous_velocity_y = 0.0
        self.vehicle_previous_time = 0.0
        self.max_vertical_accel_seen = 0.0
        
        # Track structure integrity
        self.initial_joint_count = 0
        self.structure_broken = False
        
        # Design constraints
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        env_class = type(environment)
        try:
            self.MAX_STRUCTURE_MASS = env_class.MAX_STRUCTURE_MASS
            self.BUILD_ZONE_X_MIN = env_class.BUILD_ZONE_X_MIN
            self.BUILD_ZONE_X_MAX = env_class.BUILD_ZONE_X_MAX
            self.BUILD_ZONE_Y_MIN = env_class.BUILD_ZONE_Y_MIN
            self.BUILD_ZONE_Y_MAX = env_class.BUILD_ZONE_Y_MAX
            self.MIN_DECK_FRICTION = env_class.MIN_DECK_FRICTION
        except AttributeError as e:
            raise AttributeError(f"Environment class {env_class.__name__} missing required constant: {e}")
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate bridge performance
        Returns: (success, score, metrics)
        Note: agent_body is not used for this task (we track vehicle instead)
        """
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get vehicle position and velocity
        vehicle_pos = self.environment.get_vehicle_position()
        vehicle_vel = self.environment.get_vehicle_velocity()
        
        if vehicle_pos is None or vehicle_vel is None:
            return False, 0.0, {"error": "Vehicle not found"}
        
        current_x, current_y = vehicle_pos
        velocity_x, velocity_y = vehicle_vel
        
        # Get vehicle body for angular velocity and angle tracking
        vehicle_chassis = self.environment._terrain_bodies.get("vehicle_chassis")
        angular_velocity = 0.0
        angle = 0.0
        if vehicle_chassis:
            angular_velocity = vehicle_chassis.angularVelocity
            angle = vehicle_chassis.angle
        
        # Calculate vertical acceleration (approximate from velocity change)
        # Note: Evaluator is called every 100 steps, so actual time step is 100 * TIME_STEP
        actual_time_step = 100 * TIME_STEP  # Evaluator called every 100 steps
        if step_count > 0:
            vertical_accel = abs(velocity_y - self.vehicle_previous_velocity_y) / actual_time_step
            self.max_vertical_accel_seen = max(self.max_vertical_accel_seen, vertical_accel)
        
        self.vehicle_previous_velocity_y = velocity_y
        
        # Check structure integrity (count joints)
        if step_count == 0:
            self.initial_joint_count = len(self.environment._joints)
        
        current_joint_count = len(self.environment._joints)
        if current_joint_count < self.initial_joint_count:
            self.structure_broken = True
        
        # Check if successful
        success = current_x >= self.target_x
        
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
        
        # Failure condition 1: Vehicle fell into water
        if current_y < 0.5:
            failed = True
            failure_reason = "Vehicle fell into water"
        
        # Failure condition 2: Structure broke
        if self.structure_broken:
            failed = True
            failure_reason = "Structure integrity lost (joints broke)"
        
        # Failure condition 3: Excessive vertical acceleration
        if self.max_vertical_accel_seen > self.max_vertical_acceleration:
            failed = True
            failure_reason = f"Vehicle vertical acceleration {self.max_vertical_accel_seen:.2f} m/s² exceeds 2g limit"
        
        # Failure condition 4: Excessive angular velocity (indicates unstable/hacking behavior)
        # Check after initial stabilization period
        if step_count > self.STABILITY_CHECK_START_STEP:
            if abs(angular_velocity) > self.MAX_ANGULAR_VELOCITY:
                self.high_angular_velocity_count += 1
                if self.high_angular_velocity_count >= self.UNSTABLE_THRESHOLD:
                    failed = True
                    failure_reason = f"Vehicle is unstable: excessive rotation (angular velocity {angular_velocity:.2f} rad/s for {self.high_angular_velocity_count * 100} steps)"
            else:
                # Reset counter if angular velocity is normal
                self.high_angular_velocity_count = 0
        
        # Failure condition 5: Vehicle flipped (angle exceeds 90 degrees = vehicle is upside down)
        # Normalize angle to [-pi, pi] range
        normalized_angle = (angle + math.pi) % (2 * math.pi) - math.pi
        abs_angle = abs(normalized_angle)
        
        # If vehicle is tilted more than 90 degrees (π/2), it's flipped
        MAX_TILT_ANGLE = math.pi / 2  # 90 degrees
        if abs_angle > MAX_TILT_ANGLE:
            failed = True
            failure_reason = f"Vehicle flipped: angle {abs_angle * 180 / math.pi:.1f}° exceeds {MAX_TILT_ANGLE * 180 / math.pi:.0f}° limit"
        
        # Failure condition 6: Excessive rotation while airborne (cannot rotate more than 180 degrees in air)
        # Real-time tracking is done in environment.step() - we just read the result here
        cliff_top = 10.0  # Cliff top is at y=10m
        is_airborne = current_y > (cliff_top + self.AIRBORNE_THRESHOLD)
        
        # Initialize tracking on first call
        if not self._rotation_tracking_initialized and self.environment and vehicle_chassis:
            if hasattr(self.environment, 'set_tracked_body'):
                self.environment.set_tracked_body(vehicle_chassis)
                self._rotation_tracking_initialized = True
        
        # Read real-time rotation status from environment
        airborne_rotation_accumulated = 0.0
        if self.environment and hasattr(self.environment, 'get_airborne_rotation_status'):
            rotation_status = self.environment.get_airborne_rotation_status()
            airborne_rotation_accumulated = rotation_status['accumulated']
            
            # Check if rotation exceeded 180 degrees (tracked in real-time by environment)
            if rotation_status['exceeded']:
                failed = True
                failure_reason = f"Vehicle rotated {airborne_rotation_accumulated * 180 / math.pi:.1f}° while airborne (exceeds 180° limit)"
        
        # Calculate score (0-100)
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Partial score based on distance traveled
            # Vehicle starts at x=5m, target is dynamic based on gap width
            start_x = 5.0
            max_distance = self.target_x - start_x
            distance_traveled = max(0, current_x - start_x)
            progress = min(distance_traveled / max_distance, 1.0) if max_distance > 0 else 0.0
            score = progress * 80.0  # Max 80 points, success gets additional 20 points
        
        # Collect metrics
        start_x = 5.0
        max_distance = self.target_x - start_x
        metrics = {
            'vehicle_x': current_x,
            'vehicle_y': current_y,
            'target_x': self.target_x,
            'progress': min((current_x - start_x) / max_distance, 1.0) * 100 if current_x >= start_x and max_distance > 0 else 0.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': self.MAX_STRUCTURE_MASS,  # Add max structure mass for feedback
            'max_vertical_accel': self.max_vertical_accel_seen,
            'structure_broken': self.structure_broken,
            'joint_count': current_joint_count,
            # Vehicle velocity information
            'velocity_x': velocity_x,
            'velocity_y': velocity_y,
            # Stability metrics
            'angular_velocity': angular_velocity,
            'angle': angle,
            'normalized_angle': normalized_angle if 'normalized_angle' in locals() else angle,
            'high_angular_velocity_count': self.high_angular_velocity_count,
            'is_airborne': is_airborne,
            'airborne_rotation_accumulated': airborne_rotation_accumulated,
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
        
        # Constraint 2: Check build zone (per prompt: structure may extend beyond for deck to reach x=30)
        # x: [10, target_x] to allow deck extension; y: [5, 15]
        build_zone_x_max = self.target_x  # Allow extension to target (30m) for deck
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= build_zone_x_max and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(f"Beam at ({x:.2f}, {y:.2f}) is outside build zone x=[{self.BUILD_ZONE_X_MIN}, {build_zone_x_max:.0f}], y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]")
        
        # Constraint 3: Check deck friction (beams used as deck should have friction > 0.5)
        # This is more of a design guideline, so we'll just warn if friction is too low
        # (Actual check would require tracking which beams are used as deck)
        
        return violations
    
    def get_task_description(self):
        """Return task description"""
        return {
            'task': 'S-01: The Bridge',
            'description': 'Design a static bridge to connect two cliffs and support a testing vehicle',
            'target_position': self.target_x,
            'terrain': {
                'left_cliff': self.terrain_bounds.get('left_cliff', {}),
                'right_cliff': self.terrain_bounds.get('right_cliff', {}),
                'gap': self.terrain_bounds.get('gap', {}),
            },
            'success_criteria': {
                'primary': f'Vehicle reaches position x={self.target_x}m',
                'secondary': 'No structural breaks (joints remain intact)',
                'tertiary': 'Vehicle vertical acceleration must not exceed 2g',
            },
            'evaluation': {
                'score_range': '0-100',
                'success_score': 100,
                'partial_score': 'Based on distance traveled, max 80 points',
                'failure_score': 0
            }
        }
