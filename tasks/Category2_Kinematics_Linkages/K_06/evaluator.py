"""
K-06: The Wiper task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system for K-06: The Wiper
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        self.min_removal_ratio = 0.8 # 80% removal (aligned with env 20% residual fail)
        self.min_simulation_time = 8.0 # seconds (aligned with description)
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)
        
        self.design_constraints_checked = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return (False, 0.0, {"error": "Environment not available"})
        
        initial_count = self.environment.get_initial_particle_count()
        remaining_count = self.environment.get_remaining_particle_count()
        
        if initial_count == 0:
            return (False, 0.0, {"error": "No particles found"})
            
        removal_ratio = (initial_count - remaining_count) / initial_count
        
        # Robust wiper tracking
        wiper = agent_body
        if wiper is None and self.environment._bodies:
            wiper = self.environment._bodies[0]
            
        wiper_x, wiper_y = 0.0, 0.0
        if wiper:
            wiper_x = wiper.position.x
            wiper_y = wiper.position.y

        failed = False
        failure_reason = None
        
        # Failure: Not enough particles removed by the end
        is_end = (step_count >= max_steps - 1)
        if is_end and removal_ratio < self.min_removal_ratio:
            failed = True
            failure_reason = f"Wiper failed: too many particles remaining ({remaining_count}/{initial_count}). Only {removal_ratio*100:.1f}% removed (need {self.min_removal_ratio*100:.0f}%)"
            
        # Success if reached target removal and survived minimum time
        success = removal_ratio >= self.min_removal_ratio and step_count >= self.min_simulation_steps
        
        done = failed or is_end
        
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = min(removal_ratio / self.min_removal_ratio, 1.0)
            score = progress * 70.0
            if step_count > 0:
                score += (min(step_count, self.min_simulation_steps) / self.min_simulation_steps) * 30.0
                
        metrics = {
            'wiper_x': wiper_x,
            'wiper_y': wiper_y,
            'initial_particle_count': initial_count,
            'current_particle_count': remaining_count,
            'particles_removed': initial_count - remaining_count,
            'cleaning_percentage': removal_ratio * 100.0,
            'residual_percentage': (1.0 - removal_ratio) * 100.0,
            'max_residual_percent': (1.0 - self.min_removal_ratio) * 100.0,
            'progress': progress * 100.0 if 'progress' in locals() else 0.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'min_simulation_steps_required': self.min_simulation_steps,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': getattr(self.environment, 'MAX_STRUCTURE_MASS', 15.0),
        }
        
        return done, score, metrics

    def get_task_description(self):
        return {
            'task': 'K-06: The Wiper',
            'success_criteria': {
                'removal': f'Remove {self.min_removal_ratio*100:.0f}% of particles',
                'time': f'Wipe for {self.min_simulation_time}s'
            }
        }
