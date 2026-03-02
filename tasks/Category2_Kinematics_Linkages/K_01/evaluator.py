"""
K-01: The Walker task evaluation module
Defines task objectives and success criteria
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system: Defines task objectives and success criteria for K-01: The Walker
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        # Target: walker must move forward at least 10 meters
        self.start_x = 10.0  # Starting position
        self.target_x = self.start_x + 10.0  # Must reach x=20m
        self.min_torso_height = 1.5  # Torso must stay above this height
        self.min_simulation_time = 5.0  # Must maintain motion for 5 seconds
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)  # Steps for 5 seconds
        
        # Track walker state
        self.initial_position = None
        self.max_distance_traveled = 0.0
        self.min_torso_y_seen = float('inf')
        self.torso_touched_ground = False
        self.steps_with_motion = 0
        self.last_position_x = None
        
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
        except AttributeError as e:
            raise AttributeError(f"Environment class {env_class.__name__} missing required constant: {e}")
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate walker performance
        Returns: (success, score, metrics)
        """
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get walker position (use agent_body if provided, otherwise find first body in build zone)
        if agent_body:
            current_x, current_y = agent_body.position.x, agent_body.position.y
        else:
            # Try to find the torso (usually the first body or a body in the build zone)
            walker_pos = self.environment.get_walker_position()
            if walker_pos is None:
                # If no walker found, check if there are any bodies
                if not self.environment._bodies:
                    return False, 0.0, {"error": "Walker not found - no bodies created"}
                # Use first body as fallback
                first_body = self.environment._bodies[0]
                current_x, current_y = first_body.position.x, first_body.position.y
            else:
                current_x, current_y = walker_pos
        
        # Initialize tracking on first evaluation
        if self.initial_position is None:
            self.initial_position = current_x
            self.last_position_x = current_x
            self.min_torso_y_seen = current_y
        
        # Track minimum torso height
        if current_y < self.min_torso_y_seen:
            self.min_torso_y_seen = current_y
        
        # Check if torso touched ground
        if current_y < self.min_torso_height:
            self.torso_touched_ground = True
        
        # Track forward movement
        distance_traveled = current_x - self.initial_position
        if distance_traveled > self.max_distance_traveled:
            self.max_distance_traveled = distance_traveled
        
        # Track motion (check if position changed)
        if self.last_position_x is not None:
            position_change = abs(current_x - self.last_position_x)
            if position_change > 0.01:  # Moved at least 1cm
                self.steps_with_motion += 1
        self.last_position_x = current_x
        
        # Check if successful
        reached_target = current_x >= self.target_x
        maintained_height = not self.torso_touched_ground and self.min_torso_y_seen >= self.min_torso_height
        maintained_motion = self.steps_with_motion >= self.min_simulation_steps
        
        success = reached_target and maintained_height and maintained_motion
        
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
        
        # Failure condition 1: Torso touched ground
        if self.torso_touched_ground:
            failed = True
            failure_reason = f"Torso touched ground (minimum y={self.min_torso_y_seen:.2f}m, required >{self.min_torso_height}m)"
        
        # Failure condition 2: No forward movement (timeout)
        if step_count >= max_steps and distance_traveled < 1.0:
            failed = True
            failure_reason = "Walker did not move forward (distance traveled < 1.0m)"
        
        # Calculate score (0-100)
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Partial score based on distance traveled and stability
            distance_score = min(distance_traveled / 10.0, 1.0) * 50.0  # Max 50 points for distance
            height_score = 0.0
            if self.min_torso_y_seen >= self.min_torso_height:
                height_score = 30.0  # 30 points for maintaining height
            motion_score = min(self.steps_with_motion / self.min_simulation_steps, 1.0) * 20.0  # Max 20 points for sustained motion
            score = distance_score + height_score + motion_score
        
        # Get velocity for feedback
        velocity_x = 0.0
        velocity_y = 0.0
        angular_velocity = 0.0
        if agent_body:
            velocity_x = agent_body.linearVelocity.x
            velocity_y = agent_body.linearVelocity.y
            angular_velocity = agent_body.angularVelocity
        
        # Collect metrics
        metrics = {
            'walker_x': current_x,
            'walker_y': current_y,
            'target_x': self.target_x,
            'distance_traveled': distance_traveled,
            'progress': min(distance_traveled / 10.0, 1.0) * 100 if distance_traveled >= 0 else 0.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': self.MAX_STRUCTURE_MASS,
            'min_torso_y': self.min_torso_y_seen,
            'torso_touched_ground': self.torso_touched_ground,
            'steps_with_motion': self.steps_with_motion,
            'min_simulation_steps_required': self.min_simulation_steps,
            'velocity_x': velocity_x,
            'velocity_y': velocity_y,
            'angular_velocity': angular_velocity,
            'speed': math.sqrt(velocity_x**2 + velocity_y**2),
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
            'task': 'K-01: The Walker',
            'description': 'Design a bipedal or quadrupedal walker that moves forward using motor rotation',
            'target_position': self.target_x,
            'terrain': {
                'ground': self.terrain_bounds.get('ground', {}),
            },
            'success_criteria': {
                'primary': f'Walker moves forward at least 10 meters (reaches x={self.target_x}m)',
                'secondary': 'Torso never touches ground (torso y > 1.5m)',
                'tertiary': 'Walker maintains forward motion for at least 5 seconds',
            },
            'evaluation': {
                'score_range': '0-100',
                'success_score': 100,
                'partial_score': 'Based on distance traveled (max 50), height maintenance (max 30), and sustained motion (max 20)',
                'failure_score': 0
            }
        }
