"""
K-05: The Lifter task evaluation module
Defines task objectives and success criteria.

Design constants (single source of truth; keep in sync with prompt, feedback, environment):
- Ground top at y=1.0m; object starts at y=1.8m; target y=9.0m (8m above ground).
- Sustain: object must stay at y>=9m for 3s (180 steps), and not sliding (velocity_y >= -0.4 m/s).
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP

# --- Task design constants (align with prompt.py, feedback.py, environment.py) ---
GROUND_Y = 1.0
OBJECT_START_Y = 1.8
TARGET_OBJECT_Y = 9.0
LIFT_HEIGHT_FROM_GROUND = 8.0   # target - ground = 9 - 1
MIN_SUSTAIN_S = 3.0
SUSTAIN_VELOCITY_THRESHOLD = -0.4  # m/s; steps count only when object_velocity_y >= this (no sliding down)


class Evaluator:
    """
    Evaluation system: Defines task objectives and success criteria for K-05: The Lifter
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        # Target: object must be lifted to at least target_object_y from ground (y>=target_object_y); mutated tasks can override via environment
        self.start_object_y = getattr(environment, 'OBJECT_START_Y', OBJECT_START_Y)
        self.start_object_x = getattr(environment, 'OBJECT_START_X', 4.0)
        self.target_object_y = getattr(environment, 'target_object_y', None) if environment else None
        if self.target_object_y is None:
            self.target_object_y = TARGET_OBJECT_Y
        
        # Calculate lift height dynamically
        self.lift_height_from_ground = self.target_object_y - GROUND_Y
        
        self.min_simulation_time = getattr(environment, 'min_sustain_s', None) if environment else None
        if self.min_simulation_time is None:
            self.min_simulation_time = MIN_SUSTAIN_S
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)
        
        # Track lifter and object state
        self.initial_object_y = None
        self.max_object_y_reached = 0.0
        self.steps_with_object_above_target = 0
        self.last_object_y = None
        self.lifting_started = False
        self.initial_joint_count = 0
        self.structure_broken = False
        
        # Design constraints
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        try:
            self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', 60.0)
            self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', 0.0)
            self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', 8.0)
            self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', 1.0)
            self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', 12.0)
            self.lifting_threshold_m = getattr(environment, 'LIFTING_THRESHOLD_M', 0.5)
        except Exception as e:
            raise AttributeError(f"Environment missing required constants: {e}")
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate lifter performance
        Returns: (success, score, metrics)
        """
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get object position
        object_pos = self.environment.get_object_position()
        if object_pos is None:
            return False, 0.0, {"error": "Object not found"}
        
        current_object_x, current_object_y = object_pos
        
        # Get lifter position (use agent_body if provided)
        if agent_body:
            lifter_x, lifter_y = agent_body.position.x, agent_body.position.y
        else:
            lifter_pos = self.environment.get_lifter_position()
            if lifter_pos is None:
                lifter_x, lifter_y = 4.0, 2.0  # Default position
            else:
                lifter_x, lifter_y = lifter_pos
        
        # Initialize tracking on first evaluation (step_count may be 0 or 1 depending on loop order)
        if self.initial_object_y is None:
            self.initial_object_y = current_object_y
            self.last_object_y = current_object_y
            self.initial_joint_count = len(self.environment._joints)
        
        # Track maximum object height
        if current_object_y > self.max_object_y_reached:
            self.max_object_y_reached = current_object_y
        
        # Check if object is being lifted (y increased from initial position by at least lifting_threshold_m)
        if current_object_y > self.initial_object_y + self.lifting_threshold_m:
            self.lifting_started = True
        if self.max_object_y_reached > self.initial_object_y + self.lifting_threshold_m:
            self.lifting_started = True  # ever reached above initial + threshold
        # Only count sustain when object is at target height AND not falling (robust: no "sliding down" counting)
        obj_vel_y = 0.0
        if self.environment._object_to_lift:
            obj_vel_y = self.environment._object_to_lift.linearVelocity.y
        if current_object_y >= self.target_object_y and obj_vel_y >= SUSTAIN_VELOCITY_THRESHOLD:
            self.steps_with_object_above_target += 1
        
        # Check structure integrity (count joints)
        current_joint_count = len(self.environment._joints)
        if current_joint_count < self.initial_joint_count:
            self.structure_broken = True
        
        self.last_object_y = current_object_y
        
        # Check if successful
        reached_target = current_object_y >= self.target_object_y
        maintained_structure = not self.structure_broken
        maintained_height = self.steps_with_object_above_target >= self.min_simulation_steps
        
        success = reached_target and maintained_structure and maintained_height
        
        # Check if failed
        failed = False
        failure_reason = None
        
        # Failure condition 0: Check design constraints (on first evaluation)
        if not self.design_constraints_checked:
            constraint_violations = self._check_design_constraints()
            if constraint_violations:
                failed = True
                failure_reason = "Design constraint violated: " + "; ".join(constraint_violations)
            self.design_constraints_checked = True
        
        # Failure condition 1: Structure broke
        if self.structure_broken:
            failed = True
            failure_reason = "Lifter structure integrity lost (joints broke under load)"
        
        # Failure condition 2: Object not lifted (timeout)
        if step_count >= max_steps and not self.lifting_started:
            failed = True
            failure_reason = "Object was not lifted (object y did not increase significantly)"
        
        # Calculate score (0-100)
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Partial score based on height reached and stability
            height_gained = current_object_y - self.initial_object_y
            height_score = min(height_gained / (self.target_object_y - self.start_object_y), 1.0) * 50.0  # Max 50 for height
            structure_score = 0.0
            if not self.structure_broken:
                structure_score = 30.0  # 30 points for maintaining structure
            # If object was never meaningfully lifted, do not reward structure (mutated tasks: harder scoring)
            if self.max_object_y_reached < self.initial_object_y + self.lifting_threshold_m:
                structure_score = 0.0
            height_maintenance_score = min(self.steps_with_object_above_target / self.min_simulation_steps, 1.0) * 20.0  # Max 20 points for sustained height
            score = max(0.0, height_score + structure_score + height_maintenance_score)

        
        obj_vel_x = obj_vel_y = 0.0
        if self.environment._object_to_lift:
            obj_vel_x = self.environment._object_to_lift.linearVelocity.x
            obj_vel_y = self.environment._object_to_lift.linearVelocity.y
        # Collect metrics
        metrics = {
            'lifter_x': lifter_x,
            'lifter_y': lifter_y,
            'object_x': current_object_x,
            'object_y': current_object_y,
            'object_velocity_x': obj_vel_x,
            'object_velocity_y': obj_vel_y,
            'target_object_y': self.target_object_y,
            'height_gained': height_gained if 'height_gained' in locals() else (current_object_y - self.initial_object_y),
            'max_object_y_reached': self.max_object_y_reached,
            'progress': min((current_object_y - self.initial_object_y) / (self.target_object_y - self.start_object_y), 1.0) * 100 if current_object_y >= self.initial_object_y else 0.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': self.MAX_STRUCTURE_MASS,
            'structure_broken': self.structure_broken,
            'joint_count': current_joint_count,
            'steps_with_object_above_target': self.steps_with_object_above_target,
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
        """Return task description (aligned with design constants and prompt)."""
        return {
            'task': 'K-05: The Lifter',
            'description': 'Design a scissor lift mechanism that lifts objects vertically using motor rotation',
            'target_position': self.target_object_y,
            'ground_y': GROUND_Y,
            'object_start_y': OBJECT_START_Y,
            'lift_height_from_ground': self.lift_height_from_ground,
            'terrain': {
                'ground': self.terrain_bounds.get('ground', {}),
            },
            'success_criteria': {
                'primary': f'Object is lifted to height of at least {self.lift_height_from_ground}m from ground (y >= {self.target_object_y}m)',
                'secondary': 'Lifter structure remains intact (no joints break)',
                'tertiary': f'Object maintains height for at least {self.min_simulation_time}s, and not sliding (velocity_y >= {SUSTAIN_VELOCITY_THRESHOLD} m/s)',
            },
            'evaluation': {
                'score_range': '0-100',
                'success_score': 100,
                'partial_score': 'Based on height reached (max 50), structure integrity (max 30), and sustained height (max 20)',
                'failure_score': 0
            }
        }
