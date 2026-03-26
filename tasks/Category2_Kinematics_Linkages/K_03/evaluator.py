"""
K-03: The Gripper task evaluation module
Defines task objectives and success criteria
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system: Defines task objectives and success criteria for K-03: The Gripper
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        # Target: object must be physically grasped and lifted (read from environment when set)
        self.min_object_height = getattr(environment, 'MIN_OBJECT_HEIGHT', 2.0) if environment else 2.0
        self.target_object_y = getattr(environment, 'TARGET_OBJECT_Y', 3.5) if environment else 3.5
        # Y-coordinate for the target line in the renderer (same as target_object_y)
        self.target_line_y = getattr(environment, 'TARGET_OBJECT_Y', 3.5) if environment else 3.5
        self.target_x = self.target_line_y  # Alias for verifier/renderer API compatibility
        self.min_simulation_time = getattr(environment, 'MIN_SIMULATION_TIME', 1.34) if environment else 1.34
        self.steps_per_eval = 10  # K_03 evaluates every 10 steps; count steps accordingly
        
        # Track gripper and object state
        self.initial_object_y = None
        self.max_object_y_reached = 0.0
        self.min_object_y_seen = float('inf')
        self.object_fell = False
        self.object_grasped = False
        self.steps_with_object_above_target = 0
        self.last_object_y = None
        self.lifting_started = False
        
        # Design constraints: read from environment instance so mutations (terrain_config) are reflected
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        try:
            self.MAX_STRUCTURE_MASS = environment.MAX_STRUCTURE_MASS
            self.BUILD_ZONE_X_MIN = environment.BUILD_ZONE_X_MIN
            self.BUILD_ZONE_X_MAX = environment.BUILD_ZONE_X_MAX
            self.BUILD_ZONE_Y_MIN = environment.BUILD_ZONE_Y_MIN
            self.BUILD_ZONE_Y_MAX = environment.BUILD_ZONE_Y_MAX
        except AttributeError as e:
            raise AttributeError(f"Environment instance missing required attribute: {e}")
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate gripper performance
        Returns: (success, score, metrics)
        """
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get object position
        object_pos = self.environment.get_object_position()
        if object_pos is None:
            return False, 0.0, {"error": "Object not found"}
        
        current_object_x, current_object_y = object_pos
        
        # Get gripper position (use agent_body if provided)
        if agent_body:
            gripper_x, gripper_y = agent_body.position.x, agent_body.position.y
        else:
            gripper_pos = self.environment.get_gripper_position()
            if gripper_pos is None:
                gripper_x, gripper_y = 5.0, 8.0  # Default position
            else:
                gripper_x, gripper_y = gripper_pos
        
        # Initialize tracking on first evaluation (main.py increments step before evaluate, so first call may be step_count=1)
        if self.initial_object_y is None:
            self.initial_object_y = current_object_y
            self.last_object_y = current_object_y
            self.min_object_y_seen = current_object_y
        
        # Track minimum object height
        if current_object_y < self.min_object_y_seen:
            self.min_object_y_seen = current_object_y
        
        # Check if object fell below minimum height (after it was lifted)
        if self.lifting_started and current_object_y < self.min_object_height:
            self.object_fell = True
        
        # Track maximum object height
        if current_object_y > self.max_object_y_reached:
            self.max_object_y_reached = current_object_y
        
        # Check if object is being lifted (y increased from initial position)
        if current_object_y > self.initial_object_y + 0.5:
            self.lifting_started = True
        # Count steps where object is at or above target (for sustained grip)
        if current_object_y >= self.target_object_y:
            self.steps_with_object_above_target += getattr(self, 'steps_per_eval', 1)
        
        # Check if object is grasped: close to any gripper body (arm/fingers) or being lifted
        distance_to_base = math.sqrt((current_object_x - gripper_x)**2 + (current_object_y - gripper_y)**2)
        if distance_to_base < 1.0:
            self.object_grasped = True
        # Also consider grasped if object is close to any gripper beam (fingers/arm)
        if not self.object_grasped and hasattr(self.environment, '_bodies'):
            for body in self.environment._bodies:
                dx = current_object_x - body.position.x
                dy = current_object_y - body.position.y
                d = math.sqrt(dx*dx + dy*dy)
                if d < 0.6:
                    self.object_grasped = True
                    break
        # Or if object is being lifted (y increased from initial)
        if current_object_y > self.initial_object_y + 0.15:
            self.object_grasped = True
        # Physical contact: grasp = gripper bodies touching object
        if hasattr(self.environment, 'get_object_contact_count'):
            num_points, num_bodies = self.environment.get_object_contact_count()
            if num_bodies > 0:
                self.object_grasped = True
        
        self.last_object_y = current_object_y
        
        # Check if successful
        reached_target = current_object_y >= self.target_object_y
        maintained_height = not self.object_fell and (not self.lifting_started or self.min_object_y_seen >= self.min_object_height)
        min_steps_hold = max(1, int(self.min_simulation_time / TIME_STEP))
        maintained_grip = self.steps_with_object_above_target >= min_steps_hold
        
        success = reached_target and maintained_height and maintained_grip and self.object_grasped
        
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
        
        # Failure condition 1: Object fell
        if self.object_fell:
            failed = True
            failure_reason = f"Object fell (minimum y={self.min_object_y_seen:.2f}m, required >={self.min_object_height}m after lifting)"
        
        # Failure condition 2: Object not lifted (timeout)
        if step_count >= max_steps and not self.lifting_started:
            failed = True
            failure_reason = "Object was not lifted (object y did not increase significantly)"
        
        height_gained = (current_object_y - self.initial_object_y) if self.initial_object_y is not None else 0.0
        min_steps_hold = max(1, int(self.min_simulation_time / TIME_STEP))

        # Calculate score (0-100)
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Partial score based on height reached and stability
            height_score = min(height_gained / 5.0, 1.0) * 50.0  # Max 50 points for height
            stability_score = 0.0
            if not self.object_fell and self.lifting_started:
                stability_score = 30.0  # 30 points for maintaining grip
            grip_score = min(self.steps_with_object_above_target / min_steps_hold, 1.0) * 20.0  # Max 20 points for sustained grip
            score = height_score + stability_score + grip_score
        
        # Contact metrics (physical grasp)
        object_contact_points = 0
        gripper_bodies_touching_object = 0
        if hasattr(self.environment, 'get_object_contact_count'):
            object_contact_points, gripper_bodies_touching_object = self.environment.get_object_contact_count()

        # Collect metrics
        metrics = {
            'gripper_x': gripper_x,
            'gripper_y': gripper_y,
            'object_x': current_object_x,
            'object_y': current_object_y,
            'target_object_y': self.target_object_y,
            'height_gained': height_gained,
            'max_object_y_reached': self.max_object_y_reached,
            'progress': min((current_object_y - self.initial_object_y) / 5.0, 1.0) * 100 if current_object_y >= self.initial_object_y else 0.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': self.MAX_STRUCTURE_MASS,
            'min_object_y_seen': self.min_object_y_seen,
            'object_fell': self.object_fell,
            'object_grasped': self.object_grasped,
            'object_contact_points': object_contact_points,
            'gripper_bodies_touching_object': gripper_bodies_touching_object,
            'steps_with_object_above_target': self.steps_with_object_above_target,
            'min_simulation_steps_required': int(self.min_simulation_time / TIME_STEP),
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
            'task': 'K-03: The Gripper',
            'description': 'Design a gripper mechanism that grasps objects and lifts them using motor rotation',
            'target_position': self.target_object_y,
            'terrain': {
                'ground': self.terrain_bounds.get('ground', {}),
            },
            'success_criteria': {
                'primary': f'Object is lifted to goldenrod line (y >= {self.target_object_y}m) and held there',
                'secondary': f'Object never falls below {self.min_object_height}m after being lifted',
                'tertiary': f'Object maintains grip at/above target for required time (~{self.min_simulation_time}s)',
            },
            'evaluation': {
                'score_range': '0-100',
                'success_score': 100,
                'partial_score': 'Based on height reached (max 50), stability (max 30), and sustained grip (max 20)',
                'failure_score': 0
            }
        }
