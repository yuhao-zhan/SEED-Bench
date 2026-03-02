"""
K-02: The Climber task evaluation module
Defines task objectives and success criteria
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system: Defines task objectives and success criteria for K-02: The Climber
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        # Climber starts BELOW red line and must climb up to it
        self.start_y = 2.2   # Expected starting height (agent spawns low, below red line)
        self.target_y = 3.5  # Red line: must reach this height by climbing (full score)
        self.min_height = 1.0  # Must never fall below this (ground at y=1m)
        self.wall_x_near_min = 3.0   # Stay near wall (x >= this)
        self.wall_x_near_max = 5.5  # Stay near wall (x <= this)
        self.min_simulation_time = 1.5  # Must show upward motion for 1.5 seconds (90 steps)
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)
        
        # Track climber state
        self.initial_position = None
        self.max_height_reached = 0.0
        self.min_height_seen = float('inf')
        self.climber_fell = False
        self.steps_with_motion = 0
        self.last_position_y = None
        
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
        Evaluate climber performance
        Returns: (success, score, metrics)
        """
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get climber position (use agent_body if provided, otherwise find first body in build zone)
        if agent_body:
            current_x, current_y = agent_body.position.x, agent_body.position.y
        else:
            # Try to find the main body (usually the first body or a body in the build zone)
            climber_pos = self.environment.get_climber_position()
            if climber_pos is None:
                # If no climber found, check if there are any bodies
                if not self.environment._bodies:
                    return False, 0.0, {"error": "Climber not found - no bodies created"}
                # Use first body as fallback
                first_body = self.environment._bodies[0]
                current_x, current_y = first_body.position.x, first_body.position.y
            else:
                current_x, current_y = climber_pos
        
        # Initialize tracking on first evaluation
        if self.initial_position is None:
            self.initial_position = current_y
            self.last_position_y = current_y
            self.min_height_seen = current_y
        
        # Track minimum height
        if current_y < self.min_height_seen:
            self.min_height_seen = current_y
        
        # Check if climber fell
        if current_y < self.min_height:
            self.climber_fell = True
        
        # Track upward movement
        height_gained = current_y - self.initial_position
        if current_y > self.max_height_reached:
            self.max_height_reached = current_y
        
        # Track motion (check if position changed upward)
        if self.last_position_y is not None:
            position_change = current_y - self.last_position_y
            if position_change > 0.01:  # Moved upward at least 1cm
                self.steps_with_motion += 1
        self.last_position_y = current_y
        
        # Pass = stay on wall (don't fall) + show upward motion. Red line = full score.
        maintained_height = not self.climber_fell and self.min_height_seen >= self.min_height
        stayed_near_wall = self.wall_x_near_min <= current_x <= self.wall_x_near_max
        maintained_motion = self.steps_with_motion >= self.min_simulation_steps
        reached_target = current_y >= self.target_y

        # Success: 2D-friendly — wall attachment + upward motion (red line optional for full score)
        success = maintained_height and stayed_near_wall and maintained_motion

        failed = False
        failure_reason = None

        if not self.design_constraints_checked and step_count == 0:
            constraint_violations = self._check_design_constraints()
            if constraint_violations:
                failed = True
                failure_reason = "Design constraint violated: " + "; ".join(constraint_violations)
            self.design_constraints_checked = True

        if self.climber_fell:
            failed = True
            failure_reason = f"Climber fell (minimum y={self.min_height_seen:.2f}m, required >={self.min_height}m)"

        if step_count >= max_steps and not maintained_motion:
            failed = True
            failure_reason = "Climber did not show upward motion (need ≥1.5s of upward movement)"

        if step_count >= max_steps and not stayed_near_wall:
            failed = True
            failure_reason = f"Climber left wall (x={current_x:.2f}m, must stay in [3, 5.5])"

        # Score: pass = 60–100. Reach red line = 100; else 60 + 40 * height bonus
        if failed:
            score = 0.0
        elif success and reached_target:
            score = 100.0
        elif success:
            height_bonus = min(1.0, max(0, (current_y - self.initial_position) / 0.5)) * 40.0  # up to 40 pts for height
            score = 60.0 + height_bonus
        else:
            stability_score = 30.0 if maintained_height else 0.0
            motion_score = min(self.steps_with_motion / self.min_simulation_steps, 1.0) * 30.0
            score = stability_score + motion_score
        
        # Get velocity information for feedback
        velocity_x = 0.0
        velocity_y = 0.0
        angular_velocity = 0.0
        speed = 0.0
        if agent_body:
            velocity_x = agent_body.linearVelocity.x
            velocity_y = agent_body.linearVelocity.y
            angular_velocity = agent_body.angularVelocity
            speed = (velocity_x**2 + velocity_y**2)**0.5
        
        # Collect metrics
        metrics = {
            'climber_x': current_x,
            'climber_y': current_y,
            'target_y': self.target_y,
            'height_gained': height_gained,
            'max_height_reached': self.max_height_reached,
            'progress': min((current_y - self.initial_position) / 0.5, 1.0) * 100 if height_gained >= 0 else 0.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': self.MAX_STRUCTURE_MASS,
            'min_height_seen': self.min_height_seen,
            'climber_fell': self.climber_fell,
            'steps_with_motion': self.steps_with_motion,
            'min_simulation_steps_required': self.min_simulation_steps,
            'velocity_x': velocity_x,
            'velocity_y': velocity_y,
            'angular_velocity': angular_velocity,
            'speed': speed,
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
            'task': 'K-02: The Climber',
            'description': 'Design a climber mechanism that climbs up a vertical wall using motor rotation',
            'target_position': self.target_y,
            'terrain': {
                'wall': self.terrain_bounds.get('wall', {}),
                'ground': self.terrain_bounds.get('ground', {}),
            },
            'success_criteria': {
                'primary': 'Climber stays on wall (don\'t fall, stay x∈[3,5.5]) and shows upward motion (≥1.5s). Red line = full score.',
                'secondary': f'Reach red line (y>={self.target_y}m) for 100 pts',
                'tertiary': 'Climber maintains upward motion for at least 10 seconds',
            },
            'evaluation': {
                'score_range': '0-100',
                'success_score': 100,
                'partial_score': 'Based on height reached (max 50), stability (max 30), and sustained motion (max 20)',
                'failure_score': 0
            }
        }
