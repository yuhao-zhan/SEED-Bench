"""
S-05: The Shelter task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """Evaluator for S-05: The Shelter task"""

    def __init__(self, terrain_bounds, environment=None):
        self.environment = environment
        self.terrain_bounds = terrain_bounds
        self.max_core_force = float(self.terrain_bounds.get("core_max_force", 150.0))
        self.MAX_STRUCTURE_HEIGHT = 7.5
        self.min_steps = 1000 # Minimum steps to evaluate success

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        core_force = self.environment.get_core_max_force()
        structure_mass = self.environment.get_structure_mass()
        max_mass = float(self.terrain_bounds.get("max_structure_mass", 300.0))
        
        failed = False
        failure_reason = None
        
        # Design constraint check (collapse)
        # The core is at y=0.5 or 1.0. If structure falls below 0.3, it's definitely a collapse.
        min_body_y = 100.0
        if self.environment._bodies:
            for body in self.environment._bodies:
                min_body_y = min(min_body_y, body.position.y)
        
        if min_body_y < 0.3: # Shelter collapsed near ground
            failed, failure_reason = True, "Shelter collapsed or fell below ground level"
        elif core_force > self.max_core_force:
            failed, failure_reason = True, f"Core protection failed: force {core_force:.1f}N > {self.max_core_force}N"
        elif structure_mass > max_mass:
            failed, failure_reason = True, f"Mass budget exceeded: {structure_mass:.1f}kg > {max_mass}kg"
            
        # Design constraint check (height)
        if not failed:
            for body in self.environment._bodies:
                if body.position.y > self.MAX_STRUCTURE_HEIGHT:
                    failed, failure_reason = True, f"Structure exceeds height limit {self.MAX_STRUCTURE_HEIGHT}m"
                    break

        is_end = (step_count >= max_steps - 1)
        can_eval_success = (step_count >= self.min_steps)
        
        success = can_eval_success and not failed
        done = failed or (is_end and can_eval_success)
        
        score = 100.0 if success else 0.0
        if not done and not failed:
            score = (min(step_count, self.min_steps) / self.min_steps) * 80.0
            
        metrics = {
            'core_force': core_force,
            'max_core_force': self.max_core_force,
            'core_x': self.environment.CORE_X if self.environment else 0,
            'core_y': self.environment.CORE_Y if self.environment else 0,
            'meteor_count': self.environment._meteor_count if self.environment else 0,
            'structure_mass': structure_mass,
            'max_mass': max_mass,
            'max_height_limit': self.MAX_STRUCTURE_HEIGHT,
            'min_body_y': min_body_y,
            'success': success,
            'failed': failed,
            'failure_reason': failure_reason
        }
        
        return done, score, metrics

    def get_task_description(self):
        return {
            'task': 'S-05: The Shelter',
            'success_criteria': {
                'protection': f'Core receives < {self.max_core_force}N force',
                'stability': 'Shelter does not collapse',
                'height_limit': f'No beam above y={self.MAX_STRUCTURE_HEIGHT}m',
                'mass_limit': f'Structure mass < {self.terrain_bounds.get("max_structure_mass", 300.0)}kg'
            }
        }
