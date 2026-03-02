"""
Basic task evaluation module
Defines task objectives and success criteria
"""
import math


class Evaluator:
    """
    Evaluation system: Defines task objectives and success criteria
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment  # Store environment reference for design constraint checks
        self.start_x = 5.0  # Agent start position
        self.target_x = 30.0  # Target position (must pass all obstacles)
        self.min_distance = 0.0  # Minimum travel distance
        self.max_distance = 0.0  # Maximum travel distance
        
        # Stability tracking for anti-hacking checks
        self.high_angular_velocity_count = 0  # Count consecutive evaluations with excessive angular velocity
        self.high_altitude_count = 0  # Count consecutive evaluations with excessive altitude
        self.MAX_ANGULAR_VELOCITY = 2.0  # rad/s - reasonable limit for stable vehicle
        self.MAX_REASONABLE_ALTITUDE = 8.0  # meters - reasonable height for climbing obstacles
        self.STABILITY_CHECK_START_STEP = 200  # Start checking after initial stabilization
        self.UNSTABLE_THRESHOLD = 5  # If unstable for this many consecutive evaluations (500 steps), fail
        
        # Air rotation tracking: cannot rotate more than 180 degrees while airborne
        # NOTE: Real-time tracking is done in environment.step(), evaluator just reads the result
        self.MAX_AIRBORNE_ROTATION = math.pi  # 180 degrees in radians
        self.AIRBORNE_THRESHOLD = 0.5  # Consider airborne if y > ground_top + this threshold (meters)
        self._rotation_tracking_initialized = False  # Flag to initialize tracking once
        
        # Design constraints (read from environment class constants to ensure consistency)
        if not environment:
            raise ValueError("Evaluator requires environment instance to read constraint constants")
        
        # Get constants from environment class (DaVinciSandbox)
        env_class = type(environment)
        try:
            self.MAX_CHASSIS_HEIGHT = env_class.MAX_CHASSIS_HEIGHT
            self.MIN_WHEEL_RADIUS = env_class.MIN_WHEEL_RADIUS
            self.MAX_WHEEL_RADIUS = env_class.MAX_WHEEL_RADIUS
            self.MAX_WHEELS = env_class.MAX_WHEELS
            self.GROUND_TOP = env_class.GROUND_TOP
            self.MAX_CONNECTION_DISTANCE = env_class.MAX_CONNECTION_DISTANCE
            self.MAX_MOTOR_SPEED = env_class.MAX_MOTOR_SPEED
            self.MAX_MOTOR_TORQUE = env_class.MAX_MOTOR_TORQUE
        except AttributeError as e:
            raise AttributeError(f"Environment class {env_class.__name__} missing required constant: {e}")
        
        self.design_constraints_checked = False  # Only check once at the beginning
        
    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate Agent performance
        Returns: (success, score, metrics)
        """
        current_x = agent_body.position.x
        current_y = agent_body.position.y
        
        # Calculate travel distance
        distance_traveled = current_x - self.start_x
        
        # Update maximum distance
        if distance_traveled > self.max_distance:
            self.max_distance = distance_traveled
        
        # Calculate physical state (for fine-grained debugging)
        velocity_x = agent_body.linearVelocity.x
        velocity_y = agent_body.linearVelocity.y
        velocity = math.sqrt(velocity_x**2 + velocity_y**2)
        angular_velocity = agent_body.angularVelocity
        angle = agent_body.angle
        
        # Check if successful (reached target position)
        success = current_x >= self.target_x
        
        # Check if failed
        failed = False
        failure_reason = None
        
        # Failure condition 0: Check all design constraints (only check once at the beginning, at step 0)
        # Only check initial design constraints at step 0, not during runtime (wheels can lift during obstacle climbing)
        if not self.design_constraints_checked and self.environment and step_count == 0:
            constraint_violations = self._check_design_constraints(agent_body)
            if constraint_violations:
                failed = True
                failure_reason = "Design constraint violated: " + "; ".join(constraint_violations)
            self.design_constraints_checked = True
        
        # Failure condition 1: Fell off map
        if current_y < -10:
            failed = True
            failure_reason = "Fell off map"
        
        # Failure condition 2: Moved backward too much (indicates design problem)
        if current_x < self.start_x - 5:
            failed = True
            failure_reason = "Moved backward too much"
        
        # Failure condition 3: Excessive angular velocity (indicates unstable/hacking behavior)
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
        
        # Failure condition 4: Excessive altitude (indicates flying/hacking behavior)
        # Check after initial stabilization period
        if step_count > self.STABILITY_CHECK_START_STEP:
            if current_y > self.MAX_REASONABLE_ALTITUDE:
                self.high_altitude_count += 1
                if self.high_altitude_count >= self.UNSTABLE_THRESHOLD:
                    failed = True
                    failure_reason = f"Vehicle is flying: excessive altitude (y={current_y:.2f}m for {self.high_altitude_count * 100} steps)"
            else:
                # Reset counter if altitude is normal
                self.high_altitude_count = 0
        
        # Failure condition 5: Excessive rotation while airborne (cannot rotate more than 180 degrees in air)
        # Real-time tracking is done in environment.step() - we just read the result here
        is_airborne = current_y > (self.GROUND_TOP + self.AIRBORNE_THRESHOLD)
        
        # Initialize tracking on first call
        if not self._rotation_tracking_initialized and self.environment:
            if hasattr(self.environment, 'set_tracked_body'):
                self.environment.set_tracked_body(agent_body)
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
            # Calculate score based on travel distance
            # Target distance is target_x - start_x = 25m
            progress = min(distance_traveled / (self.target_x - self.start_x), 1.0)
            score = progress * 80.0  # Max 80 points, success gets additional 20 points
        
        # Collect metrics (including physical state for fine-grained debugging)
        metrics = {
            'distance_traveled': distance_traveled,
            'current_x': current_x,
            'current_y': current_y,
            'target_x': self.target_x,
            'progress': min(distance_traveled / (self.target_x - self.start_x), 1.0) * 100,
            'success': success and not failed,  # Only success if not failed
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'max_distance': self.max_distance,
            # Physical state information
            'velocity': velocity,
            'velocity_x': velocity_x,
            'velocity_y': velocity_y,
            'angular_velocity': angular_velocity,
            'angle': angle,
            # Stability tracking
            'high_angular_velocity_count': self.high_angular_velocity_count,
            'high_altitude_count': self.high_altitude_count,
            'is_airborne': is_airborne,
            'airborne_rotation_accumulated': airborne_rotation_accumulated
        }
        
        return success or failed, score, metrics
    
    def _check_design_constraints(self, agent_body):
        """
        Check all design constraints against environment constants
        Returns: List of violation messages (empty if all constraints met)
        """
        violations = []
        
        if not self.environment:
            raise ValueError("Cannot check design constraints: environment not provided")
        
        if not hasattr(self.environment, '_bodies') or not hasattr(self.environment, '_joints'):
            raise AttributeError(f"Environment {type(self.environment).__name__} missing required attributes '_bodies' or '_joints'")
        
        from Box2D.b2 import dynamicBody, circleShape, polygonShape
        
        # Get all bodies and joints
        bodies = self.environment._bodies
        joints = self.environment._joints
        
        # Find chassis and wheels
        chassis = agent_body
        wheels = [b for b in bodies if b != chassis and b.type == dynamicBody]
        
        # Constraint 1: Check wheel count
        if len(wheels) > self.MAX_WHEELS:
            violations.append(f"vehicle has {len(wheels)} wheels, but maximum {self.MAX_WHEELS} wheels are allowed")
        
        # Constraint 2: Check chassis height
        if chassis:
            # Try to get chassis height from fixtures
            chassis_height = None
            for fixture in chassis.fixtures:
                shape = fixture.shape
                if isinstance(shape, polygonShape):
                    # Get height from box shape (box returns (half_width, half_height))
                    if hasattr(shape, 'box'):
                        box = shape.box
                        if isinstance(box, tuple) and len(box) >= 2:
                            chassis_height = box[1] * 2  # height is half-extent, so multiply by 2
                            break
            
            if chassis_height and chassis_height > self.MAX_CHASSIS_HEIGHT:
                violations.append(f"chassis height {chassis_height:.2f}m exceeds maximum {self.MAX_CHASSIS_HEIGHT}m")
        
        # Constraint 3: Check wheel radius
        for wheel in wheels:
            wheel_radius = None
            for fixture in wheel.fixtures:
                shape = fixture.shape
                if isinstance(shape, circleShape):
                    wheel_radius = shape.radius
                    break
            
            if wheel_radius:
                if wheel_radius < self.MIN_WHEEL_RADIUS:
                    violations.append(f"wheel radius {wheel_radius:.2f}m is below minimum {self.MIN_WHEEL_RADIUS}m")
                elif wheel_radius > self.MAX_WHEEL_RADIUS:
                    violations.append(f"wheel radius {wheel_radius:.2f}m exceeds maximum {self.MAX_WHEEL_RADIUS}m")
                
                # Constraint 4: Check wheel contacts ground (only check initial position, not runtime)
                # Note: Wheels can lift during obstacle climbing, so we only check initial design position
                wheel_bottom = wheel.position.y - wheel_radius
                if wheel_bottom > self.GROUND_TOP + 0.2:  # Allow 0.2m tolerance
                    violations.append(f"wheel at ({wheel.position.x:.2f}, {wheel.position.y:.2f}) does not contact ground initially (bottom y={wheel_bottom:.2f}m, ground top y={self.GROUND_TOP}m)")
        
        # Constraint 5: Check connection distance
        for joint in joints:
            if hasattr(joint, 'anchor') and hasattr(joint, 'bodyA') and hasattr(joint, 'bodyB'):
                anchor = joint.anchor
                body_a = joint.bodyA
                body_b = joint.bodyB
                
                if body_a and body_b:
                    # Get anchor position (anchor can be tuple or have x, y attributes)
                    if isinstance(anchor, tuple) and len(anchor) >= 2:
                        anchor_x, anchor_y = anchor[0], anchor[1]
                    elif hasattr(anchor, 'x') and hasattr(anchor, 'y'):
                        anchor_x, anchor_y = anchor.x, anchor.y
                    else:
                        continue  # Skip if can't get anchor position
                    
                    # Calculate distance from anchor to each body
                    pos_a = body_a.position
                    pos_b = body_b.position
                    distance_a = math.sqrt((anchor_x - pos_a.x)**2 + (anchor_y - pos_a.y)**2)
                    distance_b = math.sqrt((anchor_x - pos_b.x)**2 + (anchor_y - pos_b.y)**2)
                    
                    if distance_a > self.MAX_CONNECTION_DISTANCE:
                        violations.append(f"connection point too far from body_a: {distance_a:.2f}m (max {self.MAX_CONNECTION_DISTANCE}m)")
                    if distance_b > self.MAX_CONNECTION_DISTANCE:
                        violations.append(f"connection point too far from body_b: {distance_b:.2f}m (max {self.MAX_CONNECTION_DISTANCE}m)")
        
        # Constraint 6: Check motor parameters
        for joint in joints:
            if hasattr(joint, 'motorEnabled') and joint.motorEnabled:
                if hasattr(joint, 'motorSpeed'):
                    if abs(joint.motorSpeed) > self.MAX_MOTOR_SPEED:
                        violations.append(f"motor speed {joint.motorSpeed:.2f} rad/s exceeds maximum {self.MAX_MOTOR_SPEED} rad/s")
                if hasattr(joint, 'maxMotorTorque'):
                    if joint.maxMotorTorque > self.MAX_MOTOR_TORQUE:
                        violations.append(f"motor torque {joint.maxMotorTorque:.2f} N·m exceeds maximum {self.MAX_MOTOR_TORQUE} N·m")
        
        return violations
    
    def get_task_description(self):
        """Return task description"""
        return {
            'task': 'Design a vehicle that can climb slopes',
            'description': 'Agent needs to design a mechanical structure (vehicle) that can move on terrain and pass obstacles',
            'start_position': self.start_x,
            'target_position': self.target_x,
            'terrain': {
                'ground_length': self.terrain_bounds['end'],
                'obstacles': self.terrain_bounds['obstacles']
            },
            'success_criteria': {
                'primary': f'Agent chassis must reach position x={self.target_x}m',
                'secondary': 'Agent cannot fall off map (y < -10)',
                'tertiary': 'Agent cannot move backward too much (x < start_x - 5)',
                'stability': f'Agent must move stably: angular velocity < {self.MAX_ANGULAR_VELOCITY} rad/s, altitude < {self.MAX_REASONABLE_ALTITUDE}m'
            },
            'evaluation': {
                'score_range': '0-100',
                'success_score': 100,
                'partial_score': 'Based on travel distance, max 80 points',
                'failure_score': 0
            }
        }
