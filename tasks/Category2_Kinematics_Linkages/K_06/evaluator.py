"""
K-06: The Wiper task evaluation module
Defines task objectives and success criteria
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system: Defines task objectives and success criteria for K-06: The Wiper
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        # Hard: 100% cleaning required (residual <= 0%), 12s motion, 15kg mass limit
        self.max_residual_particles_percent = 0.0   # All particles must be removed
        self.min_simulation_time = 12.0  # Must maintain motion for 12 seconds (was 8)
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)  # Steps for 8 seconds
        
        # Track wiper and particle state
        self.initial_particle_count = None
        self.steps_with_motion = 0
        self.last_particle_count = None
        
        # Design constraints
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        env_class = type(environment)
        try:
            self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', env_class.MAX_STRUCTURE_MASS)
            self.BUILD_ZONE_X_MIN = env_class.BUILD_ZONE_X_MIN
            self.BUILD_ZONE_X_MAX = env_class.BUILD_ZONE_X_MAX
            self.BUILD_ZONE_Y_MIN = env_class.BUILD_ZONE_Y_MIN
            self.BUILD_ZONE_Y_MAX = env_class.BUILD_ZONE_Y_MAX
        except AttributeError as e:
            raise AttributeError(f"Environment class {env_class.__name__} missing required constant: {e}")
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate wiper performance
        Returns: (success, score, metrics)
        """
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get particle count
        current_particle_count = self.environment.get_particle_count()
        if self.initial_particle_count is None:
            self.initial_particle_count = self.environment.get_initial_particle_count()
        
        # Get wiper position (use agent_body if provided)
        if agent_body:
            wiper_x, wiper_y = agent_body.position.x, agent_body.position.y
        else:
            wiper_pos = self.environment.get_wiper_position()
            if wiper_pos is None:
                wiper_x, wiper_y = 6.0, 4.0  # Default position
            else:
                wiper_x, wiper_y = wiper_pos
        
        # Initialize tracking on first step
        if step_count == 0:
            self.last_particle_count = current_particle_count
        
        # Track motion (check if particle count changed)
        if self.last_particle_count is not None:
            particle_change = abs(current_particle_count - self.last_particle_count)
            if particle_change > 0:  # Particles were removed
                self.steps_with_motion += 1
        self.last_particle_count = current_particle_count
        
        # Calculate cleaning percentage
        particles_removed = self.initial_particle_count - current_particle_count
        cleaning_percentage = (particles_removed / self.initial_particle_count * 100.0) if self.initial_particle_count > 0 else 0.0
        residual_percentage = (current_particle_count / self.initial_particle_count * 100.0) if self.initial_particle_count > 0 else 0.0
        
        # Check if successful: 100% particles removed AND simulation ran at least 12 seconds (wiper had time to sweep)
        cleaned_sufficiently = residual_percentage <= self.max_residual_particles_percent
        # "Maintain motion for 8 seconds" = run for at least 8 seconds (not 480 removal events; we only have 20 particles)
        maintained_motion = step_count >= self.min_simulation_steps
        
        success = cleaned_sufficiently and maintained_motion
        
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
        
        # Failure condition 1: Too many particles remaining (timeout)
        if step_count >= max_steps and residual_percentage > self.max_residual_particles_percent:
            failed = True
            failure_reason = f"Too many particles remaining ({residual_percentage:.1f}%, required <= {self.max_residual_particles_percent}%)"
        
        # Calculate score (0-100)
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Partial score based on cleaning percentage and motion (threshold 100%)
            cleaning_score = min(cleaning_percentage / 100.0, 1.0) * 70.0  # Max 70 points for cleaning
            motion_score = min(self.steps_with_motion / self.min_simulation_steps, 1.0) * 30.0  # Max 30 points for sustained motion
            score = cleaning_score + motion_score
        
        # Collect metrics
        metrics = {
            'wiper_x': wiper_x,
            'wiper_y': wiper_y,
            'initial_particle_count': self.initial_particle_count,
            'current_particle_count': current_particle_count,
            'particles_removed': particles_removed,
            'cleaning_percentage': cleaning_percentage,
            'residual_percentage': residual_percentage,
            'max_residual_percent': self.max_residual_particles_percent,
            'progress': cleaning_percentage,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': self.MAX_STRUCTURE_MASS,
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
            'task': 'K-06: The Wiper',
            'description': 'Design a wiper mechanism that cleans particles from a glass surface using motor rotation',
            'target_cleaning': f'At least {100 - self.max_residual_particles_percent:.0f}% particles removed (residual <= {self.max_residual_particles_percent}%)',
            'terrain': {
                'glass': self.terrain_bounds.get('glass', {}),
            },
            'success_criteria': {
                'primary': f'At least {100 - self.max_residual_particles_percent:.0f}% of particles removed (residual <= {self.max_residual_particles_percent}%)',
                'secondary': 'Wiper covers glass surface area effectively',
                'tertiary': 'Wiper maintains motion for at least 8 seconds',
            },
            'evaluation': {
                'score_range': '0-100',
                'success_score': 100,
                'partial_score': 'Based on cleaning percentage (max 70) and sustained motion (max 30)',
                'failure_score': 0
            }
        }
